# Production Dockerfile for Reflex Dashboard
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Bun (latest)
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.local/share/reflex/bun/bin:$PATH"
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

WORKDIR /app

# Copy requirements for both the scanner engine and reflex
COPY stock_scanner_sovereign/requirements.txt ./scanner_requirements.txt
COPY stock_scanner_sovereign/frontend_reflex/requirements.txt ./reflex_requirements.txt

RUN pip install --no-cache-dir -r ./scanner_requirements.txt
RUN pip install --no-cache-dir -r ./reflex_requirements.txt

# Copy the entire scanner project
COPY stock_scanner_sovereign /app/stock_scanner_sovereign

# Move to the reflex app directory
WORKDIR /app/stock_scanner_sovereign/frontend_reflex

# Bypass certificate issues for npm/bun if in a restrictive network
ENV NODE_TLS_REJECT_UNAUTHORIZED=0
ENV BUN_CONFIG_STRICT_SSL=false
RUN bun install || true
RUN reflex init

# Expose ports
EXPOSE 3000 8000

# Default command (Dev Mode for Hot-Reloading)
CMD ["reflex", "run", "--env", "dev", "--backend-host", "0.0.0.0", "--loglevel", "debug"]
