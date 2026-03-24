"""
Step 3 -- Realised Volatility

What this script does:

    Part A -- Build the RV time series
        - Loads daily price data for all 5 tickers from data/raw/prices/
        - Computes 20-day rolling realised volatility (annualised)
        - Saves a standalone RV file per ticker to data/rv/

    Part B -- Merge RV onto options features
        - Loads every feature-enriched file from data/features/
        - Joins RV onto each file by matching collection_date to the price date
        - Adds one new column: realised_vol
        - Saves enriched files to data/enriched/ (same folder structure)

What is realised volatility?

    Realised volatility (RV) measures how much a stock actually moved over a
    past window of time. We compute it from the daily log returns already in
    the price data:

        RV_20day = std(last 20 log returns) * sqrt(252)

    The sqrt(252) converts from daily standard deviation to an annualised
    figure (252 is the number of trading days in a year). This puts RV on
    the same scale as implied volatility (IV), which is always quoted as an
    annualised number, making them directly comparable.

    Why 20 days?
    20 trading days is approximately one calendar month -- a standard lookback
    window in options analysis. It captures recent market behaviour without
    being too sensitive to any single day's extreme move.

"""

import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
PRICES_DIR   = PROJECT_ROOT / "data" / "raw" / "prices"
FEAT_DIR     = PROJECT_ROOT / "data" / "features"
RV_DIR       = PROJECT_ROOT / "data" / "rv"
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched"

RV_DIR.mkdir(parents=True, exist_ok=True)
ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

TICKERS    = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES     = ["phase1", "phase2", "phase3"]
RV_WINDOW  = 20      # trading days
TRADING_DAYS_PER_YEAR = 252

print(f"Project root  : {PROJECT_ROOT}")
print(f"Prices input  : {PRICES_DIR}")
print(f"RV output     : {RV_DIR}")
print(f"Enriched output: {ENRICHED_DIR}")
print(f"RV window     : {RV_WINDOW} days")


# =============================================================================
# PART A -- Build the RV time series
# =============================================================================

# ── Step 1: Load all price files and compute RV ───────────────────────────────

print("\n--- Part A: Computing realised volatility ---\n")

rv_frames = []

for ticker in TICKERS:
    price_file = PRICES_DIR / f"{ticker}_daily_prices.csv"
    if not price_file.exists():
        print(f"  [{ticker}] Price file not found -- skipping")
        continue

    df = pd.read_csv(price_file, parse_dates=["date"])

    # Sort chronologically -- essential for rolling calculations.
    # Rolling windows look backwards in time, so if the rows are out of order
    # the window would grab the wrong dates.
    df = df.sort_values("date").reset_index(drop=True)

    # The price file already has log_return computed by scrape_prices.py.
    # We use it directly rather than recomputing to stay consistent.
    # The first row has NaN log_return (no previous day to compare against),
    # which is correct -- rolling() handles NaN gracefully by not including
    # it in the window count.

    # rolling(RV_WINDOW).std() computes the standard deviation of the last
    # RV_WINDOW log returns ending at each row.
    #
    # min_periods=RV_WINDOW means we only produce a valid RV once we have
    # a full window of data. Rows with fewer than 20 prior returns get NaN.
    # This prevents artificially low RV estimates at the start of the series.
    #
    # Multiplying by sqrt(252) annualises the daily standard deviation.
    df["realised_vol"] = (
        df["log_return"]
        .rolling(window=RV_WINDOW, min_periods=RV_WINDOW)
        .std()
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )

    # Keep only the columns needed for the merge downstream
    rv_df = df[["ticker", "date", "close", "realised_vol"]].copy()

    # Save standalone RV file
    out_path = RV_DIR / f"{ticker}_rv.csv"
    rv_df.to_csv(out_path, index=False)

    valid_rv = rv_df["realised_vol"].notna().sum()
    total    = len(rv_df)
    print(f"  [{ticker}] {total} days, {valid_rv} with valid RV "
          f"(first valid: {rv_df.loc[rv_df['realised_vol'].notna(), 'date'].min().date()})")

    rv_frames.append(rv_df)

# Combine all tickers into one lookup DataFrame for the merge in Part B
rv_all = pd.concat(rv_frames, ignore_index=True)
print(f"\nTotal RV rows across all tickers: {len(rv_all):,}")


# ── Step 2: RV summary statistics ─────────────────────────────────────────────

print("\n=== RV summary by ticker (annualised) ===")
rv_summary = (
    rv_all.groupby("ticker")["realised_vol"]
    .describe(percentiles=[0.25, 0.5, 0.75])
    [["min", "25%", "50%", "mean", "75%", "max"]]
    .round(4)
)
print(rv_summary.to_string())

