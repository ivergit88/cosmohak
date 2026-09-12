# Патч robustness: валидация мусорного JSON, Streamlit callbacks, очистка state.
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def patch(rel, pairs):
    p = ROOT / rel
    src = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in src, f"{rel}: НЕ НАЙДЕНО {old[:60]!r}"
        src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("ok:", rel)

# ================= 1. validation.py: устойчивость к мусору =================
patch("src/cosmo/validation.py", [
    # plane_id: защита от unhashable перед проверкой множества
    ('''            plane_id = sat.get("plane_id")
            if plane_id not in plane_ids:
                errors.append(
                    f'{path}.plane_id = {plane_id!r}: плоскость {plane_id!r} отсутствует в design.planes'
                )''',
     '''            plane_id = sat.get("plane_id")
            if not isinstance(plane_id, str) or plane_id not in plane_ids:
                errors.append(
                    f'{path}.plane_id = {plane_id!r}: плоскость с таким идентификатором отсутствует в design.planes'
                )'''),
    # launch_batch: явная проверка типа перед membership
    ('''            batch = sat.get("launch_batch")
            if not isinstance(batch, int) or isinstance(batch, bool) or batch not in LAUNCH_BATCHES:
                errors.append(f"{path}.launch_batch = {batch!r}: допустимы значения 1, 2 или 3")''',
     '''            batch = sat.get("launch_batch")
            if not isinstance(batch, int) or isinstance(batch, bool) or batch not in LAUNCH_BATCHES:
                errors.append(f"{path}.launch_batch = {batch!r}: допустимы значения 1, 2 или 3")
            if "launch_batch" not in sat:
                errors.append(f"{path}.launch_batch: поле отсутствует")'''),
    # ground role: защита от unhashable
    ('''        role = site.get("role")
        if role in roles:
            roles[role] += 1
        else:
            errors.append(f'{path}.role = {role!r}: допустимы значения "client" или "gateway"')''',
     '''        role = site.get("role")
        if isinstance(role, str) and role in roles:
            roles[role] += 1
        else:
            errors.append(f'{path}.role = {role!r}: допустимы значения "client" или "gateway"')'''),
    # outages: id только строкой перед membership
    ('''        oid = outage.get(id_key)
        if oid not in valid_ids:
            errors.append(f"{opath}.{id_key} = {oid!r}: {label} с таким идентификатором отсутствует")''',
     '''        oid = outage.get(id_key)
        if not isinstance(oid, str) or oid not in valid_ids:
            errors.append(f"{opath}.{id_key} = {oid!r}: {label} с таким идентификатором отсутствует")'''),
    # failures / gateway_outages: секция обязана присутствовать
    ('''    failures = _require_list(scenario.get("failures", []), "failures", errors)
    _validate_outages(failures, "failures", "satellite_id", set(sat_ids), env, errors, label="спутника")
    gw_outages = _require_list(scenario.get("gateway_outages", []), "gateway_outages", errors)''',
     '''    failures = _require_list(scenario.get("failures"), "failures", errors)
    _validate_outages(failures, "failures", "satellite_id", set(sat_ids), env, errors, label="спутника")
    gw_outages = _require_list(scenario.get("gateway_outages"), "gateway_outages", errors)'''),
    # официальный validate: любое исключение заворачиваем в понятную ошибку
    ('''    errors = validate_scenario(scenario)
    if errors:
        raise ScenarioValidationError(errors)
    geometry_adapter.validate_official(scenario)
    return scenario''',
     '''    errors = validate_scenario(scenario)
    if errors:
        raise ScenarioValidationError(errors)
    try:
        geometry_adapter.validate_official(scenario)
    except Exception as exc:  # официальный модуль бросает разные типы
        raise ScenarioValidationError([f"официальная проверка geometry.validate: {exc}"]) from exc
    return scenario'''),
])

