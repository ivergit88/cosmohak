"""Быстрый автоподбор RAAN/фазирования плоскостей (бонус-модуль).

Стратегия: детерминированный координатный поиск (hill climbing) по
осям «RAAN плоскости» и «фазирование плоскости» на прореженной сетке
времени (coarse), затем пересчёт лучшего кандидата на полной сетке.

Цель — лексикографический ключ (см. comparison.objective_key):
max min-доступность → max mean-доступность → min худшего перерыва.
launch_batch спутников не изменяется; изменяются только raan_deg /
phase_deg выбранных пользователем плоскостей.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from .comparison import objective_key
from .metrics import ClientMetrics, GlobalMetrics
from .models import STRATEGY_MIN_DISTANCE, deep_copy
from .simulation import SimulationResult, simulate_scenario

logger = logging.getLogger(__name__)

OFFSET_STEPS = (-60.0, -30.0, -15.0, -7.5, 7.5, 15.0, 30.0, 60.0)


@dataclass(frozen=True)
class OptimizationResult:
    """Итог автоподбора конфигурации."""

    best_scenario: dict[str, Any]
    baseline_key: tuple
    best_key: tuple
    evaluations: int
    coarse_step_s: int
    improved: bool
    history: tuple[tuple[str, tuple], ...] = field(default_factory=tuple)

    def as_summary(self) -> dict[str, Any]:
        return {
            "evaluations": self.evaluations,
            "coarse_step_s": self.coarse_step_s,
            "improved": self.improved,
            "baseline_key": self.baseline_key,
            "best_key": self.best_key,
        }


def _coarse_scenario(scenario: dict[str, Any], multiplier: int) -> dict[str, Any]:
    """Копия сценария с прореженной сеткой времени (horizon/step сохраняют смысл)."""
    coarse = deep_copy(scenario)
    env = coarse["environment"]
    env["step_s"] = int(env["step_s"]) * int(multiplier)
    return coarse


def _params_of(scenario: dict[str, Any], plane_ids: list[str]) -> dict[str, list[float]]:
    return {
        p["id"]: [float(p["raan_deg"]), float(p["phase_deg"])]
        for p in scenario["design"]["planes"]
        if p["id"] in plane_ids
    }


def _apply_params(scenario: dict[str, Any], params: dict[str, list[float]]) -> dict[str, Any]:
    """Возвращает копию сценария с применёнными RAAN/phase (нормировка в [0;360))."""
    result = deep_copy(scenario)
    for plane in result["design"]["planes"]:
        if plane["id"] in params:
            raan, phase = params[plane["id"]]
            plane["raan_deg"] = round(raan % 360.0, 6)
            plane["phase_deg"] = round(phase % 360.0, 6)
    return result


def _evaluate(
    coarse_base: dict[str, Any],
    params: dict[str, list[float]],
    strategy: str,
) -> tuple[tuple, dict[str, ClientMetrics], GlobalMetrics]:
    candidate = _apply_params(coarse_base, params)
    sim = simulate_scenario(candidate, strategy=strategy, with_backups=False)
    return objective_key(sim.metrics, sim.global_metrics), sim.metrics, sim.global_metrics


def optimize_configuration(
    scenario: dict[str, Any],
    plane_ids: list[str] | None = None,
    budget: int = 30,
    coarse_multiplier: int = 4,
    seed: int = 20260912,
    strategy: str = STRATEGY_MIN_DISTANCE,
    progress_cb: Callable[[int, int], None] | None = None,
) -> OptimizationResult:
    """Подбирает RAAN/phase выбранных плоскостей за ограниченный бюджет оценок.

    Детерминирован при фиксированном seed: генератор случайных смещений
    инициализируется явно. Никакие параметры, кроме raan_deg/phase_deg,
    не изменяются.
    """
    if plane_ids is None:
        plane_ids = [p["id"] for p in scenario["design"]["planes"]]
    plane_ids = [pid for pid in plane_ids if any(p["id"] == pid for p in scenario["design"]["planes"])]
    if not plane_ids:
        raise ValueError("Не выбрано ни одной плоскости для оптимизации")

    coarse_base = _coarse_scenario(scenario, coarse_multiplier)
    rng = random.Random(seed)
    current = _params_of(scenario, plane_ids)
    best_key, _m, _g = _evaluate(coarse_base, current, strategy)
    baseline_key = best_key
    evaluations = 1
    history: list[tuple[str, tuple]] = [("baseline", best_key)]
    total_budget = max(int(budget), 8)

    # 1) Несколько случайных мульти-смещений (детерминированных по seed).
    random_shots = max(4, total_budget // 6)
    for _ in range(random_shots):
        if evaluations >= total_budget:
            break
        candidate = {pid: list(vals) for pid, vals in current.items()}
        for pid in plane_ids:
            candidate[pid][0] = (candidate[pid][0] + rng.choice(OFFSET_STEPS) * rng.choice((1, 2))) % 360.0
            candidate[pid][1] = (candidate[pid][1] + rng.choice(OFFSET_STEPS)) % 360.0
        key, _m, _g = _evaluate(coarse_base, candidate, strategy)
        evaluations += 1
        history.append((f"random:{evaluations}", key))
        if key < best_key:
            best_key, current = key, candidate

    # 2) Координатный спуск: по одной оси за шаг.
    improved = True
    while improved and evaluations < total_budget:
        improved = False
        for pid in plane_ids:
            for axis in (0, 1):
                for offset in OFFSET_STEPS:
                    if evaluations >= total_budget:
                        break
                    candidate = {p: list(v) for p, v in current.items()}
                    candidate[pid][axis] = (candidate[pid][axis] + offset) % 360.0
                    key, _m, _g = _evaluate(coarse_base, candidate, strategy)
                    evaluations += 1
                    history.append((f"coord:{pid}:{'raan' if axis == 0 else 'phase'}:{offset:+.1f}", key))
                    if key < best_key:
                        best_key, current = key, candidate
                        improved = True
                        break
                if evaluations >= total_budget:
                    break
            if evaluations >= total_budget:
                break
        if progress_cb is not None:
            progress_cb(evaluations, total_budget)

    best_scenario = _apply_params(scenario, current)  # полная сетка сохраняется
    return OptimizationResult(
        best_scenario=best_scenario,
        baseline_key=baseline_key,
        best_key=best_key,
        evaluations=evaluations,
        coarse_step_s=int(scenario["environment"]["step_s"]) * coarse_multiplier,
        improved=best_key < baseline_key,
        history=tuple(history),
    )


def full_grid_evaluation(scenario: dict[str, Any], strategy: str) -> SimulationResult:
    """Пересчёт кандидата на полной сетке (после coarse-отбора)."""
    return simulate_scenario(scenario, strategy=strategy)
