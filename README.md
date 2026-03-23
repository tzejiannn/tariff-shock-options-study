# Tariff Shock Option Microstructure Study
### Cross-sector analysis of the 2025 US tariff event through options market data

---

## Research question

*Did the 2025 tariff shock produce asymmetric implied volatility and liquidity responses across sectors, and does the option market microstructure signal which sectors the market treated as structurally damaged versus temporarily disrupted?*

---

## Tickers and sectors

| Ticker | Sector | Rationale |
|--------|--------|-----------|
| AAPL | Technology | Indirect tariff exposure via supply chain |
| NVDA | Semiconductors | Direct chip export restriction exposure |
| AMZN | Consumer Discretionary | Supply chain + consumer spending exposure |
| PG | Consumer Staples | Defensive FMCG, low beta, expected contrast case |
| CAT | Industrials | Heavy machinery, large China revenue, direct exposure |

---

## Study timeline

| Phase | Period | Frequency | Strike limit | Purpose |
|-------|--------|-----------|--------------|---------|
| 1 — Baseline | Mar 24 → Apr 1 2025 | Daily | 20 | Pre-shock microstructure regime |
| 2 — Event window | Apr 2 → May 9 2025 | Daily | 30 | Shock, escalation, and pause |
| 3 — Recovery | May 12 2025 → Jan 16 2026 | Weekly | 20 | Regime normalisation per sector |

> **Note on AAPL:** AAPL is whitelisted on the Market Data App free/trial tier with no
> historical lookback restriction. AAPL data has been collected from Jan 6 2025 as an
> extended baseline. All cross-sector comparisons use the common window from Mar 24 2025
> onwards to ensure fair comparison across all five tickers.

### Key event dates
- **Apr 2 2025** — Liberation Day: sweeping tariffs announced on ~60 countries
- **Apr 9 2025** — Tariff escalation for 57 partners + 90-day pause announced same day
- **May 12 2025** — US-China truce: 90-day tariff reduction agreement

---

## API limitation notice

Data is sourced from [Market Data App](https://www.marketdata.app/).

**Trial / Starter plan restriction:** Historical options data for non-AAPL tickers is
limited to 1 year of lookback from the current date. This means:

- AAPL data is available from Jan 6 2025 (extended free tier)
- NVDA, AMZN, PG, CAT data is available from Mar 24 2025 onwards only
- All cross-sector analysis uses Mar 24 2025 as the common start date
- The `strikeLimit` parameter controls credits consumed per request —
  each option symbol returned costs 1 credit (10,000 credits/day on Starter plan)

---

## Setup

```bash
git clone <your-repo>
cd tariff-shock-options-study
pip install -r requirements.txt
```

Edit `config/settings.yaml` and paste your Market Data App API token:
```yaml
api:
  token: "YOUR_API_TOKEN_HERE"
```

---

## Data collection

Run from the project root. The `--resume` flag skips files already collected
so interrupted runs can be safely restarted without re-spending credits.

```bash
# Step 1: Fetch daily OHLCV prices for all tickers (5 credits total, run once)
python scripts/scrape_prices.py

# Step 2: Collect option chains per phase
# Phase 1 — ~1,600 credits, completes in one run
python scripts/scrape_options.py --phase 1 --resume

# Phase 2 — ~45,600 credits, spread across 5 days (10,000 credit daily limit)
python scripts/scrape_options.py --phase 2 --resume   # run each day until complete

# Phase 3 — ~27,200 credits, spread across 3 days
python scripts/scrape_options.py --phase 3 --resume

# Collect a single date (useful for testing or backfilling a missed date)
python scripts/scrape_options.py --date 2025-04-02
```

---

## Project structure

```
tariff-shock-options-study/
|
+-- config/
|   +-- settings.yaml              # Single source of truth: tickers, phases, paths
|   +-- loader.py                  # Config loader imported by all scripts
|   +-- __init__.py
|
+-- scripts/
|   +-- api_client.py              # Market Data App HTTP wrapper (auth, retries, 2xx)
|   +-- trading_calendar.py        # US trading day generation with NYSE holidays
|   +-- scrape_options.py          # Option chain collection across all phases
|   +-- scrape_prices.py           # Daily OHLCV price collection
|   +-- __init__.py
|
+-- data/
|   +-- raw/
|   |   +-- options/
|   |   |   +-- AAPL/
|   |   |   |   +-- phase1/        # AAPL_2025-01-06_2025-02-07.csv etc.
|   |   |   |   +-- phase2/        # AAPL_2025-04-02_2025-04-17.csv etc.
|   |   |   |   +-- phase3/
|   |   |   +-- NVDA/
|   |   |   |   +-- phase1/        # starts 2025-03-24 (1-year limit)
|   |   |   |   +-- phase2/
|   |   |   |   +-- phase3/
|   |   |   +-- AMZN/
|   |   |   |   +-- phase1/
|   |   |   |   +-- phase2/
|   |   |   |   +-- phase3/
|   |   |   +-- PG/
|   |   |   |   +-- phase1/
|   |   |   |   +-- phase2/
|   |   |   |   +-- phase3/
|   |   |   +-- CAT/
|   |   |       +-- phase1/
|   |   |       +-- phase2/
|   |   |       +-- phase3/
|   |   +-- prices/
|   |       +-- AAPL_daily_prices.csv
|   |       +-- NVDA_daily_prices.csv
|   |       +-- AMZN_daily_prices.csv
|   |       +-- PG_daily_prices.csv
|   |       +-- CAT_daily_prices.csv
|   |
|   +-- clean/                     # Cleaned + feature-engineered CSVs
|   +-- combined/                  # Master combined datasets (all tickers, all phases)
|
+-- notebooks/
|   +-- EDA.ipynb                  # Full analysis notebook
|
+-- logs/
|   +-- scrape_options.log
|   +-- scrape_prices.log
|
+-- requirements.txt
+-- setup.py
+-- README.md
```

### File naming convention

Option chain files follow the pattern:

```
{ticker}_{collection_date}_{expiry_date}.csv
```

For example, `AAPL_2025-04-02_2025-04-17.csv` contains the AAPL option chain
as observed on April 2 2025, for contracts expiring April 17 2025.
Each file contains both calls and puts (native Market Data App format, no splitting).