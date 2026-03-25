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
RV_WINDOW  = 20      # trading days in a month


rv_frames = []
for ticker in TICKERS:
    price_file = PRICES_DIR / f"{ticker}_daily_prices.csv"
    if not price_file.exists():
        print(f"  [{ticker}] Price file not found -- skipping")
        continue

    df = pd.read_csv(price_file, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["realised_vol"] = (
        df["log_return"]
        .rolling(window=RV_WINDOW, min_periods=RV_WINDOW)
        .std()
        * np.sqrt(252) # Multiplying by sqrt(252) annualises the daily standard deviation.
    )

    # Keep only the columns needed for the merge downstream
    rv_df = df[["ticker", "date", "close", "realised_vol"]].copy()

    # Save standalone RV file
    out_path = RV_DIR / f"{ticker}_rv.csv"
    rv_df.to_csv(out_path, index=False)
    rv_frames.append(rv_df)

# Combine all tickers into one dataframe
rv_all = pd.concat(rv_frames, ignore_index=True)


# Merge Step
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

def merge_rv(df_opts: pd.DataFrame, rv_lookup: pd.DataFrame) -> pd.DataFrame:
    # Rename 'date' to 'collection_date' so the merge key matches
    rv_keyed = rv_lookup.rename(columns={"date": "collection_date"})[
        ["ticker", "collection_date", "realised_vol"]
    ]

    return df_opts.merge(rv_keyed, on=["ticker", "collection_date"], how="left")


for entry in feat_files:
    raw_path = entry["path"]
    ticker   = entry["ticker"]
    phase    = entry["phase"]

    df = pd.read_csv(raw_path, parse_dates=["collection_date", "expiration"])

    rv_ticker = rv_all[rv_all["ticker"] == ticker].copy()
    df_enriched = merge_rv(df, rv_ticker)
    out_folder = ENRICHED_DIR / ticker / phase
    out_folder.mkdir(parents=True, exist_ok=True)
    out_path = out_folder / raw_path.name
    df_enriched.to_csv(out_path, index=False)

print("RV added data saved to data/enriched/")


# Spot check one enriched file to ensure RV merged correctly.
# print("\n=== Spot check -- AAPL Liberation Day enriched file ===")
# sample = ENRICHED_DIR / "AAPL" / "phase2" / "AAPL_2025-04-02_2025-04-11.csv"
# if sample.exists():
#    df_check = pd.read_csv(sample)
#    print(f"File  : {sample.name}")
#    print(f"Shape : {df_check.shape}")
#    print(f"\nNew columns:")
#    new_cols = ["collection_date", "ticker", "side", "strike",
#                "relative_spread", "realised_vol"]
#    print(df_check[new_cols].head(6).to_string())
#    rv_val = df_check["realised_vol"].iloc[0]
#    print(f"\nAAPL realised_vol on 2025-04-02: {rv_val:.4f} ({rv_val*100:.2f}% annualised)")


