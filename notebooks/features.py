"""
Step 2 — Feature Engineering

What this script does:
    - Loads every cleaned CSV from data/clean/
    - Engineers derived columns used throughout the analysis:
        spread           -- absolute cost of trading one contract
        relative_spread  -- spread normalised by mid price (comparable across tickers)
        moneyness        -- strike relative to spot price (1.0 = at-the-money)
        moneyness_pct    -- moneyness expressed as % away from spot
        moneyness_cat    -- categorical: ITM / ATM / OTM
        phase            -- which collection phase (1, 2, or 3)
        days_from_apr2   -- signed integer days relative to Liberation Day
    - Saves feature-enriched files to data/features/ mirroring the same
      {ticker}/phase{N}/ folder structure as data/clean/

"""

import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean"
FEAT_DIR     = PROJECT_ROOT / "data" / "features"
FEAT_DIR.mkdir(parents=True, exist_ok=True)

TICKERS     = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES      = ["phase1", "phase2", "phase3"]
LIBERATION_DAY = pd.Timestamp("2025-04-02")

ATM_BAND = 0.03

print(f"Project root : {PROJECT_ROOT}")
print(f"Clean input  : {CLEAN_DIR}")
print(f"Feature output: {FEAT_DIR}")


# ── Step 1: Discover all cleaned files ────────────────────────────────────────

all_files = []
for ticker in TICKERS:
    for phase in PHASES:
        folder = CLEAN_DIR / ticker / phase
        if not folder.exists():
            continue
        for csv in sorted(folder.glob("*.csv")):
            all_files.append({
                "ticker": ticker,
                "phase":  phase,
                "path":   csv,
            })

print(f"\nTotal cleaned files found: {len(all_files)}")


# ── Step 2: Feature engineering functions ─────────────────────────────────────

