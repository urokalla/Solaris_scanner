# Data layers (how Solaris is wired)

This matches the in-code comments (“Layer 1–4”) and how **`live_state`** fits in.

## Single source of truth (calculations)

**Rule:** Every number shown in the app must be **produced in exactly one place** (one engine + shared helpers). **Reflex, SQL merges, and validation scripts** may **read** and **format**; they must **not** re-implement market math “to fill gaps.” If a value is missing, fix the **producer** or **persistence**, not the UI.

| Concern | Canonical implementation | Consumed via |
|--------|---------------------------|--------------|
| Weekly / daily **mRS**, **RS rating** (live grid) | `backend/scanner_math.py` — `RSMathEngine.calculate_rs()` | MasterScanner → SHM → `get_ui_view` / `live_state` flush |
| **PROFILE** (ELITE / LEADER / …) | `utils/scanner_analysis.py` — `compute_trading_profile(rs_rating, mrs, mrs_daily)` | MasterScanner writes SHM `profile` only; **no** extra benchmark or universe math |
| **Breakout** status, **pivot (`brk_lvl`)**, MRS signal line, tape crossover | `backend/breakout_logic.py` → `utils/breakout_math.py` + `utils/signals_math.py` + `utils/quant_breakout_config.py` | `BreakoutScanner.results` → `upsert_brk_lvls` → `live_state.brk_lvl`; sidecar reads same memory or DB hydrate |
| Pivot / MRS **window parameters** | `config/settings.py` (env) merged by `utils/quant_breakout_config.py` | Breakout path only (do not duplicate defaults in the UI except `update_params` overrides) |
| **Historical OHLCV** (inputs) | Postgres `prices` and/or Parquet under `PIPELINE_DATA_DIR` via `PipelineBridge` / `DatabaseManager.get_historical_data` | Seed RingBuffers and backfills — not a second RS engine |

**Non-canonical / legacy:** `utils/rs_math.py` (`compute_rs_logic`) uses a **different** RS formulation than `RSMathEngine`. Do not mix it with live SHM numbers without an explicit product decision and tests. Prefer one engine for all “official” dashboard values.

**Storage vs logic:** `live_state` and SHM hold **snapshots** written by the processes above. They are **not** alternate calculators.

### SHM for speed, ticks computed live

- **`scanner_results.mmap` (SHM)** exists so the **UI and slaves read the latest numbers in O(1)** without a DB round-trip per symbol. It is a **transport layer** for the already-computed snapshot, not a second formula.
- **Each live tick** from the master websocket runs **`MasterScanner.on_tick`** → **`RSMathEngine.update_tick`** (pushes the new price into the last bar of the price matrices) → **`get_instant_mrs`** (weekly mRS from current price vs cached SMAs) → writes **LTP / mRS / heartbeat** (and related flags) into **SHM**. That is **on-the-fly** math for the streaming path.
- **Full RS pass** (`RSMathEngine.calculate_rs()` — weekly + daily mRS, **rs_rating** ranks, etc.) runs on the master’s **periodic flush** (e.g. ~60s), then mirrors the full result set into SHM and eventually **`live_state`**. So: **ticks = continuous micro-updates; timer = full coherent RS + ratings.**

### PROFILE (SHM `profile` field)

**PROFILE** is a **display-only** label derived **only** from **`rs_rating`**, **weekly mRS**, and **daily mRS** (`mrs_daily`) already produced by **`RSMathEngine`**. It does **not** change RS formulas, benchmark selection (`DASHBOARD_BENCHMARK_MAP` / `BENCHMARK_MAP`), or universe membership. The master sets **`profile`** on **baseline boot**, on each **~60s** RS flush (all fields aligned), and on **`on_tick`** using the **live** instant weekly mRS with **`rs_rating` / `mrs_daily` from the row** (so **`rs_rating` can lag** the last full pass until the next flush—acceptable for a bucket label).

## Layer 1 — Identity (`symbols`, `universes`, `universe_members`)

Postgres holds **which tickers exist** and **universe membership**. The **master scanner** builds its trading list from here (plus benchmark indices).

**Dashboard benchmark + membership validation (canonical):** RS header and the **“VALIDATION / BENCHMARK”** sidebar use **`DASHBOARD_BENCHMARK_MAP`** in `utils/constants.py` — **only** **Nifty 50** → `NSE:NIFTY50-INDEX` and **Nifty 500** → `NSE:NIFTY500-INDEX`. Automated checks that **`universe_members` matches canonical CSV** are scoped to those two universes only (`utils/universe_validation.py`, `scripts/validate_universe_members.py`). The broader **`BENCHMARK_MAP`** remains for SHM bench slots, master pulse, and breakout bench buffers — it is **not** an extra dashboard benchmark picker.

