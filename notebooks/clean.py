"""
What this script does:
    - Parses all columns into correct data types
    - Strips timezone info from datetime columns
    - Flags illiquid rows (bid=0) without dropping them
    - Validates data integrity (bid <= ask, strike > 0, etc.)
    - Reports a data quality summary
    - Saves cleaned files to data/clean/

Note on IV and Greeks:
    The Market Data App Starter plan does not return implied volatility,
    delta, gamma, theta, or vega. These columns will be present but entirely
    null. They are kept as placeholders -- if you upgrade your plan and
    re-collect, the cleaning pipeline handles them automatically.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR      = PROJECT_ROOT / "data" / "raw" / "options"
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES  = ["phase1", "phase2", "phase3"]

print(f"Project root : {PROJECT_ROOT}")
print(f"Raw data     : {RAW_DIR}")
print(f"Clean output : {CLEAN_DIR}")


# ── Step 1: Discover all raw files ────────────────────────────────────────────

all_files = []
for ticker in TICKERS:
    for phase in PHASES:
        folder = RAW_DIR / ticker / phase
        if not folder.exists():
            continue
        for csv in sorted(folder.glob("*.csv")):
            all_files.append({
                "ticker": ticker,
                "phase":  phase,
                "path":   csv,
            })

print(f"\nTotal raw files found: {len(all_files)}")

summary = pd.DataFrame(all_files).groupby(["ticker", "phase"]).size().unstack(fill_value=0)
print("\nFiles per ticker per phase:")
print(summary.to_string())


# ── Step 2: Cleaning functions ────────────────────────────────────────────────

def parse_datetime_col(series: pd.Series) -> pd.Series:
    """
    Parse a datetime column that may contain timezone offsets.

    Example input:  '2025-05-16 16:00:00 -04:00'
    Example output: Timestamp('2025-05-16 16:00:00')  (no timezone)

    The raw data contains mixed UTC offsets (-04:00 in summer, -05:00 in
    winter due to daylight saving time). Using utc=True handles mixed
    offsets correctly by converting everything to UTC first, then we
    strip the timezone entirely for simplicity.
    """
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_localize(None)


def parse_collection_date(series: pd.Series) -> pd.Series:
    """
    Parse collection_date which is always a plain YYYY-MM-DD string.
    No timezone handling needed.
    """
    return pd.to_datetime(series, errors="coerce")


def clean_float_col(series: pd.Series) -> pd.Series:
    """
    Coerce a column to float. Any non-numeric values become NaN.
    """
    return pd.to_numeric(series, errors="coerce")


def clean_int_col(series: pd.Series, fill_zero: bool = True) -> pd.Series:
    """
    Coerce a column to integer.

    fill_zero=True  -- replace NaN with 0 before converting.
                       Used for volume and open interest where
                       null means no activity, not missing data.
    fill_zero=False -- keep NaN as NaN (stored as float since
                       pandas int columns cannot hold NaN).
                       Used for dte where null is genuinely unknown.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    if fill_zero:
        return numeric.fillna(0).astype(int)
    return numeric


def clean_bool_col(series: pd.Series) -> pd.Series:
    """
    Parse the inTheMoney column which arrives as string 'True'/'False'
    or native Python bool depending on how pandas read the CSV.
    Maps all variants to a proper pandas boolean type.
    """
    return series.map(
        {True: True, False: False,
         "True": True, "False": False,
         1: True, 0: False}
    ).astype("boolean")


