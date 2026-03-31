#!/usr/bin/env python3
"""
Grid search the monthly RSI2 + weekly mRS event study **on your parquet data**.

Loads the universe **once**, then evaluates many parameter combos via
``evaluate_mrsi2_mrs_event_study`` from ``backtest_monthly_rsi2_mrs_forward_weeks``.

Default score (``--objective mps``): **median(return) − λ·std(return)** with λ=``--std-penalty``.
Rows with ``n_events < --min-events`` are dropped (avoid tiny‑n “winners”).

Parallelism: default ``--workers 0`` uses ``min(8, CPUs)`` with **fork** (Linux/WSL) so the
panel is not re-read from disk per combo. Use ``--workers 1`` for sequential + progress every 10 combos.

Example:
  python scripts/grid_search_mrsi2_mrs.py \\
    --universe \"Nifty 500\" --bench NSE:NIFTY500-INDEX \\
    --grid-mrsi2 3,5,7,10 --grid-mrs 0,0.5,1 --grid-fw 5,8,10 \\
    --grid-sl 5,7,10 --grid-tp 8,10,15,20 \\
    --exit-on daily --round-trip-pct 0.3 \\
    --min-events 40 --top 15
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402


def _load_bt_module():
    path = os.path.join(os.path.dirname(__file__), "backtest_monthly_rsi2_mrs_forward_weeks.py")
    spec = importlib.util.spec_from_file_location("mrsi2_bt", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _parse_floats(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def _parse_ints(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _score(arr: np.ndarray, objective: str, std_penalty: float) -> float:
    if objective == "mean":
        return float(arr.mean())
    if objective == "median":
        return float(np.median(arr))
    if objective == "win":
        return float((arr > 0).mean())
    if objective == "mps":
        return float(np.median(arr) - std_penalty * arr.std())
    raise ValueError(objective)


_G_PANEL = None
_G_EVAL = None
_G_STATIC: dict | None = None


def _pool_init(bundle: tuple) -> None:
    """Runs in child: load panel + backtest module once per worker."""
    global _G_PANEL, _G_EVAL, _G_STATIC
    panel, script_path, static = bundle
    _G_PANEL = panel
    _G_STATIC = static
    spec = importlib.util.spec_from_file_location("mrsi2_bt", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    _G_EVAL = mod.evaluate_mrsi2_mrs_event_study


def _pool_eval_combo(kw: dict) -> tuple[dict, np.ndarray]:
    assert _G_EVAL is not None and _G_PANEL is not None and _G_STATIC is not None
    arr, _, _ = _G_EVAL(panel=_G_PANEL, **_G_STATIC, **kw)
    return kw, arr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--bench", default="NSE:NIFTY500-INDEX")
    ap.add_argument("--rsi-period", type=int, default=2)
    ap.add_argument("--max-symbols", type=int, default=0)
    ap.add_argument("--grid-mrsi2", default="3,5,7,10", help="Comma-separated mrsi2-max values")
    ap.add_argument("--grid-mrs", default="0,0.5,1", help="Comma-separated min-weekly-mRS floors")
    ap.add_argument("--grid-fw", default="5,8,10", help="Comma-separated forward-weeks")
    ap.add_argument("--grid-sl", default="5,7,10", help="Comma-separated stop-loss %% (positive)")
    ap.add_argument("--grid-tp", default="8,10,15,20", help="Comma-separated take-profit %%")
    ap.add_argument(
        "--exit-on",
        choices=("weekly", "daily"),
        default="daily",
        help="Which bar stream for stop/target (default daily = stricter)",
    )
    ap.add_argument("--round-trip-pct", type=float, default=0.3)
    ap.add_argument("--signal-after", default=None)
    ap.add_argument("--signal-before", default=None)
    ap.add_argument("--min-events", type=int, default=40, help="Drop combos with fewer events")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument(
        "--objective",
        choices=("mps", "mean", "median", "win"),
        default="mps",
        help="mps = median − λ·std (see --std-penalty)",
    )
    ap.add_argument("--std-penalty", type=float, default=0.25)
    ap.add_argument("--export-csv", default=None, metavar="PATH")
    ap.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel processes (0 = min(8, CPUs); 1 = sequential with progress every 10)",
    )
    args = ap.parse_args()

    bt = _load_bt_module()
    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)

    g_mrsi2 = _parse_floats(args.grid_mrsi2)
    g_mrs = _parse_floats(args.grid_mrs)
    g_fw = _parse_ints(args.grid_fw)
    g_sl = _parse_floats(args.grid_sl)
    g_tp = _parse_floats(args.grid_tp)

    max_fw = max(g_fw)
    print(f"Loading panel (max forward_weeks={max_fw})…", flush=True)
    try:
        panel, _ = bt.build_mrsi2_mrs_panel(
            universe=args.universe,
            data_dir=data_dir,
            bench=args.bench,
            max_forward_weeks=max_fw,
            rsi_period=args.rsi_period,
            max_symbols=args.max_symbols,
        )
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
    print(f"Panel symbols: {len(panel)}", flush=True)

    static = {
        "rsi_period": args.rsi_period,
        "exit_on": args.exit_on,
        "round_trip_pct": args.round_trip_pct,
        "signal_after": args.signal_after,
        "signal_before": args.signal_before,
    }
    combos: list[dict] = [
        {
            "mrsi2_max": mrsi2,
            "min_weekly_mrs": mrs,
            "forward_weeks": fw,
            "stop_loss_pct": sl,
            "take_profit_pct": tp,
        }
        for mrsi2, mrs, fw, sl, tp in itertools.product(g_mrsi2, g_mrs, g_fw, g_sl, g_tp)
    ]
    total = len(combos)
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "backtest_monthly_rsi2_mrs_forward_weeks.py")
    )
    ncpu = mp.cpu_count() or 1
    nw = args.workers if args.workers > 0 else min(8, ncpu)
    nw = max(1, min(nw, total))

    rows: list[dict] = []
    t0 = time.perf_counter()

    def _append_row(kw: dict, arr: np.ndarray) -> None:
        n = len(arr)
        if n < args.min_events:
            return
        rows.append(
            {
                "score": _score(arr, args.objective, args.std_penalty),
                "n": n,
                "mean_pct": arr.mean() * 100,
                "median_pct": float(np.median(arr)) * 100,
                "std_pct": arr.std() * 100,
                "win_pct": (arr > 0).mean() * 100,
                "worst_pct": arr.min() * 100,
                "mrsi2_max": kw["mrsi2_max"],
                "min_weekly_mrs": kw["min_weekly_mrs"],
                "forward_weeks": kw["forward_weeks"],
                "stop_loss_pct": kw["stop_loss_pct"],
                "take_profit_pct": kw["take_profit_pct"],
            }
        )

    def _run_sequential(label: str) -> None:
        print(label, flush=True)
        for done, kw in enumerate(combos, start=1):
            if done == 1 or done % 10 == 0 or done == total:
                elapsed = time.perf_counter() - t0
                print(f"Grid {done}/{total}  ({elapsed:.1f}s elapsed)…", flush=True)
            arr, _, _ = bt.evaluate_mrsi2_mrs_event_study(panel=panel, **static, **kw)
            _append_row(kw, arr)

    if nw == 1:
        _run_sequential(
            f"Running {total} grid points sequentially (use --workers 4+ to parallelize)…"
        )
    else:
        print(
            f"Running {total} grid points on {nw} workers (fork; short pause while workers start)…",
            flush=True,
        )
        bundle = (panel, script_path, static)
        chunk = max(1, total // (nw * 8))
        try:
            try:
                ctx = mp.get_context("fork")
            except ValueError:
                ctx = mp.get_context()
            with ctx.Pool(nw, initializer=_pool_init, initargs=(bundle,)) as pool:
                for done, (kw, arr) in enumerate(
                    pool.imap_unordered(_pool_eval_combo, combos, chunksize=chunk),
                    start=1,
                ):
                    if done == 1 or done % 25 == 0 or done == total:
                        elapsed = time.perf_counter() - t0
                        print(f"Grid {done}/{total}  ({elapsed:.1f}s elapsed)…", flush=True)
                    _append_row(kw, arr)
        except (PermissionError, OSError) as e:
            _run_sequential(
                f"Parallel pool unavailable on this machine ({e!s}); falling back to sequential…"
            )

    print(f"Grid finished in {time.perf_counter() - t0:.1f}s", flush=True)

    if not rows:
        print(f"No combo had n_events >= {args.min_events}. Lower --min-events or widen grids.")
        sys.exit(1)

    df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    top = df.head(max(1, args.top))
    print(f"\nObjective: {args.objective}" + (f" (std_penalty={args.std_penalty})" if args.objective == "mps" else ""))
    print(f"exit_on={args.exit_on}  round_trip_pct={args.round_trip_pct}  min_events={args.min_events}")
    print(f"Combos kept: {len(df)} / {total} grid points\n")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(top.to_string(index=True))

    if args.export_csv:
        out = os.path.abspath(args.export_csv)
        df.to_csv(out, index=False)
        print(f"\nWrote full ranked table ({len(df)} rows) to {out}")


if __name__ == "__main__":
    main()
