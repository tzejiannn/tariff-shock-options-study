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
| **Regression dataset** | 49,473 rows — all liquid contracts with valid realised volatility, all moneyness levels |
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

## Finding 5 — Regression confirms the shock effect and reveals what drives spreads

**Models:** OLS main effects, OLS with sector×shock interactions, Random Forest
**Dataset:** 49,473 liquid contracts with valid realised volatility — all moneyness levels, all tickers, all phases

The statistical tests in Findings 1–4 established *whether* group differences were significant. Regression asks a harder question: **after controlling for everything else that independently drives spreads, does the tariff shock still explain additional spread widening?**

This matters because NVDA's +39.1% spread widening during Phase 2 could partly be explained by confounders — NVDA options naturally have higher realised volatility and tend to trade at shorter DTE, both of which widen spreads regardless of any event. Regression isolates the shock's own contribution from those pre-existing structural effects.

### OLS Model 1 — Main effects

The model regresses `log(relative_spread)` on phase indicators, ticker dummies, realised volatility, log(DTE), distance from ATM, option side, log(open interest), and log(volume). Because the target is log-transformed, each coefficient is a multiplicative effect on spreads: a coefficient of `c` means spreads are `e^c` times wider or tighter, all else equal.

**Key results:**

| Variable | Direction | Interpretation |
|----------|-----------|----------------|
| `phase_2` | Positive *** | The tariff shock independently widened spreads even after controlling for vol, DTE, moneyness, and sector. The event had a real effect beyond what market conditions alone would predict. |
| `phase_3` | Negative *** | Spreads compressed below baseline in recovery — consistent with the overshoot in Finding 4, and robust to controlling for the fact that longer-dated Phase 3 options are structurally tighter. |
| Ticker dummies (NVDA, PG, CAT, AMZN vs AAPL) | Positive *** | The structural spread divide from Finding 2 persists after controlling for all contract-level variables. Sector identity is independently predictive of spreads beyond what DTE, volatility, or open interest explain. |
| `realised_vol` | Positive *** | Higher volatility predicts wider spreads — market makers widen quotes when the underlying is more uncertain. This partially explains Phase 2 widening, but the `phase_2` coefficient captures the event effect that remains after accounting for volatility. |
| `log_dte` | Negative *** | Longer-dated options have tighter relative spreads. This captures the well-known term structure of options liquidity and validates the DTE feature as a core structural control. |
| `abs_moneyness_pct` | Positive *** | Distance from ATM widens spreads. This validates the ATM focus of the statistical analysis — restricting to ATM contracts in Findings 1–4 removed this source of variation. |
| `log_oi`, `log_vol` | Negative *** | Higher open interest and trading volume tighten spreads. Liquid, actively-traded contracts attract more market maker competition. |

### OLS Model 2 — Was the shock asymmetric across sectors?

Model 1 assumes one `phase_2` coefficient applies equally to all tickers. Model 2 adds **ticker×phase_2 interaction terms**, allowing each sector to have its own shock magnitude after controlling for all other variables.

**Key interaction results:**

- **NVDA's interaction coefficient is positive and significant.** This confirms that NVDA absorbed a larger shock than AAPL even after controlling for NVDA's naturally higher volatility and shorter DTE. The excess widening was real, not an artefact of pre-existing contract characteristics.
- **AMZN, PG, and CAT interaction terms are not significant.** Consistent with Finding 1 — the regression cannot find an event effect that the raw data does not show.
- **Total Phase 2 effect per ticker** (baseline phase_2 + interaction) is largest for NVDA, followed by AAPL, with AMZN, PG, and CAT near zero. This rank order mirrors the Mann-Whitney results exactly, but the regression provides a stronger statement: the difference holds after controlling for all confounders.

### Random Forest — What drives spreads?

The Random Forest makes no linearity assumptions and captures interactions automatically. Its out-of-sample test R² (on a held-out 20% of the data) measures genuine predictive power rather than in-sample fit.

The model's **feature importance** ranks how much each variable reduces prediction error across all 100 trees. The ranking reveals a clear hierarchy in what drives option spreads:

