"""Parity-тесты: собственный движок (формулы «Описание данных») против официального geometry.py."""

from __future__ import annotations

import pytest

from cosmo.geometry_adapter import (
    compare_snapshots,
    reference_module,
    snapshot,
    snapshot_own,
    time_grid,
)

CHECK_TS = (0, 1, 6000, 21600, 43200, 86280)


@pytest.mark.parametrize("scenario_name", [
    "01_full_constellation.json",
    "02_first_launch.json",
    "03_satellite_outages.json",
    "04_link_range.json",
])
def test_own_engine_matches_reference(scenarios, scenario_name):
    scenario = scenarios[scenario_name]
    for t in CHECK_TS:
        if t >= scenario["environment"]["horizon_s"]:
            continue
        official = snapshot(scenario, t)
        own = snapshot_own(scenario, t)
        issues = compare_snapshots(official, own, tol=1e-7)
        assert issues == [], (scenario_name, t, issues[:5])


def test_reference_module_is_official_file():
    """Используется именно vendor/geometry.py (reference implementation)."""
    module = reference_module()
    assert hasattr(module, "snapshot")
    assert hasattr(module, "validate")
    assert hasattr(module, "positions")


def test_simulation_edges_come_from_official_snapshot(scenarios):
    """Маршруты строятся на рёбрах официального snapshot (spot-check)."""
    from cosmo.graph import build_link_graph
    from cosmo.routing import validate_path

    scenario = scenarios["01_full_constellation.json"]
    for t in (0, 43200):
        snap = snapshot(scenario, t)
        graph = build_link_graph(snap, scenario)
        for client in graph.clients:
            from cosmo.routing import find_route

            route = find_route(graph, client)
            if route.connected:
                assert validate_path(snap, scenario, client, route.path) == []


def test_grid_parity_with_official_usage(scenarios):
    """Официальная документация: отсчёты 0,120,…,86280 (720 шт.), конец не включён."""
    grid = time_grid(scenarios["01_full_constellation.json"])
    assert len(grid) == 720 and grid[-1] == 86280
    ref = reference_module()
    assert ref is not None
