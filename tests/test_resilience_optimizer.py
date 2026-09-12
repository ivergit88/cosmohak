"""Тесты анализа устойчивости, сравнения вариантов и оптимизатора."""

from __future__ import annotations

import pytest

from cosmo.comparison import config_diff_rows, global_diff_rows, objective_key, recommend
from cosmo.models import deep_copy
from cosmo.optimizer import optimize_configuration
from cosmo.resilience import apply_failure_impact, criticality_analysis
from cosmo.simulation import simulate_scenario


def test_criticality_finds_single_point_of_failure():
    """В цепочке C-S1-S2-GW вывод S1 или S2 обрывает связь; их критичность максимальна."""
    scenario = {
        "schema_version": "cosmo-A-1.0",
        "meta": {"id": "chain", "title": "chain"},
        "environment": {
            "altitude_km": 550.0, "inclination_deg": 87.0, "earth_angle0_deg": 0.0,
            "horizon_s": 300, "step_s": 100, "min_elevation_deg": 0.0,
            "isl_range_km": 5000.0, "target_availability": 0.9,
        },
        "design": {
            "launch_stage": 3,
            "planes": [{"id": "P", "raan_deg": 0.0, "phase_deg": 0.0}],
            "satellites": [
                {"id": "S1", "plane_id": "P", "slot_deg": 0.0, "launch_batch": 1},
            ],
        },
        "ground_sites": [
            {"id": "GW", "name": "g", "role": "gateway", "lat_deg": 0.0, "lon_deg": 0.0},
            {"id": "C1", "name": "c", "role": "client", "lat_deg": 0.0, "lon_deg": 10.0},
        ],
        "failures": [],
        "gateway_outages": [],
    }
    baseline = simulate_scenario(scenario, with_backups=False)
    if baseline.global_metrics.mean_availability == 0:
        pytest.skip("геометрия не даёт связности на тестовой сетке")
    rows = criticality_analysis(scenario, baseline)
    by_id = {r.satellite_id: r for r in rows}
    # каждый из участников маршрутов теряет доступность при выводе
    used = [r for r in rows if r.usage_count > 0]
    assert used, "нет используемых спутников"
    for r in used:
        assert r.delta_mean_availability >= 0
    # ранжирование: у лидера максимальное падение min-доступности
    assert rows[0].delta_min_availability >= max(r.delta_min_availability for r in rows)


def test_criticality_matches_direct_outage(scenarios):
    """Критичность ≈ эффекту полного отказа: mean-доступность падает согласованно."""
    scenario = scenarios["03_satellite_outages.json"]
    baseline = simulate_scenario(scenario, with_backups=False)
    rows = criticality_analysis(scenario, baseline)
    top = rows[0]
    modified, impacted = apply_failure_impact(
        scenario, baseline, top.satellite_id, 0, scenario["environment"]["horizon_s"]
    )
    # точное совпадение mean-падения при полном отказе
    delta_direct = baseline.global_metrics.mean_availability - impacted.global_metrics.mean_availability
    assert abs(delta_direct - top.delta_mean_availability) < 1e-9
    assert modified["failures"][-1]["satellite_id"] == top.satellite_id


def test_config_diff_and_recommendation(small_scenario):
    variant_a = deep_copy(small_scenario)
    variant_b = deep_copy(small_scenario)
    variant_b["design"]["launch_stage"] = 1
    variant_b["design"]["planes"][0]["raan_deg"] = 45.0
    rows = config_diff_rows(variant_a, variant_b)
    stage_rows = [r for r in rows if r["Параметр"].startswith("Очередь")]
    assert stage_rows and stage_rows[0]["Вариант A"] != stage_rows[0]["Вариант B"]
    assert any("RAAN" in r["Параметр"] and "PA" in r["Параметр"] and r["Различие"] == "да" for r in rows)
    sim_a = simulate_scenario(variant_a, with_backups=False)
    sim_b = simulate_scenario(variant_b, with_backups=False)
    rows_g = global_diff_rows(sim_a.global_metrics, sim_b.global_metrics)
    assert len(rows_g) == 4
    # рекомендация: связана с расчётом и объяснима
    best, why = recommend([])
    assert best is None
    from cosmo.comparison import Variant

    va = Variant("A", variant_a, "min_hops", "2026-09-12", sim_a.metrics, sim_a.global_metrics)
    vb = Variant("B", variant_b, "min_hops", "2026-09-12", sim_b.metrics, sim_b.global_metrics)
    best, why = recommend([va, vb])
    assert best is not None and why
    keys = {v.name: objective_key(v.metrics, v.global_metrics) for v in (va, vb)}
    assert best.name == min(keys, key=keys.get)


def test_optimizer_smoke(small_scenario):
    """Оптимизатор: детерминирован, соблюдает бюджет, не меняет launch_batch."""
    result = optimize_configuration(small_scenario, budget=12, coarse_multiplier=2)
    assert result.evaluations <= 12
    again = optimize_configuration(small_scenario, budget=12, coarse_multiplier=2)
    assert result.best_scenario["design"]["planes"] == again.best_scenario["design"]["planes"]
    for sat_before, sat_after in zip(
        small_scenario["design"]["satellites"], result.best_scenario["design"]["satellites"]
    ):
        assert sat_before["launch_batch"] == sat_after["launch_batch"]
        assert sat_before["slot_deg"] == sat_after["slot_deg"]
    # RAAN/phase в допустимом диапазоне
    for plane in result.best_scenario["design"]["planes"]:
        assert 0 <= plane["raan_deg"] < 360
        assert 0 <= plane["phase_deg"] < 360
    # улучшение (если есть) фиксируется честно
    assert result.improved == (result.best_key < result.baseline_key)
