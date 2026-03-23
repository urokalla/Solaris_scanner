# PROD Verification SOP (Quick)

Small runbook for daily production-style validation.

## Scope

Validates:
- services up
- scanner shared-memory to DB sync
- websocket live subscription health
- EOD job status

## 1) One-command full verification

From repo root:

```bash
python3 stock_scanner_sovereign/scripts/prod_verify.py
```

Expected:
- `status=OK all checks passed`

## 2) Individual checks

### A. WS health (scanner)

```bash
python3 stock_scanner_sovereign/scripts/check_ws_health.py --since 20m
```

Read:
- `tokens=X/2442` -> higher is better
- `unresolved=0` preferred
- `last_tick_age` low during market hours
- `ssl_eof_errors` should not keep climbing for long

### B. SHM <-> DB sync

```bash
docker compose exec -e DB_HOST=db dashboard bash -lc \
  'cd /app/stock_scanner_sovereign && python3 validate_shm_db_sync.py'
```

Read:
- SHM map count > 0
- `live_state` row count aligns with symbol universe
- sample SHM LTP ~= DB `last_price`

### C. EOD result

```bash
python3 stock_scanner_sovereign/scripts/check_eod_status.py --since 24h
```

Read:
- latest `EOD_SYNC_RESULT`
- healthy target: `fail=0`

## 3) Suggested cadence

- Pre-open: full verification once
- During market: WS health every 30-60 min
- Post-close: EOD status once after scheduler window

## 4) Incident triggers

- `tokens` drops hard and does not recover
- `unresolved` stays high over multiple checks
- `last_tick_age` grows continuously during market
- `EOD fail > 0`

If triggered: restart affected service, refresh Fyers token, rerun verification.

