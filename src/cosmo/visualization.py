"""Визуализация на Plotly: 3D-сеть, таймлайн, карта треков, графики сравнения.

Все рисунки строятся из данных симуляции и официального snapshot.
Используются только бесплатные/офлайн возможности Plotly (без карт-API).

Система координат 3D-сцены — расчётная модель: позиции спутников и
наземных пунктов берутся в том же кадре, в котором official geometry
считает контакты (наземные пункты неподвижны, спутники движутся).
"""

from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
import plotly.graph_objects as go

from . import geometry_adapter
from .models import STATUS_COLORS, STATUS_LABELS, hhmmss
from .simulation import SimulationResult

R_EARTH = 6371.0

def _sphere_traces(opacity: float = 0.12, step_deg: int = 15) -> list[go.Trace]:
    """Полупрозрачная сфера Земли + сетка параллелей/меридианов."""
    u = np.linspace(0, 2 * np.pi, 73)
    v = np.linspace(-np.pi / 2, np.pi / 2, 37)
    x = R_EARTH * np.outer(np.cos(u), np.cos(v))
    y = R_EARTH * np.outer(np.sin(u), np.cos(v))
    z = R_EARTH * np.outer(np.ones_like(u), np.sin(v))
    surface = go.Surface(
        x=x, y=y, z=z, opacity=opacity, showscale=False,
        colorscale=[[0, "#9fb8cc"], [1, "#9fb8cc"]],
        hoverinfo="skip", name="Земля", showlegend=False,
    )
    lines: list[go.Trace] = []
    # параллели
    for lat_deg in range(-60, 90, 30):
        lat = math.radians(lat_deg)
        r_lat = R_EARTH * math.cos(lat)
        zz = R_EARTH * math.sin(lat)
        th = np.linspace(0, 2 * np.pi, 97)
        lines.append(go.Scatter3d(
            x=r_lat * np.cos(th), y=r_lat * np.sin(th), z=np.full_like(th, zz),
            mode="lines", line=dict(color="#7a8ba0", width=2), hoverinfo="skip",
            showlegend=False, name=f"lat {lat_deg}°",
        ))
    # меридианы
    for lon_deg in range(0, 180, 30):
        lon = math.radians(lon_deg)
        th = np.linspace(0, 2 * np.pi, 97)
        xx = R_EARTH * np.cos(th) * math.cos(lon)
        yy = R_EARTH * np.cos(th) * math.sin(lon)
        zz = R_EARTH * np.sin(th)
        lines.append(go.Scatter3d(
            x=xx, y=yy, z=zz, mode="lines", line=dict(color="#7a8ba0", width=2),
            hoverinfo="skip", showlegend=False, name=f"meridian {lon_deg}°",
        ))
    return [surface, *lines]


def _ground_position(site: dict[str, Any]) -> tuple[float, float, float]:
    lat, lon = math.radians(site["lat_deg"]), math.radians(site["lon_deg"])
    return (
        R_EARTH * math.cos(lat) * math.cos(lon),
        R_EARTH * math.cos(lat) * math.sin(lon),
        R_EARTH * math.sin(lat),
    )


def _edges_trace(
    edges: Iterable[list],
    positions: dict[str, tuple[float, float, float]],
    color: str, width: int, name: str, dash: str | None = None,
) -> go.Scatter3d:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for a, b, *_ in edges:
        xa, ya, za = positions[a]
        xb, yb, zb = positions[b]
        xs += [xa, xb, None]
        ys += [ya, yb, None]
        zs += [za, zb, None]
    line = dict(color=color, width=width)
    if dash:
        line["dash"] = dash
    return go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=line, hoverinfo="skip", name=name, showlegend=True)


