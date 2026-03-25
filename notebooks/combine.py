import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched"
COMBINED_DIR = PROJECT_ROOT / "data" / "combined"
COMBINED_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES  = ["phase1", "phase2", "phase3"]

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


combined = pd.concat(frames, ignore_index=True)
print(f"Total rows: {len(combined):,}")

existing_ordered = [c for c in COL_ORDER if c in combined.columns]
remaining        = [c for c in combined.columns if c not in COL_ORDER]
combined         = combined[existing_ordered + remaining]

combined = combined.sort_values(
    ["ticker", "collection_date", "expiration", "side", "strike"]
).reset_index(drop=True)



# Validation Check

# Check for nulls in key columns
null_ticker = combined["ticker"].isnull().sum()
null_date   = combined["collection_date"].isnull().sum()
if null_ticker > 0:
    print(f"  WARNING: {null_ticker} rows with null ticker")
if null_date > 0:
    print(f"  WARNING: {null_date} rows with null collection_date")

# Check for unexpected phase values
bad_phase = ~combined["phase"].isin([1, 2, 3])
if bad_phase.sum() > 0:
    print(f"  WARNING: {bad_phase.sum()} rows with unexpected phase value")

# Check for duplicate option symbols
dupes = combined.duplicated(subset=["optionSymbol", "collection_date"]).sum()
if dupes > 0:
    print(f"  WARNING: {dupes} duplicate (optionSymbol, collection_date) pairs")

if null_ticker == 0 and null_date == 0 and bad_phase.sum() == 0 and dupes == 0:
    print("  All checks passed.")


# Save combined file

out_all = COMBINED_DIR / "combined_all.csv"
combined.to_csv(out_all, index=False)
size_mb = out_all.stat().st_size / (1024 * 1024)
print(f"\nSaved: {out_all.name}  ({len(combined):,} rows, {size_mb:.1f} MB)")


# Save by ticker
for ticker in TICKERS:
    df_t = combined[combined["ticker"] == ticker].copy()
    if df_t.empty:
        continue
    out_path = COMBINED_DIR / f"{ticker}_combined.csv"
    df_t.to_csv(out_path, index=False)
    print(f"  {out_path.name}  ({len(df_t):,} rows)")


# Final Data Inventory
print("\nMaster datasets saved to data/combined/")
