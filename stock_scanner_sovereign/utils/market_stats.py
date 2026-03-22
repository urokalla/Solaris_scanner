import os, numpy as np
from nselib import capital_market
from datetime import datetime, timedelta

def get_top_gainers(limit=10):
    """Sovereign Gainers: Zero-Pandas."""
    try:
        df = capital_market.top_gainers_or_losers()
        if df is None or df.empty: return []
        
        # Convert to list of dicts manually to avoid DataFrame overhead in UI
        records = df.to_dict('records')
        for r in records:
            # Normalize keys to lowercase for internal consistency
            for k in list(r.keys()):
                r[k.lower()] = r.pop(k)
        
        # Sort and limit
        records.sort(key=lambda x: float(x.get('perchange', 0)), reverse=True)
        return records[:limit]
    except Exception: return []

def get_bulk_delivery_data():
    """Sovereign Delivery: Zero-Pandas Bhavcopy."""
    for i in range(1, 6):
        try:
            date_str = (datetime.now() - timedelta(days=i)).strftime('%d-%m-%Y')
            df = capital_market.bhav_copy_with_delivery(date_str)
            if df is not None and not df.empty:
                # Convert to dict {SYMBOL: DELIVERY_PERCENT}
                res = {}
                for _, row in df.iterrows():
                    sym = str(row.get('SYMBOL', '')).strip()
                    try: d = float(row.get('DELIV_PER', 0))
                    except: d = 0.0
                    if sym: res[sym] = d
                return res
        except: continue
    return {}

def get_delivery_percentage(symbol, bulk_data=None):
    ticker = symbol.split(":")[1].split("-")[0] if ":" in symbol else symbol
    if bulk_data and ticker in bulk_data: return float(bulk_data[ticker])
    try:
        df = capital_market.deliverable_position_data(ticker, period='1D')
        if not df.empty: return float(df.iloc[-1]['%DlyQttoTradedQty'])
    except: pass
    return 0.0
