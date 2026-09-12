"""Дружественная валидация сценария cosmo-A-1.0.

Собственная проверка собирает ВСЕ ошибки (а не только первую) и
формулирует их с указанием пути к полю, например:

    design.satellites[7].plane_id = "P9": плоскость P9 отсутствует в design.planes

После собственной проверки вызывается официальная geometry.validate
как финальный safety check (см. ensure_valid).
"""

from __future__ import annotations

from typing import Any

from . import geometry_adapter
from .models import LAUNCH_BATCHES, LAUNCH_STAGES, is_finite_number

SCHEMA_VERSION = "cosmo-A-1.0"


class ScenarioValidationError(ValueError):
    """Ошибка валидации сценария со списком человекочитаемых сообщений."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        shown = errors[:12]
        suffix = "" if len(errors) <= 12 else f"\n… и ещё {len(errors) - 12} ошибок"
        super().__init__("Сценарий не прошёл проверку:\n" + "\n".join(f"• {e}" for e in shown) + suffix)


def _require_dict(payload: Any, path: str, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append(f"{path}: ожидается объект (dict), получено {type(payload).__name__}")


def _require_list(payload: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(payload, list):
        errors.append(f"{path}: ожидается список, получено {type(payload).__name__}")
        return []
    return payload


def validate_scenario(scenario: Any) -> list[str]:
    """Проверяет сценарий и возвращает список ошибок (пустой = всё корректно)."""
    errors: list[str] = []
    _require_dict(scenario, "scenario", errors)
    if errors:
        return errors

    if scenario.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f'schema_version = {scenario.get("schema_version")!r}: '
            f'ожидается "{SCHEMA_VERSION}"'
        )

    env = scenario.get("environment")
    _require_dict(env, "environment", errors)
    if isinstance(env, dict):
        _validate_environment(env, errors)

    design = scenario.get("design")
    _require_dict(design, "design", errors)
    if isinstance(design, dict):
        _validate_design(design, errors)

    ground = _require_list(scenario.get("ground_sites"), "ground_sites", errors)
    ground_ids = _validate_ground_sites(ground, errors)
    sat_ids = [s.get("id") for s in design.get("satellites", [])] if isinstance(design, dict) else []

    failures = _require_list(scenario.get("failures", []), "failures", errors)
    _validate_outages(failures, "failures", "satellite_id", set(sat_ids), env, errors, label="спутника")
    gw_outages = _require_list(scenario.get("gateway_outages", []), "gateway_outages", errors)
    gateway_ids = {g["id"] for g in ground if isinstance(g, dict) and g.get("role") == "gateway"}
    _validate_outages(gw_outages, "gateway_outages", "gateway_id", gateway_ids, env, errors, label="шлюза")

    overlap = ground_ids & set(sat_ids)
    if overlap:
        errors.append(
            f"Идентификаторы наземных пунктов и спутников пересекаются: {sorted(overlap)}"
        )
    return errors


def _validate_environment(env: dict[str, Any], errors: list[str]) -> None:
    float_fields = (
        "altitude_km",
        "inclination_deg",
        "earth_angle0_deg",
        "min_elevation_deg",
        "isl_range_km",
        "target_availability",
    )
    for key in float_fields:
        if key not in env:
            errors.append(f"environment.{key}: поле отсутствует")
        elif not is_finite_number(env[key]):
            errors.append(f"environment.{key} = {env[key]!r}: требуется конечное число")

    for key in ("horizon_s", "step_s"):
        if key not in env:
            errors.append(f"environment.{key}: поле отсутствует")
        elif not isinstance(env[key], int) or isinstance(env[key], bool):
            errors.append(f"environment.{key} = {env[key]!r}: требуется целое число секунд")

    if is_finite_number(env.get("altitude_km")) and not (200 <= env["altitude_km"] <= 1200):
        errors.append(f"environment.altitude_km = {env['altitude_km']}: допустимый диапазон 200..1200")
    if is_finite_number(env.get("inclination_deg")) and not (0 < env["inclination_deg"] <= 180):
        errors.append(f"environment.inclination_deg = {env['inclination_deg']}: допустимый диапазон (0..180]")
    if is_finite_number(env.get("min_elevation_deg")) and not (0 <= env["min_elevation_deg"] < 90):
        errors.append(f"environment.min_elevation_deg = {env['min_elevation_deg']}: допустимый диапазон [0..90)")
    if is_finite_number(env.get("isl_range_km")) and not (0 < env["isl_range_km"] <= 10000):
        errors.append(f"environment.isl_range_km = {env['isl_range_km']}: допустимый диапазон (0..10000]")
    if is_finite_number(env.get("target_availability")) and not (0 <= env["target_availability"] <= 1):
        errors.append(f"environment.target_availability = {env['target_availability']}: допустимый диапазон [0..1]")

    horizon, step = env.get("horizon_s"), env.get("step_s")
    if isinstance(horizon, int) and isinstance(step, int) and not isinstance(horizon, bool) and not isinstance(step, bool):
        if step <= 0:
            errors.append(f"environment.step_s = {step}: шаг должен быть положительным")
        if horizon <= 0:
            errors.append(f"environment.horizon_s = {horizon}: горизонт должен быть положительным")
        if step > horizon:
            errors.append(f"environment.step_s = {step} больше environment.horizon_s = {horizon}")
        elif step > 0 and horizon % step != 0:
            errors.append(
                f"environment.horizon_s = {horizon} не кратен environment.step_s = {step}"
            )
        if horizon > 172800:
            errors.append(f"environment.horizon_s = {horizon}: максимум 172800 (48 часов)")


def _validate_design(design: dict[str, Any], errors: list[str]) -> None:
    stage = design.get("launch_stage")
    if not isinstance(stage, int) or isinstance(stage, bool) or stage not in LAUNCH_STAGES:
        errors.append(f"design.launch_stage = {stage!r}: допустимы значения 1, 2 или 3")

    planes = _require_list(design.get("planes"), "design.planes", errors)
    plane_ids: set[str] = set()
    if isinstance(planes, list):
        if not planes:
            errors.append("design.planes: список пуст — требуется хотя бы одна плоскость")
        for idx, plane in enumerate(planes):
            path = f"design.planes[{idx}]"
            _require_dict(plane, path, errors)
            if not isinstance(plane, dict):
                continue
            pid = plane.get("id")
            if not isinstance(pid, str) or not pid:
                errors.append(f"{path}.id = {pid!r}: требуется непустая строка")
            elif pid in plane_ids:
                errors.append(f"{path}.id = {pid!r}: идентификатор плоскости не уникален")
            else:
                plane_ids.add(pid)
            for key in ("raan_deg", "phase_deg"):
                value = plane.get(key)
                if not is_finite_number(value):
                    errors.append(f"{path}.{key} = {value!r}: требуется конечное число")
                elif not (0 <= value < 360):
                    errors.append(f"{path}.{key} = {value}: допустимый диапазон [0..360)")

    sats = _require_list(design.get("satellites"), "design.satellites", errors)
    sat_ids: set[str] = set()
    if isinstance(sats, list):
        if not sats:
            errors.append("design.satellites: список пуст — требуется хотя бы один спутник")
        for idx, sat in enumerate(sats):
            path = f"design.satellites[{idx}]"
            _require_dict(sat, path, errors)
            if not isinstance(sat, dict):
                continue
            sid = sat.get("id")
            if not isinstance(sid, str) or not sid:
                errors.append(f"{path}.id = {sid!r}: требуется непустая строка")
            elif sid in sat_ids:
                errors.append(f"{path}.id = {sid!r}: идентификатор спутника не уникален")
            else:
                sat_ids.add(sid)
            plane_id = sat.get("plane_id")
            if plane_id not in plane_ids:
                errors.append(
                    f'{path}.plane_id = {plane_id!r}: плоскость {plane_id!r} отсутствует в design.planes'
                )
            batch = sat.get("launch_batch")
            if not isinstance(batch, int) or isinstance(batch, bool) or batch not in LAUNCH_BATCHES:
                errors.append(f"{path}.launch_batch = {batch!r}: допустимы значения 1, 2 или 3")
            if not is_finite_number(sat.get("slot_deg")):
                errors.append(
                    f"{path}.slot_deg = {sat.get('slot_deg')!r}: требуется конечное число"
                )


def _validate_ground_sites(ground: list[Any], errors: list[str]) -> set[str]:
    ids: set[str] = set()
    roles: dict[str, int] = {"client": 0, "gateway": 0}
    for idx, site in enumerate(ground):
        path = f"ground_sites[{idx}]"
        _require_dict(site, path, errors)
        if not isinstance(site, dict):
            continue
        gid = site.get("id")
        if not isinstance(gid, str) or not gid:
            errors.append(f"{path}.id = {gid!r}: требуется непустая строка")
        elif gid in ids:
            errors.append(f"{path}.id = {gid!r}: идентификатор наземного пункта не уникален")
        else:
            ids.add(gid)
        role = site.get("role")
        if role in roles:
            roles[role] += 1
        else:
            errors.append(f'{path}.role = {role!r}: допустимы значения "client" или "gateway"')
        for key, lo, hi in (("lat_deg", -90, 90), ("lon_deg", -180, 180)):
            value = site.get(key)
            if not is_finite_number(value):
                errors.append(f"{path}.{key} = {value!r}: требуется конечное число")
            elif not (lo <= value <= hi):
                errors.append(f"{path}.{key} = {value}: допустимый диапазон [{lo}..{hi}]")
    if roles["client"] == 0:
        errors.append('ground_sites: требуется хотя бы один пункт с ролью "client"')
    if roles["gateway"] == 0:
        errors.append('ground_sites: требуется хотя бы один пункт с ролью "gateway"')
    return ids


def _validate_outages(
    outages: list[Any],
    path: str,
    id_key: str,
    valid_ids: set[str],
    env: Any,
    errors: list[str],
    label: str,
) -> None:
    horizon = env.get("horizon_s") if isinstance(env, dict) else None
    for idx, outage in enumerate(outages):
        opath = f"{path}[{idx}]"
        _require_dict(outage, opath, errors)
        if not isinstance(outage, dict):
            continue
        oid = outage.get(id_key)
        if oid not in valid_ids:
            errors.append(f"{opath}.{id_key} = {oid!r}: {label} с таким идентификатором отсутствует")
        for key in ("start_s", "end_s"):
            if not is_finite_number(outage.get(key)):
                errors.append(f"{opath}.{key} = {outage.get(key)!r}: требуется конечное число")
        start, end = outage.get("start_s"), outage.get("end_s")
        if is_finite_number(start) and is_finite_number(end):
            if not 0 <= start < end:
                errors.append(
                    f"{opath}: интервал [{start}; {end}) некорректен — требуется 0 <= start_s < end_s"
                )
            elif isinstance(horizon, (int, float)) and end > horizon:
                errors.append(
                    f"{opath}: конец интервала end_s = {end} выходит за горизонт расчёта {horizon}"
                )


def ensure_valid(scenario: Any) -> dict[str, Any]:
    """Полная проверка: собственная + официальная geometry.validate.

    Возвращает сценарий без изменений; бросает ScenarioValidationError
    (наши сообщения) или ValueError официального модуля как последний
    рубеж защиты.
    """
    errors = validate_scenario(scenario)
    if errors:
        raise ScenarioValidationError(errors)
    geometry_adapter.validate_official(scenario)
    return scenario
