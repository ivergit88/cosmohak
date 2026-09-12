"""Torture-тесты валидации: границы диапазонов, типы, пропуски, ссылки.

Каждый кейс — мутация корректного сценария. Проверяется и факт отказа,
и человекочитаемое сообщение с путём к полю.
"""

from __future__ import annotations

import copy

import pytest

from cosmo.validation import ScenarioValidationError, validate_scenario
from tests.conftest import scenario_copy


# ---------------------------------------------------------------- границы ОК
@pytest.mark.parametrize("field,lo,hi", [
    ("altitude_km", 200.0, 1200.0),
    ("inclination_deg", 0.001, 180.0),
    ("min_elevation_deg", 0.0, 89.999),
    ("isl_range_km", 0.001, 10000.0),
    ("target_availability", 0.0, 1.0),
])
def test_boundary_values_are_valid(small_scenario, field, lo, hi):
    for value in (lo, hi):
        scenario = scenario_copy(small_scenario)
        scenario["environment"][field] = value
        assert validate_scenario(scenario) == [], (field, value)


# ------------------------------------------------------------ границы FAIL
@pytest.mark.parametrize("field,value,path", [
    ("altitude_km", 199.9, "environment.altitude_km"),
    ("altitude_km", 1200.1, "environment.altitude_km"),
    ("inclination_deg", 0.0, "environment.inclination_deg"),
    ("inclination_deg", 180.1, "environment.inclination_deg"),
    ("min_elevation_deg", -0.1, "environment.min_elevation_deg"),
    ("min_elevation_deg", 90.0, "environment.min_elevation_deg"),
    ("isl_range_km", 10000.1, "environment.isl_range_km"),
    ("target_availability", 1.0001, "environment.target_availability"),
    ("target_availability", -0.0001, "environment.target_availability"),
])
def test_out_of_range_rejected_with_path(small_scenario, field, value, path):
    scenario = scenario_copy(small_scenario)
    scenario["environment"][field] = value
    errors = validate_scenario(scenario)
    assert any(path in e for e in errors), (field, value, errors)


