"""Веб-сервис «Проектирование устойчивой спутниковой группировки».

Streamlit-приложение. Вся расчётная логика — в пакете src/cosmo;
здесь только интерфейс, формы и вызовы ядра.

Запуск: streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cosmo import visualization as viz  # noqa: E402
from cosmo.comparison import (  # noqa: E402
    Variant,
    config_diff_rows,
    global_diff_rows,
    metrics_diff_rows,
    objective_key,
    recommend,
)
from cosmo.export import (  # noqa: E402
    build_analysis_report,
    build_result,
    dumps_result,
    dumps_scenario,
    metrics_csv,
    timeline_csv,
)
from cosmo.geometry_adapter import load_file  # noqa: E402
from cosmo.models import (  # noqa: E402
    STATUS_LABELS,
    STRATEGY_LABELS,
    STRATEGY_MIN_DISTANCE,
    STRATEGY_MIN_HOPS,
    deep_copy,
    fmt_pct,
    hhmmss,
    scenario_meta,
    scenario_title,
)
from cosmo.optimizer import optimize_configuration  # noqa: E402
from cosmo.resilience import apply_failure_impact, criticality_analysis, reason_summary  # noqa: E402
from cosmo.simulation import simulate_scenario  # noqa: E402
from cosmo.validation import ScenarioValidationError, ensure_valid  # noqa: E402

DATA_DIR = ROOT / "data"
BUILTIN_SCENARIOS = {
    "01_full_constellation.json — Полная группировка": "01_full_constellation.json",
    "02_first_launch.json — Первая очередь запуска": "02_first_launch.json",
    "03_satellite_outages.json — Недоступность десяти аппаратов": "03_satellite_outages.json",
    "04_link_range.json — Дальность МСC 2000 км": "04_link_range.json",
}

st.set_page_config(page_title="КосмоХакатон — Устойчивая спутниковая группировка", page_icon="🛰", layout="wide")


# ---------------------------------------------------------------------------
# Кэширование расчётов
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def cached_simulate(scenario_json: str, strategy: str) -> object:
    """Полное моделирование с кэшированием по стабильному ключу сценария."""
    scenario = json.loads(scenario_json)
    return simulate_scenario(scenario, strategy=strategy, with_backups=True)


@st.cache_data(show_spinner=False)
def cached_criticality(scenario_json: str, strategy: str) -> list:
    scenario = json.loads(scenario_json)
    sim = simulate_scenario(scenario, strategy=strategy, with_backups=False)
    return criticality_analysis(scenario, sim)


def scenario_json_of(scenario: dict) -> str:
    return json.dumps(scenario, ensure_ascii=False, sort_keys=True, allow_nan=False)


# ---------------------------------------------------------------------------
# Состояние и загрузка сценария
# ---------------------------------------------------------------------------

def prime_widgets(scenario: dict, nonce: int) -> None:
    """Инициализирует виджеты значениями загруженного сценария.

    st.data_editor нельзя инициализировать через st.session_state[key] —
    поэтому таблицы отказов хранятся в seed-списках и передаются через
    параметр data при монтировании (nonce меняется при каждой загрузке).
    """
    st.session_state["launch_stage_sel"] = int(scenario["design"]["launch_stage"])
    for plane in scenario["design"]["planes"]:
        st.session_state[f"raan_{plane['id']}_{nonce}"] = float(plane["raan_deg"])
        st.session_state[f"phase_{plane['id']}_{nonce}"] = float(plane["phase_deg"])
    st.session_state["failures_seed"] = [
        {"satellite_id": f["satellite_id"], "start_s": int(f["start_s"]), "end_s": int(f["end_s"])}
        for f in scenario.get("failures", [])
    ]
    st.session_state["gw_seed"] = [
        {"gateway_id": f["gateway_id"], "start_s": int(f["start_s"]), "end_s": int(f["end_s"])}
        for f in scenario.get("gateway_outages", [])
    ]
    st.session_state["failures_nonce"] = st.session_state.get("failures_nonce", 0) + 1
    st.session_state["gw_nonce"] = st.session_state.get("gw_nonce", 0) + 1
    env = scenario["environment"]
    for key in ("altitude_km", "inclination_deg", "earth_angle0_deg", "min_elevation_deg",
                "isl_range_km", "target_availability"):
        st.session_state[f"env_{key}_{nonce}"] = float(env[key])
    st.session_state[f"env_horizon_s_{nonce}"] = int(env["horizon_s"])
    st.session_state[f"env_step_s_{nonce}"] = int(env["step_s"])
    st.session_state["sites_seed"] = [
        {"id": g["id"], "name": str(g.get("name", g["id"])), "role": g["role"],
         "lat_deg": float(g["lat_deg"]), "lon_deg": float(g["lon_deg"])}
        for g in scenario["ground_sites"]
    ]
    st.session_state["sites_nonce"] = st.session_state.get("sites_nonce", 0) + 1
    st.session_state["sats_seed"] = [
        {"id": x["id"], "plane_id": x["plane_id"], "slot_deg": float(x["slot_deg"]),
         "launch_batch": int(x["launch_batch"])}
        for x in scenario["design"]["satellites"]
    ]
    st.session_state["sats_nonce"] = st.session_state.get("sats_nonce", 0) + 1
    st.session_state[f"meta_title_{nonce}"] = str(scenario_meta(scenario).get("title", ""))


def load_builtin(filename: str) -> None:
    scenario = load_file(DATA_DIR / filename)
    st.session_state["base_scenario"] = scenario
    st.session_state["base_name"] = filename
    st.session_state["nonce"] = st.session_state.get("nonce", 0) + 1
    prime_widgets(scenario, st.session_state["nonce"])
    st.session_state["sim"] = None
    st.session_state["sim_scenario"] = None
    st.session_state["stale"] = True
    st.session_state["autorun"] = True


if "nonce" not in st.session_state:
    load_builtin("01_full_constellation.json")

base_scenario: dict = st.session_state["base_scenario"]
nonce: int = st.session_state["nonce"]


# ---------------------------------------------------------------------------
# Формирование effective scenario из виджетов
# ---------------------------------------------------------------------------

def rows_from_editor(seed: list[dict], state: object) -> list[dict]:
    """Применяет DataEditorState к seed-строкам и возвращает итоговый список.

    Streamlit хранит в session_state не данные, а правки (edited_rows,
    added_rows, deleted_rows) относительно переданного data.
    """
    if state is None:
        return [dict(r) for r in seed]
    if isinstance(state, dict):
        edited = state.get("edited_rows") or {}
        added = state.get("added_rows") or []
        deleted = set(state.get("deleted_rows") or [])
    else:
        edited = getattr(state, "edited_rows", None) or {}
        added = getattr(state, "added_rows", None) or []
        deleted = set(getattr(state, "deleted_rows", None) or [])
    rows: list[dict] = []
    for i, raw in enumerate(seed):
        if i in deleted:
            continue
        row = dict(raw)
        changes = edited.get(i, edited.get(str(i)))
        if isinstance(changes, dict):
            row.update(changes)
        rows.append(row)
    for raw in added:
        if isinstance(raw, dict):
            rows.append(dict(raw))
    return rows


def build_effective() -> tuple[dict, list[str]]:
    """Собирает рабочий сценарий из базового и значений виджетов.

    Возвращает (сценарий, список ошибок). Сценарий валиден, если ошибок нет.
    """
    effective = deep_copy(base_scenario)
    errors: list[str] = []
    design = effective["design"]
    design["launch_stage"] = int(st.session_state.get("launch_stage_sel", design["launch_stage"]))

    for plane in design["planes"]:
        raan = st.session_state.get(f"raan_{plane['id']}_{nonce}", plane["raan_deg"])
        phase = st.session_state.get(f"phase_{plane['id']}_{nonce}", plane["phase_deg"])
        plane["raan_deg"] = float(raan) % 360.0
        plane["phase_deg"] = float(phase) % 360.0

    # --- состав группировки: все поля спутников из исходного JSON ---
    sats_key = f"sats_{st.session_state.get('sats_nonce', 0)}"
    raw_sats = rows_from_editor(
        st.session_state.get("sats_seed", []), st.session_state.get(sats_key)
    )
    edited_sats = []
    for row in raw_sats:
        sid = str(row.get("id") or "").strip()
        if not sid:
            continue
        edited_sats.append({
            "id": sid,
            "plane_id": str(row.get("plane_id") or "").strip(),
            "slot_deg": float(row.get("slot_deg") or 0.0),
            "launch_batch": int(row.get("launch_batch") or 1),
        })
    if edited_sats:
        design["satellites"] = edited_sats

    # --- meta.title ---
    title_value = st.session_state.get(f"meta_title_{nonce}")
    if title_value is not None and isinstance(effective.get("meta"), dict):
        effective["meta"]["title"] = str(title_value)

    fkey = f"failures_{st.session_state.get('failures_nonce', 0)}"
    raw_failures = rows_from_editor(
        st.session_state.get("failures_seed", []), st.session_state.get(fkey)
    )
    failures = []
    sat_ids = {s["id"] for s in design["satellites"]}
    for idx, row in enumerate(raw_failures):
        sid = (row.get("satellite_id") or "").strip()
        start, end = row.get("start_s"), row.get("end_s")
        if not sid and start in (None, 0) and end in (None, 0):
            continue
        try:
            failures.append(
                {"satellite_id": sid, "start_s": int(round(float(start))), "end_s": int(round(float(end)))}
            )
        except (TypeError, ValueError):
            errors.append(f"failures[{idx}]: некорректные значения времени ({start!r}; {end!r})")
            continue
    effective["failures"] = failures

    gkey = f"gw_outages_{st.session_state.get('gw_nonce', 0)}"
    raw_gw = rows_from_editor(
        st.session_state.get("gw_seed", []), st.session_state.get(gkey)
    )
    gw_outages = []
    gw_ids = {g["id"] for g in effective["ground_sites"] if g["role"] == "gateway"}
    for idx, row in enumerate(raw_gw):
        gid = (row.get("gateway_id") or "").strip()
        start, end = row.get("start_s"), row.get("end_s")
        if not gid and start in (None, 0) and end in (None, 0):
            continue
        try:
            gw_outages.append(
                {"gateway_id": gid, "start_s": int(round(float(start))), "end_s": int(round(float(end)))}
            )
        except (TypeError, ValueError):
            errors.append(f"gateway_outages[{idx}]: некорректные значения времени ({start!r}; {end!r})")
    effective["gateway_outages"] = gw_outages

    env = effective["environment"]
    for key in ("altitude_km", "inclination_deg", "earth_angle0_deg", "min_elevation_deg",
                "isl_range_km", "target_availability"):
        if f"env_{key}_{nonce}" in st.session_state:
            env[key] = float(st.session_state[f"env_{key}_{nonce}"])
    for key in ("horizon_s", "step_s"):
        if f"env_{key}_{nonce}" in st.session_state:
            env[key] = int(st.session_state[f"env_{key}_{nonce}"])

    skey = f"sites_{st.session_state.get('sites_nonce', 0)}"
    raw_sites = rows_from_editor(
        st.session_state.get("sites_seed", []), st.session_state.get(skey)
    )
    ground_by_id = {g["id"]: g for g in effective["ground_sites"]}
    seen_ids = set()
    for row in raw_sites:
        gid = str(row.get("id") or "").strip()
        if not gid:
            continue
        role = str(row.get("role") or "").strip()
        try:
            lat = float(row.get("lat_deg"))
            lon = float(row.get("lon_deg"))
        except (TypeError, ValueError):
            errors.append(f"ground_sites ({gid}): некорректные координаты")
            continue
        site = ground_by_id.get(gid)
        if site is None:  # новая строка редактора — новый наземный пункт
            site = {"id": gid, "name": str(row.get("name") or gid), "role": role or "client",
                    "lat_deg": lat, "lon_deg": lon}
            effective["ground_sites"].append(site)
            ground_by_id[gid] = site
        site["lat_deg"], site["lon_deg"] = lat, lon
        if role in ("client", "gateway"):
            site["role"] = role
        site["name"] = str(row.get("name") or site.get("name", gid))
        seen_ids.add(gid)
    effective["ground_sites"] = [g for g in effective["ground_sites"] if g["id"] in seen_ids]

    try:
        ensure_valid(effective)
    except ScenarioValidationError as exc:
        errors.extend(exc.errors)
    except ValueError as exc:  # официальная geometry.validate
        errors.append(f"Официальная проверка geometry.validate: {exc}")
    return effective, errors


# ---------------------------------------------------------------------------
# Боковая панель
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🛰 Устойчивая группировка")
    st.caption("КосмоХакатон 2026 · кейс «Проектирование устойчивой спутниковой группировки»")

    st.header("1. Сценарий")
    choice = st.selectbox(
        "Встроенный сценарий",
        list(BUILTIN_SCENARIOS.keys()),
        index=0,
        key=f"builtin_choice_{nonce}",
    )
    upload = st.file_uploader("…или загрузите свой JSON (cosmo-A-1.0)", type=["json"])
    col_a, col_b = st.columns(2)
    if col_a.button("Открыть встроенный", use_container_width=True):
        load_builtin(BUILTIN_SCENARIOS[choice])
        st.rerun()
    if upload is not None and col_b.button("Загрузить файл", use_container_width=True, type="primary"):
        try:
            scenario = json.loads(upload.getvalue().decode("utf-8"))
            errors = []
            try:
                ensure_valid(scenario)
            except ScenarioValidationError as exc:
                errors = exc.errors
            except ValueError as exc:
                errors = [str(exc)]
            if errors:
                st.error("Файл не прошёл проверку:\n" + "\n".join(f"• {e}" for e in errors[:12]))
            else:
                st.session_state["base_scenario"] = scenario
                st.session_state["base_name"] = upload.name
                st.session_state["nonce"] = nonce + 1
                prime_widgets(scenario, st.session_state["nonce"])
                st.session_state["sim"] = None
                st.session_state["sim_scenario"] = None
                st.session_state["stale"] = True
                st.session_state["autorun"] = True
                st.rerun()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            st.error(f"Файл не является корректным JSON (UTF-8): {exc}")

    st.divider()
    st.header("2. Конфигурация проекта")
    st.selectbox(
        "Этап развёртывания (launch_stage)",
        [1, 2, 3],
        key="launch_stage_sel",
        format_func=lambda v: f"{v} — запущено {v * 16} аппаратов",
        help="В расчёте участвуют спутники с launch_batch ≤ launch_stage.",
    )
    for plane in base_scenario["design"]["planes"]:
        with st.expander(f"Плоскость {plane['id']}", expanded=False):
            c1, c2 = st.columns(2)
            c1.number_input(
                f"RAAN {plane['id']}, °", min_value=0.0, max_value=359.99, step=7.5,
                key=f"raan_{plane['id']}_{nonce}",
            )
            c2.number_input(
                f"Фазирование {plane['id']}, °", min_value=0.0, max_value=359.99, step=7.5,
                key=f"phase_{plane['id']}_{nonce}",
            )

    st.subheader("Периоды отказа спутников")
    sat_ids = [s["id"] for s in base_scenario["design"]["satellites"]]
    st.data_editor(
        st.session_state.get("failures_seed", []),
        key=f"failures_{st.session_state.get('failures_nonce', 0)}",
        num_rows="dynamic",
        column_config={
            "satellite_id": st.column_config.SelectboxColumn("Спутник", options=sat_ids, required=True),
            "start_s": st.column_config.NumberColumn("Начало, с", min_value=0, step=60),
            "end_s": st.column_config.NumberColumn("Конец, с", min_value=0, step=60),
        },
        use_container_width=True,
    )
    st.caption("Интервал [start_s; end_s): начало включается, конец исключается.")

    st.subheader("Периоды отказа шлюзов")
    gw_ids = [g["id"] for g in base_scenario["ground_sites"] if g["role"] == "gateway"]
    st.data_editor(
        st.session_state.get("gw_seed", []),
        key=f"gw_outages_{st.session_state.get('gw_nonce', 0)}",
        num_rows="dynamic",
        column_config={
            "gateway_id": st.column_config.SelectboxColumn("Шлюз", options=gw_ids, required=True),
            "start_s": st.column_config.NumberColumn("Начало, с", min_value=0, step=60),
            "end_s": st.column_config.NumberColumn("Конец, с", min_value=0, step=60),
        },
        use_container_width=True,
    )

    with st.expander("Advanced: предпосылки сценария и пункты", expanded=False):
        st.caption(
            "Физические предпосылки расчёта (не управление аппаратом). "
            "Движок принимает значения из файла; здесь их можно исследовать."
        )
        env = base_scenario["environment"]
        c1, c2 = st.columns(2)
        c1.number_input("Высота орбиты, км", 200.0, 1200.0, key=f"env_altitude_km_{nonce}", step=10.0)
        c2.number_input("Наклонение, °", 0.0, 180.0, key=f"env_inclination_deg_{nonce}", step=1.0)
        c1.number_input("Поворот Земли в t=0, °", -36000.0, 36000.0, key=f"env_earth_angle0_deg_{nonce}", step=1.0)
        c2.number_input("Мин. угол возвышения, °", 0.0, 89.0, key=f"env_min_elevation_deg_{nonce}", step=1.0)
        c1.number_input("Дальность МСC, км", 1.0, 10000.0, key=f"env_isl_range_km_{nonce}", step=100.0)
        c2.number_input("Целевая доступность", 0.0, 1.0, key=f"env_target_availability_{nonce}", step=0.05)
        c1.number_input("Горизонт, с", 120, 172800, key=f"env_horizon_s_{nonce}", step=120)
        c2.number_input("Шаг, с", 1, 172800, key=f"env_step_s_{nonce}", step=10)
        st.markdown("**Название проекта (meta.title)**")
        st.text_input("Название", key=f"meta_title_{nonce}")
        st.markdown("**Состав группировки (satellites)**")
        st.data_editor(
            st.session_state.get("sats_seed", []),
            key=f"sats_{st.session_state.get('sats_nonce', 0)}",
            num_rows="dynamic",
            column_config={
                "id": st.column_config.TextColumn("ID", required=True),
                "plane_id": st.column_config.SelectboxColumn(
                    "Плоскость",
                    options=[p["id"] for p in base_scenario["design"]["planes"]],
                    required=True,
                ),
                "slot_deg": st.column_config.NumberColumn("slot_deg, °", step=7.5),
                "launch_batch": st.column_config.SelectboxColumn(
                    "Очередь (launch_batch)", options=[1, 2, 3], required=True,
                ),
            },
            use_container_width=True,
        )
        st.caption("ID, плоскость, положение в плоскости и очередь каждого аппарата.")
        st.markdown("**Наземные пункты (ground_sites)**")
        st.data_editor(
            st.session_state.get("sites_seed", []),
            key=f"sites_{st.session_state.get('sites_nonce', 0)}",
            num_rows="dynamic",
            column_config={
                "id": st.column_config.TextColumn("ID", required=True),
                "name": st.column_config.TextColumn("Название"),
                "role": st.column_config.SelectboxColumn("Роль", options=["client", "gateway"], required=True),
                "lat_deg": st.column_config.NumberColumn("Широта", min_value=-90.0, max_value=90.0, step=0.5),
                "lon_deg": st.column_config.NumberColumn("Долгота", min_value=-180.0, max_value=180.0, step=0.5),
            },
            use_container_width=True,
        )
        st.caption("Роль, координаты и название пунктов; можно добавлять и удалять строки.")

    st.divider()
    st.header("3. Расчёт")
    strategy = st.selectbox(
        "Стратегия маршрутизации",
        [STRATEGY_MIN_DISTANCE, STRATEGY_MIN_HOPS],
        format_func=lambda v: STRATEGY_LABELS[v],
        help="По умолчанию — минимум суммарной геометрической длины "
             "(взвешенный поиск кратчайшего пути по реальным расстояниям модели, "
             "детерминированный tie-break). "
             "«Минимум переходов» — baseline для сравнения; достижимость совпадает.",
    )
    do_run = st.button("▶ Пересчитать", type="primary", use_container_width=True)
    col_r1, col_r2 = st.columns(2)
    if col_r1.button("↺ Сброс изменений", use_container_width=True, help="Вернуть параметры загруженного сценария"):
        prime_widgets(base_scenario, nonce)
        st.session_state["stale"] = True
        st.rerun()
    if col_r2.button("💾 Сохранить вариант", use_container_width=True):
        effective, errors = build_effective()
        if errors:
            st.error("Сначала исправьте ошибки сценария:\n" + "\n".join(errors[:5]))
        else:
            name = f"Вариант {len(st.session_state.get('variants', {})) + 1}"
            # вариант обязан соответствовать и сценарию, и выбранной стратегии:
            # иначе подпись стратегии не совпадёт с реальными метриками
            sim_now = st.session_state.get("sim")
            if (
                sim_now is None
                or scenario_json_of(sim_now.scenario) != scenario_json_of(effective)
                or sim_now.strategy != strategy
            ):
                sim_now = simulate_scenario(effective, strategy=strategy, with_backups=True)
            variants = st.session_state.setdefault("variants", {})
            variants[name] = Variant(
                name=name,
                scenario=deep_copy(effective),
                strategy=strategy,
                created_at=datetime.now().strftime("%H:%M:%S"),
                metrics=dict(sim_now.metrics),
                global_metrics=sim_now.global_metrics,
            )
            st.toast(f"Сохранено: {name} (стратегия: {STRATEGY_LABELS[strategy].split(' (')[0]})")


# ---------------------------------------------------------------------------
# Расчёт (автозапуск при загрузке сценария или по кнопке)
# ---------------------------------------------------------------------------

effective, effective_errors = build_effective()
sim_prev = st.session_state.get("sim")
is_stale = (
    sim_prev is None
    or scenario_json_of(sim_prev.scenario) != scenario_json_of(effective)
    or sim_prev.strategy != strategy
)
if is_stale and sim_prev is not None and not do_run:
    st.sidebar.warning("Параметры изменены — результаты ниже относятся к предыдущему расчёту. "
                       "Нажмите «▶ Пересчитать».")

if do_run or (st.session_state.get("autorun") and st.session_state.get("sim") is None):
    if effective_errors:
        st.error("Сценарий не прошёл проверку:\n" + "\n".join(f"• {e}" for e in effective_errors[:12]))
        st.stop()
    progress = st.progress(0.0, text="Моделирование сети…")
    sim = cached_simulate(scenario_json_of(effective), strategy)
    progress.empty()
    st.session_state["sim"] = sim
    st.session_state["sim_scenario"] = effective
    st.session_state["stale"] = False
    st.session_state["autorun"] = False
    st.session_state["t_slider"] = 0

sim = st.session_state.get("sim")
if sim is None:
    st.info("Настройте конфигурацию слева и нажмите «▶ Пересчитать».")
    st.stop()
if effective_errors and not do_run:
    st.warning("Текущие настройки содержат ошибки — показан последний успешный расчёт:\n"
               + "\n".join(f"• {e}" for e in effective_errors[:8]))

scenario_used = st.session_state["sim_scenario"]
step_s = sim.step_s()
target = float(scenario_used["environment"]["target_availability"])


# ---------------------------------------------------------------------------
# Заголовок
# ---------------------------------------------------------------------------

st.title(f"📋 {scenario_title(scenario_used)}")
head_cols = st.columns(6)
head_cols[0].metric("Активных спутников (t=0)", f"{sim.active_counts[0]} / {len(sim.sat_ids)}")
head_cols[1].metric("Этап развёртывания", scenario_used["design"]["launch_stage"])
head_cols[2].metric("Целевая доступность", fmt_pct(target, 0))
head_cols[3].metric("Отсчётов", len(sim.ticks))
head_cols[4].metric("Шаг", f"{step_s} с")
head_cols[5].metric("Горизонт", hhmmss(scenario_used["environment"]["horizon_s"]))

if sim.validation_problems:
    st.error(f"Обнаружены недопустимые маршруты ({len(sim.validation_problems)}): "
             + "; ".join(sim.validation_problems[:3]))

tab_names = ["Обзор", "Сеть и время", "Сравнение", "Устойчивость", "Экспорт", "О методике"]
tab_choice = st.radio("Раздел", tab_names, horizontal=True, key="tab_nav", label_visibility="collapsed")
tabs = [tab_choice]  # совместимость с блоками below


# ---------------------------------------------------------------------------
# Текущий вариант для сравнения/рекомендации (нужен нескольким разделам)
# ---------------------------------------------------------------------------

saved = st.session_state.get("variants", {})
current = Variant(
    name="Текущий", scenario=scenario_used, strategy=sim.strategy,
    created_at=datetime.now().strftime("%H:%M:%S"),
    metrics=dict(sim.metrics), global_metrics=sim.global_metrics,
)

# ---------------------------------------------------------------------------
# Вкладка «Обзор»
# ---------------------------------------------------------------------------

if tab_choice == "Обзор":
    st.subheader("Показатели клиентских пунктов")
    cols = st.columns(max(1, len(sim.clients)))
    for col, client_id in zip(cols, sim.clients):
        m = sim.metrics[client_id]
        col.markdown(
            f"""
            <div style="border:1px solid {'#2e7d32' if m.target_met else '#c62828'}; border-radius:10px;
                 padding:12px 16px; margin-bottom:8px;">
              <div style="font-weight:700; font-size:16px;">{client_id}</div>
              <div style="font-size:26px; font-weight:800; color:{'#2e7d32' if m.target_met else '#c62828'};">
                {fmt_pct(m.availability_fraction)}</div>
              <div style="font-size:13px;">доступность (цель {fmt_pct(target, 0)}: {'✅' if m.target_met else '❌'})</div>
              <div style="font-size:13px; margin-top:6px;">видимость: <b>{fmt_pct(m.visibility_fraction)}</b></div>
              <div style="font-size:13px;">макс. перерыв: <b>{m.max_outage_s} с</b> ({hhmmss(m.max_outage_s)})</div>
              <div style="font-size:13px;">переходов в среднем: <b>{'—' if m.mean_hops is None else f'{m.mean_hops:.2f}'}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    g = sim.global_metrics
    total_changes = sum(m.route_change_count for m in sim.metrics.values())
    st.info(
        f"**Сводка:** min доступность по пунктам — **{fmt_pct(g.min_availability)}**, "
        f"средняя — **{fmt_pct(g.mean_availability)}**, худший максимальный перерыв — "
        f"**{g.worst_max_outage_s} с**, цель достигнута для **{g.target_met_clients} из {g.total_clients}** пунктов. "
        f"Перестроений маршрута за сутки: **{total_changes}** — конфигурации с равной доступностью "
        f"могут отличаться эксплуатационно."
    )

    best, why = recommend([*saved.values(), current])
    if best is not None:
        st.success(f"**Рекомендация:** {why}")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(viz.connectivity_over_time(sim), use_container_width=True)
    with right:
        st.plotly_chart(viz.ground_track(scenario_used, sim, sim.ticks[min(st.session_state.get("t_slider", 0), len(sim.ticks) - 1)]),
                        use_container_width=True)

    rows = []
    for client_id in sim.clients:
        m = sim.metrics[client_id]
        rows.append({
            "Пункт": client_id,
            "Видимость": fmt_pct(m.visibility_fraction),
            "Доступность": fmt_pct(m.availability_fraction),
            "Макс. перерыв, с": m.max_outage_s,
            "Перерывов": len(m.outage_intervals),
            "Ср. переходов": "—" if m.mean_hops is None else f"{m.mean_hops:.2f}",
            "P95 переходов": "—" if m.p95_hops is None else f"{m.p95_hops:.0f}",
            "Смен маршрута": m.route_change_count,
            "Резерв есть, %": "—" if m.backup_fraction is None else fmt_pct(m.backup_fraction, 0),
            "Цель": "✅" if m.target_met else "❌",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Вкладка «Сеть и время»
# ---------------------------------------------------------------------------

if tab_choice == "Сеть и время":
    st.subheader("Состояние сети в выбранный момент")
    client_options = list(sim.clients)
    if "net_client" not in st.session_state or st.session_state["net_client"] not in client_options:
        st.session_state["net_client"] = client_options[0]
    sel_cols = st.columns([3, 1, 1, 1.4])
    selected_client = st.session_state.get("net_client", client_options[0])
    series = sim.series[selected_client]
    m = sim.metrics[selected_client]

    jump_targets: list[tuple[str, int]] = []
    for iv in m.outage_intervals:
        idx = min(range(len(sim.ticks)), key=lambda i: abs(sim.ticks[i] - iv.start_s))
        jump_targets.append((f"начало перерыва {iv.start_s} с ({hhmmss(iv.start_s)})", idx))
    if jump_targets:
        worst = max(m.outage_intervals, key=lambda iv: iv.duration_s)
        worst_idx = min(range(len(sim.ticks)), key=lambda i: abs(sim.ticks[i] - worst.start_s))
        jump_targets.insert(0, (f"⚠ самый длинный перерыв: {worst.duration_s} с от {hhmmss(worst.start_s)}", worst_idx))
    cur_idx = st.session_state.get("t_slider", 0)
    prev_outages = [idx for label, idx in jump_targets if idx < cur_idx]
    next_outages = [idx for label, idx in jump_targets if idx > cur_idx]

    def _go_prev() -> None:
        st.session_state["t_slider"] = prev_outages[-1]

    def _go_next() -> None:
        st.session_state["t_slider"] = next_outages[0]

    sel_cols[1].button("◀ Перерыв", on_click=_go_prev, disabled=not prev_outages, use_container_width=True)
    sel_cols[2].button("Перерыв ▶", on_click=_go_next, disabled=not next_outages, use_container_width=True)
    t_index = sel_cols[0].select_slider(
        "Время расчёта",
        options=list(range(len(sim.ticks))),
        value=min(cur_idx, len(sim.ticks) - 1),
        format_func=lambda i: f"{sim.ticks[i]} с ({hhmmss(sim.ticks[i])})",
        key="t_slider",
    )
    selected_client = sel_cols[3].selectbox("Клиентский пункт", client_options, key="net_client")
    t_s = sim.ticks[t_index]

    status = series.statuses[t_index]
    path = series.paths[t_index]
    if jump_targets:
        sel_cols[0].caption("Быстрый переход: " + " · ".join(label for label, _ in jump_targets[:4]))

    if status == 0:
        st.success(f"**Маршрут есть:** {' → '.join(path)} · переходов: {len(path) - 1}")
    else:
        st.error(f"**Маршрута нет ({hhmmss(t_s)}):** {STATUS_LABELS.get(status)} — {series.details[t_index]}")

    net_fig = viz.network_3d(scenario_used, sim, t_s, selected_client, path)
    st.plotly_chart(net_fig, use_container_width=True)

    st.plotly_chart(viz.timeline_heatmap(sim, selected_client), use_container_width=True)
    st.plotly_chart(viz.hops_scatter(sim, selected_client), use_container_width=True)

    st.subheader("Перерывы связи выбранного пункта")
    iv_rows = [
        {
            "Начало, с": iv.start_s, "Начало": hhmmss(iv.start_s),
            "Конец, с": iv.end_s, "Конец": hhmmss(iv.end_s),
            "Длительность, с": iv.duration_s,
            "Причина": iv.reason,
            "Состав": iv.detail,
        }
        for iv in m.outage_intervals
    ]
    st.dataframe(pd.DataFrame(iv_rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Вкладка «Сравнение»
# ---------------------------------------------------------------------------

if tab_choice == "Сравнение":
    if not saved:
        st.info("Сохраните хотя бы один вариант в боковой панели («💾 Сохранить вариант»), "
                "затем измените конфигурацию и пересчитайте — после этого варианты можно сравнить.")
    options = [*saved.keys(), "Текущий"]
    colc1, colc2 = st.columns(2)
    name_a = colc1.selectbox("Вариант A", options, index=0, key="cmp_a")
    name_b = colc2.selectbox(
        "Вариант B", options,
        index=max(0, len(options) - 1),
        key="cmp_b",
    )

    def variant_by_name(name: str) -> Variant:
        return current if name == "Текущий" else saved[name]

    if name_a and name_b and name_a != name_b:
        va, vb = variant_by_name(name_a), variant_by_name(name_b)
        st.markdown("#### Различия конфигурации")
        st.dataframe(pd.DataFrame(config_diff_rows(va.scenario, vb.scenario)),
                     use_container_width=True, hide_index=True)
        st.markdown("#### Метрики по пунктам")
        st.dataframe(pd.DataFrame(metrics_diff_rows(va.metrics, vb.metrics)),
                     use_container_width=True, hide_index=True)
        st.markdown("#### Глобальные показатели")
        st.dataframe(pd.DataFrame(global_diff_rows(va.global_metrics, vb.global_metrics)),
                     use_container_width=True, hide_index=True)
        bar1, bar2 = st.columns(2)
        bar1.plotly_chart(
            viz.availability_bars(
                {va.name: {c: m.availability_fraction for c, m in va.metrics.items()},
                 vb.name: {c: m.availability_fraction for c, m in vb.metrics.items()}},
                target,
            ),
            use_container_width=True,
        )
        bar2.plotly_chart(
            viz.outage_bars(
                {va.name: {c: m.max_outage_s for c, m in va.metrics.items()},
                 vb.name: {c: m.max_outage_s for c, m in vb.metrics.items()}},
            ),
            use_container_width=True,
        )
        best, why = recommend([va, vb])
        if best is not None:
            st.success(f"**Рекомендация:** {why}")
        with st.expander("Как считается рекомендация"):
            st.markdown(
                "Лексикографический критерий (без «магического» score):\n\n"
                "1. максимум **минимальной** доступности среди пунктов;\n"
                "2. затем максимум **средней** доступности;\n"
                "3. затем минимум **худшего** максимального перерыва;\n"
                "4. затем минимум среднего числа переходов.\n\n"
                "Целевая доступность показывается линией на графиках, но конфигурация "
                "не объявляется «невалидной» при её недостижении."
            )
    elif name_a == name_b:
        st.warning("Выберите два разных варианта.")


# ---------------------------------------------------------------------------
# Вкладка «Устойчивость»
# ---------------------------------------------------------------------------

if tab_choice == "Устойчивость":
    st.subheader("Причины перерывов (все пункты, весь горизонт)")
    summary = reason_summary(sim)
    if summary:
        st.dataframe(
            pd.DataFrame([{"Причина": k, "Отсчётов (пункт × время)": v} for k, v in summary.items()]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.success("Перерывов нет: полный маршрут существует на всех отсчётах для всех пунктов.")

    st.subheader("Критичность спутников (single-satellite outage analysis)")
    st.caption(
        "Для каждого спутника моделируется его отсутствие на всём горизонте без пересчёта орбитальной "
        "геометрии; ранжирование — по падению минимальной доступности, затем по росту худшего перерыва. "
        "Так выявляются самые уязвимые места группировки."
    )
    if st.button("🔎 Запустить анализ критичности", disabled=not sim.clients):
        with st.spinner("Анализ критичности (один проход по сетке времени)…"):
            rows = cached_criticality(scenario_json_of(st.session_state["sim_scenario"]), sim.strategy)
        st.session_state["crit_rows"] = rows
    crit_rows = st.session_state.get("crit_rows")
    if crit_rows:
        top = [r for r in crit_rows if r.usage_count > 0 or r.ticks_made_unavailable > 0][:10]
        df = pd.DataFrame([
            {
                "Спутник": r.satellite_id,
                "В маршрутах, отсчётов": r.usage_count,
                "Δ min доступности, п.п.": round(100 * r.delta_min_availability, 2),
                "Δ mean доступности, п.п.": round(100 * r.delta_mean_availability, 2),
                "Δ худшего перерыва, с": r.delta_worst_outage_s,
                "Потеряно отсчётов": r.ticks_made_unavailable,
                "Затронуты": ", ".join(r.affected_clients),
            }
            for r in top
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        if top:
            st.markdown("##### Применить отказ выбранного спутника к сценарию")
            ac1, ac2, ac3 = st.columns([2, 1, 1])
            victim = ac1.selectbox("Спутник", [r.satellite_id for r in top], key="crit_victim")
            fail_start = ac2.number_input("Начало, с", 0, scenario_used["environment"]["horizon_s"], 0, step=60, key="crit_start")
            fail_end = ac3.number_input(
                "Конец, с", 1, scenario_used["environment"]["horizon_s"],
                scenario_used["environment"]["horizon_s"], step=60, key="crit_end",
            )
            if st.button("➕ Добавить отказ в сценарий"):
                fkey_now = f"failures_{st.session_state.get('failures_nonce', 0)}"
                current_rows = [
                    {"satellite_id": r["satellite_id"], "start_s": int(r["start_s"]), "end_s": int(r["end_s"])}
                    for r in rows_from_editor(
                        st.session_state.get("failures_seed", []), st.session_state.get(fkey_now)
                    )
                    if r.get("satellite_id")
                ]
                current_rows.append({"satellite_id": victim, "start_s": int(fail_start), "end_s": int(fail_end)})
                st.session_state["failures_seed"] = current_rows
                st.session_state["failures_nonce"] = st.session_state.get("failures_nonce", 0) + 1
                st.session_state["stale"] = True
                st.rerun()

    st.divider()
    st.subheader("Что если: отказ одного аппарата")
    with st.expander("Смоделировать отказ и увидеть эффект", expanded=False):
        ic1, ic2, ic3 = st.columns(3)
        impact_sat = ic1.selectbox("Спутник", sim.sat_ids, key="impact_sat")
        horizon = scenario_used["environment"]["horizon_s"]
        impact_start = ic2.number_input("Начало, с", 0, horizon - 1, 21600, step=60, key="impact_start")
        impact_end = ic3.number_input("Конец, с", 1, horizon, horizon, step=60, key="impact_end")
        if st.button("📊 Оценить влияние отказа"):
            modified, impacted = apply_failure_impact(
                deep_copy(scenario_used), sim, impact_sat, int(impact_start), int(impact_end)
            )
            st.session_state["impact_result"] = (modified, impacted, impact_sat)
        if "impact_result" in st.session_state:
            modified, impacted, impact_sat = st.session_state["impact_result"]
            delta_rows = []
            for client_id in sim.clients:
                base_m, new_m = sim.metrics[client_id], impacted.metrics[client_id]
                delta_rows.append({
                    "Пункт": client_id,
                    "Доступность была": fmt_pct(base_m.availability_fraction),
                    "Стала": fmt_pct(new_m.availability_fraction),
                    "Δ, п.п.": f"{100 * (new_m.availability_fraction - base_m.availability_fraction):+.2f}",
                    "Макс. перерыв был, с": base_m.max_outage_s,
                    "Стал, с": new_m.max_outage_s,
                })
            st.dataframe(pd.DataFrame(delta_rows), use_container_width=True, hide_index=True)
            if st.button("✔ Оставить этот отказ в сценарии"):
                st.session_state["failures_seed"] = [
                    {"satellite_id": f["satellite_id"], "start_s": int(f["start_s"]), "end_s": int(f["end_s"])}
                    for f in modified["failures"]
                ]
                st.session_state["failures_nonce"] = st.session_state.get("failures_nonce", 0) + 1
                st.session_state["stale"] = True
                st.rerun()

    st.divider()
    st.subheader("🚀 Быстрый подбор конфигурации (бонус)")
    with st.expander("Автоподбор RAAN/фазирования плоскостей", expanded=False):
        st.caption(
            "Координатный поиск по осям RAAN/фазирование на прореженной сетке времени "
            "(детерминированный, launch_batch не меняется), затем полный пересчёт лучшего кандидата."
        )
        plane_ids = [p["id"] for p in scenario_used["design"]["planes"]]
        opt_planes = st.multiselect("Какие плоскости разрешено менять", plane_ids, default=plane_ids, key="opt_planes")
        opt_budget = st.slider("Бюджет оценок", 8, 60, 24, key="opt_budget")
        if st.button("Запустить подбор", disabled=not opt_planes):
            with st.spinner("Поиск конфигурации…"):
                opt = optimize_configuration(
                    deep_copy(scenario_used), plane_ids=opt_planes, budget=opt_budget,
                    strategy=sim.strategy,
                )
                opt_sim = simulate_scenario(opt.best_scenario, strategy=sim.strategy, with_backups=True)
            # «оптимизированный» — только если кандидат победил базовый на ПОЛНОЙ сетке
            base_key = objective_key(sim.metrics, sim.global_metrics)
            cand_key = objective_key(opt_sim.metrics, opt_sim.global_metrics)
            st.session_state["opt_result"] = (opt, opt_sim, cand_key < base_key)
        if "opt_result" in st.session_state:
            opt, opt_sim, confirmed = st.session_state["opt_result"]
            if not confirmed:
                st.warning("На полной сетке улучшение не подтверждено: coarse-кандидат не лучше "
                           "текущей конфигурации по лексикографическому критерию. Кнопка применения скрыта.")
            col_o1, col_o2 = st.columns(2)
            col_o1.metric("Оценок выполнено", opt.evaluations)
            col_o2.metric("Шаг coarse-сетки", f"{opt.coarse_step_s} с")
            b1, b2 = st.columns(2)
            b1.plotly_chart(
                viz.availability_bars(
                    {"Базовый": {c: m.availability_fraction for c, m in sim.metrics.items()},
                     "Оптимизированный": {c: m.availability_fraction for c, m in opt_sim.metrics.items()}},
                    target,
                ),
                use_container_width=True,
            )
            b2.plotly_chart(
                viz.outage_bars(
                    {"Базовый": {c: m.max_outage_s for c, m in sim.metrics.items()},
                     "Оптимизированный": {c: m.max_outage_s for c, m in opt_sim.metrics.items()}},
                ),
                use_container_width=True,
            )
            st.markdown("**Параметры лучшего кандидата:**")
            st.dataframe(
                pd.DataFrame([
                    {"Плоскость": p["id"], "RAAN было": q["raan_deg"], "RAAN стало": p["raan_deg"],
                     "Фазирование было": q["phase_deg"], "Фазирование стало": p["phase_deg"]}
                    for p, q in zip(opt.best_scenario["design"]["planes"], scenario_used["design"]["planes"])
                ]),
                use_container_width=True, hide_index=True,
            )
            if confirmed and st.button("✔ Использовать подтверждённую конфигурацию"):
                for plane in opt.best_scenario["design"]["planes"]:
                    st.session_state[f"raan_{plane['id']}_{nonce}"] = float(plane["raan_deg"])
                    st.session_state[f"phase_{plane['id']}_{nonce}"] = float(plane["phase_deg"])
                st.session_state["stale"] = True
                st.rerun()


# ---------------------------------------------------------------------------
# Вкладка «Экспорт»
# ---------------------------------------------------------------------------

if tab_choice == "Экспорт":
    st.subheader("Экспорт результатов расчёта")
    result = build_result(sim)
    routes_total = len(result["routes"])
    st.caption(
        f"Официальный формат cosmo-A-result-1.0 строго по схеме: routes = {routes_total} записей "
        f"({len(sim.ticks)} отсчётов × {len(sim.clients)} пунктов), effective_scenario включает все изменения. "
        "Дополнительных top-level полей в result нет — сводки и причины выгружаются отдельным analysis report."
    )
    col_e1, col_e2 = st.columns(2)
    col_e1.download_button(
        "⬇ Download result JSON (официальная схема)",
        data=dumps_result(result).encode("utf-8"),
        file_name=f"result_{scenario_used.get('meta', {}).get('id', 'scenario')}.json",
        mime="application/json",
        use_container_width=True,
    )
    col_e2.download_button(
        "⬇ Download analysis report JSON (сводки и причины)",
        data=dumps_result(build_analysis_report(sim)).encode("utf-8"),
        file_name=f"analysis_report_{scenario_used.get('meta', {}).get('id', 'scenario')}.json",
        mime="application/json",
        use_container_width=True,
    )
    col_e2.download_button(
        "⬇ Download effective scenario JSON",
        data=dumps_scenario(scenario_used).encode("utf-8"),
        file_name=f"effective_{scenario_used.get('meta', {}).get('id', 'scenario')}.json",
        mime="application/json",
        use_container_width=True,
    )
    col_e3, col_e4 = st.columns(2)
    col_e3.download_button(
        "⬇ Download metrics CSV",
        data=metrics_csv(sim).encode("utf-8-sig"),
        file_name="metrics.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_e4.download_button(
        "⬇ Download timeline CSV",
        data=timeline_csv(sim).encode("utf-8-sig"),
        file_name="timeline.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption("Экспортированный effective scenario можно снова загрузить через «…или загрузите свой JSON» "
               "— он проходит полную валидацию (включая официальную geometry.validate).")


# ---------------------------------------------------------------------------
# Вкладка «О методике»
# ---------------------------------------------------------------------------

if tab_choice == "О методике":
    st.markdown(
        """
### Методика

**Геометрия.** Позиции спутников, видимость и контакты считает официальный
расчётный модуль `geometry.py` (reference implementation) — он подключён как
`vendor/geometry.py` без изменений. Сетка времени: `0, step, …, horizon − step`
(правый конец не включается; для базовых сценариев 720 отсчётов по 120 с).
Интервалы отказов: `[start_s; end_s)` — начало включается, конец исключается.

**Маршрутизация.** Граф на каждом отсчёте строится из `snapshot.edges`:
спутники + наземные пункты; наземные узлы не ретранслируют (client — только
источник, gateway — только терминал). Стратегия по умолчанию — **минимум
суммарной геометрической длины**: маршрут опирается на реальные расстояния
модели (ключ: длина км → число рёбер → путь), выбор полностью
детерминирован. Baseline-альтернатива — BFS «минимум переходов»
(лексикографический tie-break); достижимость у стратегий идентична.
Дополнительно ищется резервный путь, не пересекающийся с основным по
спутникам.

**Метрики (по «Описанию данных»).** Для каждого пункта: доля отсчётов с видимым
активным спутником (visibility), доля отсчётов со сквозным маршрутом
(availability), максимальный перерыв = самая длинная серия отсчётов без маршрута
× step (включая начало и конец горизонта), список перерывов с причинами:
`NO_VISIBLE_CLIENT_SATELLITE`, `GATEWAY_UNAVAILABLE`, `NO_GATEWAY_CONTACT`,
`ISL_NETWORK_DISCONNECTED`. Число переходов маршрута = число рёбер, включая две
наземные линии.

**Рекомендация.** Прозрачный лексикографический критерий: max min-доступность →
max mean-доступность → min худшего перерыва → min среднего числа переходов.
90% — целевой ориентир (линия на графиках), не жёсткое ограничение.

**RAAN и фазирование — проектные параметры.** Мы не управляем положением
спутника в полёте: конфигурация плоскостей задаётся до развёртывания, после
вывода аппараты движутся по ней. Изменение RAAN/фазы в сервисе — это
сравнение проектных вариантов, каждый со своим полным пересчётом. В
конкурсном сценарии один целевой шлюз; ядро при этом универсально и
поддерживает несколько шлюзов.

**Оцениваем и перестроения маршрута.** Помимо доли доступности сервис
считает число смен маршрута (`route_change_count`): конфигурации с равной
доступностью могут отличаться эксплуатационно.

**Что не входит в базовую модель** (по документу «Описание данных»):
рельеф и локальный горизонт, городская застройка, многолучёвость,
радиочастотный бюджет и энергетика. Следующий этап развития —
site-specific horizon mask (рельеф/urban obstruction) поверх официальной
модели возвышения без изменения ядра расчёта.

**Качество.** 131 pytest-теста: валидация (с путями полей), сетка, границы
отказов, маршрутизация на синтетических графах, метрики, экспорт (число записей
= отсчёты × пункты, каждый путь допустим в свой момент), parity собственного
движка с официальным `geometry.py`, регрессионные числа по 4 сценариям.
        """
    )
