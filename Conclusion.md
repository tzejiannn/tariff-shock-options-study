# Findings: 2025 Tariff Shock — Option Market Microstructure Study

## Research Question

*Did the 2025 tariff shock produce asymmetric liquidity responses across sectors, and does option market microstructure signal which sectors the market treated as structurally damaged versus temporarily disrupted?*

---

## Data Overview

| | |
|---|---|
| **Tickers** | AAPL (Tech), NVDA (Semiconductors), AMZN (Consumer Discretionary), PG (Consumer Staples), CAT (Industrials) |
| **Total option rows** | 68,358 |
| **Analysis subset** | 9,922 rows — ATM, liquid (bid > 0), from Mar 24 2025 |
| **Date range** | Jan 6 2025 – Jan 12 2026 |
| **Liquidity proxy** | Relative bid-ask spread (spread / mid) — used throughout because IV and Greeks were unavailable on the data plan |

**Study phases:**

| Phase | Period | Purpose |
|-------|--------|---------|
| 1 — Baseline | Mar 24 – Apr 1 2025 | Pre-shock microstructure regime |
| 2 — Event window | Apr 2 – May 9 2025 | Liberation Day, escalation, 90-day pause |
| 3 — Recovery | May 12 2025 – Jan 16 2026 | Post-shock normalisation |

**Key event dates:**
- **Apr 2 2025** — Liberation Day: sweeping tariffs announced on ~60 countries
- **Apr 9 2025** — Escalation for 57 partners + 90-day pause announced same day
- **May 12 2025** — US-China truce: 90-day tariff reduction agreement

---

## Finding 1 — The shock widened spreads for tech, not industrials

**Test:** Mann-Whitney U, Phase 1 vs Phase 2 relative spread, per ticker (ATM liquid contracts)

| Ticker | Baseline median | Shock median | Change | Result |
|--------|----------------|--------------|--------|--------|
| AAPL | 0.0230 | 0.0263 | **+14.4%** | ** (p=0.002) |
| NVDA | 0.0151 | 0.0210 | **+39.1%** | *** (p<0.001) |
| AMZN | 0.0189 | 0.0195 | +3.4% | ns (p=0.321) |
| PG | 0.1704 | 0.1709 | +0.3% | ns (p=0.525) |
| CAT | 0.1019 | 0.1046 | +2.6% | ns (p=0.598) |

Only **AAPL and NVDA** showed statistically significant spread widening during the tariff shock. AMZN, PG, and CAT showed negligible changes that were indistinguishable from noise.

This is counterintuitive. CAT (heavy machinery, large China revenue) and PG (direct input cost exposure) had the highest fundamental tariff exposure but showed no significant liquidity deterioration. NVDA — which faced direct chip export restrictions — showed the largest widening (+39.1%), consistent with the market repricing its core business risk. AAPL's widening (+14.4%) reflects indirect supply chain uncertainty.

**Why PG and CAT did not register:** Their baseline spreads were already structurally wide (0.17 and 0.10 respectively, vs 0.015–0.023 for tech). Options in these tickers trade with lower volume and thinner market maker participation. The tariff shock did not materially worsen liquidity that was already constrained — there was little room to deteriorate further in relative terms.

---

## Finding 2 — Sector spread levels are highly asymmetric

**Test:** Kruskal-Wallis across all five tickers during Phase 2

| Statistic | Value |
|-----------|-------|
| H | 1675.813 |
| p-value | < 0.001 *** |
| Eta-squared (η²) | **0.502** |

η² = 0.502 means **50% of the total variance in Phase 2 relative spreads is explained simply by which sector the contract belongs to** — before accounting for any event-specific shock. This is a large effect by any standard (η² > 0.14 is considered large).

**Pairwise comparisons (Bonferroni corrected, α = 0.005):**

