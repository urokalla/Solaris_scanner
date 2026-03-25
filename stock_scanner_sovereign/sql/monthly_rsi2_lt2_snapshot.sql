-- Run once in DBeaver if you prefer (optional). Or: first run of populate script creates the table.

CREATE TABLE IF NOT EXISTS monthly_rsi2_lt2_snapshot (
    snapshot_date   DATE NOT NULL,
    universe        TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    month_bucket    DATE,
    rsi2            DOUBLE PRECISION,
    last_daily      DATE,
    last_close      DOUBLE PRECISION,
    PRIMARY KEY (snapshot_date, universe, symbol)
);

CREATE INDEX IF NOT EXISTS idx_monthly_rsi2_lt2_snap_date
    ON monthly_rsi2_lt2_snapshot (snapshot_date);