def network_3d(
    scenario: dict[str, Any],
    sim: SimulationResult,
    t_s: int,
    selected_client: str,
    route: tuple[str, ...],
) -> go.Figure:
    """3D-схема сети: Земля, спутники (активные/нет), наземные пункты, связи, маршрут."""
    snap = geometry_adapter.snapshot(scenario, t_s)
    node_pos: dict[str, tuple[float, float, float]] = {}
    traces: list[go.Trace] = []
    traces.extend(_sphere_traces())

    ground_sites = {g["id"]: g for g in scenario["ground_sites"]}
    for site in scenario["ground_sites"]:
        node_pos[site["id"]] = _ground_position(site)

    active_x, active_y, active_z, active_text = [], [], [], []
    inactive_x, inactive_y, inactive_z, inactive_text = [], [], [], []
    for s in snap["satellites"]:
        node_pos[s["id"]] = (s["x_km"], s["y_km"], s["z_km"])
        label = f"{s['id']}<br>{'активен' if s['active'] else 'НЕ активен'}"
        if s["active"]:
            active_x.append(s["x_km"]); active_y.append(s["y_km"]); active_z.append(s["z_km"]); active_text.append(label)
        else:
            inactive_x.append(s["x_km"]); inactive_y.append(s["y_km"]); inactive_z.append(s["z_km"]); inactive_text.append(label)

    traces.append(go.Scatter3d(
        x=active_x, y=active_y, z=active_z, mode="markers+text",
        marker=dict(size=4, color="#1b5e20"), text=[t.split('<br>')[0] for t in active_text],
        textposition="top center", textfont=dict(size=8),
        hovertext=active_text, hoverinfo="text", name="Спутники (активные)",
    ))
    if inactive_x:
        traces.append(go.Scatter3d(
            x=inactive_x, y=inactive_y, z=inactive_z, mode="markers+text",
            marker=dict(size=5, color="#c62828", symbol="x"), text=[t.split('<br>')[0] for t in inactive_text],
            textposition="top center", textfont=dict(size=8, color="#c62828"),
            hovertext=inactive_text, hoverinfo="text", name="Спутники (неактивные)",
        ))

    isl_edges = [e for e in snap["edges"] if e[0] not in ground_sites and e[1] not in ground_sites]
    ground_edges = [e for e in snap["edges"] if e[0] in ground_sites or e[1] in ground_sites]
    if isl_edges:
        traces.append(_edges_trace(isl_edges, node_pos, "#90a4ae", 2, "Межспутниковые связи"))
    if ground_edges:
        traces.append(_edges_trace(ground_edges, node_pos, "#2e7d32", 3, "Наземные линии", dash="dash"))

    if route:
        route_coords = [node_pos[node] for node in route if node in node_pos]
        traces.append(go.Scatter3d(
            x=[c[0] for c in route_coords], y=[c[1] for c in route_coords], z=[c[2] for c in route_coords],
            mode="lines+markers", line=dict(color="#e65100", width=9),
            marker=dict(size=5, color="#e65100"),
            hovertext=" -> ".join(route), hoverinfo="text", name="Маршрут",
        ))

    for site in scenario["ground_sites"]:
        x, y, z = node_pos[site["id"]]
        is_client = site["role"] == "client"
        color = "#1565c0" if is_client else "#ef6c00"
        symbol = "square" if is_client else "diamond"
        size = 9 if site["id"] == selected_client else 7
        traces.append(go.Scatter3d(
            x=[x], y=[y], z=[z], mode="markers+text",
            marker=dict(size=size, color=color, symbol=symbol),
            text=[f"{site['id']} ({'клиент' if is_client else 'шлюз'})"],
            textposition="bottom center", textfont=dict(size=9),
            name=site["id"], hovertext=f"{site['id']}: {site.get('name', site['id'])}, роль={site['role']}", hoverinfo="text",
        ))

    fig = go.Figure(traces)
    fig.update_layout(
        title=f"Сеть в момент t={t_s} с ({hhmmss(t_s)})",
        scene=dict(
            xaxis_title="x, км", yaxis_title="y, км", zaxis_title="z, км",
            aspectmode="data",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=0.0, font=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0),
        height=640,
        uirevision="keep-3d",
    )
    return fig