| Pair | Bonferroni p | Effect r | Magnitude |
|------|-------------|---------|-----------|
| AAPL vs NVDA | 0.0000 | −0.186 | Small |
| AAPL vs AMZN | 0.0000 | −0.256 | Small |
| AAPL vs PG | 0.0000 | +0.879 | **Large** |
| AAPL vs CAT | 0.0000 | +0.755 | **Large** |
| NVDA vs AMZN | 0.484 | −0.062 | Negligible — **not significant** |
| NVDA vs PG | 0.0000 | +0.862 | **Large** |
| NVDA vs CAT | 0.0000 | +0.765 | **Large** |
| AMZN vs PG | 0.0000 | +0.917 | **Large** |
| AMZN vs CAT | 0.0000 | +0.833 | **Large** |
| PG vs CAT | 0.0000 | −0.352 | Medium |

9 of 10 pairs are statistically distinct after Bonferroni correction. The one non-significant pair is **NVDA vs AMZN** — two stocks with similar liquidity profiles and comparable tariff uncertainty. The largest effects separate the industrial/staples group (PG, CAT) from the tech group (AAPL, NVDA, AMZN), confirming a structural two-tier liquidity divide that exists independently of the tariff event.

---

## Finding 3 — Put/call spread asymmetry was selective

**Test:** Mann-Whitney U, calls vs puts during Phase 2 (ATM liquid contracts)

| Ticker | Call median | Put median | Direction | Result |
|--------|------------|-----------|-----------|--------|
| AAPL | 0.0248 | 0.0277 | Puts wider | * (p=0.026) |
| NVDA | 0.0198 | 0.0222 | Puts wider | ns (p=0.122) |
| AMZN | 0.0176 | 0.0216 | **Puts wider** | *** (p<0.001) |
| PG | 0.1657 | 0.1782 | Puts wider | ns (p=0.137) |
| CAT | 0.1089 | 0.0968 | Calls wider | ns (p=0.537) |

Put spreads were significantly wider than call spreads only for **AAPL** and **AMZN**. This indicates that demand for downside protection was concentrated in the consumer-facing tech names — the stocks most exposed to a weakening consumer and import cost pass-through. NVDA's put/call gap, while directionally consistent, did not reach significance, suggesting its market feared a structural repricing of the whole book rather than a one-sided directional bet.

CAT is the outlier: calls were slightly wider than puts (though not significantly), which may reflect genuine uncertainty about whether tariffs benefit or harm domestic industrial producers — a genuinely two-sided risk that prevented one-sided hedging demand from dominating.

---

## Finding 4 — Recovery overshot the baseline for most tickers

**Test:** Mann-Whitney U, Phase 1 vs Phase 3 relative spread, per ticker

| Ticker | Baseline median | Recovery median | Change | Status |
|--------|----------------|----------------|--------|--------|
| AAPL | 0.0230 | 0.0202 | **−12.1%** | Overshot * (p=0.029) |
| NVDA | 0.0151 | 0.0108 | **−28.3%** | Overshot *** (p<0.001) |
| AMZN | 0.0189 | 0.0166 | **−12.1%** | Overshot * (p=0.016) |
| PG | 0.1704 | 0.1411 | **−17.2%** | Overshot * (p=0.019) |
| CAT | 0.1019 | 0.1138 | +11.7% | **Recovered** ns (p=0.129) |

Four of five tickers did not simply recover — they **overshot**, ending Phase 3 with spreads significantly tighter than their pre-shock baseline. Only CAT returned to baseline.

The overshoot pattern is notable for NVDA (−28.3%): as the export restriction uncertainty resolved into a known regulatory regime, market makers appear to have resumed aggressive liquidity provision well below prior levels. The same dynamic played out for AAPL, AMZN, and PG — once the tariff regime became predictable, even if unfavourable, the resolution of uncertainty itself tightened markets.

CAT's flat recovery (not overshot, not elevated) is consistent with its options market being structurally illiquid throughout — the shock had no impact on the way in, and the recovery had no impact on the way out.

---

## Overall Conclusions

**1. The tariff shock had asymmetric but concentrated liquidity effects.**
Statistically significant spread widening was limited to AAPL and NVDA. The intuitive candidates for damage — CAT and PG — showed no measurable liquidity deterioration. This is not because they were unaffected fundamentally, but because their options markets were already structurally illiquid, leaving little measurable room to worsen.

