# Fyers Stock Scanner Dashboard

A real-time, read-only stock scanner dashboard that monitors indices and applies custom logic using Fyers API.

## Architecture & Tech Stack (as implemented in this repo)

### Services (Docker Compose)
- **Postgres (`db`)**: persistent storage (symbols/universes, daily prices, `live_state` snapshot).
- **Pipeline (`pipeline`)**: maintains **daily Parquet OHLCV** under `PIPELINE_DATA_DIR` (EOD sync + backfills).
- **Master scanner (`scanner`)**: connects to **Fyers WebSocket**, computes **weekly Mansfield mRS + RS rating**, writes to:
  - **Shared memory mmap**: `scanner_results.mmap` + `symbols_idx_map.json`
  - **Postgres**: upserts durable snapshot into `live_state`
- **Sidecar (`sidecar`)**: SHM *reader* that computes breakout-related fields (e.g. `brk_lvl`) and persists to Postgres.
- **Dashboard (`dashboard`)**: Reflex UI/backend that reads SHM + Postgres (thin client; does not recompute RS).

### Core technologies & libraries
- **Python**: main application + jobs (`backend/`, `utils/`, `scripts/`).
- **Fyers API v3**: live market data via WebSocket (`fyers_apiv3`).
- **PostgreSQL + psycopg2**: DB access (connection pool, batch upserts).
- **NumPy + mmap**: high-speed shared memory “live state bus” (`SIGNAL_DTYPE` in `utils/constants.py`).
- **Parquet**: historical daily OHLCV storage; read via **PyArrow** (`utils/pipeline_bridge.py`) and pandas in some scripts.
- **Reflex**: dashboard web UI (`frontend_reflex/`).
- **Docker / Docker Compose**: reproducible deployment and service wiring (`docker-compose.yml`).

## Features
- **Automated Login**: Headless login using TOTP (no manual daily login required).
- **Real-time Scanning**: Monitors live ticks via WebSocket across an entire index.
- **Modern UI**: Streamlit-based dashboard for easy visualization.
- **Dockerized**: Easy deployment with one command.

## Setup Instructions

1. **Clone & Configure**:
   - Copy `.env.example` to `.env`.
   - Fill in your Fyers credentials:
     - `FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`
     - `FYERS_USERNAME` (Your Fyers ID)
     - `FYERS_PIN` (4-digit PIN)
     - `FYERS_TOTP_KEY` (From Fyers Manage Account -> External 2FA)

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Access Dashboard**:
   Open `http://localhost:8501` in your browser.

## Logic Translation
To update the scanning logic, modify `backend/scanner.py` in the `apply_custom_logic` method. 
You can use functions from `utils/indicators.py` to match Pine Script patterns.
