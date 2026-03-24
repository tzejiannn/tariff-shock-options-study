"""
Step 4 -- Combine into Master Datasets

What this script does:

    - Loads all enriched CSV files from data/enriched/
    - Concatenates them into two master datasets:

        combined_all.csv      -- every ticker, every phase, every row
                                 (~68,000 rows, 31 columns)

        {TICKER}_combined.csv -- one file per ticker, all phases merged
                                 useful for single-ticker deep dives

    - Prints a final data inventory so you know exactly what you have
      before opening the EDA notebook

Why a combined file?

    Right now your data lives in 1,442 separate CSVs split by ticker and
    phase. For analysis you almost always want to query across tickers or
    across phases -- e.g. "show me relative_spread for all 5 tickers on
    April 9". Loading 1,442 files individually in the EDA notebook would
    be slow and clunky. A single combined file loads in one line:

        df = pd.read_csv("data/combined/combined_all.csv")

    From there you filter, group, and pivot as needed. The ticker and phase
    columns tell you where every row came from.

Column reference for the combined file:

    Identifying
        ticker            -- AAPL / NVDA / AMZN / PG / CAT
        collection_date   -- date the snapshot was taken
        phase             -- 1 (baseline), 2 (event), 3 (recovery)
        days_from_apr2    -- signed days relative to Liberation Day
        optionSymbol      -- OCC option identifier
        side              -- call or put
        expiration        -- contract expiry date
        dte               -- days to expiry at snapshot

    Pricing
        strike            -- strike price
        underlyingPrice   -- stock spot price at snapshot
        bid / ask / mid   -- best bid, ask, midpoint
        last              -- most recent trade price

    Size
        bidSize / askSize -- number of contracts at best bid/ask
        volume            -- contracts traded on collection day
        openInterest      -- total outstanding contracts

    Derived -- liquidity
        spread            -- ask - bid
        relative_spread   -- spread / mid (normalised, comparable across tickers)
        is_illiquid       -- True where bid = 0 (no active market maker quote)

    Derived -- moneyness
        moneyness         -- strike / underlyingPrice  (1.0 = ATM)
        moneyness_pct     -- % above/below spot
        moneyness_cat     -- ITM / ATM / OTM
        inTheMoney        -- True if intrinsic value > 0
        intrinsicValue    -- immediate exercise value
        extrinsicValue    -- time and uncertainty premium

    Derived -- volatility
        realised_vol      -- 20-day rolling RV, annualised
"""

import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched"
COMBINED_DIR = PROJECT_ROOT / "data" / "combined"
COMBINED_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES  = ["phase1", "phase2", "phase3"]

# Column order for the combined file -- puts the most useful columns first
# so that when you open the CSV in Excel or print df.head() you immediately
# see the identifying and analytical columns without scrolling right.
COL_ORDER = [
    # Identity
    "ticker", "collection_date", "phase", "days_from_apr2",
    "optionSymbol", "side", "expiration", "dte",
    # Spot and strike
    "underlyingPrice", "strike", "moneyness", "moneyness_pct", "moneyness_cat",
    # Pricing
    "bid", "ask", "mid", "last",
    # Liquidity metrics (the core of this project)
    "spread", "relative_spread", "is_illiquid",
    # Size
    "bidSize", "askSize", "volume", "openInterest",
    # Contract value
    "intrinsicValue", "extrinsicValue", "inTheMoney",
    # Volatility
    "realised_vol",
    # Metadata
    "underlying", "firstTraded", "updated",
]

print(f"Project root   : {PROJECT_ROOT}")
print(f"Enriched input : {ENRICHED_DIR}")
print(f"Combined output: {COMBINED_DIR}")


# ── Step 1: Discover and load all enriched files ───────────────────────────────

print("\nLoading enriched files...")

frames = []

for ticker in TICKERS:
    for phase in PHASES:
        folder = ENRICHED_DIR / ticker / phase
        if not folder.exists():
            continue
        for csv in sorted(folder.glob("*.csv")):
            df = pd.read_csv(
                csv,
                parse_dates=["collection_date", "expiration", "firstTraded", "updated"],
                dtype={
                    "ticker":        str,
                    "optionSymbol":  str,
                    "underlying":    str,
                    "side":          str,
                    "moneyness_cat": str,
                    "is_illiquid":   bool,
                }
            )
            frames.append(df)

print(f"Loaded {len(frames)} files")


