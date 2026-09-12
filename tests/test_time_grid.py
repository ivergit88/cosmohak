"""Тесты расчётной сетки времени и границ отказов."""

from __future__ import annotations

from cosmo.geometry_adapter import active_flags, time_grid
from tests.conftest import scenario_copy


def test_grid_excludes_right_endpoint(small_scenario):
    """Сетка 0,100,…,500; правый конец horizon_s=600 НЕ включается."""
    grid = time_grid(small_scenario)
    assert grid == [0, 100, 200, 300, 400, 500]
    assert small_scenario["environment"]["horizon_s"] not in grid


def test_grid_official_case_720_ticks(scenarios):
    grid = time_grid(scenarios["01_full_constellation.json"])
    assert len(grid) == 720
    assert grid[0] == 0
    assert grid[-1] == 86280


def test_grid_derived_from_scenario(small_scenario):
    """Число отсчётов выводится из сценария, нигде не захардкожено."""
    modified = scenario_copy(small_scenario)
    modified["environment"]["horizon_s"] = 300
    modified["environment"]["step_s"] = 100
    assert time_grid(modified) == [0, 100, 200]


def test_failure_boundaries(small_scenario):
    """Отказ [200; 400): активен до начала, неактивен в [start; end), активен ровно в end."""
    modified = scenario_copy(small_scenario)
    modified["failures"] = [{"satellite_id": "T1", "start_s": 200, "end_s": 400}]
    before = active_flags(modified, 100)
    at_start = active_flags(modified, 200)
    inside = active_flags(modified, 300)
    at_end = active_flags(modified, 400)
    assert before["T1"] is True
    assert at_start["T1"] is False  # start включается
    assert inside["T1"] is False
    assert at_end["T1"] is True  # end исключается


def test_failure_only_affects_target(small_scenario):
    modified = scenario_copy(small_scenario)
    modified["failures"] = [{"satellite_id": "T1", "start_s": 200, "end_s": 400}]
    flags = active_flags(modified, 300)
    assert flags["T1"] is False
    assert flags["T2"] is True
    assert flags["T3"] is True


def test_launch_stage_filters_satellites(small_scenario):
    modified = scenario_copy(small_scenario)
    modified["design"]["launch_stage"] = 1
    flags = active_flags(modified, 0)
    assert flags["T1"] is True
    assert flags["T2"] is False  # launch_batch 2
    assert flags["T3"] is False  # launch_batch 3
    modified["design"]["launch_stage"] = 2
    flags = active_flags(modified, 0)
    assert flags["T2"] is True
    assert flags["T3"] is False


def test_tick_at_floors_to_lower_tick(small_scenario):
    """t=190 при шаге 100 → нижний отсчёт 100 (не округление вверх до 200)."""
    from cosmo.simulation import simulate_scenario

    sim = simulate_scenario(small_scenario, with_backups=False)
    assert sim.step_s() == 100
    assert sim.ticks[sim.tick_at(190)] == 100
    assert sim.ticks[sim.tick_at(200)] == 200
    assert sim.ticks[sim.tick_at(-5)] == 0  # защита от отрицательных
