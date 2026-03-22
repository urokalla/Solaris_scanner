import os, csv, logging; from backend.database import DatabaseManager; from utils.constants import SYMBOL_GROUPS
from psycopg2.extras import execute_values
L = logging.getLogger("Seeder"); logging.basicConfig(level=20)

def seed_universes():
    db = DatabaseManager(); bas = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with db.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM universe_members")
        for u_n, rel in SYMBOL_GROUPS.items():
            p = os.path.join(bas, rel)
            if not os.path.exists(p) and u_n == "All NSE Stocks": p = os.path.join(bas, "data/available_symbols.txt")
            if not os.path.exists(p): continue
            try:
                if p.endswith(".txt"):
                    with open(p) as f: sn = [l.strip().upper() for l in f if l.strip()]
                else:
                    with open(p, encoding='utf-8-sig') as f:
                        r = csv.DictReader(f); c = next((h for h in r.fieldnames if h.lower()=='symbol'), r.fieldnames[0])
                        sn = []
                        for row in r:
                            v = row.get(c); s = v.strip().upper() if v else ""
                            if s: sn.append(s if s.startswith("NSE:") else (f"NSE:{s}" if "INDEX" in s else f"NSE:{s}-EQ"))
            except Exception as e: L.error(f"Err {p}: {e}"); continue
            if not sn: continue
            u_i = u_n.upper().replace(" ", "_").replace("NIFTY_", "").replace("_STOCKS", "").replace("ALL_NSE_STOCKS", "ALL_NSE")
            L.info(f"Adding {len(sn)} to {u_i}..."); cur.execute("INSERT INTO universes (universe_id) VALUES (%s) ON CONFLICT DO NOTHING", (u_i,))
            for s in set(sn): cur.execute("INSERT INTO symbols (symbol_id, is_active) VALUES (%s, TRUE) ON CONFLICT DO NOTHING", (s,))
            execute_values(cur, "INSERT INTO universe_members (universe_id, symbol_id) VALUES %s ON CONFLICT DO NOTHING", [(u_i, s) for s in set(sn)])
        conn.commit()
    L.info("✅ Done.")

if __name__ == "__main__": seed_universes()
