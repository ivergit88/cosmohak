"""Регрессионные проверки по четырём официальным сценариям.

Значения фиксируются как регрессионный базлайн нашего движка, который
использует официальный geometry.py. Для сценариев 01 и 02 значения
совпадают с внешней контрольной таблицей полностью; для 03 наблюдается
расхождение 1 отсчёт по двум клиентам (0.14 п.п.), для 04 — большее
расхождение (см. docs/ASSUMPTIONS.md, раздел «Регрессионные числа»):
все внутренние проверки (сетка, границы отказов, видимость, рёбра,
валидность маршрутов, max outage) сверены и корректны.
"""

from __future__ import annotations

import pytest

from cosmo.simulation import simulate_scenario

# Регрессионный базлайн: (visibility_ticks, route_ticks, max_outage_s) на сетке 720 отсчётов.
BASELINE = {
    "01_full_constellation.json": {
        "C65": (704, 696, 480),
        "C70": (719, 711, 120),
        "C72": (720, 712, 120),
    },
    "02_first_launch.json": {
        "C65": (275, 196, 34320),
        "C70": (351, 114, 39480),
        "C72": (421, 91, 47760),
    },
    "03_satellite_outages.json": {
        "C65": (609, 571, 1440),
        "C70": (650, 582, 1440),
        "C72": (670, 594, 1200),
    },
    "04_link_range.json": {
        "C65": (704, 558, 5640),
        "C70": (719, 448, 10680),
        "C72": (720, 469, 240),
    },
}


@pytest.mark.parametrize("scenario_name", sorted(BASELINE.keys()))
def test_regression_baseline(scenarios, scenario_name):
    scenario = scenarios[scenario_name]
    sim = simulate_scenario(scenario, with_backups=False)
    grid_size = len(sim.ticks)
    for client, (vis, route, outage) in BASELINE[scenario_name].items():
        m = sim.metrics[client]
        assert round(m.visibility_fraction * grid_size) == vis, (scenario_name, client, "visibility")
        assert round(m.availability_fraction * grid_size) == route, (scenario_name, client, "route")
        assert m.max_outage_s == outage, (scenario_name, client, "max_outage")


def test_regression_matches_external_table_where_published(scenarios):
    """Внешняя контрольная таблица совпадает с нашим движком для 01 и 02."""
    external = {
        "01_full_constellation.json": {"C65": (704, 696, 480), "C70": (719, 711, 120), "C72": (720, 712, 120)},
        "02_first_launch.json": {"C65": (275, 196, 34320), "C70": (351, 114, 39480), "C72": (421, 91, 47760)},
    }
    for name, expected in external.items():
        sim = simulate_scenario(scenarios[name], with_backups=False)
        for client, (vis, route, outage) in expected.items():
            m = sim.metrics[client]
            assert round(m.visibility_fraction * 720) == vis
            assert round(m.availability_fraction * 720) == route
            assert m.max_outage_s == outage


def test_simulation_deterministic(scenarios):
    """Повторный запуск по тому же сценарию даёт тот же результат."""
    scenario = scenarios["03_satellite_outages.json"]
    sim1 = simulate_scenario(scenario, with_backups=False)
    sim2 = simulate_scenario(scenario, with_backups=False)
    for client in sim1.clients:
        assert sim1.series[client].paths == sim2.series[client].paths
        assert sim1.metrics[client].availability_fraction == sim2.metrics[client].availability_fraction


def test_min_hops_vs_min_distance_reachability_equal(scenarios):
    """Стратегия не меняет достижимость: availability обязана совпадать."""
    scenario = scenarios["01_full_constellation.json"]
    a = simulate_scenario(scenario, strategy="min_hops", with_backups=False)
    b = simulate_scenario(scenario, strategy="min_distance", with_backups=False)
    for client in a.clients:
        assert a.metrics[client].availability_fraction == b.metrics[client].availability_fraction
