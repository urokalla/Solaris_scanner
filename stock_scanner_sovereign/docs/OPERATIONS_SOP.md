# Solaris RS / Scanner — Operations SOP (junior)

How the stack works, what to check, and what to do when something breaks. Commands assume repo root `RS_PROJECT` and Docker Compose unless noted.

---

## 1. What this system does

- **Master scanner** (`sovereign_scanner`): connects to Fyers, ingests **live ticks**, computes **weekly mRS**, **RS rating**, **grid STATUS** (BUY / TRENDING / NOT TRENDING), writes to **shared memory (SHM)** and **Postgres `live_state`**.
- **Pipeline** (`fyers_pipeline`): keeps **daily Parquet** (+ DB metadata) updated via **EOD append** and optional **deep backfill** (scheduled).
- **Sidecar** (`sovereign_sidecar`): reads SHM, computes **breakout tape** + **`brk_lvl`** → DB; optional **Udai Pine** daily logic.
- **Dashboard** (`sovereign_dashboard`): Reflex UI on **http://localhost:3000** (and backend **8000**). Reads SHM + DB like a slave.

**Rule:** RS math runs in **one place** (master + `RSMathEngine`). UI does not recompute mRS.

---

## 2. Four data layers (sanity model)

| Layer | Where | What |
|-------|--------|------|
| **1** | Postgres `symbols`, `universes`, `universe_members` | Which tickers exist and universe membership. |
| **2** | Postgres `prices` + Parquet under `PIPELINE_DATA_DIR` | Historical daily OHLCV for seeds / audits. |
| **3** | `scanner_results.mmap` + `symbols_idx_map.json` (in `stock_scanner_sovereign/`) + `live_state` | Live **LTP, mRS, status, heartbeat**; DB is durable snapshot. |
| **4** | Reflex UI + sidecar `BreakoutScanner.results` | Display + breakout / Udai; **`brk_lvl`** written to DB from sidecar/dashboard process. |

More detail: `architecture_data_layers.md`.

---

## 3. Docker services (what must be running)

| Service | Container | Role |
|---------|-----------|------|
| `db` | `fyers_postgres` | Postgres. |
| `pipeline` | `fyers_pipeline` | Scheduler: EOD sync + nightly backfill window; Fyers auth for history. |
| `scanner` | `sovereign_scanner` | **SHM master** — live ticks mandatory for live grid. |
| `sidecar` | `sovereign_sidecar` | Breakout + `brk_lvl` + optional Udai. |
| `dashboard` | `sovereign_dashboard` | UI. |

**Minimum for live trading UI:** `db` + `scanner` (often + `dashboard`). **Parquet freshness:** `pipeline`. **Pivot column filled:** `sidecar` *or* breakout engine inside dashboard process.

```bash
docker compose ps
```

All critical rows should show **Up** (or **running**).

---

## 4. Environment you must have

- **`stock_scanner_sovereign/.env`**: Fyers API fields (`FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`, `FYERS_USERNAME`, `FYERS_PIN`, `FYERS_TOTP_KEY`, etc.). Loaded by Compose for pipeline, scanner, sidecar, dashboard.
- **`stock_scanner_sovereign/access_token.txt`**: Short-lived Fyers access token. **If expired:** live ticks and API history calls fail until refreshed (auto-auth scripts or manual login flow — see repo scripts under `fyers_data_pipeline/scripts/`).

---

## 5. What runs automatically (pipeline container)

From `fyers_data_pipeline/main.py` (inside `pipeline`):

| Job | When (IST) | Script | Purpose |
|-----|------------|--------|---------|
| **EOD sync** | Mon–Fri, after `EOD_SYNC_IST_HOUR:MINUTE` (default **15:45**) | `scripts/eod_sync.py` | Append **today’s** daily bar per symbol to Parquet (+ DB bookkeeping). Once **per calendar day** success → flag file `.eod_last_ok_date` under `PIPELINE_DATA_DIR`. |
| **Deep backfill** | Narrow window default **01:00** IST (`BACKFILL_IST_HOUR` / `BACKFILL_IST_MINUTE`) | `scripts/backfill.py` | Chunked history for symbols DB marks as needing sync. |

**If EOD didn’t run:** check `pipeline` logs, Fyers token, and that IST time passed after market close.

---

## 6. Checks that prove the system is healthy

### 6.1 Processes

```bash
docker compose ps
```

### 6.2 SHM vs DB (Layer 3)

Run **inside** a container that has the same mounts as the app (e.g. `dashboard`), with DB reachable:

