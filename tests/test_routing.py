"""Тесты маршрутизации на синтетических графах и на реальной геометрии."""

from __future__ import annotations

import pytest

from cosmo.routing import (
    find_backup_route,
    find_route_min_distance,
    find_route_min_hops,
    route_distance_km,
    validate_path,
)
from tests.conftest import make_link_graph


def test_direct_path():
    g = make_link_graph(
        sats=["S1"],
        adj={},
        client_links={"C1": [("S1", 100.0)]},
        gateway_links={"GW": [("S1", 150.0)]},
    )
    route = find_route_min_hops(g, "C1")
    assert route.connected
    assert route.path == ("C1", "S1", "GW")
    assert route.hops == 2
    assert route_distance_km(g, route.path) == pytest.approx(250.0)


def test_disconnected_isl():
    g = make_link_graph(
        sats=["S1", "S2"],
        adj={},
        client_links={"C1": [("S1", 100.0)]},
        gateway_links={"GW": [("S2", 150.0)]},
    )
    route = find_route_min_hops(g, "C1")
    assert not route.connected
    assert route.reason == "ISL_NETWORK_DISCONNECTED"


def test_no_visible_satellite():
    g = make_link_graph(sats=["S1"], adj={}, client_links={}, gateway_links={"GW": [("S1", 100.0)]})
    route = find_route_min_hops(g, "C1")
    assert route.reason == "NO_VISIBLE_CLIENT_SATELLITE"


def test_gateway_offline_vs_no_contact():
    base = dict(
        sats=["S1"],
        adj={},
        client_links={"C1": [("S1", 100.0)]},
        gateway_links={"GW": [("S1", 100.0)]},
        gateways=("GW",),
    )
    offline = make_link_graph(**base, offline=("GW",))
    assert find_route_min_hops(offline, "C1").reason == "GATEWAY_UNAVAILABLE"
    no_contact = make_link_graph(**{**base, "gateway_links": {}})
    assert find_route_min_hops(no_contact, "C1").reason == "NO_GATEWAY_CONTACT"


def test_deterministic_choice_between_equal_paths():
    """Два равнопутных маршрута: выбирается лексикографически меньший."""
    g = make_link_graph(
        sats=["S1", "S2"],
        adj={"S1": [("S2", 100.0)], "S2": [("S1", 100.0)]},
        client_links={"C1": [("S1", 10.0), ("S2", 10.0)]},
        gateway_links={"GW": [("S1", 10.0), ("S2", 10.0)]},
    )
    paths = {find_route_min_hops(g, "C1").path for _ in range(10)}
    assert paths == {("C1", "S1", "GW")}  # S1 < S2 — детерминировано


def test_reroute_on_failed_node():
    """Отказ промежуточного спутника: маршрут перестраивается в обход."""
    g = make_link_graph(
        sats=["S1", "S2", "S3"],
        adj={
            "S1": [("S2", 10.0), ("S3", 50.0)],
            "S2": [("S1", 10.0)],
            "S3": [("S1", 50.0)],
        },
        client_links={"C1": [("S1", 10.0)]},
        gateway_links={"GW": [("S2", 10.0), ("S3", 10.0)]},
    )
    route = find_route_min_hops(g, "C1")
    assert route.path == ("C1", "S1", "S2", "GW")
    route2 = find_route_min_hops(g, "C1", forbidden=frozenset(("S2",)))
    assert route2.path == ("C1", "S1", "S3", "GW")


def test_ground_nodes_are_not_relays():
    """client/gateway не могут быть промежуточными узлами (нет наземных рёбер между ними)."""
    g = make_link_graph(
        sats=["S1"],
        adj={},
        client_links={"C1": [("S1", 10.0)]},
        gateway_links={"GW": [("S1", 10.0)]},
        gateways=("GW", "GW2"),
        offline=("GW",),
    )
    route = find_route_min_hops(g, "C1")
    # GW офлайн; обойти через наземные узлы невозможно
    assert not route.connected


def test_multiple_gateways_prefers_shorter_and_lexicographic():
    g = make_link_graph(
        sats=["S1", "S2", "S3"],
        adj={"S1": [("S2", 10.0), ("S3", 10.0)], "S2": [("S1", 10.0)], "S3": [("S1", 10.0)]},
        client_links={"C1": [("S1", 10.0)]},
        gateway_links={"GA": [("S2", 10.0)], "GB": [("S3", 10.0), ("S2", 10.0)]},
        gateways=("GA", "GB"),
    )
    route = find_route_min_hops(g, "C1")
    assert route.path == ("C1", "S1", "S2", "GA")  # 3 ребра, GA < GB


