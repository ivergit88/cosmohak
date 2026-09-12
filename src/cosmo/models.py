"""Базовые типы и вспомогательные структуры расчётного ядра."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from typing import Any

# Категории состояния связи клиента на отсчёте времени.
STATUS_CONNECTED = 0
STATUS_NO_VISIBLE_SAT = 1
STATUS_GATEWAY_OFFLINE = 2
STATUS_NO_GATEWAY_CONTACT = 3
STATUS_ISL_DISCONNECTED = 4

STATUS_LABELS: dict[int, str] = {
    STATUS_CONNECTED: "Маршрут есть",
    STATUS_NO_VISIBLE_SAT: "Нет видимого спутника",
    STATUS_GATEWAY_OFFLINE: "Шлюз недоступен",
    STATUS_NO_GATEWAY_CONTACT: "Нет контакта шлюза",
    STATUS_ISL_DISCONNECTED: "Разрыв межспутниковой сети",
}

STATUS_COLORS: dict[int, str] = {
    STATUS_CONNECTED: "#2e7d32",
    STATUS_NO_VISIBLE_SAT: "#b71c1c",
    STATUS_GATEWAY_OFFLINE: "#ef6c00",
    STATUS_NO_GATEWAY_CONTACT: "#f9a825",
    STATUS_ISL_DISCONNECTED: "#6a1b9a",
}

ROLES = ("client", "gateway")
LAUNCH_BATCHES = (1, 2, 3)
LAUNCH_STAGES = (1, 2, 3)

STRATEGY_MIN_HOPS = "min_hops"
STRATEGY_MIN_DISTANCE = "min_distance"

STRATEGY_LABELS: dict[str, str] = {
    STRATEGY_MIN_DISTANCE: "Минимум суммарной длины (Dijkstra, по умолчанию)",
    STRATEGY_MIN_HOPS: "Минимум переходов (BFS, baseline)",
}


@dataclass(frozen=True)
class GroundSite:
    """Наземный пункт сценария."""

    id: str
    name: str
    role: str
    lat_deg: float
    lon_deg: float


def scenario_meta(scenario: dict[str, Any]) -> dict[str, Any]:
    """Возвращает meta сценария, допуская его отсутствие."""
    meta = scenario.get("meta")
    return meta if isinstance(meta, dict) else {}


def scenario_title(scenario: dict[str, Any]) -> str:
    return str(scenario_meta(scenario).get("title") or scenario_meta(scenario).get("id") or "Сценарий")


def clients_of(scenario: dict[str, Any]) -> list[str]:
    """ID клиентских пунктов в порядке файла."""
    return [g["id"] for g in scenario.get("ground_sites", []) if g.get("role") == "client"]


def gateways_of(scenario: dict[str, Any]) -> list[str]:
    """ID шлюзов в порядке файла."""
    return [g["id"] for g in scenario.get("ground_sites", []) if g.get("role") == "gateway"]


def satellite_ids(scenario: dict[str, Any]) -> list[str]:
    return [s["id"] for s in scenario["design"]["satellites"]]


def deep_copy(scenario: dict[str, Any]) -> dict[str, Any]:
    """Независимая копия сценария (JSON-совместимая)."""
    return copy.deepcopy(scenario)


def canonical_json(payload: Any) -> str:
    """Стабильное JSON-представление для ключей кэша и хэшей."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hhmmss(seconds: float) -> str:
    """Формат «чч:мм:сс» для отображения времени расчёта."""
    total = int(round(seconds))
    h, rem = divmod(max(total, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_pct(fraction: float, digits: int = 2) -> str:
    """Доля [0..1] -> строка процентов."""
    return f"{100.0 * fraction:.{digits}f}%"


def is_finite_number(value: Any) -> bool:
    """True для конечных чисел (bool не считается числом)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
