# RS_PROJECT — run book (short)

Use this to bring the stack up **predictably**. Deep troubleshooting lives in `stock_scanner_sovereign/docs/OPERATIONS_SOP.md`.

**Repo root:** `RS_PROJECT` (where `docker-compose.yml` lives).

---

## 1. Preconditions (every machine)

| Check | Why |
|--------|-----|
| **Docker Desktop** running | Compose needs the engine. |
| **`stock_scanner_sovereign/.env`** present | Fyers + `DB_USER` / `DB_PASSWORD` / `DB_NAME` / `DB_HOST` (use `localhost` on host, `db` in Compose). Defaults in Compose for Postgres: `fyers_user` / `fyers_pass` / `fyers_db` — **`.env` must match** what the `db` service uses. |
| **`stock_scanner_sovereign/access_token.txt`** non‑empty | Pipeline/scanner history + live feed fail without a valid token. **Do not** mount this file twice in Compose (stale empty overlay). |
| **Disk** | `postgres_data/` (DB) and `fyers_data_pipeline/data/historical/` (Parquet) are **not** in Git; copy them when moving machines if you want the same data. |

---

## 2. First time on a host (empty DB)

From repo root:

```bash
docker compose up -d --build db
# wait ~5–10s for Postgres
docker compose up -d --build pipeline
docker compose exec pipeline python scripts/init_db.py
docker compose exec pipeline python initialize_db.py
```

Then start the rest (scanner, sidecar, dashboard, crons) as in §3.

If `initialize_db.py` fails (network), at least `init_db.py` creates tables; re-run seed when Fyers is reachable.

---

## 3. Normal start (DB already exists)

```bash
cd /path/to/RS_PROJECT
docker compose up -d --build
docker compose ps
```

**UI:** `http://localhost:3000` (Reflex) and backend `http://localhost:8000`.

**Optional — save CPU when not backfilling/EOD:**

```bash
docker compose stop pipeline
```

Scanner + dashboard can still run if DB + Parquet already exist; pipeline is needed for scheduled EOD/backfill and token-friendly history jobs.

---

## 4. Prove it is healthy (2 minutes)

```bash
docker compose ps
```

All non-stopped services you care about should be **running**.

```bash
docker compose logs pipeline --tail 80
docker compose logs scanner --tail 40
```

Look for Fyers connected / no repeated DB `UndefinedColumn` / auth errors.

**DB column guard (older volumes):** first run of `backfill.py` or `update_eod.py` runs `ALTER TABLE … IF NOT EXISTS last_historical_sync` automatically.

---

## 5. Manual jobs (when you choose to run them)

| Goal | Command |
|------|---------|
| **Backfill** (heavy) | `docker compose exec pipeline python scripts/backfill.py` |
| **EOD once** | `docker compose exec pipeline python scripts/eod_sync.py` |
| **Schema only** | `docker compose exec pipeline python scripts/init_db.py` |

Useful env (host or Compose): `BACKFILL_YEARS` (default 5), `BACKFILL_FORCE=1` to ignore `last_historical_sync` day filter for **which symbols** are queued, `EOD_UNIVERSE_ID` (default `ALL_NSE` in Compose), `EOD_NIFTY500_ONLY=1` for Nifty 500 universe only.

---

## 6. After `git pull` on any OS

```bash
docker compose up -d --build
```

Code updates apply; **Postgres data** and **Parquet** stay on disk unless you removed volumes/folders.

---

## 7. Quick fixes

| Symptom | Action |
|---------|--------|
| `access_token` / auth errors | Refresh token into `access_token.txt`; restart `pipeline` + `scanner`. |
| `column … does not exist` on `symbols` | Run `init_db` or any `backfill`/`update_eod` once (auto DDL). |
| Empty grid / no SHM | Ensure **`scanner`** is up (`SHM_MASTER=true`). |
| Compose errors after edits | `docker compose config -q` |

---

## 8. Stop everything

```bash
docker compose down
```

**Data kept:** `./postgres_data`, `./fyers_data_pipeline/data/historical`.

**Data removed:** only if you use `docker compose down -v` (avoid unless you mean it).