def add_spread(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the absolute bid-ask spread.

    spread = ask - bid

    This is the raw cost of immediately buying AND selling one contract --
    the amount you would lose if you entered and exited a position at the
    prevailing quotes. A wider spread means less liquidity.

    We also handle the case where mid is zero or NaN (illiquid contracts
    with no quote) by setting relative_spread to NaN rather than dividing
    by zero, which would produce inf and corrupt downstream calculations.
    """
    df["spread"] = df["ask"] - df["bid"]

    # relative_spread = spread / mid
    # This normalises by the price level so you can compare a $0.50 spread
    # on a $2 option (25% -- very wide) with a $0.50 spread on a $50 option
    # (1% -- very tight). Without normalisation, cheap options always look
    # more liquid than expensive ones just because their spread is smaller.
    mid_safe = df["mid"].replace(0, np.nan)
    df["relative_spread"] = df["spread"] / mid_safe

    return df


def add_moneyness(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute moneyness -- where the strike sits relative to the current stock price.

    moneyness = strike / underlyingPrice

        > 1.0  means the strike is above the current stock price
        = 1.0  means exactly at-the-money (ATM)
        < 1.0  means the strike is below the current stock price

    moneyness_pct = (strike - underlyingPrice) / underlyingPrice * 100

        Expresses the same thing as a percentage above or below spot.
        e.g. -5.0 means the strike is 5% below the current stock price.

    moneyness_cat -- categorises each contract as ITM, ATM, or OTM:

        For CALLS:
            ITM  -- strike < spot * (1 - ATM_BAND)  -- strike well below spot
            ATM  -- strike within +/- ATM_BAND of spot
            OTM  -- strike > spot * (1 + ATM_BAND)  -- strike well above spot

        For PUTS:
            ITM  -- strike > spot * (1 + ATM_BAND)  -- strike well above spot
            ATM  -- strike within +/- ATM_BAND of spot
            OTM  -- strike < spot * (1 - ATM_BAND)  -- strike well below spot

        A call is ITM when the stock is above the strike (you can exercise
        profitably). A put is ITM when the stock is below the strike.
        This is why the same strike can be OTM for a call and ITM for a put.

    ATM_BAND = 0.03 means "within 3% of spot counts as at-the-money".
    """
    spot = df["underlyingPrice"]

    df["moneyness"]     = df["strike"] / spot
    df["moneyness_pct"] = (df["strike"] - spot) / spot * 100

    # Classify by side
    upper = spot * (1 + ATM_BAND)
    lower = spot * (1 - ATM_BAND)

    call_mask = df["side"] == "call"
    put_mask  = df["side"] == "put"

    # Default to ATM, then overwrite OTM and ITM
    df["moneyness_cat"] = "ATM"

    # Calls
    df.loc[call_mask & (df["strike"] < lower), "moneyness_cat"] = "ITM"
    df.loc[call_mask & (df["strike"] > upper), "moneyness_cat"] = "OTM"

    # Puts
    df.loc[put_mask  & (df["strike"] > upper), "moneyness_cat"] = "ITM"
    df.loc[put_mask  & (df["strike"] < lower), "moneyness_cat"] = "OTM"

    return df


def add_phase(df: pd.DataFrame, phase_label: str) -> pd.DataFrame:
    """
    Add a phase column indicating which collection window each row belongs to.

    Phase 1 = pre-tariff baseline (calm market, reference regime)
    Phase 2 = tariff event window (shock, escalation, pause)
    Phase 3 = recovery (post-event normalisation)

    This is extracted from the folder structure rather than re-derived from
    the collection_date because the phase boundaries in settings.yaml are
    the authoritative definition. The folder name is the source of truth.
    """
    # phase_label is "phase1", "phase2", or "phase3" -- extract the integer
    df["phase"] = int(phase_label.replace("phase", ""))
    return df


def add_days_from_apr2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add days_from_apr2 -- the signed number of calendar days between each
    row's collection_date and Liberation Day (April 2 2025).

    Negative values = before the tariff announcement (pre-shock)
    Zero            = Liberation Day itself
    Positive values = after the announcement (shock + recovery)

    This column is essential for event study charts -- it lets you align
    all tickers and expiries on the same time axis relative to the event,
    regardless of the absolute date. For example, you can plot
    "average relative_spread at day -5, -4, ..., 0, +1, +2, ..."
    across all five tickers on the same chart, centred on the shock.
    """
    df["days_from_apr2"] = (
        df["collection_date"] - LIBERATION_DAY
    ).dt.days
    return df


def engineer_features(df: pd.DataFrame, phase_label: str) -> pd.DataFrame:
    """
    Apply all feature engineering functions to a single cleaned DataFrame.
    Returns the enriched DataFrame.
    """
    df = add_spread(df)
    df = add_moneyness(df)
    df = add_phase(df, phase_label)
    df = add_days_from_apr2(df)
    return df


def validate_features(df: pd.DataFrame, filename: str) -> list:
    """
    Sanity check the engineered features. Returns a list of warnings.

    spread must be >= 0 (ask >= bid was already checked in step1, so
    spread = ask - bid should be non-negative)

    moneyness must be positive (strike and underlyingPrice are both > 0)

    moneyness_cat must only contain ITM, ATM, OTM

    relative_spread should not contain inf (would mean mid was zero, which
    we handled with replace(0, NaN), but verify it worked)
    """
    warnings = []

    neg_spread = (df["spread"] < 0).sum()
    if neg_spread > 0:
        warnings.append(f"  WARNING {filename}: {neg_spread} rows with negative spread")

    non_pos_moneyness = (df["moneyness"] <= 0).dropna().sum()
    if non_pos_moneyness > 0:
        warnings.append(f"  WARNING {filename}: {non_pos_moneyness} rows with moneyness <= 0")

    bad_cat = ~df["moneyness_cat"].isin(["ITM", "ATM", "OTM"])
    if bad_cat.sum() > 0:
        warnings.append(f"  WARNING {filename}: {bad_cat.sum()} rows with unexpected moneyness_cat")

    inf_rs = np.isinf(df["relative_spread"]).sum()
    if inf_rs > 0:
        warnings.append(f"  WARNING {filename}: {inf_rs} rows with inf relative_spread")

    return warnings


# ── Step 3: Run feature engineering across all files ──────────────────────────

print("\nEngineering features...")

results        = []
total_warnings = []

for entry in all_files:
    raw_path = entry["path"]
    ticker   = entry["ticker"]
    phase    = entry["phase"]

    df = pd.read_csv(raw_path, parse_dates=["collection_date", "expiration"])

    df = engineer_features(df, phase)

    warnings = validate_features(df, raw_path.name)
    for w in warnings:
        total_warnings.append(w)

    out_folder = FEAT_DIR / ticker / phase
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / raw_path.name
    df.to_csv(out_path, index=False)

    results.append({
        "ticker":       ticker,
        "phase":        phase,
        "file":         raw_path.name,
        "rows":         len(df),
        "atm_rows":     int((df["moneyness_cat"] == "ATM").sum()),
        "itm_rows":     int((df["moneyness_cat"] == "ITM").sum()),
        "otm_rows":     int((df["moneyness_cat"] == "OTM").sum()),
        "mean_spread":  round(df.loc[~df["is_illiquid"], "spread"].mean(), 4),
        "mean_rel_spread": round(df.loc[~df["is_illiquid"], "relative_spread"].mean(), 4),
    })

results_df = pd.DataFrame(results)
print(f"Feature-engineered {len(results_df)} files")


# ── Step 4: Validation report ─────────────────────────────────────────────────

print(f"\nValidation warnings: {len(total_warnings)}")
if total_warnings:
    for w in total_warnings:
        print(w)
else:
    print("No warnings -- all feature checks passed.")


# ── Step 5: Feature summary ───────────────────────────────────────────────────

print("\n=== Moneyness distribution (all tickers, all phases) ===")
mono_totals = results_df[["atm_rows", "itm_rows", "otm_rows"]].sum()
total_rows  = results_df["rows"].sum()
print(f"  ITM : {mono_totals['itm_rows']:>7,}  ({mono_totals['itm_rows']/total_rows*100:.1f}%)")
print(f"  ATM : {mono_totals['atm_rows']:>7,}  ({mono_totals['atm_rows']/total_rows*100:.1f}%)")
print(f"  OTM : {mono_totals['otm_rows']:>7,}  ({mono_totals['otm_rows']/total_rows*100:.1f}%)")

print("\n=== Average spread (liquid contracts only, bid > 0) by ticker ===")
print(
    results_df[~results_df["mean_spread"].isna()]
    .groupby("ticker")[["mean_spread", "mean_rel_spread"]]
    .mean()
    .round(4)
    .to_string()
)

print("\n=== Average spread by phase ===")
print(
    results_df[~results_df["mean_spread"].isna()]
    .groupby("phase")[["mean_spread", "mean_rel_spread"]]
    .mean()
    .round(4)
    .to_string()
)

print("\n=== Average relative spread by ticker by phase ===")
pivot = (
    results_df[~results_df["mean_rel_spread"].isna()]
    .groupby(["ticker", "phase"])["mean_rel_spread"]
    .mean()
    .round(4)
    .unstack("phase")
)
print(pivot.to_string())
print("\nNote: Higher relative_spread in phase2 vs phase1 indicates widening")
print("during the tariff shock. Cross-ticker comparison shows sector asymmetry.")


# ── Step 6: Spot check ────────────────────────────────────────────────────────

print("\n=== Spot check -- AAPL Liberation Day file ===")
sample = FEAT_DIR / "AAPL" / "phase2" / "AAPL_2025-04-02_2025-04-11.csv"
if sample.exists():
    df_check = pd.read_csv(sample)
    print(f"File  : {sample.name}")
    print(f"Shape : {df_check.shape}")
    print(f"\nNew columns added:")
    new_cols = ["spread", "relative_spread", "moneyness", "moneyness_pct",
                "moneyness_cat", "phase", "days_from_apr2"]
    print(df_check[new_cols].head(8).to_string())
    print(f"\ndays_from_apr2 range: {df_check['days_from_apr2'].min()} to {df_check['days_from_apr2'].max()}")
    print(f"phase value         : {df_check['phase'].iloc[0]}")
    print(f"moneyness_cat counts:")
    print(df_check["moneyness_cat"].value_counts().to_string())

print("\nFeature Engineering Complete. Feature-enriched files saved to data/features/")