def timeline_heatmap(sim: SimulationResult, selected_client: str | None = None) -> go.Figure:
    """Теплокарта состояний: клиенты × отсчёты; цвет = категория причины."""
    clients = list(sim.clients)
    z = np.array([sim.series[c].statuses for c in clients], dtype=float)
    times = [hhmmss(t) for t in sim.ticks]
    custom = np.empty((len(clients), len(sim.ticks)), dtype=object)
    for i, c in enumerate(clients):
        s = sim.series[c]
        for j in range(len(sim.ticks)):
            custom[i][j] = f"{c} · {times[j]}<br>{STATUS_LABELS.get(s.statuses[j], '')}<br>{s.details[j] or ''}"

    # жесткие сегменты: каждый статус занимает ровно 1/5 шкалы, без интерполяции.
    # zmin=-0.5, zmax=4.5, поэтому значение v попадает в сегмент [(v+0.5)/5; (v+1.5)/5]
    colorscale = []
    for code in range(5):
        lo = code / 5.0
        hi = (code + 1) / 5.0
        colorscale.append([lo, STATUS_COLORS[code]])
        colorscale.append([hi, STATUS_COLORS[code]])

    fig = go.Figure(
        go.Heatmap(
            z=z, x=times, y=clients, zmin=-0.5, zmax=4.5,
            colorscale=colorscale, showscale=False, customdata=custom,
            hovertemplate="%{customdata}<extra></extra>", xgap=0, ygap=2,
        )
    )
    fig.update_layout(
        title="Шкала доступности: зелёный — маршрут есть; цвета перерывов — по причине",
        xaxis=dict(title="Время расчёта (чч:мм:сс)", tickmode="array",
                   tickvals=times[:: max(1, len(times) // 12)], tickangle=0),
        yaxis=dict(title="Клиентский пункт"),
        margin=dict(l=40, r=20, t=50, b=40), height=230 + 30 * len(clients),
    )
    if selected_client in clients:
        fig.add_hline(y=selected_client, line=dict(color="#e65100", width=2, dash="dot"))
    return fig


def connectivity_over_time(sim: SimulationResult) -> go.Figure:
    """Число подключённых клиентов на каждом отсчёте."""
    counts = [
        sum(1 for c in sim.clients if sim.series[c].statuses[i] == 0)
        for i in range(len(sim.ticks))
    ]
    fig = go.Figure(
        go.Scatter(
            x=[hhmmss(t) for t in sim.ticks], y=counts, mode="lines",
            line=dict(shape="hv", color="#1565c0"), name="Подключено клиентов",
        )
    )
    fig.update_layout(
        title="Число клиентов со сквозным маршрутом",
        xaxis=dict(title="Время", tickmode="array",
                   tickvals=[hhmmss(t) for t in sim.ticks[:: max(1, len(sim.ticks) // 12)]]),
        yaxis=dict(title="Клиентов", range=[0, len(sim.clients)], dtick=1),
        margin=dict(l=40, r=20, t=50, b=40), height=280,
    )
    return fig


def ground_track(scenario: dict[str, Any], sim: SimulationResult, t_s: int) -> go.Figure:
    """Карта подспутниковых точек в системе координат, связанной с Землёй."""
    planes: dict[str, list[str]] = {}
    pmap = {s["id"]: s["plane_id"] for s in scenario["design"]["satellites"]}
    for sid, plane in pmap.items():
        planes.setdefault(plane, []).append(sid)

    fig = go.Figure()
    step = max(1, len(sim.ticks) // 240)
    ticks = sim.ticks[::step]
    # lat/lon по каждому аппарату отдельно: своя траектория на сутки
    tracks: dict[str, dict[str, tuple[list[float], list[float]]]] = {}
    for t in ticks:
        ids, _inertial, xyz = geometry_adapter.positions(scenario, t)
        for k, sid in enumerate(ids):
            v = xyz[k]
            norm = float(np.linalg.norm(v))
            lat = math.degrees(math.asin(max(-1, min(1, v[2] / norm))))
            lon = math.degrees(math.atan2(v[1], v[0]))
            plane = pmap[sid]
            entry = tracks.setdefault(plane, {}).setdefault(sid, ([], []))
            entry[0].append(lat)
            entry[1].append(lon)
    for plane_id in sorted(tracks):
        lats: list[float] = []
        lons: list[float] = []
        for sid in sorted(tracks[plane_id]):
            sat_lats, sat_lons = tracks[plane_id][sid]
            lats += sat_lats + [None]
            lons += sat_lons + [None]
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons, mode="lines", name=f"плоскость {plane_id}",
            line=dict(width=1), opacity=0.6,
        ))
    # текущие позиции
    ids, _inertial, xyz = geometry_adapter.positions(scenario, t_s)
    cur_lat, cur_lon, cur_text = [], [], []
    for k, sid in enumerate(ids):
        v = xyz[k]
        cur_lat.append(math.degrees(math.asin(max(-1, min(1, v[2] / np.linalg.norm(v))))))
        cur_lon.append(math.degrees(math.atan2(v[1], v[0])))
        cur_text.append(sid)
    fig.add_trace(go.Scattergeo(
        lat=cur_lat, lon=cur_lon, mode="markers+text", name=f"позиции t={hhmmss(t_s)}",
        marker=dict(size=5, color="#1b5e20"), text=cur_text, textposition="top center",
        textfont=dict(size=7),
    ))
    for site in scenario["ground_sites"]:
        color = "#1565c0" if site["role"] == "client" else "#ef6c00"
        fig.add_trace(go.Scattergeo(
            lat=[site["lat_deg"]], lon=[site["lon_deg"]], mode="markers+text",
            marker=dict(size=10, color=color, symbol="square" if site["role"] == "client" else "diamond"),
            text=[site["id"]], textposition="bottom center", name=site["id"],
        ))
    fig.update_geos(
        projection_type="natural earth", showland=True, landcolor="#e8eaf0",
        showcountries=True, countrycolor="#c5cdd8", showcoastlines=True, coastlinecolor="#b0bac6",
        lataxis_range=[35, 85], lonaxis_range=[-20, 180], resolution=50,
        domain=dict(x=[0, 1], y=[0, 1]),
    )
    # легенда — горизонтально под картой, поля минимальные: карта занимает всё место
    # и не перекрывается легендой на узких экранах
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=4, r=4, t=6, b=4), height=430,
    )
    return fig


def availability_bars(series: dict[str, dict[str, float]], target: float) -> go.Figure:
    """Столбцы доступности по клиентам для нескольких вариантов."""
    fig = go.Figure()
    for label, values in series.items():
        fig.add_trace(go.Bar(
            name=label, x=list(values.keys()), y=[100 * v for v in values.values()],
            text=[f"{100 * v:.1f}%" for v in values.values()], textposition="outside",
        ))
    fig.add_hline(y=100 * target, line=dict(color="#c62828", width=2, dash="dash"),
                  annotation_text=f"цель {100 * target:.0f}%", annotation_position="top left")
    fig.update_layout(
        barmode="group", title="Доступность по клиентам", yaxis_title="Доступность, %",
        yaxis=dict(range=[0, 112]), margin=dict(l=40, r=20, t=50, b=40), height=360,
        legend=dict(orientation="h"),
    )
    return fig


def outage_bars(series: dict[str, dict[str, int]]) -> go.Figure:
    """Столбцы максимального перерыва по клиентам для нескольких вариантов."""
    fig = go.Figure()
    for label, values in series.items():
        fig.add_trace(go.Bar(
            name=label, x=list(values.keys()), y=list(values.values()),
            text=[f"{v} с" for v in values.values()], textposition="outside",
        ))
    fig.update_layout(
        barmode="group", title="Максимальный перерыв по клиентам", yaxis_title="Секунды",
        margin=dict(l=40, r=20, t=50, b=40), height=360, legend=dict(orientation="h"),
    )
    return fig


def hops_scatter(sim: SimulationResult, client_id: str) -> go.Figure:
    """Число переходов маршрута клиента по времени."""
    s = sim.series[client_id]
    xs = [hhmmss(t) for t in sim.ticks]
    ys = [h if h is not None else None for h in s.hops]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers",
                               marker=dict(size=4), line=dict(shape="hv"),
                               name=f"{client_id}: переходов"))
    fig.update_layout(
        title=f"Число переходов маршрута ({client_id})",
        xaxis=dict(title="Время", tickmode="array",
                   tickvals=xs[:: max(1, len(xs) // 12)]),
        yaxis=dict(title="Переходы (рёбра)", dtick=1),
        margin=dict(l=40, r=20, t=50, b=40), height=300,
    )
    return fig
