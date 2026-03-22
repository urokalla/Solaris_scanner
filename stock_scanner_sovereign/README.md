# Fyers Stock Scanner Dashboard

A real-time, read-only stock scanner dashboard that monitors indices and applies custom logic using Fyers API.

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
