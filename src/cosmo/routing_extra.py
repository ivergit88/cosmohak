"""Дополнительные стратегии маршрутизации: A* с гео-эвристикой и жадная географическая.

A*  — тот же оптимальный маршрут по суммарной длине, что и у базовой стратегии,
      но раскрывает меньше узлов: эвристика h(u) = |u − шлюз| (Earth-fixed кадр)
      допустима и согласована по неравенству треугольника, поэтому первое
      извлечение шлюза из кучи даёт оптимум.
Жадная — реальный подход из LEO-протоколов: на каждом шаге выбирается сосед,
      ближайший к шлюзу; быстро (O(шаги × степень)), но может застрять в
      локальном минимуме и не найти существующий маршрут — сообщаем честно.

Обе функции возвращают (RouteResult, число раскрытых узлов) — метрика
эффективности для сравнения стратегий.
"""
from __future__ import annotations

import heapq
import math

from .graph import LinkGraph
from .models import (
    STATUS_CONNECTED,
    STATUS_ISL_DISCONNECTED,
    STATUS_NO_VISIBLE_SAT,
)
from .routing import RouteResult, _gateway_state, _no_route_result


def _dist3(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _gateway_positions(g: LinkGraph) -> dict[str, tuple[float, float, float]]:
    return {gw: g.positions[gw] for gw in g.gateways if gw in g.positions}


def find_route_astar(g: LinkGraph, client_id: str,
                     forbidden: frozenset[str] = frozenset()) -> tuple[RouteResult, int]:
    """A* по суммарной длине линий: оптимум = min_distance, раскрытий меньше."""
    client_links = [lk for lk in g.client_links.get(client_id, ()) if lk[0] not in forbidden]
    if not client_links:
        return (RouteResult((), STATUS_NO_VISIBLE_SAT, "NO_VISIBLE_CLIENT_SATELLITE",
                            "нет видимого спутника"), 0)

    usable, fail_code, fail_reason = _gateway_state(g)
    if not usable:
        return _no_route_result(g, fail_code, fail_reason), 0

    gw_pos = _gateway_positions(g)

    def h(node: str) -> float:
        p = g.positions.get(node)
        if p is None:
            return 0.0
        return min(_dist3(p, g.positions[gw]) for gw in gw_pos)

    heap: list[tuple[float, float, int, tuple[str, ...]]] = []
    for sat, dist in client_links:
        if sat in forbidden:
            continue
        heapq.heappush(heap, (dist + h(sat), dist, 1, (client_id, sat)))

    best_g: dict[str, float] = {}
    expanded = 0
    while heap:
        f, g_cost, _hops, path = heapq.heappop(heap)
        node = path[-1]
        expanded += 1
        if node in g.gateways:
            return (RouteResult(path, STATUS_CONNECTED, "", ""), expanded)
        if g_cost > best_g.get(node, float("inf")):
            continue
        best_g[node] = g_cost
        for neighbor, w in g.sat_adj.get(node, ()):
            if neighbor in forbidden:
                continue
            ng = g_cost + w
            if ng < best_g.get(neighbor, float("inf")):
                heapq.heappush(heap, (ng + h(neighbor), ng, len(path), path + (neighbor,)))
                best_g[neighbor] = ng  # нижняя граница для отсева
        for gw, links in g.gateway_links.items():
            for sat, w in links:
                if sat == node:
                    ng = g_cost + w
                    if ng < best_g.get(gw, float("inf")):
                        heapq.heappush(heap, (ng, ng, len(path), path + (gw,)))
                        best_g[gw] = ng
    return _no_route_result(g, STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED"), expanded


def find_route_greedy(g: LinkGraph, client_id: str,
                      forbidden: frozenset[str] = frozenset()) -> tuple[RouteResult, int]:
    """Жадная географическая маршрутизация: сосед, ближайший к шлюзу."""
    client_links = [lk for lk in g.client_links.get(client_id, ()) if lk[0] not in forbidden]
    if not client_links:
        return (RouteResult((), STATUS_NO_VISIBLE_SAT, "NO_VISIBLE_CLIENT_SATELLITE",
                            "нет видимого спутника"), 0)

    usable, fail_code, fail_reason = _gateway_state(g)
    if not usable:
        return _no_route_result(g, fail_code, fail_reason), 0

    gw_pos = _gateway_positions(g)

    def d_to_gw(node: str) -> float:
        p = g.positions.get(node)
        return min(_dist3(p, g.positions[gw]) for gw in gw_pos) if p else float("inf")

    first = min(client_links, key=lambda lk: lk[1])
    cur = first[0]
    path = [client_id, cur]
    visited = {client_id, cur}
    expanded = 0
    while len(path) <= 64:
        expanded += 1
        for gw, links in g.gateway_links.items():
            for sat, _w in links:
                if sat == cur:
                    path.append(gw)
                    return (RouteResult(tuple(path), STATUS_CONNECTED, "", ""), expanded)
        neighbors = [(n, w) for n, w in g.sat_adj.get(cur, ()) if n not in visited and n not in forbidden]
        if not neighbors:
            return (RouteResult((), STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED",
                                "жадная маршрутизация застряла в локальном минимуме"), expanded)
        nxt, _w = min(neighbors, key=lambda nw: d_to_gw(nw[0]))
        visited.add(nxt)
        path.append(nxt)
        cur = nxt
    return (RouteResult((), STATUS_ISL_DISCONNECTED, "ISL_NETWORK_DISCONNECTED",
                        "жадная маршрутизация превысила лимит шагов"), expanded)
