"""Адаптер официального расчётного модуля geometry.py.

Официальный модуль (vendor/geometry.py) — reference implementation:
его load/validate/positions/snapshot используются как единственный
источник геометрии в расчётах. Здесь он загружается по пути
относительно пакета (никаких абсолютных локальных путей).

Дополнительно реализован собственный движок (positions_own /
snapshot_own) строго по формулам документа «Описание данных» —
он применяется в parity-тестах: результаты обоих движков обязаны
совпадать для всех сценариев и моментов времени.
"""

from __future__ import annotations

import importlib.util
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

R_EARTH = 6371.0
MU = 398600.435507
OMEGA_EARTH = 2 * math.pi / 86164.09054

_VENDOR_PATH = Path(__file__).resolve().parents[2] / "vendor" / "geometry.py"


@lru_cache(maxsize=1)
def reference_module() -> Any:
    """Загружает vendor/geometry.py как отдельный модуль (один раз)."""
    if not _VENDOR_PATH.exists():
        raise FileNotFoundError(f"Официальный модуль не найден: {_VENDOR_PATH}")
    spec = importlib.util.spec_from_file_location("reference_geometry", _VENDOR_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - защитный случай
        raise ImportError("Не удалось создать spec для reference_geometry")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_official(scenario: dict[str, Any]) -> None:
    """Официальная проверка geometry.validate (финальный safety check)."""
    reference_module().validate(scenario)


def load_file(path: str | Path) -> dict[str, Any]:
    """Читает JSON-сценарий из файла (UTF-8)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def time_grid(scenario: dict[str, Any]) -> list[int]:
    """Расчётная сетка: 0, step, 2*step, …; правый конец горизонта НЕ включается.

    Формат «Описание данных»: каждый отсчёт представляет интервал
    длиной step_s, начиная с этого момента.
    """
    env = scenario["environment"]
    horizon, step = int(env["horizon_s"]), int(env["step_s"])
    return list(range(0, horizon, step))


def positions(scenario: dict[str, Any], t_s: float) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Позиции спутников через официальный модуль.

    Возвращает (ids, инерциальные координаты [км], координаты во
    вращающейся системе Земли [км]). Контакты в модели считаются в
    инерциальной системе (см. snapshot официального модуля).
    """
    return reference_module().positions(scenario, t_s)


def snapshot(scenario: dict[str, Any], t_s: float) -> dict[str, Any]:
    """Состояние сети в момент t_s через официальный модуль."""
    return reference_module().snapshot(scenario, float(t_s))


# ---------------------------------------------------------------------------
# Собственный движок по формулам «Описание данных» (для parity-тестов).
# ---------------------------------------------------------------------------

def positions_own(scenario: dict[str, Any], t_s: float) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Позиции спутников по формулам документа (круговая орбита, сферическая Земля)."""
    env, design = scenario["environment"], scenario["design"]
    pmap = {p["id"]: p for p in design["planes"]}
    r = R_EARTH + env["altitude_km"]
    n = math.sqrt(MU / r**3)
    inc = math.radians(env["inclination_deg"])
    u = np.array([math.radians(x["slot_deg"] + pmap[x["plane_id"]]["phase_deg"]) + n * t_s for x in design["satellites"]])
    om = np.array([math.radians(pmap[x["plane_id"]]["raan_deg"]) for x in design["satellites"]])
    cu, su, co, so = np.cos(u), np.sin(u), np.cos(om), np.sin(om)
    xyz = r * np.stack(
        (co * cu - so * su * math.cos(inc), so * cu + co * su * math.cos(inc), su * math.sin(inc)), axis=1
    )
    th = math.radians(env["earth_angle0_deg"]) + OMEGA_EARTH * t_s
    c, s = math.cos(th), math.sin(th)
    fixed = xyz @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return [x["id"] for x in design["satellites"]], xyz, fixed


def ground_position_own(site: dict[str, Any]) -> np.ndarray:
    lat, lon = math.radians(site["lat_deg"]), math.radians(site["lon_deg"])
    return R_EARTH * np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])


def snapshot_own(scenario: dict[str, Any], t_s: float) -> dict[str, Any]:
    """Состояние сети по формулам документа — структурно идентично official snapshot."""
    env, design = scenario["environment"], scenario["design"]
    ids, _, xyz = positions_own(scenario, t_s)
    failed = {f["satellite_id"] for f in scenario["failures"] if f["start_s"] <= t_s < f["end_s"]}
    active = np.array(
        [sat["launch_batch"] <= design["launch_stage"] and sat["id"] not in failed for sat in design["satellites"]]
    )
    i, j = np.triu_indices(len(ids), 1)
    delta = xyz[j] - xyz[i]
    dist = np.linalg.norm(delta, axis=1)
    denom = np.sum(delta * delta, axis=1)
    lam = np.clip(-np.sum(xyz[i] * delta, axis=1) / np.maximum(denom, 1e-12), 0, 1)
    closest = np.linalg.norm(xyz[i] + lam[:, None] * delta, axis=1)
    ok = (dist < env["isl_range_km"]) & (closest > R_EARTH) & active[i] & active[j]
    edges = [[ids[a], ids[b], float(dd)] for a, b, dd in zip(i[ok], j[ok], dist[ok])]
    elevations: dict[str, dict[str, float]] = {}
    for site in scenario["ground_sites"]:
        gp = ground_position_own(site)
        dif = xyz - gp
        dl = np.linalg.norm(dif, axis=1)
        el = np.degrees(np.arcsin(np.clip(dif @ (gp / R_EARTH) / dl, -1, 1)))
        elevations[site["id"]] = {sid: float(el[k]) for k, sid in enumerate(ids) if active[k]}
        offline = any(
            f["gateway_id"] == site["id"] and f["start_s"] <= t_s < f["end_s"]
            for f in scenario["gateway_outages"]
        )
        vis = (el >= env["min_elevation_deg"]) & active & (not offline)
        edges.extend([[site["id"], ids[k], float(dl[k])] for k in np.where(vis)[0]])
    return {
        "t_s": t_s,
        "satellites": [
            {"id": sid, "x_km": float(xyz[k, 0]), "y_km": float(xyz[k, 1]), "z_km": float(xyz[k, 2]), "active": bool(active[k])}
            for k, sid in enumerate(ids)
        ],
        "edges": edges,
        "elevation_deg": elevations,
    }


def compare_snapshots(a: dict[str, Any], b: dict[str, Any], tol: float = 1e-8) -> list[str]:
    """Сравнение двух snapshot-ов (parity official vs own). Возвращает список расхождений."""
    issues: list[str] = []
    if a["t_s"] != b["t_s"]:
        issues.append(f"t_s: {a['t_s']} != {b['t_s']}")
    sa = {s["id"]: s for s in a["satellites"]}
    sb = {s["id"]: s for s in b["satellites"]}
    if set(sa) != set(sb):
        issues.append("списки спутников различаются")
        return issues
    for sid in sa:
        for key in ("x_km", "y_km", "z_km"):
            if abs(sa[sid][key] - sb[sid][key]) > tol:
                issues.append(f"{sid}.{key}: {sa[sid][key]} != {sb[sid][key]}")
        if sa[sid]["active"] != sb[sid]["active"]:
            issues.append(f"{sid}.active: {sa[sid]['active']} != {sb[sid]['active']}")
    ea = {(e[0], e[1]) for e in a["edges"]}
    eb = {(e[0], e[1]) for e in b["edges"]}
    if ea != eb:
        only_a, only_b = ea - eb, eb - ea
        if only_a:
            issues.append(f"рёбра только в official: {sorted(only_a)[:5]}")
        if only_b:
            issues.append(f"рёбра только в own: {sorted(only_b)[:5]}")
    da = {tuple(sorted(e[:2])): e[2] for e in a["edges"]}
    db = {tuple(sorted(e[:2])): e[2] for e in b["edges"]}
    for key in da.keys() & db.keys():
        if abs(da[key] - db[key]) > tol:
            issues.append(f"дистанция {key}: {da[key]} != {db[key]}")
    for gid in set(a["elevation_deg"]) | set(b["elevation_deg"]):
        for sid, el_a in a["elevation_deg"].get(gid, {}).items():
            el_b = b["elevation_deg"].get(gid, {}).get(sid)
            if el_b is None or abs(el_a - el_b) > tol:
                issues.append(f"elevation[{gid}][{sid}]: {el_a} != {el_b}")
    return issues


def active_flags(scenario: dict[str, Any], t_s: float) -> dict[str, bool]:
    """Активность каждого спутника в момент t (этап развёртывания + отказы).

    Границы отказа: start_s включается, end_s исключается — [start; end).
    """
    design = scenario["design"]
    stage = design["launch_stage"]
    failed = {f["satellite_id"] for f in scenario["failures"] if f["start_s"] <= t_s < f["end_s"]}
    return {s["id"]: (s["launch_batch"] <= stage and s["id"] not in failed) for s in design["satellites"]}
