"""Анализ устойчивости: критичность спутников и влияние отказов.

Критичность считается БЕЗ пересчёта орбитальной геометрии: отказ
спутника лишь удаляет узел и его рёбра из графа каждого отсчёта.
Ключевая оптимизация: если основной маршрут клиента на отсчёте не
содержит исключаемый спутник, маршрут остаётся допустимым и клиент
остаётся подключённым; повторный BFS запускается только для тех
(отсчёт, клиент), где спутник входил в основной маршрут.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

from .graph import LinkGraph
from .models import STATUS_CONNECTED, STATUS_ISL_DISCONNECTED, deep_copy
from .routing import find_route_min_hops
from .simulation import SimulationResult, snapshot_at


@dataclass(frozen=True)
class CriticalityRow:
    """Показатель влияния одного спутника на устойчивость сети."""

    satellite_id: str
    usage_count: int  # число отсчётов, где спутник в чьём-то основном маршруте
    delta_min_availability: float  # падение MIN доступности по клиентам
    delta_mean_availability: float  # падение MEAN доступности
    delta_worst_outage_s: int  # рост худшего максимального перерыва
    affected_clients: tuple[str, ...]
    ticks_made_unavailable: int  # суммарное число потерянных (клиент, отсчёт)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _reachable_without(g: LinkGraph, client_id: str, forbidden: frozenset[str]) -> bool:
    """Существует ли допустимый маршрут без перечисленных спутников (BFS достижимости)."""
    if not any(sat not in forbidden for sat, _ in g.client_links.get(client_id, ())):
        return False
    usable = {
        gw for gw in g.gateways
        if gw not in g.offline_gateways and g.gateway_links.get(gw)
    }
    if not usable:
        return False
    gw_by_sat: set[str] = set()
    for gw in usable:
        for sat, _d in g.gateway_links.get(gw, ()):
            if sat not in forbidden:
                gw_by_sat.add(sat)
    visited = set()
    queue: deque[str] = deque()
    for sat, _dist in g.client_links.get(client_id, ()):
        if sat not in forbidden and sat not in visited:
            visited.add(sat)
            queue.append(sat)
    while queue:
        node = queue.popleft()
        if node in gw_by_sat:
            return True
        for neighbor, _w in g.sat_adj.get(node, ()):
            if neighbor not in visited and neighbor not in forbidden:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


def criticality_analysis(
    scenario: dict,
    baseline: SimulationResult,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[CriticalityRow]:
    """Ранжирует спутники по влиянию на доступность (виртуальный отказ на весь горизонт).

    Геометрия не пересчитывается: один проход по отсчётам, граф каждого
    отсчёта строится один раз. Если основной маршрут клиента не содержит
    исключаемый спутник, маршрут остаётся допустимым; повторный BFS
    запускается только для спутников из текущего маршрута.
    Ранжирование: по падению MIN доступности, затем по росту худшего
    перерыва, затем по числу потерянных отсчётов.
    """
    sats = list(baseline.sat_ids)
    clients = list(baseline.clients)
    ticks = list(baseline.ticks)
    step_s = ticks[1] - ticks[0] if len(ticks) > 1 else 1

    base_avail = {c: baseline.metrics[c].availability_fraction for c in clients}
    base_outage = {c: baseline.metrics[c].max_outage_s for c in clients}
    base_min = min(base_avail.values())
    base_mean = sum(base_avail.values()) / len(base_avail)
    base_worst = max(base_outage.values())

    lost: dict[str, dict[str, list[int]]] = {s: {c: [] for c in clients} for s in sats}
    usage: dict[str, int] = {s: 0 for s in sats}

    for tick_idx, t in enumerate(ticks):
        _snap, graph = snapshot_at(scenario, t)
        for client_id in clients:
            s = baseline.series[client_id]
            if s.statuses[tick_idx] != STATUS_CONNECTED:
                continue
            path = s.paths[tick_idx]
            in_path = [sat for sat in path[1:-1] if sat in usage]
            for sat in in_path:
                usage[sat] += 1
            for sat in in_path:
                route = find_route_min_hops(graph, client_id, frozenset((sat,)))
                if not route.connected:
                    lost[sat][client_id].append(tick_idx)
        if progress_cb is not None:
            progress_cb(tick_idx + 1, len(ticks))

    rows: list[CriticalityRow] = []
    for sat_id in sats:
        lost_map = lost[sat_id]
        if not any(lost_map.values()) and usage[sat_id] == 0:
            rows.append(
                CriticalityRow(
                    satellite_id=sat_id, usage_count=0,
                    delta_min_availability=0.0, delta_mean_availability=0.0,
                    delta_worst_outage_s=0, affected_clients=(), ticks_made_unavailable=0,
                )
            )
            continue
        new_avail = {
            c: base_avail[c] - len(lost_map[c]) / len(ticks) for c in clients
        }
        delta_min = base_min - min(new_avail.values())
        delta_mean = base_mean - sum(new_avail.values()) / len(new_avail)
        ticks_lost_total = sum(len(v) for v in lost_map.values())
        affected = tuple(c for c in clients if lost_map[c])
        # новый худший перерыв: базовые перерывы + потерянные отсчёты
        new_worst = base_worst
        for c in clients:
            if not lost_map[c]:
                continue
            statuses = baseline.series[c].statuses
            lost_set = set(lost_map[c])
            merged = [
                STATUS_ISL_DISCONNECTED if i in lost_set else st
                for i, st in enumerate(statuses)
            ]
            worst = _longest_disconnected_s(merged, step_s)
            new_worst = max(new_worst, worst)
        rows.append(
            CriticalityRow(
                satellite_id=sat_id,
                usage_count=usage[sat_id],
                delta_min_availability=delta_min,
                delta_mean_availability=delta_mean,
                delta_worst_outage_s=max(0, new_worst - base_worst),
                affected_clients=affected,
                ticks_made_unavailable=ticks_lost_total,
            )
        )
    rows.sort(key=lambda r: (-r.delta_min_availability, -r.delta_worst_outage_s, -r.ticks_made_unavailable))
    return rows


def _longest_disconnected_s(statuses: list[int], step_s: int) -> int:
    """Максимальная серия подряд идущих отсчётов без маршрута, секунд."""
    best = cur = 0
    for st in statuses:
        if st != STATUS_CONNECTED:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best * step_s


def apply_failure_impact(
    scenario: dict,
    baseline: SimulationResult,
    satellite_id: str,
    start_s: int,
    end_s: int,
) -> tuple[dict, "SimulationResult"]:
    """Добавляет отказ спутника в копию сценария и пересчитывает (полная сетка)."""
    modified = deep_copy(scenario)
    modified.setdefault("failures", []).append(
        {"satellite_id": satellite_id, "start_s": int(start_s), "end_s": int(end_s)}
    )
    from .simulation import simulate_scenario  # локальный импорт против цикла

    return modified, simulate_scenario(modified, strategy=baseline.strategy)


def reason_summary(sim: SimulationResult) -> dict[str, int]:
    """Сколько отсчётов каждой причины по всем клиентам (для обзора устойчивости)."""
    from .models import STATUS_LABELS

    summary: dict[str, int] = {}
    for client_id in sim.clients:
        for code in sim.series[client_id].statuses:
            if code != STATUS_CONNECTED:
                label = STATUS_LABELS.get(code, str(code))
                summary[label] = summary.get(label, 0) + 1
    return dict(sorted(summary.items(), key=lambda kv: -kv[1]))