```bash
docker compose exec -e DB_HOST=db dashboard bash -lc \
  'cd /app/stock_scanner_sovereign && python3 validate_shm_db_sync.py'
```

**Good:** `scanner_results.mmap` exists, index map **> 0** symbols, sample **SHM LTP** matches **DB `last_price`**.  
**Bad:** empty index map → **master scanner not writing** (not running, wrong `SHM_MASTER`, or crash).

**Note:** Host `DB_HOST=localhost` often fails unless port 5432 is published; use `DB_HOST=db` inside Compose network.

### 6.3 Live market (NSE hours)

- Main grid: **LTP** and **prices moving**; stale heartbeat = no ticks or wrong symbol map.

### 6.4 Parquet / Udai

- Sidecar/dashboard need **`PIPELINE_DATA_DIR`** pointing at the **same** host directory as pipeline’s Parquet (see `docker-compose.yml` mounts). Wrong path → missing files → empty/strange **BRK_LVL** / Udai.

---

## 7. Troubleshooting (symptom → action)

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| **No live prices / frozen LTP** | Token expired; scanner down; websocket error | `docker compose logs scanner --tail 200`; refresh **`access_token.txt`**; restart `scanner`. |
| **`validate_shm_db_sync` → 0 symbols in map** | Master not running or SHM not created | Start `sovereign_scanner`; check `stock_scanner_sovereign/scanner_results.mmap` and `symbols_idx_map.json` exist after boot. |
| **Postgres connection refused from host** | DB only on Docker network | Use `docker compose exec …` with `DB_HOST=db`, or expose port in compose (dev only). |
| **BRK_LVL always "—"** | No breakout writer | Run **`sidecar`** or open dashboard page that runs `BreakoutScanner`; ensure tape/Parquet seed possible (`PIPELINE_DATA_DIR`). See `architecture_data_layers.md` § loopholes. |
| **Udai column OFF / empty** | Feature flag; Parquet path | Set `SIDECAR_UDAI_PINE=1`; set `PIPELINE_DATA_DIR` for dashboard to mounted historical dir (see compose). |
| **Universe wrong / empty** | DB not seeded | Run `python scripts/seed_universes.py` (from app context; often `docker compose exec …`). |
| **Missing daily Parquet for many symbols** | Never backfilled / API errors | See § 8 manual backfill. |
| **EOD didn’t append today** | Scheduler missed window; token; script error | Read `fyers_pipeline` logs; run **manual EOD** (§ 8); verify `.eod_last_ok_date` in `PIPELINE_DATA_DIR`. |

---

## 8. Manual jobs (when auto schedule failed)

Run from host with correct `DB_HOST` / paths, or **`docker compose exec -w /app pipeline`** (pipeline has Fyers + data dir).

**EOD (append today’s bar):**

```bash
docker compose exec -w /app pipeline python scripts/eod_sync.py
```

**Full DB-driven backfill (heavy):**

```bash
docker compose exec -w /app pipeline python scripts/backfill.py
```

**Only missing/empty Parquet files (sovereign script):**

```bash
docker compose exec -w /app/stock_scanner_sovereign pipeline \
  python scripts/backfill_missing_parquet.py --universe "Nifty 50" --dry-run
# remove --dry-run and optionally --limit N to execute
```

Use **`--data-dir /app/data/historical`** inside pipeline container if paths differ.

---

## 9. Logs (where to look)

```bash
docker compose logs scanner --tail 300
docker compose logs pipeline --tail 300
docker compose logs sidecar --tail 200
docker compose logs dashboard --tail 200
```

Pipeline also writes **`pipeline.log`** / script logs under the pipeline working tree (see `fyers_data_pipeline` logging setup).

---

## 10. Restart after config / code change

```bash
docker compose up -d --build
# or restart one service:
docker compose restart scanner
```

---

## 11. One-page checklist (before market)

1. `docker compose ps` — **scanner**, **db**, **pipeline** (if you rely on EOD), **dashboard** as needed.  
2. `access_token.txt` not expired (if unsure, watch scanner logs at open).  
3. `validate_shm_db_sync.py` — mmap exists, symbol count > 0, LTP matches DB.  
4. UI: benchmark + universe selected; prices move after open.

---

## 12. Further reading (in-repo)

| Doc | Topic |
|-----|--------|
| `architecture_data_layers.md` | Layers, SHM, `brk_lvl`, loopholes |
| `quant_rs_accuracy.md` | Breakout tape, mRS grid STATUS, windows |
| `validate_shm_db_sync.py` docstring | DB/SHM check commands |

---

*Keep this doc short: add new **symptom → fix** rows as you repeat incidents.*
