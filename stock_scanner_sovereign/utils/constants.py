# utils/constants.py
# Canonical Schema for 4-Layer Architecture (Sovereign Dashboard)

# Fixed-width binary schema for SHM (mmap). Live snapshot extras (e.g. brk_lvl) go to live_state — see docs/architecture_data_layers.md
# ensures O(1) alignment for NumPy/Polars vectorization.
SIGNAL_DTYPE = [
    ('symbol', 'S40'),      # NSE:NIFTYMIDCAP100-INDEX (max headroom)
    ('ltp', 'f8'),         # Last Transaction Price
    ('mrs', 'f8'),         # Real-time Weekly Mansfield RS (Layer 2)
    ('mrs_prev', 'f8'),    # Last Week's Baseline MRS (Layer 1/2 Sync)
    ('mrs_daily', 'f8'),   # Daily Drift of MRS (Since Market Open)
    ('rs_rating', 'i4'),   # RS Percentile (0-100)
    ('change_pct', 'f8'),  # Daily change % 
    ('profile', 'S20'),    # Trading Profile (Value/Growth)
    ('status', 'S25'),     # Master: BUY | TRENDING | NOT TRENDING (weekly mRS vs 0); not breakout tape
    ('rv', 'f8'),           # Relative Volume (Current vs Avg)
    ('heartbeat', 'f8'),   # Unix micro-pulse for staleness
    ('price_up', 'i1'),    # 1 if LTP > Previous Week's close
    ('price_down', 'i1')   # 1 if LTP < Previous Week's close
]

# Dashboard RS benchmark picker + Layer-1 universe_members checks: only these two (NIFTY50 / NIFTY500 indices).
# RS math and reconciliation use the selected index symbol with `universe_members` for the matching universe.
DASHBOARD_BENCHMARK_MAP = {
    "Nifty 50": "NSE:NIFTY50-INDEX",
    "Nifty 500": "NSE:NIFTY500-INDEX",
}

# Full index registry: SHM bench slots, master pulse, BreakoutScanner bench buffer, legacy rs_math, etc.
# Do not use this for the Reflex benchmark panel — use DASHBOARD_BENCHMARK_MAP.
BENCHMARK_MAP = {
    "Nifty 50": "NSE:NIFTY50-INDEX",
    "Nifty 100": "NSE:NIFTY100-INDEX",
    "Nifty 500": "NSE:NIFTY500-INDEX",
    "Nifty Midcap 100": "NSE:NIFTYMIDCAP100-INDEX",
    "Nifty Smallcap 100": "NSE:NIFTYSMLCAP100-INDEX",
    "Microcap 250": "NSE:NIFTYMICROCAP250-INDEX",
    "Bank Nifty": "NSE:NIFTYBANK-INDEX",
    "All NSE Stocks": "NSE:NIFTY500-INDEX"
}

# Display names that have canonical CSV + DB universe_members rows we validate (same keys as DASHBOARD_BENCHMARK_MAP).
CANONICAL_MEMBERSHIP_UNIVERSES = tuple(DASHBOARD_BENCHMARK_MAP.keys())

SYMBOL_GROUPS = {
    "Nifty 50": "data/nifty50.csv",
    "Nifty 100": "data/nifty100.csv", 
    "Nifty 500": "data/nifty500.csv",
    "Nifty Midcap 100": "data/nifty_midcap100.csv",
    "Nifty Smallcap 100": "data/nifty_smallcap100.csv",
    "Microcap 250": "data/microcap250.csv",
    "Bank Nifty": "data/banknifty.csv",
    "All NSE Stocks": "data/NSE_EQ.csv"
}

UNIVERSE_OPTIONS = list(SYMBOL_GROUPS.keys())
