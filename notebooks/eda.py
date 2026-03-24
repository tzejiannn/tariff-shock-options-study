"""
Exploratory Data Analysis -- 2025 Tariff Shock Option Microstructure

Research question:
    Did the 2025 tariff shock produce asymmetric liquidity responses
    across sectors, and can option market microstructure signal which
    sectors the market treated as structurally damaged versus temporarily
    disrupted?

What this script produces (saved to outputs/figures/):
    fig1_prices.png            -- Underlying stock prices over time
    fig2_realised_vol.png      -- Realised volatility over time
    fig3_spread_timeline.png   -- ATM relative spread over time (core finding)
    fig4_spread_by_phase.png   -- Spread distribution: baseline vs shock vs recovery
    fig5_event_study.png       -- Relative spread centred on Liberation Day
    fig6_open_interest.png     -- Open interest over time
    fig7_call_put_spread.png   -- Calls vs puts relative spread during the shock

Key dates annotated on every chart:
    Apr 2  2025 -- Liberation Day (tariff announcement)
    Apr 9  2025 -- Escalation + 90-day pause announced same day
    May 12 2025 -- US-China truce, recovery begins

Analysis notes:
    - All cross-sector charts use Mar 24 2025 as the common start date
      because NVDA, AMZN, PG, and CAT data only begins then (API limitation).
      AAPL's extended Jan 2025 baseline is used where noted.
    - Spread analysis filters out illiquid contracts (bid = 0) to avoid
      quoting artefacts distorting the liquidity signal.
    - ATM contracts (within 3% of spot) are used for like-for-like
      comparisons because their spreads reflect market maker willingness
      to provide liquidity at the most actively traded strikes.
    - IV and Greeks are unavailable (plan limitation) so this analysis
      uses bid-ask spread and relative spread as liquidity proxies.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path


# ── Setup ─────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
COMBINED_CSV = PROJECT_ROOT / "data" / "combined" / "combined_all.csv"
FIG_DIR      = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Consistent colour for each ticker across every chart
COLORS = {
    "AAPL": "#2196F3",   # blue
    "NVDA": "#4CAF50",   # green
    "AMZN": "#FF9800",   # orange
    "PG":   "#E53935",   # red
    "CAT":  "#9C27B0",   # purple
}
TICKERS = list(COLORS.keys())

# Key event dates
EVENTS = {
    "Liberation Day\n(Apr 2)":       pd.Timestamp("2025-04-02"),
    "Escalation +\nPause (Apr 9)":   pd.Timestamp("2025-04-09"),
    "US-China\nTruce (May 12)":      pd.Timestamp("2025-05-12"),
}
EVENT_COLORS = ["#E53935", "#FB8C00", "#43A047"]

# Cross-sector analysis starts here (all tickers have data from this date)
COMMON_START = pd.Timestamp("2025-03-24")

plt.rcParams.update({
    "figure.dpi":       150,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "grid.linestyle":   "--",
    "font.size":        10,
})


def add_event_lines(ax, y_pos=0.97):
    """
    Draw a vertical dashed line for each key event date and add a text label
    at the top of the axis. Called on every time-series chart so the same
    three events are consistently annotated across all figures.

    y_pos controls how high up the label sits (0 = bottom, 1 = top of axis).
    """
    for (label, dt), color in zip(EVENTS.items(), EVENT_COLORS):
        ax.axvline(dt, color=color, linestyle="--", linewidth=1.2, alpha=0.8, zorder=3)
        ax.text(
            dt, ax.get_ylim()[1] * y_pos, label,
            color=color, fontsize=7, ha="center", va="top",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )


def save(fig, name):
    """Save figure and print confirmation."""
    path = FIG_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {name}")


# ── Load data ──────────────────────────────────────────────────────────────────

print("Loading combined_all.csv...")
df = pd.read_csv(
    COMBINED_CSV,
    parse_dates=["collection_date", "expiration"],
    dtype={"ticker": str, "side": str, "moneyness_cat": str},
)
df["is_illiquid"] = df["is_illiquid"].astype(bool)

print(f"  {len(df):,} rows  |  {df['ticker'].nunique()} tickers  |  "
      f"{df['collection_date'].min().date()} to {df['collection_date'].max().date()}")

# Working subsets used across multiple charts
liquid    = df[~df["is_illiquid"]].copy()                        # bid > 0
atm       = liquid[liquid["moneyness_cat"] == "ATM"].copy()      # ATM + liquid
cross     = atm[atm["collection_date"] >= COMMON_START].copy()   # common start date

print(f"  Liquid rows: {len(liquid):,}  |  ATM liquid: {len(atm):,}  "
      f"|  Cross-sector (from {COMMON_START.date()}): {len(cross):,}")
print()


# =============================================================================
# Figure 1 -- Underlying stock prices over time
# =============================================================================
# Shows the raw equity price movement for each ticker across the study period.
# The divergence in price behaviour during Phase 2 (the shock) is the market
# signal that the options data is capturing -- sectors that fell further should
# show larger spread widening in Figure 3.
# =============================================================================

print("Generating Figure 1: prices...")

price_ts = (
    cross.groupby(["collection_date", "ticker"])["underlyingPrice"]
    .median()
    .reset_index()
)

# Normalise to 100 at the common start date so all tickers are on the same
# scale. This makes relative drawdowns immediately visible -- a line dropping
# to 80 means a 20% drawdown regardless of whether the stock started at $50
# or $500. Without normalisation, NVDA's absolute price would dominate the chart.
price_norm = price_ts.copy()
for ticker in TICKERS:
    mask    = price_norm["ticker"] == ticker
    base    = price_norm.loc[mask, "underlyingPrice"].iloc[0]
    price_norm.loc[mask, "price_idx"] = (
        price_norm.loc[mask, "underlyingPrice"] / base * 100
    )

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = price_norm[price_norm["ticker"] == ticker]
    ax.plot(data["collection_date"], data["price_idx"],
            color=COLORS[ticker], label=ticker, linewidth=1.8)

add_event_lines(ax)
ax.axhline(100, color="grey", linestyle=":", linewidth=0.8, alpha=0.5)
ax.set_title("Indexed Stock Price (Base = 100 at Mar 24 2025)", fontsize=13, pad=12)
ax.set_xlabel("Date")
ax.set_ylabel("Price Index")
ax.legend(loc="lower left", framealpha=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout()
save(fig, "fig1_prices.png")


# =============================================================================
# Figure 2 -- Realised volatility over time
# =============================================================================
# Realised vol (RV) is the rolling 20-day annualised standard deviation of
# log returns. It shows what volatility actually was, not what the market
# expected. The spike in RV around Liberation Day confirms the tariff shock
# was a genuine volatility event, not just an options market overreaction.
# AAPL has full coverage; other tickers only have RV from ~Apr 22 onwards
# (the 20-day window needs 20 prior trading days).
# =============================================================================

print("Generating Figure 2: realised volatility...")

rv_ts = (
    df.dropna(subset=["realised_vol"])
    .groupby(["collection_date", "ticker"])["realised_vol"]
    .first()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = rv_ts[rv_ts["ticker"] == ticker]
    ax.plot(data["collection_date"], data["realised_vol"] * 100,
            color=COLORS[ticker], label=ticker, linewidth=1.8)

add_event_lines(ax)
ax.set_title("20-Day Realised Volatility -- Annualised (%)", fontsize=13, pad=12)
ax.set_xlabel("Date")
ax.set_ylabel("Realised Volatility (%)")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.legend(loc="upper left", framealpha=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout()
save(fig, "fig2_realised_vol.png")


# =============================================================================
# Figure 3 -- ATM relative spread over time (core finding)
# =============================================================================
# This is the central chart of the project. Relative spread (spread / mid)
# measures the cost of trading as a fraction of the option's price -- a spread
# of 0.10 means you pay 10% of the option's value to enter and exit a position.
# ATM contracts are used because they are the most actively traded and give the
# cleanest liquidity signal free of deep-OTM illiquidity artefacts.
#
# What to look for:
#   - All tickers should show a spike around Apr 2-9 (the shock)
#   - The height of the spike varies by sector (asymmetric response)
#   - The speed of recovery in Phase 3 also differs (structural vs temporary)
# =============================================================================

print("Generating Figure 3: ATM relative spread timeline...")

spread_ts = (
    cross.groupby(["collection_date", "ticker"])["relative_spread"]
    .median()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = spread_ts[spread_ts["ticker"] == ticker]
    ax.plot(data["collection_date"], data["relative_spread"],
            color=COLORS[ticker], label=ticker, linewidth=1.8)

add_event_lines(ax)
ax.set_title("Median ATM Relative Bid-Ask Spread Over Time\n"
             "(ATM liquid contracts, common start Mar 24 2025)", fontsize=13, pad=12)
ax.set_xlabel("Date")
ax.set_ylabel("Relative Spread (spread / mid)")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
ax.legend(loc="upper left", framealpha=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout()
save(fig, "fig3_spread_timeline.png")


# =============================================================================
# Figure 4 -- Relative spread distribution by phase (box plots)
# =============================================================================
# Box plots show the full distribution of relative spreads in each phase,
# not just the median. This reveals whether the shock caused a consistent
# widening across all contracts (the whole distribution shifts up) or only
# in specific cases (the tail widens but the median barely moves).
# Comparing Phase 1 vs Phase 2 vs Phase 3 side by side per ticker makes
# the shock magnitude and recovery visible at a glance.
# =============================================================================

print("Generating Figure 4: spread distribution by phase...")

fig, axes = plt.subplots(1, 5, figsize=(16, 5), sharey=True)

phase_labels = {1: "Phase 1\nBaseline", 2: "Phase 2\nShock", 3: "Phase 3\nRecovery"}
phase_colors = {1: "#90CAF9", 2: "#EF9A9A", 3: "#A5D6A7"}

for ax, ticker in zip(axes, TICKERS):
    data = cross[cross["ticker"] == ticker]
    phase_data = [
        data.loc[data["phase"] == p, "relative_spread"].dropna().values
        for p in [1, 2, 3]
    ]
    bp = ax.boxplot(
        phase_data,
        tick_labels=[phase_labels[p] for p in [1, 2, 3]],
        patch_artist=True,
        showfliers=False,    # hide extreme outliers to keep the chart readable
        medianprops=dict(color="black", linewidth=1.5),
        whiskerprops=dict(linewidth=1),
        capprops=dict(linewidth=1),
    )
    for patch, p in zip(bp["boxes"], [1, 2, 3]):
        patch.set_facecolor(phase_colors[p])
        patch.set_alpha(0.8)

    ax.set_title(ticker, color=COLORS[ticker], fontweight="bold", fontsize=12)
    ax.tick_params(axis="x", labelsize=8)
    if ax == axes[0]:
        ax.set_ylabel("Relative Spread")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

fig.suptitle("Relative Spread Distribution by Phase\n(ATM liquid contracts, outliers hidden)",
             fontsize=13, y=1.01)
fig.tight_layout()
save(fig, "fig4_spread_by_phase.png")


# =============================================================================
# Figure 5 -- Event study: relative spread centred on Liberation Day
# =============================================================================
# An event study aligns all observations on a common time axis: the number
# of calendar days before or after the event (Liberation Day = 0). This lets
# you see the typical pattern of spread behaviour across tickers without
# the different phase boundaries obscuring the signal.
#
# The x-axis runs from -8 trading days before Liberation Day to +25 days
# after, capturing the immediate pre-announcement period through to the
# first few weeks of the post-pause recovery.
#
# What to look for:
#   - A sharp jump at day 0 (Liberation Day announcement)
#   - A second jump or plateau around day +7 (Apr 9 escalation)
#   - Different recovery slopes by ticker after day +7
# =============================================================================

print("Generating Figure 5: event study...")

event_window = cross[
    (cross["days_from_apr2"] >= -8) &
    (cross["days_from_apr2"] <= 25)
].copy()

event_ts = (
    event_window.groupby(["days_from_apr2", "ticker"])["relative_spread"]
    .median()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = event_ts[event_ts["ticker"] == ticker]
    ax.plot(data["days_from_apr2"], data["relative_spread"],
            color=COLORS[ticker], label=ticker, linewidth=1.8, marker="o",
            markersize=3)

ax.axvline(0,  color=EVENT_COLORS[0], linestyle="--", linewidth=1.2,
           label="Liberation Day (Day 0)", alpha=0.8)
ax.axvline(7,  color=EVENT_COLORS[1], linestyle="--", linewidth=1.2,
           label="Escalation + Pause (Day +7)", alpha=0.8)
ax.axvline(40, color=EVENT_COLORS[2], linestyle="--", linewidth=1.2,
           label="US-China Truce (Day +40)", alpha=0.8)

ax.set_title("Event Study: Median ATM Relative Spread\nCentred on Liberation Day (Day 0 = Apr 2 2025)",
             fontsize=13, pad=12)
ax.set_xlabel("Days Relative to Liberation Day")
ax.set_ylabel("Relative Spread")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
ax.legend(loc="upper right", framealpha=0.8, fontsize=8)
ax.axvline(0, color="grey", linewidth=0.5, linestyle=":")
fig.tight_layout()
save(fig, "fig5_event_study.png")


# =============================================================================
# Figure 6 -- Open interest over time
# =============================================================================
# Open interest (OI) is the total number of outstanding contracts. Rising OI
# means new positions are being opened; falling OI means they are being closed
# or expiring. During the tariff shock you would expect OI in near-term
# contracts to spike as traders buy downside protection -- a spike visible
# even without IV data because OI is available regardless of plan tier.
# =============================================================================

print("Generating Figure 6: open interest...")

oi_ts = (
    cross.groupby(["collection_date", "ticker"])["openInterest"]
    .sum()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = oi_ts[oi_ts["ticker"] == ticker]
    ax.plot(data["collection_date"], data["openInterest"] / 1_000,
            color=COLORS[ticker], label=ticker, linewidth=1.8)

add_event_lines(ax)
ax.set_title("Total Open Interest Over Time\n(sum across all ATM contracts in snapshot)",
             fontsize=13, pad=12)
ax.set_xlabel("Date")
ax.set_ylabel("Open Interest (thousands)")
ax.legend(loc="upper left", framealpha=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout()
save(fig, "fig6_open_interest.png")


# =============================================================================
# Figure 7 -- Calls vs puts relative spread during the event window
# =============================================================================
# In a normal market, call and put spreads should be roughly equal for
# the same strike and expiry (put-call parity keeps them anchored). During
# a shock, put spreads typically widen more than call spreads because demand
# for downside protection surges, overwhelming market makers' willingness
# to quote tight markets. A widening gap between put and call spreads is
# therefore a direct measure of how asymmetric the fear was.
#
# This chart shows Phase 2 (Apr 2 -- May 9) only, where the effect is largest.
# =============================================================================

print("Generating Figure 7: call vs put spread...")

phase2 = cross[cross["phase"] == 2].copy()
cp_ts = (
    phase2.groupby(["collection_date", "ticker", "side"])["relative_spread"]
    .median()
    .reset_index()
)

fig, axes = plt.subplots(1, 5, figsize=(16, 4), sharey=True)

for ax, ticker in zip(axes, TICKERS):
    data = cp_ts[cp_ts["ticker"] == ticker]
    for side, ls, label in [("call", "-", "Call"), ("put", "--", "Put")]:
        sdata = data[data["side"] == side]
        ax.plot(sdata["collection_date"], sdata["relative_spread"],
                color=COLORS[ticker], linestyle=ls, linewidth=1.5, label=label)

    ax.axvline(pd.Timestamp("2025-04-09"), color=EVENT_COLORS[1],
               linestyle=":", linewidth=1, alpha=0.7)
    ax.set_title(ticker, color=COLORS[ticker], fontweight="bold", fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", labelsize=7)
    if ax == axes[0]:
        ax.set_ylabel("Relative Spread")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

# Add a shared legend using the last axis
from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0], [0], color="black", linestyle="-",  linewidth=1.5, label="Call"),
    Line2D([0], [0], color="black", linestyle="--", linewidth=1.5, label="Put"),
    Line2D([0], [0], color=EVENT_COLORS[1], linestyle=":", linewidth=1, label="Apr 9"),
]
axes[-1].legend(handles=legend_handles, fontsize=8, loc="upper right")

fig.suptitle("Call vs Put Relative Spread During Tariff Event Window (Phase 2)\n"
             "ATM liquid contracts", fontsize=13, y=1.02)
fig.tight_layout()
save(fig, "fig7_call_put_spread.png")


# =============================================================================
# Figure 8 -- Recovery: Phase 3 spread relative to Phase 1 baseline
# =============================================================================
# The most analytically interesting question is not "did spreads spike?" --
# they clearly did -- but "how quickly did each sector normalise?"
#
# This chart computes a recovery ratio for each ticker in each week of Phase 3:
#     recovery_ratio = phase3_spread / phase1_baseline_spread
#
# A ratio of 1.0 means fully recovered. Above 1.0 means still wider than before.
# Below 1.0 means tighter than baseline (overshooting recovery, often seen
# in sectors that temporarily lost trading volume).
# =============================================================================

print("Generating Figure 8: recovery analysis...")

# Baseline: median ATM relative spread per ticker in Phase 1
baseline = (
    cross[cross["phase"] == 1]
    .groupby("ticker")["relative_spread"]
    .median()
    .rename("baseline")
)

# Phase 3: median ATM relative spread per collection date per ticker
phase3_ts = (
    cross[cross["phase"] == 3]
    .groupby(["collection_date", "ticker"])["relative_spread"]
    .median()
    .reset_index()
)
phase3_ts = phase3_ts.join(baseline, on="ticker")
phase3_ts["recovery_ratio"] = phase3_ts["relative_spread"] / phase3_ts["baseline"]

fig, ax = plt.subplots(figsize=(12, 5))

for ticker in TICKERS:
    data = phase3_ts[phase3_ts["ticker"] == ticker]
    ax.plot(data["collection_date"], data["recovery_ratio"],
            color=COLORS[ticker], label=ticker, linewidth=1.8)

ax.axhline(1.0, color="black", linestyle="-", linewidth=1.0,
           alpha=0.5, label="Fully recovered (ratio = 1.0)")

ax.set_title("Recovery Ratio: Phase 3 Spread / Phase 1 Baseline\n"
             "(1.0 = fully recovered, >1.0 = still wider than pre-tariff)",
             fontsize=13, pad=12)
ax.set_xlabel("Date")
ax.set_ylabel("Recovery Ratio")
ax.legend(loc="upper right", framealpha=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout()
save(fig, "fig8_recovery.png")


# =============================================================================
# Summary
# =============================================================================

print()
print("=== EDA complete ===")
print(f"All figures saved to: {FIG_DIR}")
print()

# Print the key numeric findings so results are visible in the terminal
print("Key findings:")
print()

print("1. Relative spread change: Phase 1 -> Phase 2 (ATM liquid, cross-sector window)")
phase_summary = (
    cross.groupby(["ticker", "phase"])["relative_spread"]
    .median()
    .unstack("phase")
    .rename(columns={1: "phase1", 2: "phase2", 3: "phase3"})
)
phase_summary["shock_pct_change"] = (
    (phase_summary["phase2"] - phase_summary["phase1"]) / phase_summary["phase1"] * 100
).round(1)
phase_summary["recovery_pct_change"] = (
    (phase_summary["phase3"] - phase_summary["phase1"]) / phase_summary["phase1"] * 100
).round(1)
print(phase_summary.round(4).to_string())

print()
print("2. AAPL realised vol on key dates:")
aapl_rv = df[(df["ticker"] == "AAPL")].groupby("collection_date")["realised_vol"].first()
for label, dt in EVENTS.items():
    val = aapl_rv.get(dt, None)
    if val is not None:
        print(f"   {dt.date()}  {label.replace(chr(10), ' '):35s} "
              f"RV = {val*100:.1f}%")
