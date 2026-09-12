"""Тесты метрик: точные доли, перерывы (начало/конец/середина), статистики маршрутов."""

from __future__ import annotations

import pytest

from cosmo.metrics import (
    compute_client_metrics,
    compute_global_metrics,
    compute_route_changes,
    outage_intervals_from_statuses,
    percentile_nearest_rank,
)
from cosmo.models import (
    STATUS_CONNECTED,
    STATUS_GATEWAY_OFFLINE,
    STATUS_ISL_DISCONNECTED,
    STATUS_NO_VISIBLE_SAT,
)

TICKS = [0, 100, 200, 300, 400, 500]


def _metrics(statuses, target=0.9, **overrides):
    n = len(TICKS)
    kwargs = dict(
        client_id="C1",
        ticks=TICKS,
        statuses=statuses,
        client_visible=[True] * n,
        hops=[2 if s == STATUS_CONNECTED else None for s in statuses],
        distances=[100.0 if s == STATUS_CONNECTED else None for s in statuses],
        paths=[("C1", "S1", "GW") if s == STATUS_CONNECTED else () for s in statuses],
        backup_exists=None,
        step_s=100,
        target_availability=target,
    )
    kwargs.update(overrides)
    return compute_client_metrics(**kwargs)


def test_no_downtime():
    m = _metrics([STATUS_CONNECTED] * 6)
    assert m.availability_fraction == 1.0
    assert m.max_outage_s == 0
    assert m.outage_intervals == ()
    assert m.target_met


def test_full_downtime():
    m = _metrics([STATUS_NO_VISIBLE_SAT] * 6)
    assert m.availability_fraction == 0.0
    assert m.max_outage_s == 600  # 6 отсчётов по 100 с
    assert len(m.outage_intervals) == 1
    iv = m.outage_intervals[0]
    assert iv.start_s == 0 and iv.end_s == 600


def test_leading_outage_counted():
    statuses = [STATUS_NO_VISIBLE_SAT, STATUS_NO_VISIBLE_SAT, STATUS_CONNECTED,
                STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED]
    m = _metrics(statuses)
    assert m.availability_fraction == pytest.approx(4 / 6)
    assert m.max_outage_s == 200
    assert m.outage_intervals[0].start_s == 0


def test_trailing_outage_counted():
    statuses = [STATUS_CONNECTED] * 4 + [STATUS_ISL_DISCONNECTED, STATUS_ISL_DISCONNECTED]
    m = _metrics(statuses)
    assert m.max_outage_s == 200
    assert m.outage_intervals[-1].end_s == 600  # последний отсчёт 500 + step 100


def test_middle_outage():
    statuses = [STATUS_CONNECTED, STATUS_ISL_DISCONNECTED, STATUS_ISL_DISCONNECTED,
                STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED]
    m = _metrics(statuses)
    assert m.max_outage_s == 200
    assert len(m.outage_intervals) == 1
    assert m.outage_intervals[0].start_s == 100
    assert m.outage_intervals[0].end_s == 300


def test_outage_interval_primary_reason_priority():
    statuses = [STATUS_GATEWAY_OFFLINE, STATUS_ISL_DISCONNECTED, STATUS_CONNECTED,
                STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED]
    iv = outage_intervals_from_statuses(TICKS, statuses, 100)[0]
    # приоритетная причина = категория с меньшим кодом среди присутствующих
    assert iv.reasons[0][0] == STATUS_GATEWAY_OFFLINE
    assert iv.reasons[1][0] == STATUS_ISL_DISCONNECTED
    assert iv.duration_s == 200


def test_visibility_fraction_exact():
    visible = [True, True, True, False, False, True]
    m = _metrics([STATUS_CONNECTED] * 6, client_visible=visible)
    assert m.visibility_fraction == pytest.approx(4 / 6)
    assert m.availability_fraction == 1.0


def test_target_threshold():
    statuses = [STATUS_CONNECTED] * 5 + [STATUS_NO_VISIBLE_SAT]
    m = _metrics(statuses, target=0.9)
    assert m.availability_fraction == pytest.approx(5 / 6)
    assert not m.target_met
    m2 = _metrics(statuses, target=0.8)
    assert m2.target_met


def test_routing_statistics():
    statuses = [STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED,
                STATUS_ISL_DISCONNECTED, STATUS_CONNECTED, STATUS_CONNECTED]
    hops = [2, 3, 4, None, 2, 2]
    m = _metrics(statuses, hops=hops)
    assert m.mean_hops == pytest.approx(13 / 5)
    assert m.max_hops == 4
    assert m.p95_hops == 4.0  # nearest-rank: ceil(0.95*5)=5-й элемент
    assert m.median_hops == 2.0  # отсортированные [2,2,2,3,4], медиана = средний элемент


def test_route_changes_counts():
    paths = [("C", "A", "G"), ("C", "A", "G"), ("C", "B", "G"), (), ("C", "B", "G"), ("C", "A", "G")]
    connected = [True, True, True, False, True, True]
    # смены: 1->2 (A->B), 4->5 (B->A); разрыв 3->4 не считается
    assert compute_route_changes(paths, connected) == 2


def test_backup_fraction():
    statuses = [STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED, STATUS_CONNECTED,
                STATUS_CONNECTED, STATUS_CONNECTED]
    backups = [True, True, False, True, False, False]
    m = _metrics(statuses, backup_exists=backups)
    assert m.backup_fraction == pytest.approx(3 / 6)


def test_global_metrics():
    from cosmo.metrics import ClientMetrics

    def cm(cid, avail, outage):
        return ClientMetrics(
            client_id=cid, visibility_fraction=avail, availability_fraction=avail,
            max_outage_s=outage, outage_intervals=(), mean_hops=2.0, median_hops=2.0,
            p95_hops=3.0, max_hops=3, route_change_count=0, mean_path_km=100.0,
            backup_fraction=None, target_met=avail >= 0.9, target_availability=0.9,
        )

    g = compute_global_metrics([cm("C1", 0.95, 100), cm("C2", 0.85, 500)], 2)
    assert g.min_availability == pytest.approx(0.85)
    assert g.mean_availability == pytest.approx(0.90)
    assert g.worst_max_outage_s == 500
    assert g.target_met_clients == 1
