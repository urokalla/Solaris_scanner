import asyncio
import csv
import datetime as dt
from collections import Counter
from pathlib import Path

import reflex as rx


def _parse_dt(s: str) -> dt.datetime:
    x = (s or "").strip()
    if not x:
        return dt.datetime.min
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y, %H-%M", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return dt.datetime.strptime(x, fmt)
        except ValueError:
            pass
    return dt.datetime.min


class InsiderState(rx.State):
    rows: list[dict] = []
    total_count: int = 0
    status_message: str = "Initializing..."
    last_sync: str = "-"
    search_query: str = ""
    filter_signal: str = "ALL"

    def on_load(self):
        return InsiderState.poll_insider

    def set_search_query(self, q: str):
        self.search_query = q or ""

    def set_filter_signal(self, v: str):
        self.filter_signal = (v or "ALL").strip().upper()

    def open_tradingview(self, symbol: str):
        s = str(symbol or "").strip().upper()
        if not s:
            return
        if ":" in s:
            base = s.split(":", 1)[1]
        else:
            base = s
        base = base.replace("_", "-")
        if base.endswith("-EQ"):
            base = base[:-3]
        elif base.endswith("-INDEX"):
            base = base[:-6]
        idx_alias = {"NIFTY50": "NIFTY", "NIFTYBANK": "BANKNIFTY"}
        tv_sym = idx_alias.get(base, base)
        return rx.redirect(f"https://www.tradingview.com/chart/?symbol=NSE:{tv_sym}", is_external=True)

    @rx.var
    def filtered_rows(self) -> list[dict]:
        q = (self.search_query or "").strip().upper()
        sig = (self.filter_signal or "ALL").strip().upper()
        out = self.rows
        if sig != "ALL":
            out = [r for r in out if str(r.get("signal", "")).upper() == sig]
        if not q:
            return out
        return [
            r
            for r in out
            if q in str(r.get("symbol", "")).upper()
            or q in str(r.get("person_name", "")).upper()
            or q in str(r.get("company", "")).upper()
        ]

    @rx.var
    def filtered_count(self) -> int:
        return len(self.filtered_rows)

    def _signal_for(self, txn: str, person_category: str) -> tuple[str, str]:
        t = (txn or "").strip().upper()
        pc = (person_category or "").strip().upper()
        promoter_like = "PROMOTER" in pc or "DIRECTOR" in pc
        is_buy = ("BUY" in t) or ("ACQUISITION" in t) or ("ACQUIRE" in t)
        is_sell = ("SELL" in t) or ("SALE" in t) or ("DISPOSAL" in t) or ("DISPOSE" in t)
        if is_buy and promoter_like:
            return "STRONG", "#00E676"
        if is_buy:
            return "BUY", "#7CFC00"
        if is_sell:
            return "SELL", "#FF6E6E"
        return "NEUTRAL", "#B0BEC5"

    @staticmethod
    def _num(row: dict, key: str) -> float:
        try:
            v = row.get(key)
            if v is None or str(v).strip() == "":
                return 0.0
            return float(str(v).replace(",", ""))
        except Exception:
            return 0.0

    @staticmethod
    def _format_inr_rupees(val: float) -> str:
        """
        NSE value fields are rupees (full amount). Show readable Indian units with labels.
        """
        if val <= 0:
            return ""
        cr = 1e7  # 1 crore
        lk = 1e5  # 1 lakh
        if val >= cr:
            x = val / cr
            s = f"{x:.2f}".rstrip("0").rstrip(".")
            return f"₹ {s} Cr"
        if val >= lk:
            x = val / lk
            s = f"{x:.2f}".rstrip("0").rstrip(".")
            return f"₹ {s} L"
        if val >= 1_000:
            s = f"{int(round(val)):,}"
            return f"₹ {s}"
        s = f"{int(round(val))}"
        return f"₹ {s}"

    def _data_roots(self) -> list[Path]:
        root = Path(__file__).resolve()
        return [root.parents[3] / "data", root.parents[2] / "data"]

    def _flat_tuples_from_csv_files(self) -> tuple[list[tuple[str, dict]], bool]:
        """Load (source, row) pairs from snapshot CSVs if present."""
        csv_files: list[tuple[Path, str]] = []
        for base in self._data_roots():
            csv_files.append((base / "nse_pit_disclosures.csv", "PIT"))
            csv_files.append((base / "nse_sast_reg29.csv", "SAST"))
        batches: list[tuple[str, dict]] = []
        found_any = False
        for p, src in csv_files:
            if not p.exists():
                continue
            found_any = True
            with p.open("r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    batches.append((src, dict(row)))
        return batches, found_any

    def _rows_from_flat_sources(self, batches: list[tuple[str, dict]]) -> list[dict]:
        out: list[dict] = []
        for src, row in batches:
            symbol = str(row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            company = str(row.get("raw_company") or "")
            person_name = str(
                row.get("person_name") or row.get("raw_acqName") or row.get("raw_acquirerName") or ""
            )
            person_category = str(
                row.get("person_category") or row.get("raw_personCategory") or row.get("raw_promoterType") or ""
            )
            txn_type = str(row.get("txn_type") or row.get("raw_acqSaleType") or "").strip()
            buy_qty = self._num(row, "raw_buyQuantity")
            sell_qty = self._num(row, "raw_sellquantity")
            buy_val = self._num(row, "raw_buyValue")
            sell_val = self._num(row, "raw_sellValue")
            sec_val = self._num(row, "raw_secVal")
            alt_val = (
                self._num(row, "raw_tradeValue")
                or self._num(row, "raw_consideration")
                or self._num(row, "raw_amount")
            )
            acq_qty = self._num(row, "raw_noOfShareAcq") or self._num(row, "raw_secAcq")
            sale_qty = self._num(row, "raw_noOfShareSale")

            if not txn_type:
                if buy_qty > 0 or buy_val > 0:
                    txn_type = "Buy"
                elif sell_qty > 0 or sell_val > 0:
                    txn_type = "Sell"
                elif sale_qty > 0:
                    txn_type = "Sale"
                elif acq_qty > 0:
                    txn_type = "Acquisition"

            txn_u = txn_type.upper()
            if "SELL" in txn_u or "SALE" in txn_u:
                qty_v = sell_qty or sale_qty
                val_v = sell_val or sec_val or alt_val
            else:
                qty_v = buy_qty or acq_qty
                val_v = buy_val or sec_val or alt_val
            qty = "" if qty_v <= 0 else str(int(qty_v) if float(qty_v).is_integer() else round(qty_v, 2))
            value = self._format_inr_rupees(val_v)
            when = str(row.get("raw_timestamp") or row.get("raw_date") or row.get("disclosure_date") or "")
            signal, signal_color = self._signal_for(txn_type, person_category)
            out.append(
                {
                    "source": src,
                    "symbol": symbol,
                    "company": company,
                    "person_name": person_name,
                    "person_category": person_category,
                    "txn_type": txn_type,
                    "qty": qty,
                    "value": value,
                    "when": when,
                    "signal": signal,
                    "signal_color": signal_color,
                }
            )

        buy_keys: list[tuple[str, str]] = []
        for r in out:
            if r["signal"] in ("STRONG", "BUY"):
                pk = (r["symbol"], (r["person_name"] or "").strip().lower() or "—")
                buy_keys.append(pk)
        buy_cnt = Counter(buy_keys)
        for r in out:
            pk = (r["symbol"], (r["person_name"] or "").strip().lower() or "—")
            n = int(buy_cnt.get(pk, 0)) if r["signal"] in ("STRONG", "BUY") else 0
            r["buy_repeat_n"] = n
            r["buy_repeat_label"] = str(n) if n else "—"
            r["buy_repeat_color"] = "#FFB000" if n > 1 else "#666666"
            r["buy_repeat_weight"] = "bold" if n > 1 else "normal"

        out.sort(key=lambda x: _parse_dt(str(x.get("when") or "")), reverse=True)
        return out

    def _load_csv_rows(self) -> list[dict]:
        """Snapshot files only — no live NSE calls (avoids rate limits / blocks)."""
        batches, found = self._flat_tuples_from_csv_files()
        if not found:
            raise FileNotFoundError("insider CSV not found (expected nse_pit_disclosures.csv / nse_sast_reg29.csv)")
        return self._rows_from_flat_sources(batches)

    @rx.event(background=True)
    async def poll_insider(self):
        while True:
            try:
                rows = self._load_csv_rows()
                async with self:
                    self.rows = rows
                    self.total_count = len(rows)
                    self.last_sync = dt.datetime.now(dt.UTC).strftime("%H:%M:%S UTC")
                    self.status_message = "✅ Active"
            except Exception as e:
                async with self:
                    self.status_message = f"⚠️ {e}"
            await asyncio.sleep(180)

