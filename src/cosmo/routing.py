"""Маршрутизация в динамической сети.

Стратегии:
A. min_distance (по умолчанию) — взвешенный поиск кратчайшего пути по
   суммарной геометрической длине доступных линий: релаксация по ключу
   (длина км, число рёбер, путь), полностью детерминирована.
B. min_hops (baseline) — BFS «минимум рёбер» с лексикографическим
   tie-break (обход соседей по отсортированным ID, FIFO); первое
   обнаружение узла даёт лексикографически наименьший кратчайший путь.
   Достижимость (availability) у стратегий совпадает — проверено тестом.

Дополнительно: резервный путь (node-disjoint к основному по
внутренним спутникам) и строгая проверка допустимости пути.

Наземные узлы не ретранслируют: client — только источник, gateway —
только терминал; внутренними узлами могут быть только спутники.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .graph import LinkGraph
from .models import (
    STATUS_CONNECTED,
    STATUS_GATEWAY_OFFLINE,
    STATUS_ISL_DISCONNECTED,
    STATUS_NO_GATEWAY_CONTACT,
    STATUS_NO_VISIBLE_SAT,
    STRATEGY_ASTAR,
    STRATEGY_GREEDY,
    STRATEGY_MIN_DISTANCE,
    STRATEGY_MIN_HOPS,
)

REASON_LABELS: dict[str, str] = {
    "NO_VISIBLE_CLIENT_SATELLITE": "У пункта нет видимого активного спутника",
    "GATEWAY_UNAVAILABLE": "Шлюз находится в периоде недоступности",
    "NO_GATEWAY_CONTACT": "Онлайн-шлюз не видит ни одного активного спутника",
    "ISL_NETWORK_DISCONNECTED": "Пункт и шлюз видят спутники, но межспутниковая сеть не связывает их",
}


@dataclass(frozen=True)
class RouteResult:
    """Результат поиска маршрута для одного клиента на одном отсчёте."""

    path: tuple[str, ...]  # пустой кортеж, если маршрута нет
    status_code: int  # STATUS_* из models
    reason: str  # "" или код причины (см. REASON_LABELS)
    detail: str  # человекочитаемое пояснение (ru)

    @property
    def connected(self) -> bool:
        return self.status_code == STATUS_CONNECTED

    @property
    def hops(self) -> int | None:
        """Число рёбер маршрута, включая две наземные линии."""
        return len(self.path) - 1 if self.path else None


def _no_route_result(g: LinkGraph, code: int, reason: str) -> RouteResult:
    """Формирует результат «маршрута нет» с пояснением по шлюзам."""
    detail = REASON_LABELS[reason]
    if g.gateways:
        offline = [gw for gw in g.gateways if gw in g.offline_gateways]
        no_contact = [
            gw for gw in g.gateways
            if gw not in g.offline_gateways and not g.gateway_links.get(gw)
        ]
        usable = [gw for gw in g.gateways if gw not in offline and gw not in no_contact]
        parts = []
        if offline:
            parts.append("недоступны: " + ", ".join(offline))
        if no_contact:
            parts.append("без видимых спутников: " + ", ".join(no_contact))
        if usable:
            parts.append("готовы: " + ", ".join(usable))
        if parts:
            detail += " [" + "; ".join(parts) + "]"
    return RouteResult((), code, reason, detail)


def _gateway_state(g: LinkGraph) -> tuple[list[str], int, str]:
    """Классификация шлюзов: (годные, код отказа, пояснение).

    Код отказа: GATEWAY_UNAVAILABLE, если все шлюзы в outage;
    NO_GATEWAY_CONTACT, если онлайн-шлюзы не видят спутников.
    """
    offline = [gw for gw in g.gateways if gw in g.offline_gateways]
    if offline and len(offline) == len(g.gateways):
        return [], STATUS_GATEWAY_OFFLINE, "GATEWAY_UNAVAILABLE"
    usable = [
        gw for gw in g.gateways
        if gw not in g.offline_gateways and g.gateway_links.get(gw)
    ]
    if not usable:
        return [], STATUS_NO_GATEWAY_CONTACT, "NO_GATEWAY_CONTACT"
    return usable, 0, ""


def find_route_min_hops(g: LinkGraph, client_id: str, forbidden: frozenset[str] = frozenset()) -> RouteResult:
    """Минимально-хоповый детерминированный маршрут (BFS).

    forbidden — внутренние спутники, которые запрещено использовать
    (используется при поиске резервного пути).
    """
    client_links = [link for link in g.client_links.get(client_id, ()) if link[0] not in forbidden]
    if not client_links:
        return RouteResult(
            (), STATUS_NO_VISIBLE_SAT, "NO_VISIBLE_CLIENT_SATELLITE",
            REASON_LABELS["NO_VISIBLE_CLIENT_SATELLITE"],
        )

    usable, fail_code, fail_reason = _gateway_state(g)
    if not usable:
        return _no_route_result(g, fail_code, fail_reason)

    usable_set = set(usable)
    # Обратный индекс: спутник -> отсортированные годные шлюзы, которые его видят.
    gw_by_sat: dict[str, list[str]] = {}
    for gw in usable:
        for sat, _dist in g.gateway_links.get(gw, ()):
            gw_by_sat.setdefault(sat, []).append(gw)
    for sats in gw_by_sat.values():
        sats.sort()

    visited = {client_id}
    parent: dict[str, str] = {}
    order: dict[str, int] = {}  # порядок обнаружения == лексикографический порядок путей
    queue: deque[str] = deque()
    counter = 0
    for sat, _dist in client_links:  # уже отсортированы по ID
        if sat not in visited:
            visited.add(sat)
            parent[sat] = client_id
            order[sat] = counter
            counter += 1
            queue.append(sat)

    best_goal: tuple[int, int, str, str] | None = None  # (total_hops, order_of_sat, sat, gateway)
    dist: dict[str, int] = {}
    while queue:
        node = queue.popleft()
        node_dist = _dist_via(parent, node, client_id)
        dist[node] = node_dist
        for neighbor, _w in g.sat_adj.get(node, ()):  # отсортировано по ID
            if neighbor in visited or neighbor in forbidden:
                continue
            visited.add(neighbor)
            parent[neighbor] = node
            order[neighbor] = counter
            counter += 1
            queue.append(neighbor)
        for gw in gw_by_sat.get(node, ()):
            key = (node_dist + 1, order[node], node, gw)
            if best_goal is None or key < best_goal:
                best_goal = key

    if best_goal is None:
        return _no_route_result(g, STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED")

    _total, _ord, sat, gateway = best_goal
    tail = [sat]
    while tail[-1] != client_id:
        tail.append(parent[tail[-1]])
    tail.reverse()  # tail = [client_id, ..., sat]
    path = (*tail, gateway)
    return RouteResult(path, STATUS_CONNECTED, "", "")


def _dist_via(parent: dict[str, str], node: str, root: str) -> int:
    """Дистанция в рёбрах от root до node по дереву родителей."""
    d = 0
    cur = node
    while cur != root:
        cur = parent[cur]
        d += 1
    return d


def find_route_min_distance(g: LinkGraph, client_id: str, forbidden: frozenset[str] = frozenset()) -> RouteResult:
    """Маршрут с минимальной суммарной геометрической длиной (км).

    Ключ пути: (сумма distance_km, число рёбер, последовательность ID) —
    лексикографическое сравнение кортежей даёт полностью детерминированный
    выбор при равной длине. Релаксация повторяется до стабилизации.
    """
    client_links = [link for link in g.client_links.get(client_id, ()) if link[0] not in forbidden]
    if not client_links:
        return RouteResult(
            (), STATUS_NO_VISIBLE_SAT, "NO_VISIBLE_CLIENT_SATELLITE",
            REASON_LABELS["NO_VISIBLE_CLIENT_SATELLITE"],
        )

    usable, fail_code, fail_reason = _gateway_state(g)
    if not usable:
        return _no_route_result(g, fail_code, fail_reason)

    best: dict[str, tuple[float, int, tuple[str, ...]]] = {}
    for sat, dist in client_links:
        key = (dist, 1, (client_id, sat))
        if sat not in best or key < best[sat]:
            best[sat] = key
    for _ in range(max(len(g.sat_ids), 1)):  # веса > 0: циклы не улучшают ключ
        changed = False
        for node in sorted(best):
            cost, hops, path = best[node]
            for neighbor, w in g.sat_adj.get(node, ()):
                if neighbor in forbidden:
                    continue
                cand = (cost + w, hops + 1, path + (neighbor,))
                if neighbor not in best or cand < best[neighbor]:
                    best[neighbor] = cand
                    changed = True
        if not changed:
            break

    goal: tuple[float, int, tuple[str, ...]] | None = None
    for gw in usable:
        for sat, dist in g.gateway_links.get(gw, ()):
            if sat not in best:
                continue
            cost, hops, path = best[sat]
            cand = (cost + dist, hops + 1, path + (gw,))
            if goal is None or cand < goal:
                goal = cand
    if goal is None:
        return _no_route_result(g, STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED")
    return RouteResult(goal[2], STATUS_CONNECTED, "", "")


def find_route(g: LinkGraph, client_id: str, strategy: str = STRATEGY_MIN_DISTANCE) -> RouteResult:
    """Диспетчер стратегии маршрутизации.

    По умолчанию — взвешенный поиск кратчайшего пути по суммарной
    геометрической длине (релаксация с детерминированным tie-break):
    маршрут опирается на реальные расстояния модели, а не только на число
    рёбер. BFS «минимум переходов» — baseline. Достижимость (availability)
    у стратегий совпадает.
    """
    if strategy == STRATEGY_MIN_DISTANCE:
        return find_route_min_distance(g, client_id)
    if strategy == STRATEGY_ASTAR:
        from .routing_extra import find_route_astar
        return find_route_astar(g, client_id)[0]
    if strategy == STRATEGY_GREEDY:
        from .routing_extra import find_route_greedy
        return find_route_greedy(g, client_id)[0]
    return find_route_min_hops(g, client_id)


def find_backup_route(g: LinkGraph, client_id: str, primary: tuple[str, ...]) -> RouteResult:
    """Резервный путь, не пересекающийся с основным по внутренним спутникам.

    Клиент и шлюз могут совпадать с основным маршрутом. Если основной
    маршрут отсутствует, резервный не ищется.
    """
    if not primary:
        return RouteResult((), STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED", "Нет основного маршрута")
    forbidden = frozenset(primary[1:-1])
    return find_route_min_hops(g, client_id, forbidden)


def route_distance_km(g: LinkGraph, path: tuple[str, ...]) -> float | None:
    """Суммарная геометрическая длина маршрута по расстояниям рёбер snapshot."""
    if len(path) < 2:
        return None
    total = 0.0
    for a, b in zip(path, path[1:]):
        candidates = [w for nb, w in g.sat_adj.get(a, ()) if nb == b]
        candidates += [w for nb, w in g.sat_adj.get(b, ()) if nb == a]
        if a in g.client_links:
            candidates += [w for nb, w in g.client_links[a] if nb == b]
        if b in g.client_links:
            candidates += [w for nb, w in g.client_links[b] if nb == a]
        if a in g.gateway_links:
            candidates += [w for nb, w in g.gateway_links[a] if nb == b]
        if b in g.gateway_links:
            candidates += [w for nb, w in g.gateway_links[b] if nb == a]
        if not candidates:
            return None
        total += candidates[0]
    return total


def validate_path(
    snapshot: dict[str, Any],
    scenario: dict[str, Any],
    client_id: str,
    path: tuple[str, ...] | list[str],
) -> list[str]:
    """Строгая проверка допустимости маршрута; возвращает список нарушений.

    Проверяются: источник — client; терминал — gateway; внутренние узлы —
    только спутники; каждое звено существует в snapshot.edges; все
    спутники пути активны; шлюз вне gateway_outage; отсутствие циклов.
    """
    if not path:
        return []  # отсутствие маршрута — допустимое состояние (см. причину отдельно)
    problems: list[str] = []
    roles = {g["id"]: g["role"] for g in scenario["ground_sites"]}
    t = snapshot["t_s"]
    if roles.get(path[0]) != "client" or path[0] != client_id:
        problems.append(f"первый узел {path[0]} не является искомым client {client_id}")
    if roles.get(path[-1]) != "gateway":
        problems.append(f"последний узел {path[-1]} не является gateway")
    active = {s["id"]: s["active"] for s in snapshot["satellites"]}
    for node in path[1:-1]:
        if node not in active:
            problems.append(f"внутренний узел {node} не является спутником")
        elif not active[node]:
            problems.append(f"спутник {node} неактивен в момент t={t}")
    if len(set(path)) != len(path):
        problems.append("маршрут содержит циклы (повторяющиеся узлы)")
    edge_set = {frozenset((e[0], e[1])) for e in snapshot["edges"]}  # контакты двунаправленные
    for a, b in zip(path, path[1:]):
        if frozenset((a, b)) not in edge_set:
            problems.append(f"звено {a} -> {b} отсутствует в snapshot.edges при t={t}")
    offline = {
        f["gateway_id"]
        for f in scenario.get("gateway_outages", [])
        if f["start_s"] <= t < f["end_s"]
    }
    if path[-1] in offline:
        problems.append(f"шлюз {path[-1]} находится в периоде недоступности при t={t}")
    return problems
