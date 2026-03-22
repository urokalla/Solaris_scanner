# Quant calibration: bars, RS/mRS, and breakout windows

This document freezes **definitions** used in the breakout path so RS and signal logic stay comparable across sessions, backtests, and the live dashboard.

## Intraday price buffer (breakout tape)

Rows stored in `RingBuffer` / ordered views are **6 × float64** per bar:

| Col | Name        | Meaning |
|-----|-------------|---------|
| 0   | pulse / ts  | Heartbeat from SHM during live scans; may be epoch seconds when replaying historical pulls. |
| 1   | open        | Session bar open. |
| 2   | high        | Session bar high (**used for pivot** prior to the current bar). |
| 3   | low         | Session bar low. |
| 4   | close       | Session bar close (**`curr` in signal logic**). |
| 5   | volume      | Bar volume. |

**Pivot rule:** the breakout engine compares the **current** close (column 4) to `max(high)` over the **previous** `pivot_high_window` bars (column 2, excluding the current bar). That window defaults from config; see below.

**Minimum history:** until the buffer has at least `min_intraday_bars_for_breakout` rows, `generate_breakout_signal` does not run full price rules; status falls back to **STAGE 2** / **STAGE 4** from **mRS sign only** (see SHM fields).

## Main grid STATUS (weekly mRS only)

Owned by the **master** (`backend/scanner.py`); the dashboard **reads SHM** (slave does not recompute).

- **`NOT TRENDING`**: weekly mRS **≤ 0** (drops out of the long side).
- **`TRENDING`**: weekly mRS **&gt; 0** and **prior EOD** `mrs_prev_day` **&gt; 0** (already strong vs benchmark last session — **not** a fresh zero-cross story).
- **`BUY`**: **session-latched** after a **valid long** signal: (a) **intraday/batch cross** from **≤ 0** to **&gt; 0**, or (b) **prior EOD ≤ 0** and current **&gt; 0** without a same-bar false “already trending” read. Stays **`BUY`** until weekly mRS goes **≤ 0** or a **new IST calendar day** clears the latch.

**`Prev W_mRS` column**: `live_state.mrs_prev_day`, filled by a **once-per-day EOD snapshot** (~after 15:30 IST) copying **`mrs` → `mrs_prev_day`** so the next session can compare “yesterday’s” weekly mRS. Until the first EOD run, the column shows **—**.

This is **not** the breakout page’s STAGE 2 / pivot labels.

## RS, mRS, and benchmark (SHM)

Weekly / ranking inputs are **not** recomputed inside the breakout price function. They come from **shared memory** (`SIGNAL_DTYPE` in `utils/constants.py`):

- **`mrs`**, **`mrs_prev`**: Mansfield-style relative strength vs the **universe benchmark** pipeline.
- **`rs_rating`**: percentile-style RS score (0–100).

**Dashboard benchmark** (RS header / sidebar) uses **`DASHBOARD_BENCHMARK_MAP`**: only **Nifty 50** → `NSE:NIFTY50-INDEX` and **Nifty 500** → `NSE:NIFTY500-INDEX`. Reconcile dashboard rows to external data with **stock vs that selected index** on aligned **weekly** bars. The full **`BENCHMARK_MAP`** covers other indices for SHM / breakout internals; do not treat every entry as a user-selectable dashboard benchmark.

For a full walk-through of the Weinstein-style ratio and 52-week mean used in offline proofs, see `scripts/proof_local_mrs.py` (parquet daily → weekly aggregation).

## MRS signal line (streaming)

In `backend/breakout_logic.py`, the **signal line** is the simple moving average of the last **`mrs_signal_period`** live **mrs** samples (deque per symbol). It feeds `mrs_signal` inside `rs_rating_info` for crossover rules in `utils/signals_math.py`.

## Config surface (env → settings → runtime)

Defaults live in `config/settings.py` and can be overridden with environment variables:

| Env | Setting attribute | Role |
|-----|-------------------|------|
| `BREAKOUT_MRS_SIGNAL_PERIOD` | `BREAKOUT_MRS_SIGNAL_PERIOD` | Length of the MRS SMA (“signal line”). |
| `BREAKOUT_PIVOT_HIGH_WINDOW` | `BREAKOUT_PIVOT_HIGH_WINDOW` | Lookback (bars) for prior highs vs current close. |
| `BREAKOUT_MIN_INTRADAY_BARS` | `BREAKOUT_MIN_INTRADAY_BARS` | Minimum tape length before full breakout rules apply. |

`utils/quant_breakout_config.py` merges these with `BreakoutScanner.update_params()` so keys `mrs_signal_period`, `pivot_high_window`, and `min_intraday_bars_for_breakout` can be set per process.

## Golden tests

`test_breakout_quant_golden.py` holds **fixed** OHLCV-style arrays and SHM-like `rs_rating_info` dicts to lock behavior when changing windows or formulas.