def test_lat_lon_boundaries(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["ground_sites"][0]["lat_deg"] = 90.0
    scenario["ground_sites"][0]["lon_deg"] = 180.0
    assert validate_scenario(scenario) == []
    scenario["ground_sites"][0]["lat_deg"] = 90.1
    errors = validate_scenario(scenario)
    assert any("lat_deg" in e for e in errors)
    scenario["ground_sites"][0]["lat_deg"] = 90.0
    scenario["ground_sites"][0]["lon_deg"] = 180.0001
    errors = validate_scenario(scenario)
    assert any("lon_deg" in e for e in errors)


# ------------------------------------------------------------------ сетка
@pytest.mark.parametrize("horizon,step", [
    (600, 100),      # кратно — ок
    (86400, 120),    # официальный кейс
    (600, 600),      # один отсчёт — ок
    (599, 100),      # не кратно — отказ
    (100, 600),      # шаг больше горизонта — отказ
    (600, 0),        # нулевой шаг
    (600, -100),     # отрицательный шаг
    (0, 100),        # нулевой горизонт
    (172801, 100),   # выше лимита горизонта
])
def test_time_grid_matrix(small_scenario, horizon, step):
    scenario = scenario_copy(small_scenario)
    scenario["environment"]["horizon_s"] = horizon
    scenario["environment"]["step_s"] = step
    multiple = horizon > 0 and 0 < step <= horizon and horizon % step == 0 and horizon <= 172800
    errors = validate_scenario(scenario)
    assert (errors == []) is multiple, (horizon, step, errors)


# ------------------------------------------------------------------ типы
def test_bool_is_not_a_number(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["environment"]["altitude_km"] = True  # bool — не число
    errors = validate_scenario(scenario)
    assert any("конечное число" in e for e in errors)


def test_bool_launch_stage_rejected(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["launch_stage"] = True
    errors = validate_scenario(scenario)
    assert any("launch_stage" in e for e in errors)


def test_string_number_rejected(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["environment"]["altitude_km"] = "550"
    errors = validate_scenario(scenario)
    assert any("altitude_km" in e for e in errors)


def test_nan_rejected(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["environment"]["altitude_km"] = float("nan")
    errors = validate_scenario(scenario)
    assert any("altitude_km" in e for e in errors)


def test_infinity_rejected(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["failures"] = [{"satellite_id": "T1", "start_s": 0, "end_s": float("inf")}]
    errors = validate_scenario(scenario)
    assert any("end_s" in e for e in errors)


# --------------------------------------------------------------- структура
def test_missing_field(small_scenario):
    scenario = scenario_copy(small_scenario)
    del scenario["environment"]["isl_range_km"]
    errors = validate_scenario(scenario)
    assert any("isl_range_km" in e and "отсутствует" in e for e in errors)


def test_missing_design_section(small_scenario):
    scenario = scenario_copy(small_scenario)
    del scenario["design"]
    errors = validate_scenario(scenario)
    assert any("design" in e for e in errors)


def test_top_level_not_dict():
    errors = validate_scenario([1, 2, 3])
    assert any("dict" in e for e in errors)


def test_empty_planes_and_satellites(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["planes"] = []
    scenario["design"]["satellites"] = []
    errors = validate_scenario(scenario)
    assert any("design.planes" in e for e in errors)
    assert any("design.satellites" in e for e in errors)


def test_plane_angle_range(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["planes"][0]["raan_deg"] = 360.0  # 360 недопустим — [0..360)
    errors = validate_scenario(scenario)
    assert any("raan_deg" in e for e in errors)
    scenario["design"]["planes"][0]["raan_deg"] = 359.9
    scenario["design"]["planes"][0]["phase_deg"] = -0.1
    errors = validate_scenario(scenario)
    assert any("phase_deg" in e for e in errors)


def test_duplicate_plane_id(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["planes"].append({"id": "PA", "raan_deg": 10.0, "phase_deg": 10.0})
    errors = validate_scenario(scenario)
    assert any("плоскости не уникален" in e and "PA" in e for e in errors)


def test_satellite_unknown_plane(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["satellites"][0]["plane_id"] = "NOPE"
    errors = validate_scenario(scenario)
    assert any("NOPE" in e for e in errors)


def test_ground_id_collides_with_satellite(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["ground_sites"][0]["id"] = "T1"
    errors = validate_scenario(scenario)
    assert any("пересекаются" in e for e in errors)


def test_gateway_outage_reference_clint_rejected(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["gateway_outages"] = [{"gateway_id": "CL1", "start_s": 0, "end_s": 100}]
    errors = validate_scenario(scenario)
    assert any("шлюза" in e for e in errors)


def test_failure_zero_duration(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["failures"] = [{"satellite_id": "T1", "start_s": 100, "end_s": 100}]
    errors = validate_scenario(scenario)
    assert any("некорректен" in e for e in errors)


def test_failure_negative_start(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["failures"] = [{"satellite_id": "T1", "start_s": -1, "end_s": 100}]
    errors = validate_scenario(scenario)
    assert any("некорректен" in e for e in errors)


def test_schema_version_missing(small_scenario):
    scenario = scenario_copy(small_scenario)
    del scenario["schema_version"]
    errors = validate_scenario(scenario)
    assert any("schema_version" in e for e in errors)


def test_launch_batch_and_stage_values(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["design"]["satellites"][0]["launch_batch"] = 4
    errors = validate_scenario(scenario)
    assert any("launch_batch" in e for e in errors)
    scenario["design"]["satellites"][0]["launch_batch"] = 1
    for stage in (0, 4, "3", 3.0):
        scenario["design"]["launch_stage"] = stage if not isinstance(stage, float) else 3
        if stage in (0, 4, "3"):
            assert validate_scenario(scenario), stage
    scenario["design"]["launch_stage"] = 3
    assert validate_scenario(scenario) == []


def test_role_renamed_to_station(small_scenario):
    scenario = scenario_copy(small_scenario)
    scenario["ground_sites"][2]["role"] = "station"
    errors = validate_scenario(scenario)
    assert any("role" in e for e in errors)


def test_errors_are_human_readable(small_scenario):
    """Все сообщения содержат путь к полю и без traceback-жаргона."""
    scenario = scenario_copy(small_scenario)
    scenario["design"]["satellites"][1] = {
        "id": "T2", "plane_id": "GHOST", "slot_deg": 60.0, "launch_batch": 2,
    }
    errors = validate_scenario(scenario)
    assert errors, "ожидается хотя бы одна ошибка"
    for e in errors:
        assert any(ch.isdigit() for ch in e) or "." in e  # есть путь/индекс
        assert not e.startswith("Traceback")


def test_structurally_broken_json_never_crashes_validator(small_scenario):
    """Мусорные структуры дают ошибки-строки, а не AttributeError/TypeError/KeyError."""
    cases = []
    for broken_sat in (None, 123, "строка", []):
        sc = scenario_copy(small_scenario)
        sc["design"]["satellites"].insert(0, broken_sat)
        cases.append(("satellite=" + type(broken_sat).__name__, sc))
    sc = scenario_copy(small_scenario)
    sc["design"]["satellites"][0]["id"] = {}
    cases.append(("satellite.id={}", sc))
    sc = scenario_copy(small_scenario)
    sc["design"]["satellites"][0]["plane_id"] = []
    cases.append(("plane_id=[]", sc))
    sc = scenario_copy(small_scenario)
    sc["ground_sites"][0] = {"role": "gateway", "lat_deg": 0.0, "lon_deg": 0.0}
    cases.append(("gateway без id", sc))
    sc = scenario_copy(small_scenario)
    sc["ground_sites"][0]["id"] = {}
    cases.append(("gateway.id={}", sc))
    sc = scenario_copy(small_scenario)
    sc["ground_sites"][0]["role"] = []
    cases.append(("role=[]", sc))
    sc = scenario_copy(small_scenario)
    sc["design"]["satellites"] = None
    cases.append(("satellites=null", sc))
    sc = scenario_copy(small_scenario)
    del sc["failures"]
    cases.append(("нет failures", sc))
    sc = scenario_copy(small_scenario)
    del sc["gateway_outages"]
    cases.append(("нет gateway_outages", sc))
    sc = scenario_copy(small_scenario)
    sc["failures"] = [{"satellite_id": [], "start_s": 0, "end_s": 100}]
    cases.append(("failure.id=[]", sc))

    for name, broken in cases:
        errors = validate_scenario(broken)
        assert errors, name  # ошибка обязана быть
        for e in errors:
            assert isinstance(e, str) and e, name


def test_missing_outage_sections_are_errors(small_scenario):
    sc = scenario_copy(small_scenario)
    del sc["failures"]
    assert any("failures" in e for e in validate_scenario(sc))
    sc = scenario_copy(small_scenario)
    del sc["gateway_outages"]
    assert any("gateway_outages" in e for e in validate_scenario(sc))
