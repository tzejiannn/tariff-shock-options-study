# Tariff Shock Option Microstructure Study
### Cross-sector analysis of the 2025 US tariff event through options market data

---

## Research question

*Did the 2025 tariff shock produce asymmetric implied volatility and liquidity responses
across sectors, and does the option market microstructure signal which sectors the market
treated as structurally damaged versus temporarily disrupted?*

---

## Tickers and sectors

| Ticker | Sector | Tariff exposure |
|--------|--------|-----------------|
| AAPL | Technology | Indirect — supply chain dependency on China |
| NVDA | Semiconductors | Direct — chip export restrictions |
| AMZN | Consumer Discretionary | Supply chain + consumer spending sensitivity |
| PG | Consumer Staples | Defensive FMCG, low beta, expected contrast case |
| CAT | Industrials | Heavy machinery, large China revenue, direct exposure |

---

## Study timeline

| Phase | Period | Frequency | Strike limit | Purpose |
|-------|--------|-----------|--------------|---------|
| 1 — Baseline | Mar 24 -> Apr 1 2025 | Daily | 20 | Pre-shock microstructure regime |
| 2 — Event window | Apr 2 -> May 9 2025 | Daily | 30 | Shock, escalation, and pause |
| 3 — Recovery | May 12 2025 -> Jan 16 2026 | Weekly | 20 | Regime normalisation per sector |

> **AAPL extended baseline:** AAPL is whitelisted on Market Data App with no historical
> lookback restriction. AAPL data was collected from Jan 6 2025 as an extended baseline.
> All cross-sector comparisons use Mar 24 2025 as the common start date to ensure fairness.

### Key event dates

| Date | Event |
|------|-------|
| Apr 2 2025 | Liberation Day — sweeping tariffs announced on ~60 countries |
| Apr 9 2025 | Tariff escalation for 57 partners + 90-day pause announced same day |
| May 12 2025 | US-China truce — 90-day tariff reduction agreement |

---

## API and data source

