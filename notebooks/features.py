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


# Feature Engineering Functions

#Absolute Spread
def add_spread(df: pd.DataFrame) -> pd.DataFrame:
    df["spread"] = df["ask"] - df["bid"]
    mid_safe = df["mid"].replace(0, np.nan)
    df["relative_spread"] = df["spread"] / mid_safe

    return df


# Moneyness
def add_moneyness(df: pd.DataFrame) -> pd.DataFrame:
    spot = df["underlyingPrice"]

    df["moneyness"]     = df["strike"] / spot
    df["moneyness_pct"] = (df["strike"] - spot) / spot * 100

    upper = spot * (1 + ATM_BAND)
    lower = spot * (1 - ATM_BAND)
    call_mask = df["side"] == "call"
    put_mask  = df["side"] == "put"
    df["moneyness_cat"] = "ATM"

    # Calls
    df.loc[call_mask & (df["strike"] < lower), "moneyness_cat"] = "ITM"
    df.loc[call_mask & (df["strike"] > upper), "moneyness_cat"] = "OTM"

    # Puts
    df.loc[put_mask  & (df["strike"] > upper), "moneyness_cat"] = "ITM"
    df.loc[put_mask  & (df["strike"] < lower), "moneyness_cat"] = "OTM"

    return df

# Phase Number Column
def add_phase(df: pd.DataFrame, phase_label: str) -> pd.DataFrame:
    df["phase"] = int(phase_label.replace("phase", ""))
    return df

# Days from Event
def add_days_from_apr2(df: pd.DataFrame) -> pd.DataFrame:

    df["days_from_apr2"] = (
        df["collection_date"] - LIBERATION_DAY
    ).dt.days
    return df


# Apply Feature Engineering Functions
def engineer_features(df: pd.DataFrame, phase_label: str) -> pd.DataFrame:
    df = add_spread(df)
    df = add_moneyness(df)
    df = add_phase(df, phase_label)
    df = add_days_from_apr2(df)
    return df


# Check features dont' violate assumptions
def validate_features(df: pd.DataFrame, filename: str) -> list:

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


# Apply Feature Engineering Functions to Data
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


# Validation Check
print(f"\nValidation warnings: {len(total_warnings)}")
if total_warnings:
    for w in total_warnings:
        print(w)
else:
    print("No warnings -- all feature checks passed.")

print("\nFeature Engineering Complete.")


#Check one sample file to ensure correct features engineered:

#sample = FEAT_DIR / "AAPL" / "phase2" / "AAPL_2025-04-02_2025-04-11.csv"
#if sample.exists():
#    df_check = pd.read_csv(sample)
#    print(f"File  : {sample.name}")
#    print(f"Shape : {df_check.shape}")
#    print(f"\nNew columns added:")
#    new_cols = ["spread", "relative_spread", "moneyness", "moneyness_pct",
#                "moneyness_cat", "phase", "days_from_apr2"]
#    print(df_check[new_cols].head(8).to_string())
#    print(f"\ndays_from_apr2 range: {df_check['days_from_apr2'].min()} to {df_check['days_from_apr2'].max()}")
#    print(f"phase value         : {df_check['phase'].iloc[0]}")
#    print(f"moneyness_cat counts:")
#    print(df_check["moneyness_cat"].value_counts().to_string())



