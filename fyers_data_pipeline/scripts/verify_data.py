import os
import pandas as pd
import numpy as np
import logging
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.parquet_manager import ParquetManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_symbol(pq_manager, symbol):
    """Verifies the integrity of a specific symbol's data."""
    df = pq_manager.read_data(symbol)
    if df.empty:
        return {"status": "empty", "error": "No data found"}

    issues = []
    
    # 1. Check for duplicates
    dupes = df.duplicated(subset=['timestamp']).sum()
    if dupes > 0:
        issues.append(f"Found {dupes} duplicate entries")

    # 2. Check for missing dates (Gaps larger than 5 days, accounting for weekends/holidays)
    df = df.sort_values('timestamp')
    df['diff'] = df['timestamp'].diff().dt.days
    gaps = df[df['diff'] > 5]
    if not gaps.empty:
        issues.append(f"Found {len(gaps)} gaps larger than 5 days")

    # 3. Check for invalid prices (Zero or Negative)
    invalid_prices = df[(df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)]
    if not invalid_prices.empty:
        issues.append(f"Found {len(invalid_prices)} rows with zero or negative prices")

    # 4. Check for High < Low or Close outside High/Low
    # Simple logic: High must be >= Low
    broken_hl = df[df['high'] < df['low']]
    if not broken_hl.empty:
        issues.append(f"Found {len(broken_hl)} rows where High < Low")

    if issues:
        return {"status": "issue", "issues": issues, "rows": len(df)}
    return {"status": "ok", "rows": len(df)}

def main():
    pq_manager = ParquetManager()
    symbols = [f.replace(".parquet", "") for f in os.listdir("data/historical") if f.endswith(".parquet")]
    
    print(f"\nVerifying integrity for {len(symbols)} symbols...")
    
    summary = {"ok": 0, "issue": 0, "empty": 0}
    all_issues = {}

    # Sample check 10% of symbols for speed, or all if user wants
    # Let's do a sample of 100 symbols for a quick health check
    sample_size = min(len(symbols), 100)
    import random
    check_list = random.sample(symbols, sample_size)

    for symbol in check_list:
        res = verify_symbol(pq_manager, symbol)
        summary[res["status"]] += 1
        if res["status"] == "issue":
            all_issues[symbol] = res["issues"]

    print("\n" + "="*40)
    print("DATA INTEGRITY REPORT (Sample Check)")
    print("="*40)
    print(f"Symbols Checked: {sample_size}")
    print(f"Healthy:         {summary['ok']}")
    print(f"Has Issues:      {summary['issue']}")
    print(f"Empty/Missing:   {summary['empty']}")
    print("="*40)

    if all_issues:
        print("\nDETAILED ISSUES:")
        for sym, issues in list(all_issues.items())[:10]:
            print(f"- {sym}: {', '.join(issues)}")
    else:
        print("\nAll sampled files passed the integrity check! ✨")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
