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

| Phase | Period | Frequency | Purpose |
|-------|--------|-----------|---------|
| 1 — Baseline | Jan 6 → Mar 17 2025 | Weekly | Establish pre-shock microstructure regime |
| 2 — Event window | Mar 18 → May 9 2025 | Daily | Capture shock, escalation, and pause |
| 3 — Recovery | May 12 2025 → Jan 16 2026 | Weekly | Track regime normalisation per sector |

### Key event dates
- **Apr 2 2025** — Liberation Day: sweeping tariffs announced
- **Apr 9 2025** — Escalation + 90-day pause announced same day
- **May 12 2025** — US-China truce: 90-day tariff reduction

---

## Setup

```bash
git clone <your-repo>
cd tariff-options-study
pip install -r requirements.txt
```

Edit `config/settings.yaml` and paste your Market Data App API token:
```yaml
api:
  token: "YOUR_API_TOKEN_HERE"
```

---

## Data collection

```bash
# Step 1: Fetch daily prices for all tickers (5 credits total)
python scripts/scrape_prices.py

# Step 2: Collect option chains — run one phase per day to stay within credit limits
python scripts/scrape_options.py --phase 1           # ~8,800 credits
python scripts/scrape_options.py --phase 2           # ~45,600 credits (4-5 days)
python scripts/scrape_options.py --phase 3           # ~27,200 credits

# Resume interrupted runs without re-fetching existing files
python scripts/scrape_options.py --phase 2 --resume

# Collect a single date (useful for testing)
python scripts/scrape_options.py --date 2025-04-02
```

---

## Project structure

```
tariff-options-study/
├── config/
│   ├── settings.yaml          # Single source of truth — tickers, phases, paths
│   └── loader.py              # Config loader (imported by all scripts)
├── scripts/
│   ├── api_client.py          # Market Data App HTTP wrapper
│   ├── trading_calendar.py    # US trading day generation
│   ├── scrape_options.py      # Option chain collection
│   └── scrape_prices.py       # Daily OHLCV price collection
├── data/
│   ├── raw/options/           # {ticker}_{date}_{expiry}.csv
│   ├── raw/prices/            # {ticker}_daily_prices.csv
│   ├── clean/                 # Cleaned + feature-engineered CSVs
│   └── combined/              # Master combined datasets
├── notebooks/
│   └── EDA.ipynb              # Full analysis notebook (coming next)
├── requirements.txt
└── README.md
```