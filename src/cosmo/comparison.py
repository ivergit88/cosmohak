"""Сравнение сохранённых вариантов конфигурации.

Рекомендация строится по прозрачному лексикографическому критерию:
1) максимум минимальной доступности среди клиентов;
2) затем максимум средней доступности;
3) затем минимум худшего максимального перерыва;
4) затем минимум среднего числа переходов.
Никаких «магических» скалярных score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .metrics import ClientMetrics, GlobalMetrics
from .models import fmt_pct, hhmmss


@dataclass(frozen=True)
class Variant:
    """Сохранённый вариант проекта."""

    name: str
    scenario: dict[str, Any]
    strategy: str
    created_at: str
    metrics: dict[str, ClientMetrics]
    global_metrics: GlobalMetrics
    note: str = ""

    def config_signature(self) -> dict[str, Any]:
        """Ключевые параметры варианта для таблицы сравнения."""
        env = self.scenario["environment"]
        design = self.scenario["design"]
        return {
            "launch_stage": design["launch_stage"],
            "planes": {p["id"]: (p["raan_deg"], p["phase_deg"]) for p in design["planes"]},
            "failures": len(self.scenario.get("failures", [])),
            "isl_range_km": env["isl_range_km"],
            "altitude_km": env["altitude_km"],
            "inclination_deg": env["inclination_deg"],
            "min_elevation_deg": env["min_elevation_deg"],
            "horizon_s": env["horizon_s"],
            "step_s": env["step_s"],
            "target_availability": env["target_availability"],
        }


def config_diff_rows(scenario_a: dict[str, Any], scenario_b: dict[str, Any]) -> list[dict[str, str]]:
    """Таблица «Параметр | A | B» только по различающимся полям + ключевые общие."""
    env_a, env_b = scenario_a["environment"], scenario_b["environment"]
    dsn_a, dsn_b = scenario_a["design"], scenario_b["design"]
    rows: list[dict[str, str]] = []

    def row(label: str, va: Any, vb: Any, fmt: str = str) -> None:
        rows.append({"Параметр": label, "Вариант A": fmt(va), "Вариант B": fmt(vb), "Различие": "да" if va != vb else "—"})

    row("Очередь запуска (launch_stage)", dsn_a["launch_stage"], dsn_b["launch_stage"])
    planes_a = {p["id"]: p for p in dsn_a["planes"]}
    planes_b = {p["id"]: p for p in dsn_b["planes"]}
    for pid in sorted(set(planes_a) | set(planes_b)):
        pa, pb = planes_a.get(pid), planes_b.get(pid)
        if pa is None or pb is None:
            row(f"Плоскость {pid}", "есть" if pa else "нет", "есть" if pb else "нет")
            continue
        row(f"Плоскость {pid} · RAAN", f"{pa['raan_deg']}°", f"{pb['raan_deg']}°")
        row(f"Плоскость {pid} · фазирование", f"{pa['phase_deg']}°", f"{pb['phase_deg']}°")
    fa, fb = scenario_a.get("failures", []), scenario_b.get("failures", [])
    row("Число периодов отказа спутников", len(fa), len(fb))
    if fa != fb:
        row(
            "Отказы (детали)",
            "; ".join(f"{f['satellite_id']} [{f['start_s']}; {f['end_s']})" for f in fa) or "нет",
            "; ".join(f"{f['satellite_id']} [{f['start_s']}; {f['end_s']})" for f in fb) or "нет",
        )
    ga, gb = scenario_a.get("gateway_outages", []), scenario_b.get("gateway_outages", [])
    if ga != gb:
        row("Отказы шлюзов", len(ga), len(gb))
    for key, label, unit in (
        ("altitude_km", "Высота орбиты", "км"),
        ("inclination_deg", "Наклонение", "°"),
        ("isl_range_km", "Дальность МСC", "км"),
        ("min_elevation_deg", "Мин. угол возвышения", "°"),
        ("horizon_s", "Горизонт расчёта", "с"),
        ("step_s", "Шаг расчёта", "с"),
        ("target_availability", "Целевая доступность", ""),
    ):
        row(f"{label} ({unit})", env_a[key], env_b[key])
    return rows


def metrics_diff_rows(metrics_a: dict[str, ClientMetrics], metrics_b: dict[str, ClientMetrics]) -> list[dict[str, str]]:
    """Сравнение метрик по каждому клиенту."""
    rows: list[dict[str, str]] = []
    for cid in metrics_a:
        ma, mb = metrics_a[cid], metrics_b[cid]
        rows.append(_mrow(f"{cid} · видимость", fmt_pct(ma.visibility_fraction), fmt_pct(mb.visibility_fraction)))
        rows.append(_mrow(f"{cid} · доступность", fmt_pct(ma.availability_fraction), fmt_pct(mb.availability_fraction)))
        rows.append(_mrow(f"{cid} · макс. перерыв", f"{ma.max_outage_s} с ({hhmmss(ma.max_outage_s)})", f"{mb.max_outage_s} с ({hhmmss(mb.max_outage_s)})"))
        rows.append(_mrow(f"{cid} · среднее число переходов", _num(ma.mean_hops), _num(mb.mean_hops)))
        rows.append(_mrow(f"{cid} · смены маршрута", str(ma.route_change_count), str(mb.route_change_count)))
    return rows


def global_diff_rows(ga: GlobalMetrics, gb: GlobalMetrics) -> list[dict[str, str]]:
    return [
        _mrow("MIN доступность по клиентам", fmt_pct(ga.min_availability), fmt_pct(gb.min_availability)),
        _mrow("MEAN доступность по клиентам", fmt_pct(ga.mean_availability), fmt_pct(gb.mean_availability)),
        _mrow("Худший макс. перерыв", f"{ga.worst_max_outage_s} с", f"{gb.worst_max_outage_s} с"),
        _mrow("Цель достигнута (пунктов)", f"{ga.target_met_clients}/{ga.total_clients}", f"{gb.target_met_clients}/{gb.total_clients}"),
    ]


def objective_key(metrics: dict[str, ClientMetrics], g: GlobalMetrics) -> tuple[float, float, int, float]:
    """Лексикографический ключ рекомендации (меньше = лучше).

    (−min availability, −mean availability, worst max outage, mean hops).
    """
    mean_hops = [m.mean_hops for m in metrics.values() if m.mean_hops is not None]
    return (
        -g.min_availability,
        -g.mean_availability,
        g.worst_max_outage_s,
        (sum(mean_hops) / len(mean_hops)) if mean_hops else 0.0,
    )


def recommend(variants: list[Variant]) -> tuple[Variant | None, str]:
    """Возвращает рекомендованный вариант и обоснование с конкретными цифрами."""
    if not variants:
        return None, "Нет сохранённых вариантов для рекомендации."
    best = min(variants, key=lambda v: objective_key(v.metrics, v.global_metrics))
    g = best.global_metrics
    parts = [
        f"минимальная доступность среди пунктов {fmt_pct(g.min_availability)}",
        f"средняя доступность {fmt_pct(g.mean_availability)}",
        f"худший максимальный перерыв {g.worst_max_outage_s} с",
        f"цель достигнута для {g.target_met_clients} из {g.total_clients} пунктов",
    ]
    why = (
        f"Вариант «{best.name}» рекомендован по лексикографическому критерию "
        "(1: max min-доступность → 2: max mean-доступность → 3: min худшего перерыва → "
        f"4: min среднего числа переходов): {', '.join(parts)}."
    )
    return best, why


def _mrow(label: str, va: str, vb: str) -> dict[str, str]:
    delta = "—" if va == vb else "≠"
    return {"Параметр": label, "Вариант A": va, "Вариант B": vb, "Различие": delta}


def _num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"