# ================= 2. app.py: callbacks и очистка state =================
patch("app.py", [
    # 2a. Сброс через on_click (callback выполняется до отрисовки виджетов)
    ('''    col_r1, col_r2 = st.columns(2)
    if col_r1.button("↺ Сброс изменений", use_container_width=True, help="Вернуть параметры загруженного сценария"):
        prime_widgets(base_scenario, nonce)
        st.session_state["stale"] = True
        st.rerun()''',
     '''    col_r1, col_r2 = st.columns(2)

    def _reset_scenario() -> None:
        prime_widgets(base_scenario, nonce)
        st.session_state["stale"] = True

    col_r1.button("↺ Сброс изменений", on_click=_reset_scenario,
                  use_container_width=True, help="Вернуть параметры загруженного сценария")'''),
    # 2b. Применение оптимизатора через on_click
    ('''            if confirmed and st.button("✔ Использовать подтверждённую конфигурацию"):
                for plane in opt.best_scenario["design"]["planes"]:
                    st.session_state[f"raan_{plane['id']}_{nonce}"] = float(plane["raan_deg"])
                    st.session_state[f"phase_{plane['id']}_{nonce}"] = float(plane["phase_deg"])
                st.session_state["stale"] = True
                st.rerun()''',
     '''            def _apply_optimized() -> None:
                result = st.session_state.get("opt_result")
                if not result or not result[2]:
                    return
                best = result[0].best_scenario
                for plane in best["design"]["planes"]:
                    st.session_state[f"raan_{plane['id']}_{nonce}"] = float(plane["raan_deg"])
                    st.session_state[f"phase_{plane['id']}_{nonce}"] = float(plane["phase_deg"])
                st.session_state["stale"] = True

            if confirmed:
                st.button("✔ Использовать подтверждённую конфигурацию", on_click=_apply_optimized)'''),
    # 2c. Метка этапа: фактическое число спутников, а не stage × 16
    ('''    st.selectbox(
        "Этап развёртывания (launch_stage)",
        [1, 2, 3],
        key="launch_stage_sel",
        format_func=lambda v: f"{v} — запущено {v * 16} аппаратов",
        help="В расчёте участвуют спутники с launch_batch ≤ launch_stage.",
    )''',
     '''    _sat_total = len(base_scenario["design"]["satellites"])
    _stage_counts = {
        v: sum(1 for _x in base_scenario["design"]["satellites"] if _x["launch_batch"] <= v)
        for v in (1, 2, 3)
    }
    st.selectbox(
        "Этап развёртывания (launch_stage)",
        [1, 2, 3],
        key="launch_stage_sel",
        format_func=lambda v: f"{v} — активно {_stage_counts[v]} из {_sat_total} аппаратов",
        help="В расчёте участвуют спутники с launch_batch ≤ launch_stage.",
    )'''),
    # 2d. Очистка сценарий-зависимого state при загрузке
    ('''if "nonce" not in st.session_state:
    load_builtin("01_full_constellation.json")''',
     '''if "nonce" not in st.session_state:
    load_builtin("01_full_constellation.json")


def clear_scenario_analytics() -> None:
    """Убирает результаты аналитик, относящиеся к предыдущему сценарию/расчёту."""
    for key in ("variants", "crit_rows", "impact_result", "opt_result"):
        st.session_state.pop(key, None)'''),
    # 2e. ...и вызов в обоих местах загрузки + после расчёта
    ('''    st.session_state["sim"] = None
    st.session_state["sim_scenario"] = None
    st.session_state["stale"] = True
    st.session_state["autorun"] = True
    st.session_state["t_slider"] = 0''',
     '''    st.session_state["sim"] = None
    st.session_state["sim_scenario"] = None
    st.session_state["stale"] = True
    st.session_state["autorun"] = True
    st.session_state["t_slider"] = 0
    clear_scenario_analytics()'''),
    ('''                st.session_state["sim"] = None
                st.session_state["sim_scenario"] = None
                st.session_state["stale"] = True
                st.session_state["autorun"] = True
                st.rerun()''',
     '''                st.session_state["sim"] = None
                st.session_state["sim_scenario"] = None
                st.session_state["stale"] = True
                st.session_state["autorun"] = True
                clear_scenario_analytics()
                st.rerun()'''),
    ('''    st.session_state["stale"] = False
    st.session_state["autorun"] = False
    st.session_state["t_slider"] = 0''',
     '''    st.session_state["stale"] = False
    st.session_state["autorun"] = False
    st.session_state["t_slider"] = 0
    # производные аналитики относятся к предыдущему расчёту
    for _k in ("crit_rows", "impact_result", "opt_result"):
        st.session_state.pop(_k, None)'''),
])
print("ALL ROBUSTNESS PATCHES APPLIED")