**1. Contract characteristics dominate**
Log DTE, distance from ATM, log open interest, and log volume are collectively the most important predictors. A short-dated, deep out-of-the-money contract in a thinly-traded name will have wide spreads under any market conditions. No event is required to explain this.

**2. Sector identity (ticker dummies) is the second tier**
Knowing which ticker a contract belongs to is highly predictive, entirely independently of contract characteristics. This is the feature importance equivalent of the η² = 0.502 finding — sector structure is baked into spreads at a level that a single market event cannot easily move.

**3. The tariff shock (phase_2) is important but ranked below structural variables**
`phase_2` is statistically significant and materially positive, but in the full variance decomposition across all contracts and dates, it explains less than DTE or moneyness alone. The shock was real; it was not the primary driver of spread levels.

**4. Realised volatility bridges structure and event**
Realised vol is important and partially overlaps with the phase_2 effect — the shock was partly a volatility event. The OLS model's ability to include both simultaneously shows that the shock explains spread widening beyond what the contemporaneous volatility spike alone would predict.

### Model fit comparison

| Model | R² | Dataset |
|-------|-----|---------|
| OLS — main effects | In-sample | Linear controls explain a substantial share of log-spread variance |
| OLS — interactions | In-sample | Modest improvement; asymmetric shock terms add incremental fit |
| Random Forest | Out-of-sample (20% test set) | Non-linear model improves predictive accuracy; confirms structural variables dominate |

The OLS and Random Forest tell a consistent story. OLS gives interpretable coefficients and confirms the independence of each effect. Random Forest confirms that the same drivers matter non-linearly, and its feature importance independently validates the hierarchy: structure first, sector second, event third.

---

## Overall Conclusions

**1. The tariff shock had asymmetric but concentrated liquidity effects.**
Statistically significant spread widening was limited to AAPL and NVDA. The intuitive candidates for damage — CAT and PG — showed no measurable liquidity deterioration. This is not because they were unaffected fundamentally, but because their options markets were already structurally illiquid, leaving little measurable room to worsen. The OLS regression confirmed this finding holds after controlling for volatility, DTE, and moneyness.

**2. Sector identity is the dominant driver of options liquidity, not event-specific shocks.**
The Kruskal-Wallis result (η² = 0.502) is the study's most striking single number: half of all spread variation during the shock window is explained by sector alone. The Random Forest feature importance independently validated this — ticker dummies ranked above the tariff shock dummy in predictive importance. The tariff event was superimposed on a pre-existing structural divide between liquid tech options and illiquid industrial/staples options.

**3. Directional fear was concentrated in consumer-facing tech.**
The significant put/call spread divergence in AAPL and AMZN — but not NVDA, PG, or CAT — suggests the market specifically priced downside risk in names with consumer revenue exposure and supply chain pass-through sensitivity. NVDA's repricing was symmetric, consistent with an export restriction being a binary regulatory risk rather than a one-sided earnings headwind. The OLS regression confirmed NVDA's shock effect was larger in magnitude than AAPL's even after controlling for NVDA's structural characteristics.

**4. Resolution of uncertainty was more powerful than the uncertainty itself.**
The overshoot in recovery — spreads finishing below baseline for four of five tickers — suggests that the primary driver of option market liquidity is not the level of risk but the *predictability* of it. Once the tariff regime stabilised, market makers re-entered with tighter quotes, producing a liquidity windfall that was statistically significant across sectors. The negative and significant `phase_3` OLS coefficient confirmed this compression is not an artefact of contract-level differences between phases.

**5. The regression establishes a driver hierarchy for option spreads.**
Combining the OLS and Random Forest results, the evidence establishes a clear ranking: (1) contract structure — DTE, moneyness, open interest, and volume are the primary determinants of spread width and explain the majority of variation; (2) sector identity — the structural divide between tech and industrial/staples options is large, persistent, and not explained by contract characteristics; (3) event-driven shocks — real, statistically independent, and economically meaningful for the affected tickers, but secondary in the overall variance decomposition. This hierarchy has a practical implication: a market shock needs to be large enough to overcome pre-existing structural liquidity constraints before it registers in the data. For PG and CAT, the tariff shock was not.

