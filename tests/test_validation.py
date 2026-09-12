"""Тесты валидации сценария (дружественные сообщения с путями полей)."""

from __future__ import annotations

import pytest

from cosmo.validation import ScenarioValidationError, ensure_valid, validate_scenario
from tests.conftest import scenario_copy


def test_valid_fixture_passes(small_scenario):
    assert validate_scenario(small_scenario) == []
    assert ensure_valid(small_scenario) is small_scenario


def test_all_official_scenarios_pass(scenarios):
    for name, scenario in scenarios.items():
        assert validate_scenario(scenario) == [], name
        ensure_valid(scenario)


def test_bad_schema_version(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["schema_version"] = "cosmo-B-9.9"
    errors = validate_scenario(bad)
    assert any("schema_version" in e for e in errors)


def test_duplicate_satellite_ids(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["design"]["satellites"][1]["id"] = "T1"
    errors = validate_scenario(bad)
    assert any("T1" in e and "не уникален" in e for e in errors)


def test_duplicate_ground_ids(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["ground_sites"][1]["id"] = "GW"
    errors = validate_scenario(bad)
    assert any("не уникален" in e for e in errors)


def test_missing_plane_reference_message_format(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["design"]["satellites"][1]["plane_id"] = "P9"
    errors = validate_scenario(bad)
    assert any(
        e.startswith("design.satellites[1].plane_id") and "P9" in e for e in errors
    ), errors


def test_invalid_coordinates(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["ground_sites"][0]["lat_deg"] = 123.0
    errors = validate_scenario(bad)
    assert any("lat_deg" in e and "[-90..90]" in e for e in errors)
    bad["ground_sites"][0]["lat_deg"] = 60.0
    bad["ground_sites"][0]["lon_deg"] = -999.0
    errors = validate_scenario(bad)
    assert any("lon_deg" in e and "[-180..180]" in e for e in errors)


def test_invalid_time_grid_not_multiple(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["environment"]["step_s"] = 250
    errors = validate_scenario(bad)
    assert any("не кратен" in e for e in errors)


def test_invalid_time_grid_non_integer(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["environment"]["step_s"] = 12.5
    errors = validate_scenario(bad)
    assert any("целое число" in e for e in errors)


def test_invalid_outage_beyond_horizon(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["failures"] = [{"satellite_id": "T1", "start_s": 0, "end_s": 10_000}]
    errors = validate_scenario(bad)
    assert any("горизонт" in e for e in errors)


def test_invalid_outage_unknown_satellite(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["failures"] = [{"satellite_id": "NOPE", "start_s": 0, "end_s": 100}]
    errors = validate_scenario(bad)
    assert any("NOPE" in e for e in errors)


def test_invalid_outage_reversed_interval(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["failures"] = [{"satellite_id": "T1", "start_s": 500, "end_s": 100}]
    errors = validate_scenario(bad)
    assert any("некорректен" in e for e in errors)


def test_gateway_outage_unknown_gateway(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["gateway_outages"] = [{"gateway_id": "CL1", "start_s": 0, "end_s": 100}]
    errors = validate_scenario(bad)
    assert any("шлюза с таким идентификатором" in e for e in errors)


def test_no_client(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["ground_sites"] = [g for g in bad["ground_sites"] if g["role"] != "client"]
    errors = validate_scenario(bad)
    assert any('ролью "client"' in e for e in errors)


def test_launch_stage_invalid(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["design"]["launch_stage"] = 4
    errors = validate_scenario(bad)
    assert any("launch_stage" in e for e in errors)


def test_multiple_errors_collected(small_scenario):
    bad = scenario_copy(small_scenario)
    bad["environment"]["altitude_km"] = 10.0
    bad["design"]["satellites"][2]["launch_batch"] = 7
    errors = validate_scenario(bad)
    assert len(errors) >= 2


def test_official_validate_as_final_check(small_scenario):
    """ensure_valid доходит до официальной geometry.validate и пропускает корректный сценарий."""
    ensure_valid(small_scenario)
    with pytest.raises((ScenarioValidationError, ValueError)):
        ensure_valid({"schema_version": "cosmo-A-1.0"})
