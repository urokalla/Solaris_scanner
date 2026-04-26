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
    try:
        if x.endswith(" UTC"):
            return dt.datetime.strptime(x, "%Y-%m-%d %H:%M:%S UTC")
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
    filter_bucket: str = "ALL"
    min_score: int = 0
    filter_window: str = "ALL"
    show_new_only: bool = False
    filter_side: str = "ALL"
    filter_buy_kind: str = "ALL"

    def on_load(self):
        return InsiderState.poll_insider

    def set_search_query(self, q: str):
        self.search_query = q or ""

    def set_filter_signal(self, v: str):
        self.filter_signal = (v or "ALL").strip().upper()

    def set_filter_bucket(self, v: str):
        self.filter_bucket = (v or "ALL").strip().upper()

    def set_min_score(self, v: str):
        try:
            self.min_score = max(0, min(100, int(float(v or 0))))
        except Exception:
            self.min_score = 0

    def set_filter_window(self, v: str):
        self.filter_window = (v or "ALL").strip().upper()

    def set_show_new_only(self, v: bool):
        self.show_new_only = bool(v)

    def set_filter_side(self, v: str):
        self.filter_side = (v or "ALL").strip().upper()

    def set_filter_buy_kind(self, v: str):
        self.filter_buy_kind = (v or "ALL").strip().upper()

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
        bucket = (self.filter_bucket or "ALL").strip().upper()
        wnd = (self.filter_window or "ALL").strip().upper()
        side = (self.filter_side or "ALL").strip().upper()
        buy_kind = (self.filter_buy_kind or "ALL").strip().upper()
        out = self.rows
        wnd_map = {"1D": 1, "7D": 7, "30D": 30, "90D": 90}
        if wnd in wnd_map:
            max_days = wnd_map[wnd]
            out = [r for r in out if int(r.get("recency_days", 9999) or 9999) <= max_days]
        if sig != "ALL":
            out = [r for r in out if str(r.get("signal", "")).upper() == sig]
        if bool(self.show_new_only):
            out = [r for r in out if bool(r.get("is_new", False))]
        if side != "ALL":
            out = [r for r in out if str(r.get("txn_side", "OTHER")).upper() == side]
        if buy_kind != "ALL":
            out = [r for r in out if str(r.get("buy_kind", "OTHER")).upper() == buy_kind]
        if bucket != "ALL":
            out = [r for r in out if str(r.get("bucket", "")).upper() == bucket]
        out = [r for r in out if int(r.get("score", 0) or 0) >= int(self.min_score or 0)]
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

    @rx.var
    def strong_buy_count(self) -> int:
        return sum(
            1
            for r in self.rows
            if str(r.get("bucket", "")).upper() in ("OPEN_MARKET_BUY", "PROMOTER_ACCUMULATION")
        )

    @rx.var
    def strong_sell_count(self) -> int:
        return sum(1 for r in self.rows if str(r.get("bucket", "")).upper() == "PROMOTER_REDUCTION")

    @rx.var
    def net_value_7d_inr(self) -> float:
        total = 0.0
        for r in self.rows:
            if int(r.get("recency_days", 9999) or 9999) <= 7:
                total += float(r.get("signed_value_num", 0.0) or 0.0)
        return total

    @rx.var
    def net_value_30d_inr(self) -> float:
        total = 0.0
        for r in self.rows:
            if int(r.get("recency_days", 9999) or 9999) <= 30:
                total += float(r.get("signed_value_num", 0.0) or 0.0)
        return total

    @rx.var
    def net_value_7d_label(self) -> str:
        return self._format_signed_inr_short(self.net_value_7d_inr)

    @rx.var
    def net_value_30d_label(self) -> str:
        return self._format_signed_inr_short(self.net_value_30d_inr)

    @rx.var
    def avg_score_filtered(self) -> int:
        rows = self.filtered_rows
        if not rows:
            return 0
        return int(round(sum(int(r.get("score", 0) or 0) for r in rows) / len(rows)))

    @rx.var
    def top_symbol_flows(self) -> list[dict]:
        acc: dict[str, dict] = {}
        for r in self.filtered_rows:
            sym = str(r.get("symbol") or "").strip().upper()
            if not sym:
                continue
            d = acc.setdefault(
                sym,
                {
                    "symbol": sym,
                    "net": 0.0,
                    "net_label": "",
                    "buys": 0,
                    "sells": 0,
                    "best_score": 0,
                    "latest": "",
                },
            )
            sv = float(r.get("signed_value_num", 0.0) or 0.0)
            d["net"] += sv
            if sv >= 0:
                d["buys"] += 1
            else:
                d["sells"] += 1
            d["best_score"] = max(int(d["best_score"]), int(r.get("score", 0) or 0))
            w = str(r.get("when") or "")
            if not d["latest"] or _parse_dt(w) > _parse_dt(d["latest"]):
                d["latest"] = w
        out = list(acc.values())
        for d in out:
            d["net_label"] = self._format_signed_inr_short(float(d.get("net", 0.0) or 0.0))
            d["net_color"] = "#00E676" if float(d.get("net", 0.0) or 0.0) >= 0 else "#FF6E6E"
        out.sort(key=lambda x: (float(x["net"]), int(x["best_score"])), reverse=True)
        return out[:12]

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
    def _bucket_for(txn: str, person_category: str) -> tuple[str, str]:
        t = (txn or "").strip().upper()
        pc = (person_category or "").strip().upper()
        promoter = "PROMOTER" in pc
        director = "DIRECTOR" in pc
        is_buy = ("BUY" in t) or ("ACQUISITION" in t) or ("ACQUIRE" in t)
        is_sell = ("SELL" in t) or ("SALE" in t) or ("DISPOSAL" in t) or ("DISPOSE" in t)

        if is_buy and ("BUY" in t) and (promoter or director):
            return "OPEN_MARKET_BUY", "#00E676"
        if is_buy and (promoter or director):
            return "PROMOTER_ACCUMULATION", "#64DD17"
        if is_sell and (promoter or director):
            return "PROMOTER_REDUCTION", "#FF5252"
        if is_buy:
            return "BUY_FLOW", "#9CCC65"
        if is_sell:
            return "SELL_FLOW", "#EF9A9A"
        return "OTHER", "#90A4AE"

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

    @staticmethod
    def _format_signed_inr_short(val: float) -> str:
        sign = "+" if val >= 0 else "-"
        x = abs(float(val or 0.0))
        cr = 1e7
        lk = 1e5
        if x >= cr:
            s = f"{x / cr:.2f}".rstrip("0").rstrip(".")
            return f"{sign}₹ {s} Cr"
        if x >= lk:
            s = f"{x / lk:.2f}".rstrip("0").rstrip(".")
            return f"{sign}₹ {s} L"
        return f"{sign}₹ {int(round(x)):,}"

    @staticmethod
    def _score_for(
        *,
        bucket: str,
        person_category: str,
        value_num: float,
        buy_repeat_n: int,
        recency_days: int,
    ) -> int:
        score = 40
        b = (bucket or "").upper()
        pc = (person_category or "").upper()

        if b == "OPEN_MARKET_BUY":
            score += 28
        elif b == "PROMOTER_ACCUMULATION":
            score += 22
        elif b == "BUY_FLOW":
            score += 12
        elif b == "PROMOTER_REDUCTION":
            score -= 16
        elif b == "SELL_FLOW":
            score -= 10

        if "PROMOTER" in pc:
            score += 8
        elif "DIRECTOR" in pc:
            score += 5

        if value_num >= 5e7:
            score += 20
        elif value_num >= 1e7:
            score += 15
        elif value_num >= 5e6:
            score += 10
        elif value_num >= 1e6:
            score += 6

        if buy_repeat_n >= 3:
            score += 10
        elif buy_repeat_n == 2:
            score += 6

        if recency_days <= 1:
            score += 10
        elif recency_days <= 3:
            score += 6
        elif recency_days <= 7:
            score += 3
        elif recency_days > 30:
            score -= 4

        return max(0, min(100, int(score)))

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
        today = dt.datetime.now(dt.UTC).date()
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
            txn_side = "OTHER"
            buy_kind = "OTHER"
            if "SELL" in txn_u or "SALE" in txn_u or "DISPOSAL" in txn_u or "DISPOSE" in txn_u:
                txn_side = "SELL"
            elif "BUY" in txn_u or "ACQUISITION" in txn_u or "ACQUIRE" in txn_u:
                txn_side = "BUY"
                # Practical classification from disclosure wording:
                # "Buy" ~= open market buy, "Acquisition/Acquire" = non-open/other acquisition mode.
                buy_kind = "OPEN_MARKET" if "BUY" in txn_u else "ACQUISITION"

            if "SELL" in txn_u or "SALE" in txn_u:
                qty_v = sell_qty or sale_qty
                val_v = sell_val or sec_val or alt_val
                signed_val = -float(val_v) if val_v > 0 else 0.0
            else:
                qty_v = buy_qty or acq_qty
                val_v = buy_val or sec_val or alt_val
                signed_val = float(val_v) if val_v > 0 else 0.0
            qty = "" if qty_v <= 0 else str(int(qty_v) if float(qty_v).is_integer() else round(qty_v, 2))
            value = self._format_inr_rupees(val_v)
            when = str(row.get("raw_timestamp") or row.get("raw_date") or row.get("disclosure_date") or "")
            when_dt = _parse_dt(when)
            recency_days = 9999
            if when_dt != dt.datetime.min:
                recency_days = max(0, (today - when_dt.date()).days)
            first_seen_at = str(row.get("first_seen_utc") or row.get("fetched_at_utc") or "").strip()
            refreshed_at = str(row.get("last_refreshed_utc") or row.get("fetched_at_utc") or "").strip()
            refreshed_dt = _parse_dt(refreshed_at)
            reflected_age_min = "—"
            if refreshed_dt != dt.datetime.min:
                now_utc = dt.datetime.now(dt.UTC).replace(tzinfo=None)
                age_val = int(round((now_utc - refreshed_dt).total_seconds() / 60.0))
                reflected_age_min = str(max(0, age_val))
            signal, signal_color = self._signal_for(txn_type, person_category)
            bucket, bucket_color = self._bucket_for(txn_type, person_category)
            out.append(
                {
                    "source": src,
                    "symbol": symbol,
                    "company": company,
                    "person_name": person_name,
                    "person_category": person_category,
                    "txn_type": txn_type,
                    "txn_side": txn_side,
                    "buy_kind": buy_kind,
                    "qty": qty,
                    "value": value,
                    "when": when,
                    "nse_time": when,
                    # Stable first ingest timestamp (does not move each poll).
                    "first_seen_at": first_seen_at if first_seen_at else (refreshed_at if refreshed_at else "—"),
                    # Latest refresh timestamp (used for feed freshness/age).
                    "refreshed_at": refreshed_at if refreshed_at else "—",
                    # IMPORTANT: NSE fields are disclosure payload timestamps, not guaranteed publish timestamps.
                    # So we expose feed freshness instead of a potentially misleading "NSE-vs-dashboard lag".
                    "reflected_age_min": reflected_age_min,
                    "recency_days": recency_days,
                    "signal": signal,
                    "signal_color": signal_color,
                    "bucket": bucket,
                    "bucket_color": bucket_color,
                    "value_num": float(val_v) if val_v > 0 else 0.0,
                    "signed_value_num": signed_val,
                    "is_new": str(row.get("is_new") or "0").strip() == "1",
                    "new_label": "NEW" if str(row.get("is_new") or "0").strip() == "1" else "",
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
            r["score"] = self._score_for(
                bucket=str(r.get("bucket", "")),
                person_category=str(r.get("person_category", "")),
                value_num=float(r.get("value_num", 0.0) or 0.0),
                buy_repeat_n=n,
                recency_days=int(r.get("recency_days", 9999) or 9999),
            )
            sc = int(r["score"])
            r["score_band"] = "green" if sc >= 70 else ("orange" if sc >= 50 else "gray")

        # Operator-first ordering: newest NSE disclosure time at top.
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

