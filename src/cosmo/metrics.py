"""Метрики доступности по «Описание данных».

Для каждого клиентского пункта:
- visibility_fraction — доля отсчётов, где виден хотя бы один активный
  спутник (угол возвышения ≥ min_elevation_deg);
- availability_fraction — доля отсчётов, где существует полный путь
  «client → спутник(и) → gateway»;
- max_outage_s — самая длинная последовательность отсчётов без пути,
  умноженная на step_s (перерывы в начале и в конце периода учитываются);
- список перерывов с причинами;
- статистика маршрутов (hops = число рёбер, включая две наземные линии).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import STATUS_CONNECTED, STATUS_LABELS, hhmmss


@dataclass(frozen=True)
class OutageInterval:
    """Непрерывный период отсутствия сквозного маршрута.

    Покрывает отрезки времени [start_s; end_s) в терминах отсчётов:
    последний отсчёт перерыва + step_s образует конец интервала.
    """

    start_s: int
    end_s: int
    duration_s: int
    reason: str  # приоритетная причина (человекочитаемая)
    reasons: tuple[tuple[int, int], ...]  # (код статуса, число отсчётов)
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": self.duration_s,
            "start_hhmmss": hhmmss(self.start_s),
            "end_hhmmss": hhmmss(self.end_s),
            "reason": self.reason,
            "reasons": [
                {"code": code, "ticks": n, "label": STATUS_LABELS.get(code, str(code))}
                for code, n in self.reasons
            ],
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ClientMetrics:
    """Сводные показатели одного клиентского пункта."""

    client_id: str
    visibility_fraction: float
    availability_fraction: float
    max_outage_s: int
    outage_intervals: tuple[OutageInterval, ...]
    mean_hops: float | None
    median_hops: float | None
    p95_hops: float | None
    max_hops: int | None
    route_change_count: int
    mean_path_km: float | None
    backup_fraction: float | None  # доля «подключённых» отсчётов с резервным путём
    target_met: bool
    target_availability: float

    def as_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "visibility_fraction": self.visibility_fraction,
            "availability_fraction": self.availability_fraction,
            "max_outage_s": self.max_outage_s,
            "outage_intervals": [o.as_dict() for o in self.outage_intervals],
            "mean_hops": self.mean_hops,
            "median_hops": self.median_hops,
            "p95_hops": self.p95_hops,
            "max_hops": self.max_hops,
            "route_change_count": self.route_change_count,
            "mean_path_km": self.mean_path_km,
            "backup_fraction": self.backup_fraction,
            "target_met": self.target_met,
            "target_availability": self.target_availability,
        }


@dataclass(frozen=True)
class GlobalMetrics:
    """Сводка по всем клиентам."""

    min_availability: float
    mean_availability: float
    worst_max_outage_s: int
    target_met_clients: int
    total_clients: int

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def outage_intervals_from_statuses(
    ticks: list[int], statuses: list[int], step_s: int
) -> tuple[OutageInterval, ...]:
    """Интервалы перерывов по последовательности кодов статусов.

    Перерыв — подряд идущие отсчёты со статусом != CONNECTED, включая
    перерывы в начале и в конце периода. Приоритетная причина интервала —
    категория с наибольшим приоритетом среди присутствующих; полный
    состав прикладывается в detail/reasons.
    """
    intervals: list[OutageInterval] = []
    run_start: int | None = None
    run_codes: list[int] = []

    def close(end_index_exclusive: int) -> None:
        nonlocal run_start, run_codes
        if run_start is None:
            return
        codes = sorted(set(run_codes))  # меньший код = выше приоритет
        counts = tuple((code, run_codes.count(code)) for code in codes)
        reason_code = codes[0]
        start_s = ticks[run_start]
        end_s = ticks[end_index_exclusive - 1] + step_s
        detail = ", ".join(f"{STATUS_LABELS.get(code, code)} ({n})" for code, n in counts)
        intervals.append(
            OutageInterval(
                start_s=start_s,
                end_s=end_s,
                duration_s=end_s - start_s,
                reason=STATUS_LABELS.get(reason_code, str(reason_code)),
                reasons=counts,
                detail=detail,
            )
        )
        run_start = None
        run_codes = []

    for idx, status in enumerate(statuses):
        if status != STATUS_CONNECTED:
            if run_start is None:
                run_start = idx
            run_codes.append(status)
        else:
            close(idx)
    close(len(statuses))
    return tuple(intervals)


def percentile_nearest_rank(sorted_values: list[int], q: float) -> float:
    """Персентиль методом ближайшего ранга (nearest-rank)."""
    if not sorted_values:
        raise ValueError("пустой список значений")
    rank = max(1, math.ceil(q * len(sorted_values)))
    return float(sorted_values[rank - 1])


def compute_route_changes(paths: list[tuple[str, ...]], connected: list[bool]) -> int:
    """Число смен маршрута между соседними «подключёнными» отсчётами.

    Переходы «маршрут был / маршрута нет» сменой маршрута не считаются —
    они фиксируются как перерывы.
    """
    changes = 0
    prev_path: tuple[str, ...] | None = None
    for path, ok in zip(paths, connected):
        if not ok:
            continue
        if prev_path is not None and path != prev_path:
            changes += 1
        prev_path = path
    return changes


def compute_client_metrics(
    client_id: str,
    ticks: list[int],
    statuses: list[int],
    client_visible: list[bool],
    hops: list[int | None],
    distances: list[float | None],
    paths: list[tuple[str, ...]],
    backup_exists: list[bool] | None,
    step_s: int,
    target_availability: float,
) -> ClientMetrics:
    """Считает все показатели одного клиента по дискретной сетке."""
    total = len(ticks)
    if total == 0:
        raise ValueError("расчётная сетка пуста")
    if not (len(statuses) == len(client_visible) == len(hops) == len(distances) == len(paths) == total):
        raise ValueError("длины временных рядов клиента не совпадают с сеткой")

    visibility = sum(1 for v in client_visible if v)
    connected = [s == STATUS_CONNECTED for s in statuses]
    availability = sum(connected)

    hops_list = sorted(h for h, ok in zip(hops, connected) if ok and h is not None)
    dist_list = [d for d, ok in zip(distances, connected) if ok and d is not None]

    if backup_exists is not None and availability:
        backup_fraction = sum(1 for ok, b in zip(connected, backup_exists) if ok and b) / availability
    else:
        backup_fraction = None

    intervals = outage_intervals_from_statuses(ticks, statuses, step_s)

    median: float | None = None
    if hops_list:
        n = len(hops_list)
        median = float(hops_list[n // 2]) if n % 2 else (hops_list[n // 2 - 1] + hops_list[n // 2]) / 2

    return ClientMetrics(
        client_id=client_id,
        visibility_fraction=visibility / total,
        availability_fraction=availability / total,
        max_outage_s=max((iv.duration_s for iv in intervals), default=0),
        outage_intervals=intervals,
        mean_hops=(sum(hops_list) / len(hops_list)) if hops_list else None,
        median_hops=median,
        p95_hops=percentile_nearest_rank(hops_list, 0.95) if hops_list else None,
        max_hops=hops_list[-1] if hops_list else None,
        route_change_count=compute_route_changes(paths, connected),
        mean_path_km=(sum(dist_list) / len(dist_list)) if dist_list else None,
        backup_fraction=backup_fraction,
        target_met=(availability / total) >= target_availability,
        target_availability=target_availability,
    )


def compute_global_metrics(metrics: list[ClientMetrics], total_clients: int) -> GlobalMetrics:
    """Сводные показатели по всем клиентам."""
    if not metrics:
        raise ValueError("нет клиентских метрик")
    return GlobalMetrics(
        min_availability=min(m.availability_fraction for m in metrics),
        mean_availability=sum(m.availability_fraction for m in metrics) / len(metrics),
        worst_max_outage_s=max(m.max_outage_s for m in metrics),
        target_met_clients=sum(1 for m in metrics if m.target_met),
        total_clients=total_clients,
    )