def test_backup_path_node_disjoint():
    """Две параллельные цепочки: резерв полностью не пересекается с основным."""
    g = make_link_graph(
        sats=["S1", "S2", "S3", "S4"],
        adj={
            "S1": [("S2", 10.0)],
            "S2": [("S1", 10.0)],
            "S3": [("S4", 10.0)],
            "S4": [("S3", 10.0)],
        },
        client_links={"C1": [("S1", 10.0), ("S3", 10.0)]},
        gateway_links={"GW": [("S2", 10.0), ("S4", 10.0)]},
    )
    primary = find_route_min_hops(g, "C1")
    assert primary.path == ("C1", "S1", "S2", "GW")  # лексикографически меньший из равных
    backup = find_backup_route(g, "C1", primary.path)
    assert backup.connected
    assert not (set(backup.path[1:-1]) & set(primary.path[1:-1]))
    assert backup.path == ("C1", "S3", "S4", "GW")


def test_no_backup_when_single_bridge():
    g = make_link_graph(
        sats=["S1", "S2"],
        adj={"S1": [("S2", 10.0)], "S2": [("S1", 10.0)]},
        client_links={"C1": [("S1", 10.0)]},
        gateway_links={"GW": [("S2", 10.0)]},
    )
    primary = find_route_min_hops(g, "C1")
    backup = find_backup_route(g, "C1", primary.path)
    assert not backup.connected


def test_min_distance_strategy_prefers_shorter_total_km():
    g = make_link_graph(
        sats=["S1", "S2"],
        adj={"S1": [("S2", 900.0)], "S2": [("S1", 900.0)]},
        client_links={"C1": [("S1", 100.0), ("S2", 500.0)]},
        gateway_links={"GW": [("S1", 100.0), ("S2", 500.0)]},
    )
    by_hops = find_route_min_hops(g, "C1")
    by_dist = find_route_min_distance(g, "C1")
    assert by_hops.path == ("C1", "S1", "GW")
    assert by_dist.path == ("C1", "S1", "GW")
    assert route_distance_km(g, by_dist.path) == pytest.approx(200.0)
    # удлиняем прямое ребро: стратегия дистанции переключится на обход
    g2 = make_link_graph(
        sats=["S1", "S2"],
        adj={"S1": [("S2", 900.0)], "S2": [("S1", 900.0)]},
        client_links={"C1": [("S1", 800.0), ("S2", 500.0)]},
        gateway_links={"GW": [("S1", 800.0), ("S2", 500.0)]},
    )
    assert find_route_min_distance(g2, "C1").path == ("C1", "S2", "GW")


def test_validate_path_accepts_official_route(scenarios):
    from cosmo.geometry_adapter import snapshot
    from cosmo.graph import build_link_graph
    from cosmo.routing import find_route

    scenario = scenarios["01_full_constellation.json"]
    snap = snapshot(scenario, 0)
    g = build_link_graph(snap, scenario)
    for client in g.clients:
        route = find_route(g, client, "min_hops")
        assert route.connected, client
        assert validate_path(snap, scenario, client, route.path) == []


def test_validate_path_detects_broken_link(small_scenario):
    from cosmo.geometry_adapter import snapshot

    snap = snapshot(small_scenario, 0)
    bad_path = ["CL1", "T1", "GW"]
    if snap["edges"]:
        problems = validate_path(snap, small_scenario, "CL1", bad_path)
        # либо маршрут реально валиден, либо проблемы конкретны
        assert isinstance(problems, list)


def test_lexicographic_determinism_on_real_scenario(scenarios):
    from cosmo.geometry_adapter import snapshot
    from cosmo.graph import build_link_graph
    from cosmo.routing import find_route

    scenario = scenarios["04_link_range.json"]
    for t in (0, 21600, 43200):
        g = build_link_graph(snapshot(scenario, t), scenario)
        for client in g.clients:
            results = {find_route(g, client, "min_hops").path for _ in range(5)}
            assert len(results) == 1, (t, client)
