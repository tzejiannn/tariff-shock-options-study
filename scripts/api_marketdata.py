"""
Handles:
  - Auth headers
  - 2xx acceptance (API returns 203 for real-time/paid data)
  - Rate limit retries (429)
  - Structured logging of every request
"""
import time
import logging
import requests
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.loader import cfg

logger = logging.getLogger(__name__)

_API_CFG  = cfg["api"]
BASE_URL  = _API_CFG["base_url"]
TOKEN     = _API_CFG["token"]
DELAY     = _API_CFG["request_delay"]
RETRIES   = _API_CFG["retry_attempts"]
BACKOFF   = _API_CFG["retry_backoff"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _get(endpoint: str, params: dict) -> Optional[dict]:
    """
    Make a GET request to BASE_URL/endpoint with params.
    Returns parsed JSON on success, None on failure.
    Retries up to RETRIES times on 429 or 5xx.
    Accepts any 2xx status (200 and 203 both indicate success).
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"

    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=_headers(),
                params=params,
                timeout=30,
            )
        except requests.RequestException as e:
            logger.warning(f"Request error (attempt {attempt}): {e}")
            time.sleep(BACKOFF)
            continue

        # Rate limit
        if resp.status_code == 429:
            logger.warning(f"Rate limit hit — sleeping {BACKOFF}s (attempt {attempt})")
            time.sleep(BACKOFF)
            continue

        # Server error — retry
        if resp.status_code >= 500:
            logger.warning(f"Server error {resp.status_code} (attempt {attempt})")
            time.sleep(10)
            continue

        # Any 2xx is success (203 = non-authoritative / real-time on paid plans)
        if 200 <= resp.status_code < 300:
            data = resp.json()
            if data.get("s") == "ok":
                return data
            elif data.get("s") == "no_data":
                logger.debug(f"no_data from API: {url} params={params}")
                return None
            else:
                logger.warning(f"Unexpected API status '{data.get('s')}': {url}")
                return None

        # 4xx (not 429) — don't retry
        logger.error(f"HTTP {resp.status_code}: {url} — {resp.text[:200]}")
        return None

        time.sleep(DELAY)

    logger.error(f"All {RETRIES} attempts failed for {url}")
    return None


# Public API Functions

def get_expirations(ticker: str, date: str) -> list[str]:
    """
    Fetch available expiration dates for ticker on a given historical date.
    Returns list of 'YYYY-MM-DD' strings sorted ascending.
    Cost: 1 credit.
    """
    data = _get(
        f"options/expirations/{ticker}/",
        {"date": date, "dateformat": "timestamp"},
    )
    if not data:
        return []

    expirations = data.get("expirations", [])
    result = []
    for e in expirations:
        # API returns unix timestamps when dateformat=timestamp
        from datetime import datetime, timezone
        if isinstance(e, (int, float)):
            dt = datetime.fromtimestamp(e, tz=timezone.utc)
            result.append(dt.strftime("%Y-%m-%d"))
        else:
            result.append(str(e)[:10])

    time.sleep(DELAY)
    return sorted(result)


def get_option_chain(
    ticker: str,
    collection_date: str,
    expiry: str,
    strike_limit: int,
) -> Optional[dict]:
    """
    Fetch the full option chain (both sides) for one expiry.
    Returns raw API dict with parallel arrays, or None.
    Cost: ~strike_limit * 2 credits.
    """
    data = _get(
        f"options/chain/{ticker}/",
        {
            "date":        collection_date,
            "expiration":  expiry,
            "strikeLimit": strike_limit,
            "dateformat":  "timestamp",
        },
    )
    time.sleep(DELAY)
    return data


def get_stock_candles(ticker: str, start: str, end: str) -> Optional[dict]:
    """
    Fetch daily OHLCV candles for ticker between start and end.
    Returns raw API dict with parallel arrays o/h/l/c/v/t, or None.
    Cost: 1 credit per ticker for full date range.
    """
    data = _get(
        f"stocks/candles/D/{ticker}/",
        {
            "from":       start,
            "to":         end,
            "dateformat": "timestamp",
        },
    )
    time.sleep(DELAY)
    return data