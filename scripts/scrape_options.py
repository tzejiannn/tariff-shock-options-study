"""
scripts/scrape_options.py
=========================
Collects option chain snapshots for all tickers across all phases.

Output structure:
    data/raw/options/{ticker}/phase{N}/{ticker}_{collection_date}_{expiry}.csv

Usage:
    python scripts/scrape_options.py --phase 1 --resume
    python scripts/scrape_options.py --phase 2 --resume
    python scripts/scrape_options.py --phase 3 --resume
    python scripts/scrape_options.py --date 2025-04-02
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.load_settings import cfg
from scripts.api_marketdata import get_expirations, get_option_chain
from scripts.trading_calendar import get_collection_dates

# -- Logging --
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

OUT_DIR = Path(cfg["paths"]["raw_options"])
OUT_DIR.mkdir(parents=True, exist_ok=True)


def pick_expiries(available, collection_date, target_dtes):
    ref = datetime.strptime(collection_date, "%Y-%m-%d")
    chosen = set()
    for dte in target_dtes:
        target_dt = ref + timedelta(days=dte)
        best = min(
            available,
            key=lambda e: abs((datetime.strptime(e, "%Y-%m-%d") - target_dt).days),
            default=None,
        )
        if best:
            chosen.add(best)
    return sorted(chosen)


def output_path(ticker, collection_date, expiry, phase_id):
    folder = OUT_DIR / ticker / f"phase{phase_id}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{ticker}_{collection_date}_{expiry}.csv"


def already_collected(ticker, collection_date, expiry, phase_id):
    return output_path(ticker, collection_date, expiry, phase_id).exists()


def chain_to_df(data, ticker, collection_date):
    data = {k: v for k, v in data.items() if k != "s"}
    df = pd.DataFrame(data)
    df.insert(0, "ticker", ticker)
    df.insert(1, "collection_date", collection_date)
    return df


def collect_one(ticker, collection_date, strike_limit, target_dtes, phase_id, resume):
    available = get_expirations(ticker, collection_date)
    if not available:
        logger.warning(f"  [{ticker}] No expirations on {collection_date}")
        return 0

    expiries = pick_expiries(available, collection_date, target_dtes)
    saved = 0

    for expiry in expiries:
        if resume and already_collected(ticker, collection_date, expiry, phase_id):
            logger.debug(f"  [{ticker}] Skip (exists): {collection_date} x {expiry}")
            continue

        logger.info(f"  [{ticker}] Fetching {collection_date} x {expiry} ...")
        data = get_option_chain(ticker, collection_date, expiry, strike_limit)

        if not data:
            logger.warning(f"  [{ticker}] Empty chain: {collection_date} x {expiry}")
            continue

        df = chain_to_df(data, ticker, collection_date)
        path = output_path(ticker, collection_date, expiry, phase_id)
        df.to_csv(path, index=False)
        logger.info(f"  [{ticker}] Saved {len(df):>3} rows -> {path.parent.parent.name}/{path.parent.name}/{path.name}")
        saved += 1

    return saved


def run_phase(phase_id, resume=False):
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
        f"Dates: {dates[0]} -> {dates[-1]}  ({len(dates)} collection days)\n"
        f"Tickers: {tickers}\n"
        f"Strike limit: {strike_limit}\n"
        f"{'='*60}"
    )

    total_files = 0
    for i, cdate in enumerate(dates, 1):
        logger.info(f"\n[{i}/{len(dates)}] {cdate}")
        for ticker in tickers:
            saved = collect_one(ticker, cdate, strike_limit, target_dtes, phase_id, resume)
            total_files += saved

    logger.info(f"\nPhase {phase_id} complete. {total_files} files saved.")


def run_single_date(date_str, resume=False):
    phases = cfg["collection"]["phases"]
    tickers = [t["symbol"] for t in cfg["tickers"]]
    target_dtes = cfg["collection"]["target_dtes"]

    phase = None
    for p in phases:
        if p["start"] <= date_str <= p["end"]:
            phase = p
            break

    if not phase:
        strike_limit = 20
        phase_id = 0
        logger.warning(f"{date_str} is outside defined phases - using strikeLimit=20")
    else:
        strike_limit = phase["strike_limit"]
        phase_id = phase["id"]

    logger.info(f"Single date: {date_str}  strikeLimit={strike_limit}")
    for ticker in tickers:
        collect_one(ticker, date_str, strike_limit, target_dtes, phase_id, resume)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect option chain snapshots")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3])
    parser.add_argument("--date", type=str)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.date:
        run_single_date(args.date, resume=args.resume)
    elif args.phase:
        run_phase(args.phase, resume=args.resume)
    else:
        for phase_id in [1, 2, 3]:
            run_phase(phase_id, resume=args.resume)