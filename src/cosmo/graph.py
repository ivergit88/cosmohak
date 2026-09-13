"""Построение графа сети из snapshot официального модуля.

Узлы: спутники, клиенты, шлюзы. Рёбра берутся напрямую из
snapshot.edges (контакты двунаправленные). Наземные узлы НЕ
являются ретрансляторами: client может быть только источником
маршрута, gateway — только терминалом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import gateways_of


@dataclass(frozen=True)
class LinkGraph:
    """Структуры смежности графа на одном отсчёте времени.

    sat_adj — только межспутниковые рёбра (отсортированы по ID соседа);
    client_links / gateway_links — наземные линии (пункт -> спутник);
    gateway_visible — спутники, видимые шлюзом (уже с учётом offline);
    offline_gateways — шлюзы в периоде недоступности [start; end).
    """

    sat_ids: tuple[str, ...]
    sat_adj: dict[str, tuple[tuple[str, float], ...]]
    client_links: dict[str, tuple[tuple[str, float], ...]]
    gateway_links: dict[str, tuple[tuple[str, float], ...]]
    clients: tuple[str, ...]
    gateways: tuple[str, ...]
    offline_gateways: frozenset[str]
    active_sats: frozenset[str]
    edge_set: frozenset[tuple[str, str]]
    positions: dict[str, tuple[float, float, float]] = field(default_factory=dict)

    def online_gateways_with_contact(self) -> list[str]:
        """Шлюзы, которые онлайн и видят хотя бы один активный спутник."""
        return [
            gw for gw in self.gateways
            if gw not in self.offline_gateways and self.gateway_links.get(gw)
        ]


def build_link_graph(snapshot: dict[str, Any], scenario: dict[str, Any]) -> LinkGraph:
    """Собирает LinkGraph из официального snapshot и сценария."""
    sat_adj: dict[str, list[tuple[str, float]]] = {}
    ground_links: dict[str, list[tuple[str, float]]] = {}
    edge_set: set[tuple[str, str]] = set()
    ground_ids = {g["id"] for g in scenario["ground_sites"]}
    for a, b, dist in snapshot["edges"]:
        edge_set.add((a, b))
        edge_set.add((b, a))
        if a in ground_ids or b in ground_ids:
            ground, sat = (a, b) if a in ground_ids else (b, a)
            ground_links.setdefault(ground, []).append((sat, float(dist)))
        else:
            sat_adj.setdefault(a, []).append((b, float(dist)))
            sat_adj.setdefault(b, []).append((a, float(dist)))

    sat_ids = tuple(s["id"] for s in snapshot["satellites"])
    active_sats = frozenset(s["id"] for s in snapshot["satellites"] if s["active"])
    adj: dict[str, tuple[tuple[str, float], ...]] = {
        sid: tuple(sorted(sat_adj.get(sid, []))) for sid in sat_ids
    }
    links: dict[str, tuple[tuple[str, float], ...]] = {
        gid: tuple(sorted(v)) for gid, v in ground_links.items()
    }
    gateways = tuple(gateways_of(scenario))
    offline = frozenset(gw for gw in gateways if not links.get(gw) and _is_offline(snapshot, scenario, gw))
    import math as _math

    positions: dict[str, tuple[float, float, float]] = {}
    for s in snapshot["satellites"]:
        v = (s["x_km"], s["y_km"], s["z_km"])
        norm = _math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
        lat = _math.degrees(_math.asin(max(-1.0, min(1.0, v[2] / norm))))
        lon = _math.degrees(_math.atan2(v[1], v[0]))
        positions[s["id"]] = v  # Earth-fixed координаты официального snapshot
    for g in scenario["ground_sites"]:
        lat = _math.radians(g["lat_deg"])
        lon = _math.radians(g["lon_deg"])
        r = 6371.0
        positions[g["id"]] = (r * _math.cos(lat) * _math.cos(lon),
                              r * _math.cos(lat) * _math.sin(lon),
                              r * _math.sin(lat))

    return LinkGraph(
        sat_ids=sat_ids,
        positions=positions,
        sat_adj=adj,
        client_links={k: v for k, v in links.items() if k not in set(gateways)},
        gateway_links={k: v for k, v in links.items() if k in set(gateways)},
        clients=tuple(g["id"] for g in scenario["ground_sites"] if g["role"] == "client"),
        gateways=gateways,
        offline_gateways=offline,
        active_sats=active_sats,
        edge_set=frozenset(edge_set),
    )


def _is_offline(snapshot: dict[str, Any], scenario: dict[str, Any], gateway_id: str) -> bool:
    """Шлюз offline, если в этот момент активен его gateway_outage.

    Если шлюз онлайн, но не видит спутников, ссылок у него тоже нет —
    поэтому offline отличаем по факту активного интервала отказа.
    """
    t = snapshot["t_s"]
    return any(
        f["gateway_id"] == gateway_id and f["start_s"] <= t < f["end_s"]
        for f in scenario.get("gateway_outages", [])
    )