**Universe list** (e.g. Midcap, Bank Nifty) still comes from `UNIVERSE_OPTIONS` / `get_symbols_by_universe`; only **benchmark selection** and **Layer-1 CSV↔DB diff** are restricted to the two NIFTY indices above.

## Layer 2 — Historical OHLCV (`prices` + Parquet)

**Daily bars** live in **`prices`** and/or **pipeline Parquet** under `PIPELINE_DATA_DIR`. The breakout engine’s **RingBuffer** is seeded from the same sources (`PipelineBridge` / `DatabaseManager.get_historical_data`).

## Layer 3 — Live snapshot (SHM mmap + `live_state`)

Two representations of the **same logical snapshot**:

| Mechanism | Role |
|-----------|------|
| **`scanner_results.mmap` + `symbols_idx_map.json`** | O(1) shared memory: **LTP, mRS, rs_rating, status, profile**, heartbeats. **Master** (`sovereign_scanner`, `SHM_MASTER=true`) writes; **slaves** (dashboard, sidecar) attach read/write selected fields. **`profile`** is a derived bucket (see above), not a second RS engine. |
| **`live_state` (Postgres)** | Durable **last known** **last_price, mrs, rs_rating, status** — flushed periodically by **`MasterScanner.persist_to_postgres()`**. |

**Breakout pivot level** is **`brk_lvl`** on **`live_state`**: computed in the **BreakoutScanner** path (dashboard and/or `sidecar`), then **upserted** on a timer so values survive restarts and match the “DB as audit trail” expectation. The master’s upsert **does not** overwrite `brk_lvl` when it syncs its own columns.

## Layer 4 — Sidecar strategy UI

The Reflex **breakout** page reads **`BreakoutScanner.results`** (fed from SHM + tape math). **`brk_lvl`** is merged from **`live_state`** when memory has not filled it yet, so the grid stays consistent with Postgres after deploys.

The **main RS grid** does not store pivot in SHM; it shows **`BRK_LVL`** by merging **`live_state.brk_lvl`** into each row in **`MasterScanner.get_ui_view()`** (same DB column the sidecar writes).

## Why `brk_lvl` is not on `SIGNAL_DTYPE`

The mmap row is a **fixed binary layout**; adding a field changes **every** consumer’s layout. Pivot level is **derived** from tape + config and is stored in **`live_state`** instead of expanding SHM.

---

## Loopholes (why BRK_LVL can stay “—” everywhere)

1. **Two writers, one column**  
   **`brk_lvl`** is **not** produced by the master websocket loop. It is computed only inside **`BreakoutScanner`** (Docker **`sovereign_sidecar`** and/or Reflex **`/breakout`** when that engine runs). **`live_state.brk_lvl`** is updated on a **timer** from that engine. If **both** are off, the column stays **NULL** for all symbols.

2. **Main grid never computes pivot**  
   The **RS Scanner** table reads **LTP/mRS/…** from **SHM** in **`get_ui_view`**, then **merges `brk_lvl` from Postgres only**. It does **not** run tape math. So **no sidecar + no dashboard breakout process** ⇒ **no DB values** ⇒ **BRK_LVL shows "—"** even when prices look fine.

3. **Schema must exist before `SELECT brk_lvl`**  
   If **`live_state.brk_lvl`** was never added (e.g. only the main page was used and older code never ran `ensure_live_state_brk_column`), the SELECT failed silently and the UI showed **"—"**. **`MasterScanner`** and **`get_brk_lvl_map`** now **ensure** the column on boot / first read.

4. **Tape length**  
   Pivot needs at least **2 rows** in the RingBuffer (adaptive window). If historical sync failed and almost no live bars arrived yet, in-memory **`brk_lvl`** can still be unset briefly.

5. **Operational checklist**  
   - Run **`sovereign_scanner`** (master SHM + **`live_state`** price/mRS rows).  
   - Run **`sovereign_sidecar`** *or* open **Sidecar** in the UI so **`BreakoutScanner`** fills **`brk_lvl`**.  
   - **Docker:** mount **`fyers_data_pipeline/data/historical`** into the sidecar at **`PIPELINE_DATA_DIR`** (see `docker-compose.yml` `sidecar:` volumes) so **`PipelineBridge`** can seed ring buffers from Parquet; otherwise pivots may never compute if DB daily bars are sparse.  
   - Confirm: `SELECT COUNT(*) FROM live_state WHERE brk_lvl IS NOT NULL;`  
   - Run **`python3 stock_scanner_sovereign/validate_shm_db_sync.py`** on the host/container.