def flag_illiquid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add is_illiquid column: True where bid = 0.

    Contracts with bid=0 have no active market maker quote. They are
    illiquid but not necessarily worthless -- they may still have valid
    open interest or last price data. We flag rather than drop so that
    downstream analysis can choose how to handle them.
    """
    df["is_illiquid"] = df["bid"] == 0
    return df


def validate(df: pd.DataFrame, filename: str) -> list:
    """
    Run data integrity checks on a cleaned DataFrame.
    Returns a list of warning strings. Empty list means all clear.

    These checks catch data corruption or API response anomalies
    that would silently corrupt downstream analysis if not caught here.
    """
    warnings = []

    # Bid should never exceed ask -- would mean negative spread
    bid_gt_ask = (df["bid"] > df["ask"]).sum()
    if bid_gt_ask > 0:
        warnings.append(f"  WARNING: {bid_gt_ask} rows where bid > ask")

    # Bid should never be negative -- price cannot be negative
    neg_bid = (df["bid"] < 0).sum()
    if neg_bid > 0:
        warnings.append(f"  WARNING: {neg_bid} rows with negative bid")

    # Strike must be positive -- a zero strike is meaningless
    zero_strike = (df["strike"] <= 0).sum()
    if zero_strike > 0:
        warnings.append(f"  WARNING: {zero_strike} rows with strike <= 0")

    # Side must be call or put only
    bad_side = ~df["side"].isin(["call", "put"])
    if bad_side.sum() > 0:
        warnings.append(f"  WARNING: {bad_side.sum()} rows with unexpected side value")

    # Collection date must not be null -- every row needs a timestamp
    null_dates = df["collection_date"].isnull().sum()
    if null_dates > 0:
        warnings.append(f"  WARNING: {null_dates} rows with null collection_date")

    # DTE must be non-negative -- expired contracts should not appear
    neg_dte = (df["dte"] < 0).sum()
    if neg_dte > 0:
        warnings.append(f"  WARNING: {neg_dte} rows with negative DTE")

    return warnings


def clean_file(raw_path: Path) -> pd.DataFrame:
    """
    Load and clean one raw CSV file. Returns a cleaned DataFrame.

    Applies all type coercions, datetime parsing, boolean cleaning,
    string normalisation, and illiquid flagging.
    """
    df = pd.read_csv(raw_path)

    # Datetime columns
    df["collection_date"] = parse_collection_date(df["collection_date"])
    df["expiration"]      = parse_datetime_col(df["expiration"])
    df["firstTraded"]     = parse_datetime_col(df["firstTraded"])
    df["updated"]         = parse_datetime_col(df["updated"])

    # Float columns
    for col in ["strike", "bid", "mid", "ask", "last",
                "intrinsicValue", "extrinsicValue", "underlyingPrice",
                "iv", "delta", "gamma", "theta", "vega"]:
        if col in df.columns:
            df[col] = clean_float_col(df[col])

    # Integer columns
    df["dte"]          = clean_int_col(df["dte"],          fill_zero=False)
    df["openInterest"] = clean_int_col(df["openInterest"], fill_zero=True)
    df["volume"]       = clean_int_col(df["volume"],       fill_zero=True)
    df["bidSize"]      = clean_int_col(df["bidSize"],      fill_zero=True)
    df["askSize"]      = clean_int_col(df["askSize"],      fill_zero=True)

    # Boolean columns
    df["inTheMoney"] = clean_bool_col(df["inTheMoney"])

    # String columns -- strip leading/trailing whitespace
    for col in ["ticker", "optionSymbol", "underlying", "side"]:
        if col in df.columns:
            df[col] = df[col].str.strip()

    # Flag illiquid rows
    df = flag_illiquid(df)

    return df


# ── Step 3: Run cleaning across all files ─────────────────────────────────────

print("\nCleaning files...")

results       = []
total_warnings = []

for entry in all_files:
    raw_path = entry["path"]
    ticker   = entry["ticker"]
    phase    = entry["phase"]

    df_clean = clean_file(raw_path)

    # Validate and collect any warnings
    warnings = validate(df_clean, raw_path.name)
    for w in warnings:
        total_warnings.append(f"{raw_path.name}: {w}")

    # Save -- mirror the raw folder structure under data/clean/
    out_folder = CLEAN_DIR / ticker / phase
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / raw_path.name
    df_clean.to_csv(out_path, index=False)

    results.append({
        "ticker":        ticker,
        "phase":         phase,
        "file":          raw_path.name,
        "rows":          len(df_clean),
        "illiquid_rows": int(df_clean["is_illiquid"].sum()),
        "null_iv":       int(df_clean["iv"].isnull().sum()),
    })

results_df = pd.DataFrame(results)
print(f"Cleaned {len(results_df)} files")


# ── Step 4: Validation report ─────────────────────────────────────────────────

print(f"\nValidation warnings: {len(total_warnings)}")
if total_warnings:
    for w in total_warnings:
        print(w)
else:
    print("No warnings -- all files passed integrity checks.")


# ── Step 5: Data quality summary ──────────────────────────────────────────────

print("\n=== Rows per ticker ===")
print(results_df.groupby("ticker")["rows"].sum().to_string())

print("\n=== Rows per phase ===")
print(results_df.groupby("phase")["rows"].sum().to_string())

print("\n=== Illiquid rows (bid=0) per ticker ===")
illiquid = results_df.groupby("ticker").agg(
    total_rows    =("rows",          "sum"),
    illiquid_rows =("illiquid_rows", "sum"),
)
illiquid["illiquid_pct"] = (
    illiquid["illiquid_rows"] / illiquid["total_rows"] * 100
).round(1)
print(illiquid.to_string())

print("\n=== IV null rate per ticker ===")
iv_summary = results_df.groupby("ticker").agg(
    total_rows =("rows",     "sum"),
    null_iv    =("null_iv",  "sum"),
)
iv_summary["null_iv_pct"] = (
    iv_summary["null_iv"] / iv_summary["total_rows"] * 100
).round(1)
print(iv_summary.to_string())
print("\nNote: IV is null for all rows on the Starter plan.")
print("Greeks (delta, gamma, theta, vega) are also null for the same reason.")

print("\n=== File count per ticker per phase ===")
file_counts = results_df.groupby(["ticker", "phase"]).size().unstack(fill_value=0)
print(file_counts.to_string())


# ── Step 6: Spot check ────────────────────────────────────────────────────────

print("\n=== Spot check -- first PG phase3 cleaned file ===")
pg_files = results_df[
    (results_df["ticker"] == "PG") &
    (results_df["phase"]  == "phase3")
]

if not pg_files.empty:
    sample_path = CLEAN_DIR / "PG" / "phase3" / pg_files.iloc[0]["file"]
    df_check = pd.read_csv(sample_path)
    print(f"File  : {sample_path.name}")
    print(f"Shape : {df_check.shape}")
    print(f"\nDtypes:\n{df_check.dtypes.to_string()}")
    print(f"\nSample rows:")
    print(df_check[[
        "ticker", "collection_date", "side", "strike",
        "bid", "ask", "mid", "volume",
        "openInterest", "inTheMoney", "is_illiquid"
    ]].head(8).to_string())

print("\nStep 1 complete. Cleaned files saved to data/clean/")
print("Next: run step2_features.py")