Data is collected from [Market Data App](https://www.marketdata.app/).

### Plan limitations (Starter trial)

- **Credits:** 10,000 per day, resetting at 9:30 AM ET
- **Historical lookback:** 1 year from today for non-AAPL tickers
- **Greeks and IV:** Not included on the Starter plan — iv, delta, gamma, theta,
  vega columns will be present but entirely null
- **Credit cost:** Each option symbol returned consumes 1 credit. With
  `strikeLimit=20`, each expiry fetch costs ~40 credits (20 calls + 20 puts)

### How credits are spent

```
Phase 1: ~7 days  x 5 tickers x 4 expiries x ~30 credits =  ~4,200 credits
Phase 2: 28 days  x 5 tickers x 4 expiries x ~50 credits = ~28,000 credits
Phase 3: 34 weeks x 5 tickers x 4 expiries x ~30 credits = ~20,400 credits
Total:  ~52,600 credits across ~6 API days
```

---

## Setup

### 1. Clone and install

```powershell
git clone <your-repo>
cd tariff-shock-options-study
pip install -r requirements.txt
```

### 2. Make the project importable

Run once from the project root. This lets all scripts import from `config/`
and `scripts/` without path errors:

```powershell
pip install -e .
```

If that fails, set PYTHONPATH permanently instead:

```powershell
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\path\to\tariff-shock-options-study", "User")
```

Then close and reopen your terminal.

Also ensure these two empty files exist — Python needs them to treat the
folders as packages:

```
config/__init__.py     (empty file)
scripts/__init__.py    (empty file)
```

### 3. Add your API token

Edit `config/settings.yaml` and paste your Market Data App token:

```yaml
api:
  token: "YOUR_API_TOKEN_HERE"
```

Never commit your token to GitHub.

---

## Data collection

Always run from the project root. The `--resume` flag skips files already
collected so interrupted runs restart safely without re-spending credits.

### Step 1 — Fetch daily prices (run once, 5 credits total)

```powershell
python scripts/scrape_prices.py
```

Fetches daily OHLCV candles for all 5 tickers from Dec 2024 to Jan 2026.
Used later to compute realised volatility and the variance risk premium.

### Step 2 — Collect option chains

Run one phase per day to stay within the 10,000 credit daily limit.
Re-run the same command each day — `--resume` picks up where it left off.

```powershell
# Phase 1 -- ~4,200 credits, finishes in one run
python scripts/scrape_options.py --phase 1 --resume

# Phase 2 -- ~28,000 credits, spread across 3 days
python scripts/scrape_options.py --phase 2 --resume

# Phase 3 -- ~20,400 credits, spread across 3 days
python scripts/scrape_options.py --phase 3 --resume
```

### Backfilling a missed date

If a specific date failed or is missing, collect just that date:

```powershell
python scripts/scrape_options.py --date 2025-04-09
```

### Verifying your collection

Check the log for errors:

```powershell
findstr "ERROR" logs\scrape_options.log
findstr "2025-04-02" logs\scrape_options.log
```

---

## File naming convention

Option chain files follow the pattern:

```
{ticker}_{collection_date}_{expiry_date}.csv
```

Example: `AAPL_2025-04-02_2025-04-17.csv`
- Collected on April 2 2025 (Liberation Day)
- Contracts expiring April 17 2025
- Contains both calls and puts (native API format, no splitting)

Each collection date produces up to 4 files, one per target DTE horizon:

```
AAPL_2025-04-02_2025-04-11.csv   (~7 DTE)
AAPL_2025-04-02_2025-04-17.csv   (~30 DTE)
AAPL_2025-04-02_2025-06-20.csv   (~90 DTE)
AAPL_2025-04-02_2025-09-19.csv   (~180 DTE)
```

---

## Data pipeline

After collection, run each step in order from the project root:

```powershell
# Step 1 -- Clean raw data, fix dtypes, flag illiquid rows
python notebooks/step1_clean.py

# Step 2 -- Feature engineering (spreads, moneyness, skew) -- coming
python notebooks/step2_features.py

# Step 3 -- Realised volatility from price data -- coming
python notebooks/step3_rv.py

# Step 4 -- Combine into master datasets -- coming
python notebooks/step4_combine.py

# EDA -- full analysis and visualisations -- coming
jupyter notebook notebooks/EDA.ipynb
```

---

## Variables reference

### Raw columns (from Market Data App)

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | str | Underlying stock symbol |
| `collection_date` | datetime | Date the snapshot was taken |
| `optionSymbol` | str | OCC option identifier e.g. AAPL250417C00200000 |
| `expiration` | datetime | Contract expiry date |
| `side` | str | "call" or "put" |
| `strike` | float | Strike price |
| `dte` | int | Days to expiry at collection date |
| `bid` | float | Best bid price |
| `ask` | float | Best ask price |
| `mid` | float | Midpoint of bid and ask |
| `last` | float | Most recent trade price |
| `volume` | int | Contracts traded on collection day |
| `openInterest` | int | Total outstanding contracts |
| `underlyingPrice` | float | Spot price of the stock at collection |
| `inTheMoney` | bool | True if intrinsic value > 0 |
| `intrinsicValue` | float | Immediate exercise value |
| `extrinsicValue` | float | Time and uncertainty premium |

**Dropped columns (not included in the pipeline):**

| Column | Reason |
|--------|--------|
| `iv` | Entirely null — implied volatility is not returned on the plan used for data collection |
| `delta` | Entirely null — same reason as iv |
| `gamma` | Entirely null — same reason as iv |
| `theta` | Entirely null — same reason as iv |
| `vega` | Entirely null — same reason as iv |

These columns are dropped in `clean.py` before any downstream processing. Retaining all-null columns would add no analytical value and would silently mislead any code that checks for their presence.

### Engineered features (added in Step 2 onwards)

| Feature | Formula | Purpose |
|---------|---------|---------|
| `spread` | ask - bid | Absolute liquidity cost |
| `relative_spread` | spread / mid | Normalised liquidity cost, comparable across tickers |
| `moneyness` | strike / underlyingPrice | Position relative to spot (1.0 = ATM) |
| `moneyness_category` | ITM / ATM / OTM | Discretised moneyness using 3% bands |
| `is_illiquid` | bid == 0 | Flag for unquoted contracts |
| `phase` | 1 / 2 / 3 | Which collection phase the row belongs to |
| `days_from_apr2` | collection_date - Apr 2 2025 | Signed distance from Liberation Day |
| `realised_vol` | rolling 20-day std of log returns | What volatility actually was |

---

## Project structure

```
tariff-shock-options-study/
|
+-- config/
|   +-- settings.yaml          # Single source of truth: tickers, phases, paths, token
|   +-- loader.py              # Loads settings.yaml, imported by all scripts
|   +-- __init__.py            # Empty -- marks config/ as a Python package
|
+-- scripts/
|   +-- api_client.py          # Market Data App HTTP wrapper (auth, retries, 2xx/203)
|   +-- trading_calendar.py    # US trading day generation with NYSE holidays baked in
|   +-- scrape_options.py      # Option chain collection across all phases and tickers
|   +-- scrape_prices.py       # Daily OHLCV price collection for all tickers
|   +-- __init__.py            # Empty -- marks scripts/ as a Python package
|
+-- notebooks/
|   +-- step1_clean.py         # Step 1: clean raw CSVs, fix dtypes, flag illiquid rows
|   +-- step2_features.py      # Step 2: engineer spread, moneyness, skew (coming)
|   +-- step3_rv.py            # Step 3: realised volatility from price data (coming)
|   +-- step4_combine.py       # Step 4: combine into master datasets (coming)
|   +-- EDA.ipynb              # Exploratory data analysis and visualisations (coming)
|
+-- data/
|   +-- raw/
|   |   +-- options/
|   |   |   +-- AAPL/
|   |   |   |   +-- phase1/    # AAPL_2025-01-06_*.csv (extended AAPL-only baseline)
|   |   |   |   +-- phase2/    # AAPL_2025-04-02_*.csv etc.
|   |   |   |   +-- phase3/
|   |   |   +-- NVDA/          # All phases start 2025-03-24 (1-year API limit)
|   |   |   |   +-- phase1/
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
|   +-- clean/                 # Cleaned CSVs mirroring raw/options/ structure
|   +-- combined/              # Master datasets (all tickers, all phases merged)
|
+-- logs/
|   +-- scrape_options.log     # Full audit trail of all collection runs
|   +-- scrape_prices.log      # Audit trail for price collection
|
+-- requirements.txt
+-- setup.py
+-- README.md
```

---

## Known data limitations

**IV and Greeks dropped from pipeline**
The data plan used for this project does not return implied volatility or
Greeks. The columns `iv`, `delta`, `gamma`, `theta`, and `vega` were
present in the raw API response but entirely null. They are dropped in
`clean.py` and do not appear in any downstream file. Analysis uses
liquidity proxies instead: bid-ask spread, relative spread, volume, and
open interest.

**Non-AAPL tickers limited to 1 year of history**
NVDA, AMZN, PG, and CAT data starts from Mar 24 2025 due to the API
1-year lookback restriction on trial accounts. AAPL data starts from
Jan 6 2025. All cross-sector analysis uses Mar 24 2025 as the common
start date.

**Missing expiry on Sep 15 2025 for PG and CAT**
No December 2025 expiry data was available for PG and CAT on September 15
2025. The API confirmed no chain existed for that expiry on that date.
This is consistent with lower options market liquidity for these tickers
compared to AAPL and NVDA. Impact on analysis is negligible given 35 other
complete weekly snapshots for both tickers in Phase 3.

**Illiquid contracts (bid = 0)**
Approximately 16% of rows have bid = 0, indicating contracts with no active
market maker quote. These are flagged with `is_illiquid = True` in the
cleaned data and retained for open interest analysis.

---

## Troubleshooting

**ModuleNotFoundError: No module named 'config'**
Run `pip install -e .` from the project root, or permanently set PYTHONPATH:
```powershell
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\path\to\project", "User")
```
Also ensure both `config/__init__.py` and `scripts/__init__.py` exist as
empty files.

**HTTP 402 for non-AAPL tickers on early dates**
The 1-year lookback limit is blocking those dates. Dates before
March 23 2025 are inaccessible for non-AAPL tickers on the trial plan.

**HTTP 203 responses being treated as errors**
The Starter plan returns HTTP 203 instead of 200 for paid data. The
api_client accepts any 2xx status code. Ensure you are using the
latest version of `scripts/api_client.py`.

**UnicodeEncodeError in terminal output**
Windows uses cp1252 encoding by default which cannot display Unicode
characters such as arrows. All log messages in the scripts use ASCII
only. Ensure you are using the latest versions of all script files.

**Logs folder is empty**
Log files are created on the first script run. If empty, either no
scripts have run yet, or the log path in settings.yaml does not match
your actual folder name. Check that `paths.logs` in settings.yaml
is set to `"logs"`.