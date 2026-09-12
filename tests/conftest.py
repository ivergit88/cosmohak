"""Общие фикстуры тестов: пути, сценарии, синтетические графы."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from cosmo.graph import LinkGraph  # noqa: E402
from cosmo.validation import ensure_valid  # noqa: E402

DATA_DIR = ROOT / "data"
SCENARIO_FILES = sorted(DATA_DIR.glob("*.json"))


@pytest.fixture(scope="session")
def scenarios() -> dict[str, dict]:
    """Все четыре официальных сценария."""
    import json

    result = {}
    for path in SCENARIO_FILES:
        with open(path, "r", encoding="utf-8") as fh:
            result[path.name] = json.load(fh)
    return result


@pytest.fixture()
def small_scenario() -> dict:
    """Минимальный валидный сценарий: 6 отсчётов по 100 с, 3 спутника, 2 клиента, шлюз."""
    scenario = {
        "schema_version": "cosmo-A-1.0",
        "meta": {"id": "test_min", "title": "Тестовый"},
        "environment": {
            "altitude_km": 550.0,
            "inclination_deg": 87.0,
            "earth_angle0_deg": 0.0,
            "horizon_s": 600,
            "step_s": 100,
            "min_elevation_deg": 0.0,
            "isl_range_km": 5000.0,
            "target_availability": 0.9,
        },
        "design": {
            "launch_stage": 3,
            "planes": [{"id": "PA", "raan_deg": 0.0, "phase_deg": 0.0}],
            "satellites": [
                {"id": "T1", "plane_id": "PA", "slot_deg": 0.0, "launch_batch": 1},
                {"id": "T2", "plane_id": "PA", "slot_deg": 60.0, "launch_batch": 2},
                {"id": "T3", "plane_id": "PA", "slot_deg": 180.0, "launch_batch": 3},
            ],
        },
        "ground_sites": [
            {"id": "GW", "name": "шлюз", "role": "gateway", "lat_deg": 60.0, "lon_deg": 30.0},
            {"id": "CL1", "name": "клиент 1", "role": "client", "lat_deg": 70.0, "lon_deg": 60.0},
            {"id": "CL2", "name": "клиент 2", "role": "client", "lat_deg": 55.0, "lon_deg": 90.0},
        ],
        "failures": [],
        "gateway_outages": [],
    }
    ensure_valid(scenario)
    return scenario


def make_link_graph(
    sats: list[str],
    adj: dict[str, list[tuple[str, float]]],
    client_links: dict[str, list[tuple[str, float]]],
    gateway_links: dict[str, list[tuple[str, float]]],
    gateways: tuple[str, ...] = ("GW",),
    offline: tuple[str, ...] = (),
) -> LinkGraph:
    """Синтетический LinkGraph для юнит-тестов маршрутизации."""
    edge_set = set()
    for a, links in adj.items():
        for b, _w in links:
            edge_set.add(frozenset((a, b)))
    for a, links in {**client_links, **gateway_links}.items():
        for b, _w in links:
            edge_set.add(frozenset((a, b)))
    return LinkGraph(
        sat_ids=tuple(sats),
        sat_adj={s: tuple(sorted(adj.get(s, []))) for s in sats},
        client_links={k: tuple(sorted(v)) for k, v in client_links.items()},
        gateway_links={k: tuple(sorted(v)) for k, v in gateway_links.items()},
        clients=tuple(client_links.keys()),
        gateways=gateways,
        offline_gateways=frozenset(offline),
        active_sats=frozenset(sats),
        edge_set=frozenset(edge_set),
    )


def scenario_copy(scenario: dict) -> dict:
    return copy.deepcopy(scenario)
