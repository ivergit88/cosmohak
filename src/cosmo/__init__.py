"""cosmo — расчётное ядро сервиса «Проектирование устойчивой спутниковой группировки».

Модули не зависят от UI: Streamlit-приложение (app.py) лишь вызывает
функции этого пакета. Геометрия берётся из официального расчётного
модуля (vendor/geometry.py) через geometry_adapter.
"""

__version__ = "1.0.0"

from .validation import ScenarioValidationError, validate_scenario  # noqa: F401
from .geometry_adapter import snapshot, time_grid  # noqa: F401
from .simulation import simulate_scenario, SimulationResult  # noqa: F401