**2. Sector identity is the dominant driver of options liquidity, not event-specific shocks.**
The Kruskal-Wallis result (η² = 0.502) is the study's most striking single number: half of all spread variation during the shock window is explained by sector alone. The tariff event was superimposed on a pre-existing structural divide between liquid tech options and illiquid industrial/staples options.

**3. Directional fear was concentrated in consumer-facing tech.**
The significant put/call spread divergence in AAPL and AMZN — but not NVDA, PG, or CAT — suggests the market specifically priced downside risk in names with consumer revenue exposure and supply chain pass-through sensitivity. NVDA's repricing was symmetric, consistent with an export restriction being a binary regulatory risk rather than a one-sided earnings headwind.

**4. Resolution of uncertainty was more powerful than the uncertainty itself.**
The overshoot in recovery — spreads finishing below baseline for four of five tickers — suggests that the primary driver of option market liquidity is not the level of risk but the *predictability* of it. Once the tariff regime stabilised, market makers re-entered with tighter quotes, producing a liquidity windfall that was statistically significant across sectors.

**5. The research question is partially answered.**
The market *did* treat sectors asymmetrically, but the asymmetry manifested differently than expected. Tech (AAPL, NVDA) showed measurable shock responses; industrials and staples (CAT, PG) showed structural illiquidity that masked any event-specific signal. Without IV data, it is not possible to determine whether the market priced structural damage vs temporary disruption through the volatility surface — the liquidity lens alone shows a more nuanced picture where pre-existing market structure dominates event-specific responses.

---

## Conclusion

The 2025 tariff shock produced measurable but highly selective liquidity disruption in the US options market. The sectors most visibly affected were not the ones with the highest fundamental exposure. NVDA and AAPL — facing export restrictions and supply chain uncertainty respectively — showed statistically significant spread widening, while CAT and PG, despite direct tariff exposure, showed no significant deterioration because their options were already structurally illiquid before the event. The dominant finding of this study is that **pre-existing market structure outweighed event-specific shock** as a driver of options liquidity: which sector a contract belonged to explained more than half of all spread variance during the event window.

The recovery phase reinforced this interpretation. Once the tariff regime became predictable — regardless of whether it was resolved favourably — four of five tickers saw spreads overshoot their pre-shock baseline. Markets responded more to the removal of uncertainty than to the uncertainty itself. The only ticker to recover to exactly baseline was CAT, whose structurally wide spreads were unaffected in either direction throughout.

Taken together, the evidence suggests that the option market did not cleanly distinguish structurally damaged sectors from temporarily disrupted ones — at least not through the liquidity channel. To make that distinction rigorously would require implied volatility and Greeks data, which the current dataset does not provide. The liquidity lens used here is a useful proxy, but the full microstructure story remains partly obscured.

---

## Limitations

1. **IV and Greeks unavailable.** The data plan used does not return implied volatility or Greeks. All analysis uses bid-ask spread and relative spread as liquidity proxies. The volatility surface — which would give the clearest signal of structural vs temporary repricing — cannot be examined.

2. **ATM filter reduces sample size.** Restricting to ATM liquid contracts (9,922 of 68,358 rows) improves comparability but limits power for less-liquid tickers. PG and CAT have fewer qualifying ATM observations than the tech stocks.

3. **Phase 1 is short.** The baseline window (Mar 24 – Apr 1 2025) is only 7 trading days for most tickers. A longer pre-event baseline would improve the reliability of the Phase 1 reference distribution.

4. **Non-AAPL tickers have no extended baseline.** NVDA, AMZN, PG, and CAT data begins Mar 24 2025 due to API lookback constraints. It is not possible to determine whether pre-tariff spreads in early 2025 were themselves already elevated relative to a longer historical norm.

5. **Weekly Phase 3 sampling.** Phase 3 was collected weekly rather than daily, reducing granularity in the recovery analysis and making it harder to pinpoint when overshooting began.