# ── Step 2: Concatenate ────────────────────────────────────────────────────────

combined = pd.concat(frames, ignore_index=True)
print(f"Total rows: {len(combined):,}")

# Reorder columns -- any column not in COL_ORDER gets appended at the end
# so we never accidentally drop a column if the schema changes
existing_ordered = [c for c in COL_ORDER if c in combined.columns]
remaining        = [c for c in combined.columns if c not in COL_ORDER]
combined         = combined[existing_ordered + remaining]

# Sort by ticker, then collection_date, then expiration, then side, then strike
# This ordering makes it easy to visually browse the file and is the natural
# order for time-series analysis
combined = combined.sort_values(
    ["ticker", "collection_date", "expiration", "side", "strike"]
).reset_index(drop=True)


# ── Step 3: Validate the combined file ────────────────────────────────────────

print("\n--- Validation ---")

# Every row must have a ticker and collection_date
null_ticker = combined["ticker"].isnull().sum()
null_date   = combined["collection_date"].isnull().sum()
if null_ticker > 0:
    print(f"  WARNING: {null_ticker} rows with null ticker")
if null_date > 0:
    print(f"  WARNING: {null_date} rows with null collection_date")

# Phase must be 1, 2, or 3
bad_phase = ~combined["phase"].isin([1, 2, 3])
if bad_phase.sum() > 0:
    print(f"  WARNING: {bad_phase.sum()} rows with unexpected phase value")

# No duplicate optionSymbol on the same collection_date
# (would mean the same contract appeared twice in the same snapshot)
dupes = combined.duplicated(subset=["optionSymbol", "collection_date"]).sum()
if dupes > 0:
    print(f"  WARNING: {dupes} duplicate (optionSymbol, collection_date) pairs")

if null_ticker == 0 and null_date == 0 and bad_phase.sum() == 0 and dupes == 0:
    print("  All checks passed.")


# ── Step 4: Save combined_all.csv ─────────────────────────────────────────────

out_all = COMBINED_DIR / "combined_all.csv"
combined.to_csv(out_all, index=False)
size_mb = out_all.stat().st_size / (1024 * 1024)
print(f"\nSaved: {out_all.name}  ({len(combined):,} rows, {size_mb:.1f} MB)")


# ── Step 5: Save per-ticker files ─────────────────────────────────────────────

print("\nSaving per-ticker files...")
for ticker in TICKERS:
    df_t = combined[combined["ticker"] == ticker].copy()
    if df_t.empty:
        continue
    out_path = COMBINED_DIR / f"{ticker}_combined.csv"
    df_t.to_csv(out_path, index=False)
    print(f"  {out_path.name}  ({len(df_t):,} rows)")


# ── Step 6: Final data inventory ──────────────────────────────────────────────

print("\n=== Final data inventory ===\n")

print("Row counts by ticker and phase:")
pivot = (
    combined.groupby(["ticker", "phase"])
    .size()
    .unstack("phase")
    .rename(columns={1: "phase1", 2: "phase2", 3: "phase3"})
)
pivot["total"] = pivot.sum(axis=1)
print(pivot.to_string())

print("\nDate coverage by ticker:")
coverage = combined.groupby("ticker")["collection_date"].agg(["min", "max", "nunique"])
coverage.columns = ["first_date", "last_date", "unique_dates"]
print(coverage.to_string())

print("\nLiquid rows (bid > 0) by ticker:")
liquid = combined[~combined["is_illiquid"]].groupby("ticker").size()
total  = combined.groupby("ticker").size()
pct    = (liquid / total * 100).round(1)
liq_df = pd.DataFrame({"liquid": liquid, "total": total, "liquid_pct": pct})
print(liq_df.to_string())

print("\nRealised vol coverage by ticker:")
rv_cov = combined.groupby("ticker")["realised_vol"].agg(
    valid   = lambda x: x.notna().sum(),
    total   = "count",
)
rv_cov["coverage_pct"] = (rv_cov["valid"] / rv_cov["total"] * 100).round(1)
print(rv_cov.to_string())

print("\nCall / put split:")
print(combined["side"].value_counts().to_string())

print("\nMoneyness category split:")
print(combined["moneyness_cat"].value_counts().to_string())

print(f"\nTotal columns in combined file: {len(combined.columns)}")
print(f"Columns: {list(combined.columns)}")

print("\nStep 4 complete.")
print("Master datasets saved to data/combined/")
print("Next: open notebooks/EDA.ipynb")
