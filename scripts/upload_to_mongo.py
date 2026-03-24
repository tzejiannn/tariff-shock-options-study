"""
Upload all processed data to MongoDB Atlas.

What this script does:
    - Reads all cleaned CSVs from data/clean/
    - Reads all feature-engineered CSVs from data/features/ (if they exist)
    - Reads price CSVs from data/raw/prices/
    - Upserts everything into MongoDB Atlas:
        options_clean    <- from data/clean/
        options_features <- from data/features/
        prices           <- from data/raw/prices/

Idempotent:
    Re-running this script updates existing documents rather than creating
    duplicates. Safe to run again after any pipeline step adds new data.

Prerequisites:
    1. pip install "pymongo[srv]" python-dotenv
    2. Create .env in the project root:
       MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/tariff_study?retryWrites=true&w=majority
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pymongo import UpdateOne

# Make sure the project root is on sys.path so we can import db.mongo
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.mongo import ensure_indexes, get_collection

TICKERS = ["AAPL", "NVDA", "AMZN", "PG", "CAT"]
PHASES  = ["phase1", "phase2", "phase3"]

CLEAN_DIR    = PROJECT_ROOT / "data" / "clean"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"
PRICES_DIR   = PROJECT_ROOT / "data" / "raw" / "prices"

# Number of documents sent to MongoDB per network round-trip.
# 500 is a safe default -- large enough to be fast, small enough
# to avoid hitting BSON document size limits.
BATCH_SIZE = 500


# ── Step 1: Value sanitisation ─────────────────────────────────────────────────

def sanitise_value(v):
    """
    Convert a single value to a MongoDB-safe Python type.

    MongoDB stores data as BSON (Binary JSON). BSON does not support:
    - float NaN or Infinity  -> we convert these to None (BSON null)
    - pandas Timestamp       -> we convert to Python datetime
    - pandas NA / NaT        -> we convert to None
    - numpy int64 / float64  -> we convert to native Python int / float

    Why native Python types?
        pymongo can handle numpy scalars in modern versions, but converting
        to native types is safer across all environments and avoids subtle
        issues when using MongoDB tools that inspect the raw BSON.
    """
    # pandas NA (nullable integer/boolean missing value) and NaT
    if v is pd.NA or v is pd.NaT:
        return None

    # pandas Timestamp -> Python datetime
    # pd.isnull(v) catches NaT before .to_pydatetime() is called
    if isinstance(v, pd.Timestamp):
        return None if pd.isnull(v) else v.to_pydatetime()

    # float NaN and Infinity -- neither is valid BSON
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None

    # numpy integer types (int8, int16, int32, int64, etc.)
    if isinstance(v, np.integer):
        return int(v)

    # numpy float types
    if isinstance(v, np.floating):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f

    # numpy bool_ (distinct from Python bool)
    if isinstance(v, np.bool_):
        return bool(v)

    return v


def df_to_docs(df: pd.DataFrame) -> list[dict]:
    """
    Convert a DataFrame to a list of MongoDB-compatible documents.

    Each row becomes one document (Python dict). All values are passed
    through sanitise_value() to make them BSON-safe.

    Why not df.to_dict(orient="records") directly?
        That preserves pandas/numpy types that pymongo cannot serialise
        (NaN, Timestamp, numpy scalars), causing insert errors. We need
        the explicit conversion step.
    """
    return [
        {k: sanitise_value(v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


# ── Step 2: Upsert helper ──────────────────────────────────────────────────────

def upsert_docs(collection, docs: list[dict], key_fields: list[str]) -> dict:
    """
    Upsert a list of documents into a MongoDB collection in batches.

    Upsert means:
        - If a document matching key_fields already exists -> UPDATE it
        - If no match is found -> INSERT a new document

    This makes the upload script idempotent. Running it twice does not
    produce duplicate documents; the second run simply overwrites the
    existing ones with the same data.

    bulk_write sends all operations in a single network round-trip per
    batch, which is far faster than one request per document.

    ordered=False means if one operation fails in a batch, the rest
    of the batch still runs. This is important for large uploads where
    a single bad document should not block thousands of good ones.

    Returns a dict with upserted and modified counts.
    """
    total_upserted = 0
    total_modified = 0

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        ops = [
            UpdateOne(
                filter={k: doc[k] for k in key_fields},
                update={"$set": doc},
                upsert=True,
            )
            for doc in batch
        ]
        result = collection.bulk_write(ops, ordered=False)
        total_upserted += result.upserted_count
        total_modified += result.modified_count

    return {"upserted": total_upserted, "modified": total_modified}


# ── Step 3: Upload options CSVs ────────────────────────────────────────────────

def upload_options(source_dir: Path, collection_name: str) -> int:
    """
    Upload all options CSVs from source_dir to a MongoDB collection.

    Scans source_dir/{ticker}/phase{N}/ for CSV files, reads each one,
    converts to documents, and upserts to MongoDB.

    The upsert key is (optionSymbol, collection_date):
        - optionSymbol is the OCC identifier: encodes ticker, expiry,
          side, and strike. Example: AAPL250417C00200000 is the AAPL
          $200 call expiring April 17 2025.
        - collection_date is the date the snapshot was taken.
        Together these uniquely identify one row -- one contract on
        one day. No two rows should share both values.

    Returns total rows processed.
    """
    if not source_dir.exists():
        print(f"  {collection_name}: {source_dir.name}/ not found -- skipping")
        return 0

    collection = get_collection(collection_name)

    all_files = []
    for ticker in TICKERS:
        for phase in PHASES:
            folder = source_dir / ticker / phase
            if not folder.exists():
                continue
            for csv in sorted(folder.glob("*.csv")):
                all_files.append({"ticker": ticker, "phase": phase, "path": csv})

    if not all_files:
        print(f"  {collection_name}: no CSV files found -- skipping")
        return 0

    print(f"  {collection_name}: {len(all_files)} files found")

    total_rows = 0
    for i, entry in enumerate(all_files, 1):
        df = pd.read_csv(
            entry["path"],
            parse_dates=["collection_date", "expiration", "firstTraded", "updated"],
        )
        docs  = df_to_docs(df)
        stats = upsert_docs(collection, docs, key_fields=["optionSymbol", "collection_date"])
        total_rows += len(docs)

        # Print progress every 50 files and on the last file
        if i % 50 == 0 or i == len(all_files):
            print(
                f"    [{i}/{len(all_files)}] {entry['ticker']} {entry['phase']}"
                f" -- {len(docs)} rows"
                f" (upserted {stats['upserted']}, modified {stats['modified']})"
            )

    return total_rows


# ── Step 4: Upload prices ──────────────────────────────────────────────────────

def upload_prices() -> int:
    """
    Upload all price CSVs from data/raw/prices/ to the prices collection.

    Price data is a simple daily OHLCV table -- one row per ticker per date.
    The upsert key is (ticker, date) since there is exactly one price
    record per stock per trading day.

    Returns total rows processed.
    """
    if not PRICES_DIR.exists():
        print("  prices: data/raw/prices/ not found -- skipping")
        return 0

    collection   = get_collection("prices")
    price_files  = sorted(PRICES_DIR.glob("*_daily_prices.csv"))

    if not price_files:
        print("  prices: no price CSV files found -- skipping")
        return 0

    print(f"  prices: {len(price_files)} files found")

    total_rows = 0
    for csv in price_files:
        df    = pd.read_csv(csv, parse_dates=["date"])
        docs  = df_to_docs(df)
        stats = upsert_docs(collection, docs, key_fields=["ticker", "date"])
        total_rows += len(docs)
        print(
            f"    {csv.name} -- {len(docs)} rows"
            f" (upserted {stats['upserted']}, modified {stats['modified']})"
        )

    return total_rows


# ── Step 5: Main ───────────────────────────────────────────────────────────────

print("=== MongoDB Atlas Upload ===\n")
print("Connecting and ensuring indexes...")

try:
    ensure_indexes()
except Exception as e:
    print(f"\nERROR: Could not connect to MongoDB Atlas.\n{e}")
    print("\nCheck that MONGO_URI is set correctly in your .env file.")
    sys.exit(1)

print("\n-- options_clean --")
n_clean = upload_options(CLEAN_DIR, "options_clean")

print("\n-- options_features --")
n_features = upload_options(FEATURES_DIR, "options_features")

print("\n-- prices --")
n_prices = upload_prices()

print("\n=== Upload Complete ===")
print(f"  options_clean    : {n_clean:,} rows")
print(f"  options_features : {n_features:,} rows")
print(f"  prices           : {n_prices:,} rows")
print("\nData is now in MongoDB Atlas under the 'tariff_study' database.")