**6. The research question is partially answered.**
The market *did* treat sectors asymmetrically, but the asymmetry manifested differently than expected. Tech (AAPL, NVDA) showed measurable shock responses; industrials and staples (CAT, PG) showed structural illiquidity that masked any event-specific signal. Without IV data, it is not possible to determine whether the market priced structural damage vs temporary disruption through the volatility surface — the liquidity lens alone shows a more nuanced picture where pre-existing market structure dominates event-specific responses.

---

## Conclusion

The 2025 tariff shock produced measurable but highly selective liquidity disruption in the US options market. The sectors most visibly affected were not the ones with the highest fundamental exposure. NVDA and AAPL — facing export restrictions and supply chain uncertainty respectively — showed statistically significant spread widening, while CAT and PG, despite direct tariff exposure, showed no significant deterioration because their options were already structurally illiquid before the event. The dominant finding of this study is that **pre-existing market structure outweighed event-specific shock** as a driver of options liquidity: which sector a contract belonged to explained more than half of all spread variance during the event window, and the Random Forest feature importance confirmed this ranking independently of the non-parametric tests.

Regression analysis deepened these findings in two ways. First, it confirmed that the tariff shock independently widened spreads even after controlling for the simultaneous spike in realised volatility, changes in DTE composition between phases, and moneyness distribution — the shock effect is not an artefact of those confounders. Second, the interaction model showed that NVDA's spread widening was disproportionately large even relative to its own structural characteristics, while AMZN, PG, and CAT showed no interaction effect, consistent with the non-parametric results. Together, OLS and Random Forest established a driver hierarchy: contract structure first, sector identity second, event-driven shock third.

The recovery phase reinforced the core interpretation. Once the tariff regime became predictable — regardless of whether it was resolved favourably — four of five tickers saw spreads overshoot their pre-shock baseline. Markets responded more to the removal of uncertainty than to the uncertainty itself, a pattern confirmed by the significant negative `phase_3` coefficient in the regression after controlling for the fact that Phase 3 contracts had longer DTE and more open interest than Phase 2 contracts. The only ticker to recover to exactly baseline was CAT, whose structurally wide spreads were unaffected in either direction throughout.

Taken together, the evidence suggests that the option market did not cleanly distinguish structurally damaged sectors from temporarily disrupted ones — at least not through the liquidity channel. To make that distinction rigorously would require implied volatility and Greeks data, which the current dataset does not provide. The liquidity lens used here is a useful proxy, but the full microstructure story remains partly obscured.

---

## Limitations

1. **IV and Greeks unavailable.** The data plan used does not return implied volatility or Greeks. All analysis uses bid-ask spread and relative spread as liquidity proxies. The volatility surface — which would give the clearest signal of structural vs temporary repricing — cannot be examined.

2. **ATM filter reduces sample size for non-parametric tests.** Restricting to ATM liquid contracts (9,922 of 68,358 rows) improves comparability but limits power for less-liquid tickers. PG and CAT have fewer qualifying ATM observations than the tech stocks. The regression used the full liquid dataset (49,473 rows) to avoid this constraint, and its findings are consistent with the narrower subset.

3. **Phase 1 is short.** The baseline window (Mar 24 – Apr 1 2025) is only 7 trading days for most tickers. A longer pre-event baseline would improve the reliability of the Phase 1 reference distribution.

4. **Non-AAPL tickers have no extended baseline.** NVDA, AMZN, PG, and CAT data begins Mar 24 2025 due to API lookback constraints. It is not possible to determine whether pre-tariff spreads in early 2025 were themselves already elevated relative to a longer historical norm.

5. **Weekly Phase 3 sampling.** Phase 3 was collected weekly rather than daily, reducing granularity in the recovery analysis and making it harder to pinpoint when overshooting began.

6. **OLS regression assumes log-linearity.** The OLS models assume that each predictor has a constant multiplicative effect on spreads. The Random Forest results suggest non-linear effects exist (RF improves on OLS out-of-sample), but the directionality of OLS coefficients is robust. A generalised additive model or quantile regression would be the natural extension.
