"""
scripts/scrape_options.py
=========================
Collects option chain snapshots for all tickers across all phases.

Usage:
    python scripts/scrape_options.py               # runs all phases
    python scripts/scrape_options.py --phase 2     # single phase
    python scripts/scrape_options.py --date 2025-04-02  # single date (all tickers)
    python scripts/scrape_options.py --resume      # skip already-collected files

Output:
    data/raw/options/{ticker}_{collection_date}_{expiry}.csv
    One file per ticker × collection_date × expiry.
    Both calls and puts are in each file (native API format, no splitting).

Credit cost (approximate):
    Phase 1: 11 weeks × 5 tickers × 4 expiries × 40 credits =  8,800
    Phase 2: 38 days  × 5 tickers × 4 expiries × 60 credits = 45,600  (strikeLimit=30)
    Phase 3: 34 weeks × 5 tickers × 4 expiries × 40 credits = 27,200
    Total: ~81,600 credits across ~9 API-days (10,000 credits/day limit)
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# Make project root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import cfg
from scripts.api_client import get_expirations, get_option_chain
from scripts.trading_calendar import get_collection_dates

# ── Logging ───────────────────────────────────────────────────────────────────
log_dir = Path(cfg["paths"]["logs"])
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "scrape_options.log"),
    ],
)
logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────
OUT_DIR = Path(cfg["paths"]["raw_options"])
OUT_DIR.mkdir(parents=True, exist_ok=True)


def pick_expiries(
    available: list[str],
    collection_date: str,
    target_dtes: list[int],
) -> list[str]:
    """
    From available expiry dates, select the one closest to each target DTE.
    Returns deduplicated sorted list.
    """
    ref = datetime.strptime(collection_date, "%Y-%m-%d")
    chosen = set()
    for dte in target_dtes:
        target_dt = ref + timedelta(days=dte)
        best = min(
            available,
            key=lambda e: abs(
                (datetime.strptime(e, "%Y-%m-%d") - target_dt).days
            ),
            default=None,
        )
        if best:
            chosen.add(best)
    return sorted(chosen)


def output_path(ticker: str, collection_date: str, expiry: str) -> Path:
    return OUT_DIR / f"{ticker}_{collection_date}_{expiry}.csv"


def already_collected(ticker: str, collection_date: str, expiry: str) -> bool:
    return output_path(ticker, collection_date, expiry).exists()


def chain_to_df(data: dict, ticker: str, collection_date: str) -> pd.DataFrame:
    """
    Convert raw API dict (parallel arrays) to a flat DataFrame.
    Adds collection_date and ticker columns.
    """
    # Remove status key before building DataFrame
    data = {k: v for k, v in data.items() if k != "s"}
    df = pd.DataFrame(data)
    df.insert(0, "ticker", ticker)
    df.insert(1, "collection_date", collection_date)
    return df


def collect_one(
    ticker: str,
    collection_date: str,
    strike_limit: int,
    target_dtes: list[int],
    resume: bool,
) -> int:
    """
    Collect all target expiries for one ticker on one date.
    Returns number of files saved.
    """
    available = get_expirations(ticker, collection_date)
    if not available:
        logger.warning(f"  [{ticker}] No expirations on {collection_date}")
        return 0

    expiries = pick_expiries(available, collection_date, target_dtes)
    saved = 0

    for expiry in expiries:
        if resume and already_collected(ticker, collection_date, expiry):
            logger.debug(f"  [{ticker}] Skip (exists): {collection_date} × {expiry}")
            continue

        logger.info(f"  [{ticker}] Fetching {collection_date} × {expiry} ...")
        data = get_option_chain(ticker, collection_date, expiry, strike_limit)

        if not data:
            logger.warning(f"  [{ticker}] Empty chain: {collection_date} × {expiry}")
            continue

        df = chain_to_df(data, ticker, collection_date)
        path = output_path(ticker, collection_date, expiry)
        df.to_csv(path, index=False)
        logger.info(f"  [{ticker}] Saved {len(df):>3} rows → {path.name}")
        saved += 1

    return saved


# ── Main runners ──────────────────────────────────────────────────────────────

def run_phase(phase_id: int, resume: bool = False):
    phases = cfg["collection"]["phases"]
    phase = next((p for p in phases if p["id"] == phase_id), None)
    if not phase:
        raise ValueError(f"Phase {phase_id} not found in config")

    tickers = [t["symbol"] for t in cfg["tickers"]]
    target_dtes = cfg["collection"]["target_dtes"]
    dates = get_collection_dates(phase)
    strike_limit = phase["strike_limit"]

    logger.info(
        f"\n{'='*60}\n"
        f"Phase {phase_id}: {phase['name']}\n"
        f"Dates: {dates[0]} → {dates[-1]}  ({len(dates)} collection days)\n"
        f"Tickers: {tickers}\n"
        f"Strike limit: {strike_limit}\n"
        f"{'='*60}"
    )

    total_files = 0
    for i, cdate in enumerate(dates, 1):
        logger.info(f"\n[{i}/{len(dates)}] {cdate}")
        for ticker in tickers:
            saved = collect_one(ticker, cdate, strike_limit, target_dtes, resume)
            total_files += saved

    logger.info(f"\nPhase {phase_id} complete. {total_files} files saved.")


def run_single_date(date_str: str, resume: bool = False):
    """Collect all tickers for a specific date, using the appropriate phase config."""
    phases = cfg["collection"]["phases"]
    tickers = [t["symbol"] for t in cfg["tickers"]]
    target_dtes = cfg["collection"]["target_dtes"]

    # Find which phase this date belongs to
    phase = None
    for p in phases:
        if p["start"] <= date_str <= p["end"]:
            phase = p
            break
    if not phase:
        # Default to phase 2 strike limit if date outside defined phases
        strike_limit = 20
        logger.warning(f"{date_str} is outside defined phases — using strikeLimit=20")
    else:
        strike_limit = phase["strike_limit"]

    logger.info(f"Single date: {date_str}  strikeLimit={strike_limit}")
    for ticker in tickers:
        collect_one(ticker, date_str, strike_limit, target_dtes, resume)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect option chain snapshots")
    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3],
        help="Run a specific phase (1, 2, or 3). Omit to run all.",
    )
    parser.add_argument(
        "--date", type=str,
        help="Collect a single date (YYYY-MM-DD) for all tickers.",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip files that already exist in the output directory.",
    )
    args = parser.parse_args()

    if args.date:
        run_single_date(args.date, resume=args.resume)
    elif args.phase:
        run_phase(args.phase, resume=args.resume)
    else:
        # Run all phases in sequence
        for phase_id in [1, 2, 3]:
            run_phase(phase_id, resume=args.resume)