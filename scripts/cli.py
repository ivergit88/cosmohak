"""CLI для проверки сценария без интерфейса: валидация, расчёт, экспорт.

Примеры:
    python scripts/cli.py data/01_full_constellation.json
    python scripts/cli.py data/03_satellite_outages.json --export result_03.json
    python scripts/cli.py data/04_link_range.json --strategy min_distance
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cosmo.export import build_result, dumps_result, metrics_csv, validate_result_structure  # noqa: E402
from cosmo.geometry_adapter import load_file  # noqa: E402
from cosmo.models import STRATEGY_LABELS, fmt_pct, hhmmss  # noqa: E402
from cosmo.simulation import simulate_scenario  # noqa: E402
from cosmo.validation import ScenarioValidationError, ensure_valid  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Расчёт доступности группировки (консольный режим)")
    parser.add_argument("scenario", help="путь к JSON-сценарию cosmo-A-1.0")
    parser.add_argument("--strategy", default="min_distance", choices=["min_hops", "min_distance"])
    parser.add_argument("--export", default=None, help="файл для сохранения result JSON")
    parser.add_argument("--csv", default=None, help="файл для сохранения metrics CSV")
    args = parser.parse_args()

    try:
        scenario = load_file(args.scenario)
        ensure_valid(scenario)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Ошибка чтения файла: {exc}")
        return 2
    except ScenarioValidationError as exc:
        print(str(exc))
        return 2

    t0 = time.time()
    sim = simulate_scenario(scenario, strategy=args.strategy, with_backups=False)
    dt = time.time() - t0
    g = sim.global_metrics
    print(f"Сценарий: {scenario.get('meta', {}).get('title', args.scenario)}")
    print(f"Стратегия: {STRATEGY_LABELS[args.strategy]}")
    print(f"Сетка: {len(sim.ticks)} отсчётов по {sim.step_s()} с (0 … {hhmmss(sim.ticks[-1])}), расчёт {dt:.2f} с")
    for cid in sim.clients:
        m = sim.metrics[cid]
        print(
            f"  {cid}: видимость {fmt_pct(m.visibility_fraction)}, доступность {fmt_pct(m.availability_fraction)}, "
            f"макс. перерыв {m.max_outage_s} с, переходов в среднем "
            f"{'—' if m.mean_hops is None else f'{m.mean_hops:.2f}'}, цель {'достигнута' if m.target_met else 'НЕ достигнута'}"
        )
    print(f"MIN доступность: {fmt_pct(g.min_availability)}; MEAN: {fmt_pct(g.mean_availability)}; "
          f"худший перерыв: {g.worst_max_outage_s} с; цель: {g.target_met_clients}/{g.total_clients}")

    result = build_result(sim, include_summary=True)
    problems = validate_result_structure(result)
    if problems:
        print("ПРОБЛЕМЫ РЕЗУЛЬТАТА:", problems)
        return 1
    print(f"routes: {len(result['routes'])} записей (структура корректна)")
    if args.export:
        Path(args.export).write_text(dumps_result(result), encoding="utf-8")
        print(f"Результат сохранён: {args.export}")
    if args.csv:
        Path(args.csv).write_text(metrics_csv(sim), encoding="utf-8-sig")
        print(f"Метрики сохранены: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
