"""Тесты экспорта: официальный формат, число записей, повторная загрузка."""

from __future__ import annotations

import json

import pytest

from cosmo.export import (
    build_analysis_report,
    build_result,
    dumps_result,
    dumps_scenario,
    metrics_csv,
    validate_result_structure,
)
from cosmo.simulation import simulate_scenario
from cosmo.validation import ensure_valid


@pytest.fixture()
def small_sim(small_scenario):
    return simulate_scenario(small_scenario)


def test_result_schema(small_sim, small_scenario):
    result = build_result(small_sim)
    assert result["schema_version"] == "cosmo-A-result-1.0"
    assert result["effective_scenario"] == small_scenario
    assert isinstance(result["routes"], list)


def test_exact_route_count(small_sim):
    result = build_result(small_sim)
    expected = len(small_sim.ticks) * len(small_sim.clients)
    assert len(result["routes"]) == expected
    keys = {(r["t_s"], r["client_id"]) for r in result["routes"]}
    assert len(keys) == expected  # каждая пара (t_s, client) ровно один раз


def test_route_endpoints(small_sim):
    roles = {g["id"]: g["role"] for g in small_sim.scenario["ground_sites"]}
    for r in build_result(small_sim)["routes"]:
        path = r["path"]
        if path:
            assert roles[path[0]] == "client"
            assert roles[path[-1]] == "gateway"
            assert all(n not in roles for n in path[1:-1])  # внутренние — спутники


def test_every_path_valid_at_its_t(small_sim, small_scenario):
    from cosmo.geometry_adapter import snapshot
    from cosmo.routing import validate_path

    for r in build_result(small_sim)["routes"]:
        if not r["path"]:
            continue
        snap = snapshot(small_scenario, r["t_s"])
        problems = validate_path(snap, small_scenario, r["client_id"], r["path"])
        assert problems == [], (r, problems)


def test_empty_path_when_disconnected():
    scenario = {
        "schema_version": "cosmo-A-1.0",
        "meta": {"id": "x", "title": "x"},
        "environment": {
            "altitude_km": 550.0, "inclination_deg": 87.0, "earth_angle0_deg": 0.0,
            "horizon_s": 200, "step_s": 100, "min_elevation_deg": 85.0,
            "isl_range_km": 10.0, "target_availability": 0.9,
        },
        "design": {
            "launch_stage": 3,
            "planes": [{"id": "P", "raan_deg": 0.0, "phase_deg": 0.0}],
            "satellites": [{"id": "S1", "plane_id": "P", "slot_deg": 0.0, "launch_batch": 1}],
        },
        "ground_sites": [
            {"id": "GW", "name": "g", "role": "gateway", "lat_deg": 0.0, "lon_deg": 0.0},
            {"id": "C1", "name": "c", "role": "client", "lat_deg": 45.0, "lon_deg": 120.0},
        ],
        "failures": [],
        "gateway_outages": [],
    }
    sim = simulate_scenario(scenario, with_backups=False)
    result = build_result(sim)
    assert len(result["routes"]) == 2 * 1
    assert all(r["path"] == [] for r in result["routes"])
    assert validate_result_structure(result) == []


def test_json_strict_utf8_no_nan(small_sim):
    text = dumps_result(build_result(small_sim))
    data = json.loads(text)
    assert data["schema_version"] == "cosmo-A-result-1.0"
    assert "NaN" not in text and "Infinity" not in text
    json.loads(dumps_scenario(small_sim.scenario))


def test_validate_result_structure_detects_duplication(small_sim):
    result = build_result(small_sim)
    result["routes"].append(dict(result["routes"][0]))
    problems = validate_result_structure(result)
    assert any("дубликат" in p for p in problems)


def test_effective_scenario_reimports(small_sim):
    """Экспортированный effective_scenario загружается валидатором повторно."""
    text = dumps_scenario(small_sim.scenario)
    reimported = json.loads(text)
    ensure_valid(reimported)


def test_metrics_csv_content(small_sim):
    csv_text = metrics_csv(small_sim)
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("client_id")
    assert len(lines) == 1 + len(small_sim.clients)
    for cid in small_sim.clients:
        assert any(line.startswith(cid + ",") for line in lines[1:])


def test_full_scenario_export_route_count(scenarios):
    sim = simulate_scenario(scenarios["01_full_constellation.json"], with_backups=False)
    result = build_result(sim)
    assert len(result["routes"]) == 720 * 3
    assert validate_result_structure(result) == []
    # строгая официальная схема: только обязательные top-level поля
    assert set(result) == {"schema_version", "effective_scenario", "routes"}
    report = build_analysis_report(sim)
    assert report["routing_strategy"] == "min_distance"
    assert set(report["clients"]) == set(sim.clients)


def test_result_allows_extra_top_level_fields(small_sim):
    """Официальный формат допускает расширения; наш экспорт минимален."""
    result = build_result(small_sim)
    assert validate_result_structure(result) == []
    result["routing_strategy"] = "min_distance"
    assert validate_result_structure(result) == []
    assert set(build_result(small_sim)) == {"schema_version", "effective_scenario", "routes"}
