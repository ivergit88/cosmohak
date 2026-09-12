"""Экспорт результатов: официальный формат cosmo-A-result-1.0.

result.json строго по официальной схеме, только обязательные поля:
- schema_version = "cosmo-A-result-1.0";
- effective_scenario — полный фактически использованный сценарий
  (со всеми изменениями пользователя);
- routes — ровно одна запись {t_s, client_id, path} на каждую пару
  «отсчёт × клиент»; path=[] если маршрута нет.

Никаких дополнительных top-level полей в result не добавляется:
структура критична. Сводки, диагностику и стратегию маршрутизации
выгружайте отдельным файлом — build_analysis_report().
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from .models import STATUS_LABELS, canonical_json
from .simulation import SimulationResult

RESULT_SCHEMA_VERSION = "cosmo-A-result-1.0"


def build_result(
    sim: SimulationResult,
    generated_at: str | None = None,
    include_summary: bool = False,
) -> dict[str, Any]:
    """Собирает результат в строгом официальном формате cosmo-A-result-1.0.

    routes идут в порядке «отсчёт, затем клиенты в порядке файла» —
    каждая пара (t_s, client_id) встречается ровно один раз.
    Дополнительные top-level поля не добавляются (структура критична);
    сводки — в build_analysis_report(). Параметры generated_at /
    include_summary оставлены для совместимости и игнорируются.
    """
    clients = list(sim.clients)
    routes: list[dict[str, Any]] = []
    for tick_idx, t_s in enumerate(sim.ticks):
        for client_id in clients:
            path = sim.series[client_id].paths[tick_idx]
            routes.append(
                {"t_s": int(t_s), "client_id": client_id, "path": list(path)}
            )
    expected = len(sim.ticks) * len(clients)
    if len(routes) != expected:
        raise AssertionError(f"routes {len(routes)} != ticks*clients {expected}")

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "effective_scenario": sim.scenario,
        "routes": routes,
    }


def build_analysis_report(sim: SimulationResult, generated_at: str | None = None) -> dict[str, Any]:
    """Дополнительный файл анализа (не часть официального result).

    Содержит стратегию маршрутизации, сводные метрики по клиентам,
    глобальные показатели и интервалы перерывов с причинами.
    """
    clients = list(sim.clients)
    return {
        "analysis_of": RESULT_SCHEMA_VERSION,
        "routing_strategy": sim.strategy,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grid": {"ticks": len(sim.ticks), "step_s": sim.step_s(), "clients": clients},
        "global": sim.global_metrics.as_dict(),
        "clients": {cid: sim.metrics[cid].as_dict() for cid in clients},
        "outage_intervals": {
            cid: [o.as_dict() for o in sim.metrics[cid].outage_intervals] for cid in clients
        },
        "status_labels": STATUS_LABELS,
    }


def dumps_result(result: dict[str, Any]) -> str:
    """Сериализация результата: UTF-8, без NaN, читаемые отступы."""
    return json.dumps(result, ensure_ascii=False, allow_nan=False, indent=1)


def dumps_scenario(scenario: dict[str, Any]) -> str:
    """Сериализация effective scenario для повторной загрузки."""
    return json.dumps(scenario, ensure_ascii=False, allow_nan=False, indent=1)


def validate_result_structure(result: dict[str, Any], expected_routes: int | None = None) -> list[str]:
    """Проверка структуры результата (используется тестами и самоконтролем)."""
    problems: list[str] = []
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        problems.append(f"schema_version={result.get('schema_version')!r}")
    extra = set(result) - {"schema_version", "effective_scenario", "routes"}
    if extra:
        problems.append(f"лишние top-level поля официального result: {sorted(extra)}")
    scenario = result.get("effective_scenario")
    if not isinstance(scenario, dict) or "environment" not in scenario or "design" not in scenario:
        problems.append("effective_scenario отсутствует или неполон")
    routes = result.get("routes")
    if not isinstance(routes, list) or not routes:
        problems.append("routes отсутствуют")
        return problems
    clients = {g["id"] for g in scenario.get("ground_sites", []) if g.get("role") == "client"}
    ticks = list(range(0, scenario["environment"]["horizon_s"], scenario["environment"]["step_s"]))
    seen: set[tuple[int, str]] = set()
    for entry in routes:
        key = (entry.get("t_s"), entry.get("client_id"))
        if key in seen:
            problems.append(f"дубликат route-записи: {key}")
        seen.add(key)
        if entry.get("client_id") not in clients:
            problems.append(f"неизвестный client_id: {entry.get('client_id')}")
        if entry.get("t_s") not in set(ticks):
            problems.append(f"t_s вне расчётной сетки: {entry.get('t_s')}")
        path = entry.get("path")
        if not isinstance(path, list) or any(not isinstance(p, str) for p in path):
            problems.append(f"path некорректен у {key}")
    missing = expected_routes if expected_routes is not None else len(ticks) * len(clients)
    if len(seen) != missing:
        problems.append(f"записей {len(seen)}, ожидалось {missing}")
    return problems


def metrics_csv(sim: SimulationResult) -> str:
    """CSV со сводными метриками по клиентам (с BOM для Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "client_id",
            "visibility_fraction",
            "availability_fraction",
            "availability_percent",
            "max_outage_s",
            "target_met",
            "target_availability",
            "mean_hops",
            "median_hops",
            "p95_hops",
            "max_hops",
            "route_change_count",
            "mean_path_km",
            "backup_fraction",
            "outage_intervals",
        ]
    )
    for cid in sim.clients:
        m = sim.metrics[cid]
        writer.writerow(
            [
                cid,
                f"{m.visibility_fraction:.6f}",
                f"{m.availability_fraction:.6f}",
                f"{100 * m.availability_fraction:.4f}",
                m.max_outage_s,
                "yes" if m.target_met else "no",
                m.target_availability,
                "" if m.mean_hops is None else f"{m.mean_hops:.4f}",
                "" if m.median_hops is None else f"{m.median_hops:.4f}",
                "" if m.p95_hops is None else f"{m.p95_hops:.1f}",
                "" if m.max_hops is None else m.max_hops,
                m.route_change_count,
                "" if m.mean_path_km is None else f"{m.mean_path_km:.2f}",
                "" if m.backup_fraction is None else f"{m.backup_fraction:.4f}",
                " | ".join(
                    f"[{o.start_s};{o.end_s}) {o.duration_s}s {o.reason}" for o in m.outage_intervals
                ),
            ]
        )
    return buffer.getvalue()


def timeline_csv(sim: SimulationResult) -> str:
    """CSV по отсчётам: статус/причина/маршрут каждого клиента."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    header = ["t_s"] + [f"{cid}::status" for cid in sim.clients] + [f"{cid}::reason" for cid in sim.clients] + [f"{cid}::path" for cid in sim.clients]
    writer.writerow(header)
    for idx, t in enumerate(sim.ticks):
        row: list[Any] = [t]
        for cid in sim.clients:
            s = sim.series[cid]
            row.append(STATUS_LABELS.get(s.statuses[idx], s.statuses[idx]))
        for cid in sim.clients:
            row.append(sim.series[cid].reasons[idx])
        for cid in sim.clients:
            row.append("->".join(sim.series[cid].paths[idx]))
        writer.writerow(row)
    return buffer.getvalue()
