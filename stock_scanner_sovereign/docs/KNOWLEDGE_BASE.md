# Solaris — Knowledge base (how signals work & what we achieve)

**Audience:** Anyone with basic math and curiosity — no finance degree required.  
**Scope:** Explains *ideas* and *outputs*; code paths live in `architecture_data_layers.md`, `quant_rs_accuracy.md`, and `OPERATIONS_SOP.md`.

---

## 1. What this system is (one paragraph)

Solaris is a **live stock scanner** for Indian equities (mostly NSE). It compares each stock to a **benchmark index** (e.g. Nifty 50 or Nifty 500) using **relative strength** math, streams **prices and signals** in real time, and adds optional tools (breakout tape, daily “Udai” rules) so you can **see** when names are strong or weak *versus the market you care about* — not predict the future.

---

## 2. Words you need first

| Term | Plain meaning |
|------|----------------|
| **Benchmark / index** | A basket of stocks that stands for “the market” (e.g. Nifty 50). |
| **Relative strength (RS)** | Is *this* stock doing better or worse than the benchmark over some window? |
| **mRS (weekly)** | A **single number** (centered near **0**) that summarizes weekly relative strength vs the benchmark. **Above 0** ≈ stronger than average; **below 0** ≈ weaker. |
| **RS rating** | A **rank** (0–100): where this stock sits among peers *right now* by that strength measure. |
| **Signal** | A **label** or **flag** the software shows when its rules fire (e.g. “BUY” on the main grid, “BREAKOUT” on the sidecar). Signals are **rules on data**, not guarantees. |
| **SHM (shared memory)** | A fast in-memory file the **master** process writes so **slaves** (UI, sidecar) read the same numbers without recomputing everything. |

---

## 3. The big idea: “Beat the benchmark”

Imagine a school race:

- The **benchmark** is the **average runner** in your grade.
- A stock with **positive weekly mRS** is, roughly, **running faster than that average** over the **weekly** window the model uses.
- A stock with **negative weekly mRS** is **lagging** that average.

The system **does not** say “this company is good or bad.” It says, **compared to the index you chose**, this name is **stronger or weaker** on the math we implemented.

---

## 4. Where signals come from (high level)

```
Market ticks (Fyers)  →  Master scanner  →  Math (RS, mRS, rating)
                              ↓
                    Write to SHM + Postgres
                              ↓
              Dashboard / Sidecar read & display
                              ↓
         Extra rules (breakout tape, Udai) add more labels
```

1. **Live data** arrives for many symbols.  
2. The **master** updates matrices and computes **weekly mRS**, **daily drift**, **percentile rank**, and **STATUS** (see below).  
3. Results are stored in **shared memory** and periodically in **the database**.  
4. The **UI** and **sidecar** **read** those values; they do not invent a second RS formula.  
5. **Breakout** and **Udai** layers add **separate** labels from **price history** and **rules** — they can disagree with each other; that is expected.

---

## 5. Main grid: how the **STATUS** column is built

This uses **weekly mRS** and a few **session rules** (see `quant_rs_accuracy.md` for exact definitions).

| Label | Idea in plain English |
|-------|------------------------|
| **NOT TRENDING** | Weekly mRS is **not** on the “strong” side of the line (≤ 0). The model is **not** flagging a long-side strength story. |
| **TRENDING** | Weekly mRS is **above 0**, and **yesterday’s** stored mRS was also above 0 — strength **was already** there; not treated as a “fresh” cross. |
| **BUY** | A **session-latched** label when the model sees a **valid move above 0** (e.g. cross from weak to strong, with rules so it doesn’t flip every tick). It **resets** when mRS goes back ≤ 0 or on a **new calendar day** (IST), depending on implementation. |

**Important:** This **“BUY”** is **not** “buy the stock.” It is **software vocabulary** for “the RS engine hit its **BUY** state.” Trading decisions are yours.

Also: **`Prev W_mRS`** uses an **end-of-day snapshot** so “yesterday vs today” comparisons make sense.

---

## 6. Sidecar: **BRK STAGE** vs **MRS STATUS**

These are **different channels**:

| Column | What it uses |
|--------|----------------|
| **MRS STATUS** | Same **BUY / TRENDING / NOT TRENDING** idea as the main grid — copied from what the **master** already wrote (weekly mRS logic). |
| **BRK STAGE** | **Price vs pivot** on the **breakout tape** (intraday buffer) + optional **mRS signal line** for labels like **BUY NOW**. Examples: **BREAKOUT** = price cleared a prior high window; **NEAR BRK** = price is in the **top 5% under** that pivot (not a “buy stock” meaning). |

So you can see **NOT TRENDING** on RS but **NEAR BRK** on price — the stock can be **weak vs index** but **tight to a short-term resistance** on the tape.

---

## 7. Udai column (optional Pine-style daily rules)

If enabled, this is a **separate** strategy snapshot:

- **Trend filter:** short vs long **daily** moving averages of **close** (with last bar updated by **live LTP**).  
- **Breakout:** price crosses above a **Donchian** level (highest high of the **prior N daily** bars, not including today).  
- **Risk / stop:** **ATR**-style trailing stop concept for display.

It answers: “**On daily rules we coded**, is this name in trend, flat, entry, or exit?” — **not** the same as **MRS STATUS**.

---

## 8. What we are trying to achieve (product goals)

| Goal | How the system helps |
|------|----------------------|
| **Screen the market** | Rank and filter thousands of names by **relative strength** vs a chosen benchmark. |
| **One definition of “strong”** | Same **mRS** and **rating** math everywhere the master writes — fewer arguments about Excel sheets. |
| **Faster feedback** | Live **ticks → SHM** so the grid updates without polling random websites. |
| **Layered views** | **RS trend** (main STATUS) vs **short-term price structure** (breakout stages) vs **optional daily rules** (Udai). |
| **Operations** | Dockerized services, DB audit trail, Parquet history for backfills — see `OPERATIONS_SOP.md`. |

---

## 9. What this is **not**

- **Not** investment advice, not a promise of profit.  
- **Not** a single “correct” strategy — **NEAR BRK**, **BUY NOW**, and **MRS BUY** mean **different things** (see sections 5–7).  
- **Not** a replacement for **risk management**, position sizing, or your own rules.

---

## 10. Where to read next

| Document | Contents |
|----------|----------|
| `architecture_data_layers.md` | Four layers, SHM, DB, who writes what |
| `quant_rs_accuracy.md` | Bar definitions, pivot windows, STATUS rules |
| `OPERATIONS_SOP.md` | Docker, EOD, backfill, when things break |

---

*Revision: keep this file conceptual; put new **product** explanations here and **exact** numeric rules in `quant_rs_accuracy.md`.*
