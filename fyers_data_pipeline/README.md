# Fyers Financial Data Pipeline

A robust, scalable data ingestion engine for Indian Equity markets (NSE) using Fyers API.

## Features
- **Historical Backfilling**: 5-year historical data for NSE equities and indices.
- **Incremental Updates**: EOD "Append" logic to keep datasets up-to-date without full re-downloads.
- **PostgreSQL Metadata**: Persistent storage for symbol metadata and ingestion tracking.
- **Parquet Storage**: High-performance historical data storage using Parquet.
- **WebSocket Live Feed**: Real-time ticker updates.

## Setup Instructions

1. **Environment**:
   - Create a `.env` file in `config/` with your Fyers API credentials.
   - Install dependencies: `pip install -r requirements.txt`

2. **Database**:
   - Initialize the database schema: `python scripts/init_db.py`

3. **Data Ingestion**:
   - Run backfill: `python scripts/backfill.py`
   - Schedule EOD updates: `python scripts/eod_sync.py` (via cron) or use the automatic scheduler `python main.py`

4. **Live Feed**:
   - Start WebSocket: `python src/websocket.py`