# Show RV around Liberation Day for each ticker
print("\n=== RV on key event dates ===")
key_dates = ["2025-04-02", "2025-04-09", "2025-05-12"]
for kd in key_dates:
    kd_ts = pd.Timestamp(kd)
    row = rv_all[rv_all["date"] == kd_ts][["ticker", "realised_vol"]]
    if not row.empty:
        vals = row.set_index("ticker")["realised_vol"].round(4).to_dict()
        print(f"  {kd}: {vals}")
    else:
        print(f"  {kd}: no data (weekend or holiday)")


# =============================================================================
# PART B -- Merge RV onto options features
# =============================================================================

print("\n--- Part B: Merging RV onto options features ---\n")

# ── Step 3: Discover all feature-enriched files ───────────────────────────────

feat_files = []
for ticker in TICKERS:
    for phase in PHASES:
        folder = FEAT_DIR / ticker / phase
        if not folder.exists():
            continue
        for csv in sorted(folder.glob("*.csv")):
            feat_files.append({
                "ticker": ticker,
                "phase":  phase,
                "path":   csv,
            })

print(f"Feature files to enrich: {len(feat_files)}")


# ── Step 4: Merge and save ─────────────────────────────────────────────────────

def merge_rv(df_opts: pd.DataFrame, rv_lookup: pd.DataFrame) -> pd.DataFrame:
    """
    Join realised_vol onto an options DataFrame.

    The join key is (ticker, date) where date in the RV lookup corresponds
    to collection_date in the options data -- both represent the same trading
    day we took the snapshot.

    We use a left join so that every options row is kept even if RV is not
    available for that date (e.g. very early AAPL rows before the 20-day
    window fills). Missing RV values appear as NaN, not dropped rows.
    """
    # Rename 'date' to 'collection_date' so the merge key matches
    rv_keyed = rv_lookup.rename(columns={"date": "collection_date"})[
        ["ticker", "collection_date", "realised_vol"]
    ]

    return df_opts.merge(rv_keyed, on=["ticker", "collection_date"], how="left")


merge_results = []

for entry in feat_files:
    raw_path = entry["path"]
    ticker   = entry["ticker"]
    phase    = entry["phase"]

    df = pd.read_csv(raw_path, parse_dates=["collection_date", "expiration"])

    # Filter RV lookup to this ticker only for efficiency
    rv_ticker = rv_all[rv_all["ticker"] == ticker].copy()

    df_enriched = merge_rv(df, rv_ticker)

    out_folder = ENRICHED_DIR / ticker / phase
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / raw_path.name
    df_enriched.to_csv(out_path, index=False)

    rv_matched = df_enriched["realised_vol"].notna().sum()
    merge_results.append({
        "ticker":     ticker,
        "phase":      phase,
        "file":       raw_path.name,
        "rows":       len(df_enriched),
        "rv_matched": rv_matched,
        "rv_null":    len(df_enriched) - rv_matched,
    })

results_df = pd.DataFrame(merge_results)
print(f"Enriched {len(results_df)} files")


# ── Step 5: Merge quality report ──────────────────────────────────────────────

print("\n=== RV merge coverage by ticker ===")
coverage = results_df.groupby("ticker").agg(
    total_rows  =("rows",       "sum"),
    rv_matched  =("rv_matched", "sum"),
    rv_null     =("rv_null",    "sum"),
)
coverage["match_pct"] = (coverage["rv_matched"] / coverage["total_rows"] * 100).round(1)
print(coverage.to_string())

print("\nNote: rv_null rows are AAPL data from before Dec 2024 + early")
print("rows where the 20-day window has not yet filled.")


# ── Step 6: Spot check ────────────────────────────────────────────────────────

print("\n=== Spot check -- AAPL Liberation Day enriched file ===")
sample = ENRICHED_DIR / "AAPL" / "phase2" / "AAPL_2025-04-02_2025-04-11.csv"
if sample.exists():
    df_check = pd.read_csv(sample)
    print(f"File  : {sample.name}")
    print(f"Shape : {df_check.shape}")
    print(f"\nNew columns:")
    new_cols = ["collection_date", "ticker", "side", "strike",
                "relative_spread", "realised_vol"]
    print(df_check[new_cols].head(6).to_string())
    rv_val = df_check["realised_vol"].iloc[0]
    print(f"\nAAPL realised_vol on 2025-04-02: {rv_val:.4f} ({rv_val*100:.2f}% annualised)")

print("\nStep 3 complete.")
print("  RV time series saved to data/rv/")
print("  Enriched options data saved to data/enriched/")
print("Next: run step4_combine.py")
