"""Сквозное моделирование сценария на расчётной сетке.

simulate_scenario() один раз вычисляет для каждого отсчёта:
- состояние сети (официальный geometry.snapshot);
- маршруты всех клиентов выбранной стратегии (+ резервные пути);
- статус/причину для каждого клиента;
- сводные метрики.

Результат иммутабелен и пригоден для кэширования (все поля —
примитивы, кортежи и dataclasses).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from . import geometry_adapter
from .graph import LinkGraph, build_link_graph
from .metrics import ClientMetrics, GlobalMetrics, compute_client_metrics, compute_global_metrics
from .models import (
    STATUS_CONNECTED,
    STRATEGY_MIN_DISTANCE,
    clients_of,
    gateways_of,
    satellite_ids,
)
from .routing import RouteResult, find_backup_route, find_route, route_distance_km, validate_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClientSeries:
    """Временные ряды одного клиента по всем отсчётам."""

    client_id: str
    statuses: tuple[int, ...]  # коды STATUS_*
    reasons: tuple[str, ...]  # коды причин ("" если маршрут есть)
    details: tuple[str, ...]
    visible: tuple[bool, ...]  # виден ли хотя бы один активный спутник
    paths: tuple[tuple[str, ...], ...]
    hops: tuple[int | None, ...]
    distances: tuple[float | None, ...]
    backup_paths: tuple[tuple[str, ...], ...]  # пустой кортеж = резерва нет

    def connected_flags(self) -> list[bool]:
        return [s == STATUS_CONNECTED for s in self.statuses]


@dataclass(frozen=True)
class SimulationResult:
    """Полный результат моделирования сценария."""

    scenario: dict[str, Any]
    strategy: str
    ticks: tuple[int, ...]
    clients: tuple[str, ...]
    gateways: tuple[str, ...]
    sat_ids: tuple[str, ...]
    series: dict[str, ClientSeries]
    metrics: dict[str, ClientMetrics]
    global_metrics: GlobalMetrics
    active_counts: tuple[int, ...]  # число активных спутников на каждом отсчёте
    edge_counts: tuple[int, ...]
    validation_problems: tuple[str, ...]  # проблемы допустимости маршрутов (debug)

    def step_s(self) -> int:
        return int(self.scenario["environment"]["step_s"])

    def tick_at(self, t_s: int) -> int:
        """Индекс отсчёта по времени: ближайший нижний дискретный отсчёт.

        Например, при step=120: t=190 → отсчёт 120 (floor, а не округление вверх).
        """
        step = self.step_s()
        idx = int(t_s // step)
        return max(0, min(len(self.ticks) - 1, idx))


def simulate_scenario(
    scenario: dict[str, Any],
    strategy: str = STRATEGY_MIN_DISTANCE,
    with_backups: bool = True,
    validate_routes: bool = False,
    progress_cb: Callable[[int, int], None] | None = None,
) -> SimulationResult:
    """Моделирует сценарий на всей расчётной сетке.

    Геометрия берётся из официального модуля. Границы отказов —
    [start_s; end_s). Сетка: range(0, horizon_s, step_s), правый
    конец не включается.
    """
    grid = geometry_adapter.time_grid(scenario)
    if not grid:
        raise ValueError("Расчётная сетка пуста: проверьте horizon_s и step_s")
    clients = clients_of(scenario)
    gateways = gateways_of(scenario)
    sat_ids = satellite_ids(scenario)
    step_s = int(scenario["environment"]["step_s"])

    per_client: dict[str, dict[str, list]] = {
        c: {"statuses": [], "reasons": [], "details": [], "visible": [], "paths": [],
            "hops": [], "distances": [], "backups": []}
        for c in clients
    }
    active_counts: list[int] = []
    edge_counts: list[int] = []
    problems: list[str] = []

    for idx, t_s in enumerate(grid):
        snap = geometry_adapter.snapshot(scenario, t_s)
        graph = build_link_graph(snap, scenario)
        active_counts.append(len(graph.active_sats))
        edge_counts.append(len(snap["edges"]))
        for client_id in clients:
            route = find_route(graph, client_id, strategy)
            bucket = per_client[client_id]
            bucket["statuses"].append(route.status_code)
            bucket["reasons"].append(route.reason)
            bucket["details"].append(route.detail)
            bucket["visible"].append(bool(graph.client_links.get(client_id)))
            bucket["paths"].append(route.path)
            bucket["hops"].append(route.hops if route.connected else None)
            bucket["distances"].append(
                route_distance_km(graph, route.path) if route.connected else None
            )
            if with_backups and route.connected:
                backup = find_backup_route(graph, client_id, route.path)
                bucket["backups"].append(backup.path if backup.connected else ())
            else:
                bucket["backups"].append(())
            if validate_routes and route.connected:
                for problem in validate_path(snap, scenario, client_id, route.path):
                    problems.append(f"t={t_s}, {client_id}: {problem}")
        if progress_cb is not None:
            progress_cb(idx + 1, len(grid))

    series: dict[str, ClientSeries] = {}
    metrics: dict[str, ClientMetrics] = {}
    target = float(scenario["environment"]["target_availability"])
    for client_id in clients:
        b = per_client[client_id]
        client_series = ClientSeries(
            client_id=client_id,
            statuses=tuple(b["statuses"]),
            reasons=tuple(b["reasons"]),
            details=tuple(b["details"]),
            visible=tuple(b["visible"]),
            paths=tuple(b["paths"]),
            hops=tuple(b["hops"]),
            distances=tuple(b["distances"]),
            backup_paths=tuple(b["backups"]),
        )
        series[client_id] = client_series
        metrics[client_id] = compute_client_metrics(
            client_id=client_id,
            ticks=grid,
            statuses=client_series.statuses,
            client_visible=client_series.visible,
            hops=client_series.hops,
            distances=client_series.distances,
            paths=client_series.paths,
            backup_exists=[bool(bp) for bp in client_series.backup_paths],
            step_s=step_s,
            target_availability=target,
        )

    return SimulationResult(
        scenario=scenario,
        strategy=strategy,
        ticks=tuple(grid),
        clients=tuple(clients),
        gateways=tuple(gateways),
        sat_ids=tuple(sat_ids),
        series=series,
        metrics=metrics,
        global_metrics=compute_global_metrics(list(metrics.values()), len(clients)),
        active_counts=tuple(active_counts),
        edge_counts=tuple(edge_counts),
        validation_problems=tuple(problems),
    )


def snapshot_at(scenario: dict[str, Any], t_s: int) -> tuple[dict[str, Any], LinkGraph]:
    """Состояние сети в произвольный момент (для сетки/карты в UI)."""
    snap = geometry_adapter.snapshot(scenario, t_s)
    return snap, build_link_graph(snap, scenario)
