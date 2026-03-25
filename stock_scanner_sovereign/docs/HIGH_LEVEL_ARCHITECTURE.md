# High-level architecture

One-page view of how services, data stores, and external systems connect. For **calculation ownership** and SHM details, see [`architecture_data_layers.md`](architecture_data_layers.md).

## System context

```mermaid
flowchart LR
  subgraph External
    Fyers[Fyers API\nWebSocket + REST]
    Trader[You\nBrowser]
  end

  subgraph Stack["Docker stack (sovereign_net)"]
    UI[Dashboard\nReflex]
    SC[Master scanner]
    SC2[Sidecar]
    PL[Data pipeline]
    DB[(PostgreSQL)]
    SHM[(SHM mmap\nscanner_results)]
  end

  PQ[(Parquet\nhistorical OHLCV)]

  Fyers <-->|ticks + history API| SC
  Fyers <-.->|EOD / tokens| PL
  Trader -->|HTTP :3000 / :8000| UI

  SC --> SHM
  SC --> DB
  SC2 --> SHM
  SC2 --> DB
  UI --> SHM
  UI --> DB
  PL --> DB
  PL --> PQ
  SC --> PQ
  SC2 --> PQ
```

## Runtime roles (who does what)

```mermaid
flowchart TB
  subgraph L1["Layer 1 — persistence & batch"]
    DB[(PostgreSQL\nsymbols, prices, live_state, …)]
    PL[pipeline\nEOD / Parquet writer]
    PQ[(Parquet files\nPIPELINE_DATA_DIR)]
  end

  subgraph L2["Layer 2 — live engine"]
    MS[Master scanner\nSHM_MASTER=true]
    SHM[(scanner_results.mmap +\nsymbols_idx_map)]
  end

  subgraph L3["Layer 3–4 — consumers"]
    SC[Sidecar\nbreakout / signals]
    REF[Dashboard\nReflex UI]
  end

  FY[Fyers WebSocket]

  FY --> MS
  MS --> SHM
  MS --> DB
  PL --> DB
  PL --> PQ
  MS -.-> PQ
  SHM --> SC
  SHM --> REF
  DB --> SC
  DB --> REF
  PQ --> MS
  PQ --> SC
```

## Optional monitoring (`monitoring` Compose profile)

Not required for trading logic; used for infra visibility.

```mermaid
flowchart LR
  PE[postgres_exporter] --> DB[(PostgreSQL)]
  PR[Prometheus] -->|scrape| PE
  PR -->|scrape| CA[cAdvisor]
  PR -->|scrape| PR
  GF[Grafana] -->|PromQL| PR
```

- **Prometheus** scrapes `/metrics` on postgres_exporter, cAdvisor, and itself.
- **Grafana** uses Prometheus as the datasource (provisioned dashboards under `monitoring/grafana/` in the repo root).

---

## Legend

| Symbol | Meaning |
|--------|--------|
| **Master scanner** | Single writer of live math + SHM; Fyers WebSocket feed. |
| **Sidecar** | Reads SHM (slave); strategy / breakout; writes signals to DB. |
| **Dashboard** | Reads SHM + DB; no separate RS engine for “official” numbers. |
| **Pipeline** | Backfill / EOD append to Parquet; DB helpers. |
| **SHM** | Memory-mapped file for low-latency snapshot of scanner results. |
| **Parquet** | Columnar daily history for ring buffers and analytics load. |
