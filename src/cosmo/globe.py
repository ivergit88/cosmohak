# Глобус-вид (ортографическая проекция, тёмный «радарный» стиль) для вкладки «Сеть и время».
from __future__ import annotations

import math

import plotly.graph_objects as go

from . import geometry_adapter

_OCEAN = "#081826"
_LAND = "#13241d"
_BORDER = "#274a38"
_COAST = "#2a4a38"
_ISL = "#34d17b"
_GROUND = "#41c9e8"
_ROUTE = "#ff8a3d"
_SAT_CORE = "#8affd4"
_SAT_HALO = "rgba(52, 209, 123, 0.22)"
_DOWN = "#e05252"


def _latlon(v) -> tuple[float, float]:
    norm = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5 or 1.0
    return math.degrees(math.asin(max(-1.0, min(1.0, v[2] / norm)))), math.degrees(math.atan2(v[1], v[0]))


def globe_view(scenario: dict, sim, t_s: int, selected_client: str, route) -> go.Figure:
    """Тёмный глобус: реальные континенты, светящиеся ISL, маршрут и наземные пункты.

    Координаты берутся из официального snapshot (Earth-fixed), поэтому картинка
    согласована с расчётом связности.
    """
    snap = geometry_adapter.snapshot(scenario, t_s)
    ground_ids = {g["id"] for g in scenario["ground_sites"]}

    pos: dict[str, tuple[float, float]] = {}
    active: dict[str, bool] = {}
    for s in snap["satellites"]:
        pos[s["id"]] = _latlon((s["x_km"], s["y_km"], s["z_km"]))
        active[s["id"]] = s["active"]

    fig = go.Figure()

    # ISL-линии между активными спутниками
    lat_isl: list[float] = []
    lon_isl: list[float] = []
    for a, b, _d in snap["edges"]:
        if a in ground_ids or b in ground_ids or a not in pos or b not in pos:
            continue
        for node in (a, b):
            lat_isl.append(pos[node][0])
            lon_isl.append(pos[node][1])
        lat_isl.append(None)
        lon_isl.append(None)
    if lat_isl:
        fig.add_trace(go.Scattergeo(
            lat=lat_isl, lon=lon_isl, mode="lines",
            line=dict(color=_ISL, width=1.6),
            hoverinfo="skip", showlegend=False, name="ISL",
        ))

    # наземные линии (пункт ↔ спутник)
    lat_g: list[float] = []
    lon_g: list[float] = []
    for a, b, _d in snap["edges"]:
        if a not in ground_ids and b not in ground_ids:
            continue
        ground, sat = (a, b) if a in ground_ids else (b, a)
        if sat not in pos or ground not in pos:
            continue
        site = next(g for g in scenario["ground_sites"] if g["id"] == ground)
        gpos = (site["lat_deg"], site["lon_deg"])
        lat_g += [gpos[0], pos[sat][0], None]
        lon_g += [gpos[1], pos[sat][1], None]
    if lat_g:
        fig.add_trace(go.Scattergeo(
            lat=lat_g, lon=lon_g, mode="lines",
            line=dict(color=_GROUND, width=1.4, dash="dot"),
            hoverinfo="skip", showlegend=False, name="Наземные линии",
        ))

    # маршрут выбранного пункта (толстая оранжевая)
    if route:
        rt_lat: list[float] = []
        rt_lon: list[float] = []
        for node in route:
            if node in pos:
                rt_lat.append(pos[node][0])
                rt_lon.append(pos[node][1])
            else:
                site = next(g for g in scenario["ground_sites"] if g["id"] == node)
                rt_lat.append(site["lat_deg"])
                rt_lon.append(site["lon_deg"])
        fig.add_trace(go.Scattergeo(
            lat=rt_lat, lon=rt_lon, mode="lines+markers",
            line=dict(color=_ROUTE, width=4),
            marker=dict(size=7, color=_ROUTE),
            hoverinfo="skip", showlegend=False, name="Маршрут",
        ))

    # спутники: гало + ядро; неактивные — красные крестики
    sat_ok_lat, sat_ok_lon, sat_hover = [], [], []
    halo_lat, halo_lon = [], []
    down_lat, down_lon = [], []
    for sid, (lat, lon) in pos.items():
        label = sid + (" · активен" if active[sid] else " · НЕ активен")
        if active[sid]:
            halo_lat.append(lat); halo_lon.append(lon)
            sat_ok_lat.append(lat); sat_ok_lon.append(lon); sat_hover.append(label)
        else:
            down_lat.append(lat); down_lon.append(lon)
    if halo_lat:
        fig.add_trace(go.Scattergeo(
            lat=halo_lat, lon=halo_lon, mode="markers",
            marker=dict(size=16, color=_SAT_HALO, symbol="circle"),
            hoverinfo="skip", showlegend=False, name="Гало",
        ))
    if sat_ok_lat:
        fig.add_trace(go.Scattergeo(
            lat=sat_ok_lat, lon=sat_ok_lon, mode="markers", text=sat_hover,
            hovertemplate="%{text}<extra></extra>",
            marker=dict(size=5.5, color=_SAT_CORE, symbol="circle"),
            showlegend=False, name="Спутники",
        ))
    if down_lat:
        fig.add_trace(go.Scattergeo(
            lat=down_lat, lon=down_lon, mode="markers",
            marker=dict(size=8, color=_DOWN, symbol="x"),
            hovertemplate="НЕ активен<extra></extra>", showlegend=False, name="Отключённые",
        ))

    # наземные пункты
    for site in scenario["ground_sites"]:
        is_sel = site["id"] == selected_client
        fig.add_trace(go.Scattergeo(
            lat=[site["lat_deg"]], lon=[site["lon_deg"]], mode="markers+text",
            marker=dict(size=13 if is_sel else 10,
                        color="#ffb14d" if site["role"] == "gateway" else "#57b0ff",
                        symbol="diamond" if site["role"] == "gateway" else "square",
                        line=dict(width=2, color="#ffffff" if is_sel else "rgba(255,255,255,0.35)")),
            text=[site["id"]], textposition="bottom center",
            textfont=dict(size=10, color="#e8f4ff"),
            name=site["id"], hovertemplate=site["id"] + "<extra></extra>",
        ))

    # вид: север в центре (там вся демо-география)
    fig.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lat=63, lon=55, roll=0),
        showocean=True, oceancolor=_OCEAN,
        showland=True, landcolor=_LAND,
        showcountries=True, countrycolor=_BORDER,
        showcoastlines=True, coastlinecolor=_COAST,
        showlakes=False, showframe=False,
        lataxis=dict(showgrid=True, gridcolor="rgba(120,160,140,0.18)", gridwidth=0.5),
        lonaxis=dict(showgrid=True, gridcolor="rgba(120,160,140,0.18)", gridwidth=0.5),
        resolution=50,
        bgcolor="#05080f",
        domain=dict(x=[0, 1], y=[0, 1]),
    )
    fig.update_layout(
        paper_bgcolor="#05080f",
        plot_bgcolor="#05080f",
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        dragmode="orbit",
        hoverlabel=dict(bgcolor="#0d1420", font=dict(color="#e8f4ff")),
    )
    return fig
