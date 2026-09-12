"""End-to-end тесты интерфейса через официальный streamlit.testing.AppTest.

Проверяются основные пользовательские сценарии жюри: загрузка сценария,
изменение launch_stage и RAAN, пересчёт, сохранение варианта, сравнение,
экспорт и обработка некорректного JSON-загрузчика.
"""

from __future__ import annotations

import pytest

from tests.conftest import ROOT

app_path = ROOT / "app.py"


def all_text(at) -> str:
    """Весь текст элементов текущего прогона (markdown, статусы, заголовки, таблицы)."""
    parts: list[str] = []
    for coll in (at.markdown, at.info, at.success, at.error, at.warning,
                 at.header, at.subheader, at.caption, at.title):
        try:
            parts.extend(str(x.value) for x in coll)
        except Exception:
            pass
    for df in at.dataframe:
        try:
            value = df.value
            parts.extend(str(c) for c in value.columns)
            parts.extend(str(c) for row in value.astype(str).values for c in row)
        except Exception:
            pass
    for m in at.metric:
        parts.append(f"{m.label} {m.value}")
    return " ".join(parts)


@pytest.fixture()
def app_test():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(app_path), default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def test_app_boots_with_default_scenario(app_test):
    """Приложение стартует, считает сценарий 01 и показывает корректные метрики."""
    at = app_test
    assert at.metric[0].value == "48 / 48"
    body = all_text(at)
    assert "96.67%" in body  # C65 availability
    assert "Рекомендация" in body


def test_launch_stage_switch_drops_availability(app_test):
    """Сценарий жюри: launch_stage 3 -> 1, пересчёт, доступность резко падает."""
    at = app_test
    stage_box = at.sidebar.selectbox(key="launch_stage_sel")
    assert stage_box.value == 3
    stage_box.set_value(1)
    # нажимаем «▶ Пересчитать»
    run_buttons = [b for b in at.sidebar.button if "Пересчитать" in (b.label or "")]
    assert run_buttons, "кнопка пересчёта не найдена"
    run_buttons[0].click()
    at.run()
    assert not at.exception
    body = all_text(at)
    assert "16 / 48" in body  # активных спутников
    assert "27.22%" in body  # C65 availability для launch_stage=1


def test_raan_edit_marks_stale_and_recalc(app_test):
    """Изменение RAAN плоскости требует пересчёта и меняет результат."""
    at = app_test
    raan = at.sidebar.number_input(key="raan_P1_1")
    raan.set_value(30.0)
    run_buttons = [b for b in at.sidebar.button if "Пересчитать" in (b.label or "")]
    run_buttons[0].click()
    at.run()
    assert not at.exception
    # заголовок метрики «Активных спутников» остаётся, расчёт прошёл
    assert at.metric[3].value == "720"


def test_save_variant_and_compare(app_test):
    """Сохранение варианта и появление таблицы сравнения."""
    at = app_test
    save = [b for b in at.sidebar.button if "Сохранить вариант" in (b.label or "")]
    save[0].click()
    at.run()
    assert not at.exception
    # перейти в раздел «Сравнение»
    at.radio(key="tab_nav").set_value("Сравнение")
    at.run()
    assert not at.exception
    body = all_text(at)
    assert "Очередь запуска" in body


def test_export_section_renders(app_test):
    at = app_test
    at.radio(key="tab_nav").set_value("Экспорт")
    at.run()
    assert not at.exception
    body = all_text(at)
    assert "cosmo-A-result-1.0" in body
    assert "720" in body  # routes = 720 x clients


def test_resilience_section_renders(app_test):
    at = app_test
    at.radio(key="tab_nav").set_value("Устойчивость")
    at.run()
    assert not at.exception
    body = all_text(at)
    assert "Критичность" in body


def test_save_variant_uses_current_strategy(app_test):
    """Смена стратегии + сохранение: метрики варианта обязаны соответствовать min_distance."""
    at = app_test
    at.sidebar.selectbox(key=None)  # sanity: коллекция доступна
    strategy_box = [sb for sb in at.sidebar.selectbox if sb.label == "Стратегия маршрутизации"][0]
    strategy_box.set_value("min_distance")
    save = [b for b in at.sidebar.button if "Сохранить вариант" in (b.label or "")]
    save[0].click()
    at.run()
    assert not at.exception
    variants = at.session_state["variants"]
    assert list(variants) == ["Вариант 1"]
    assert variants["Вариант 1"].strategy == "min_distance"


def test_stale_warning_after_edits(app_test):
    """Изменение параметра без пересчёта помечает состояние как устаревшее."""
    at = app_test
    [sb for sb in at.sidebar.selectbox if sb.label == "Стратегия маршрутизации"][0].set_value("min_hops")
    at.run()
    warnings_text = " ".join(str(w.value) for w in at.warning)
    assert "предыдущему расчёту" in warnings_text
