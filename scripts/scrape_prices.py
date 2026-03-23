"""
scripts/scrape_prices.py
========================
Fetches daily OHLCV price data for all tickers for the full study window.
Used to compute realised volatility (RV), variance risk premium, and
underlying price context for the options analysis.

One API call per ticker — extremely cheap (5 credits total).

Usage:
    python scripts/scrape_prices.py

Output:
    data/raw/prices/{ticker}_daily_prices.csv
    Columns: ticker, date, open, high, low, close, volume
"""

import sys
import logging
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.load_settings import cfg
from scripts.api_marketdata import get_stock_candles

# ── Logging ───────────────────────────────────────────────────────────────────
log_dir = Path(cfg["paths"]["logs"])
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "scrape_prices.log"),
    ],
)
logger = logging.getLogger(__name__)

OUT_DIR = Path(cfg["paths"]["raw_prices"])
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Full window: start of Phase 1 to end of Phase 3
# Fetch slightly earlier to allow 20-day RV lookback from Phase 1 start
PRICE_START = "2024-12-01"
PRICE_END   = "2026-01-16"


def fetch_prices(ticker: str) -> pd.DataFrame:
    data = get_stock_candles(ticker, PRICE_START, PRICE_END)
    if not data:
        logger.warning(f"[{ticker}] No price data returned")
        return pd.DataFrame()

    df = pd.DataFrame({
        "date":   data.get("t", []),
        "open":   data.get("o", []),
        "high":   data.get("h", []),
        "low":    data.get("l", []),
        "close":  data.get("c", []),
        "volume": data.get("v", []),
    })

    df["ticker"] = ticker
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    # Compute log returns immediately
    df["log_return"] = df["close"].apply(lambda x: x).pct_change().apply(
        lambda r: __import__("math").log(1 + r) if r == r else float("nan")
    )

    return df[["ticker", "date", "open", "high", "low", "close", "volume", "log_return"]]


def main():
    tickers = [t["symbol"] for t in cfg["tickers"]]
    logger.info(f"Fetching daily prices for: {tickers}")
    logger.info(f"Window: {PRICE_START} → {PRICE_END}")

    for ticker in tickers:
        logger.info(f"  [{ticker}] Fetching...")
        df = fetch_prices(ticker)
        if df.empty:
            continue
        path = OUT_DIR / f"{ticker}_daily_prices.csv"
        df.to_csv(path, index=False)
        logger.info(f"  [{ticker}] Saved {len(df)} rows → {path.name}")

    logger.info("\nPrice collection complete.")


if __name__ == "__main__":
    main()