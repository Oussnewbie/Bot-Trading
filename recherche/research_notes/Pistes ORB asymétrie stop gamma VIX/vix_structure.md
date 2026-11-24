# VIX level and VIX term structure as regime filters for a 5-minute opening-range breakout on the Nasdaq 100

Scope: US equity indices, intraday horizon. The context is the user's robot: a 5-minute ORB at 9:30 New York on the NAS100 CFD, both directions, stop at 3x the opening range, exit at 15:50. Research done on 2026-11-24.

Labels used below:
- "Own computation" means a statistic I computed from the Cboe or FRED CSV files downloaded on 2026-11-24. Scratch scripts are not kept in the repo.
- "Snippet-level" means I only saw an abstract or search excerpt, not the full text.

## Q1. What evidence links the VIX level, or changes in it, to intraday momentum and ORB returns?

### Takeaway
The published evidence consistently finds that intraday continuation (momentum, breakouts) is stronger when volatility is high. Two caveats limit how far this goes:
- Most studies condition on **realised** volatility (often same-day), not on the VIX.
- The only VIX-conditioned result found comes from an intraday momentum paper on SPY (a noise-band breakout, not a 5-minute ORB). It uses the VIX at the open with cumulative thresholds.

No paper was found that tests a 5-minute ORB on the Nasdaq 100 (or the S&P 500) split by VIX level, VIX change or VIX term structure.

### Cited Findings

**Gao, Han, Li & Zhou, "Market intraday momentum"**
- Published in the Journal of Financial Economics, 2018. The numbers below come from the October 2014 working-paper version ("Intraday Momentum: The First Half-Hour Return Predicts the Last Half-Hour Return") — [JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351); [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
- Sample: SPY, 1993–2013. The predictor is the first half-hour return, measured from the previous close to 10:00, so it includes the overnight gap. It predicts the last half-hour return (15:30–16:00). The authors state the effect is stronger "on more volatile days, higher volume days, recession days and some macroeconomic news" days — [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
- How volatility is defined: days are sorted into three equal groups by the **realised volatility of the first half-hour on the same day**, computed from 30 one-minute returns. This is not the VIX. In-sample R² by group, for the **joint regression on r1 and r12** (the first and twelfth half-hour returns):
  - low volatility: 0.6%
  - medium volatility: 1.0%
  - high volatility: 3.3%

  The authors conclude: "The higher the volatility, the greater the predictability" — [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
- Out-of-sample timing strategy η(r1), by first-half-hour volatility tercile:

  | Tercile | Annualised average return (t-stat) | Sharpe ratio |
  |---|---|---|
  | Low | 0.54% (0.43) | 0.183 |
  | Medium | 4.75% (2.27) | 0.971 |
  | High | 14.73% (3.8) | 1.626 |

  [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
- Other ETFs: QQQ has the **lowest** R² of the ETFs tested. Predictive R² ranges "from 0.70% for QQQ to 6.53% for EEM" — [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)

**Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)"**
- Swiss Finance Institute RP 24-97 / SSRN, 2024 — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download); [RePEc](https://ideas.repec.org/p/chf/rpseri/rp2497.html)
- Strategy and data: a breakout from a time-of-day "noise area" around the open, with a VWAP/band trailing stop. Data are 1-minute SPY and VIX from IQFeed, May 2007 to April 2024 — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- VIX result (section 4.1, Fig. 8): days are classified by "the VIX Index value at the opening of each trading session", using cumulative thresholds ("VIX above X"). The authors report:
  - Sharpe ratio of about 1.50 when VIX > 6, which is effectively all days.
  - About 3.50 when VIX > 40.
  - The Sharpe ratio "begins to decrease" at even higher VIX levels, which they attribute to few observations.

  [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- Daily patterns (Table 5):
  - Unconditional: 2,620 observations, 12 bps average PnL, t = 5.34, hit ratio 43%, Sharpe 1.7.
  - NR4 days (the previous day's range is the narrowest of 4): 22 bps, Sharpe 3.2.
  - "Trend" days: −2 bps.

  [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)

**Lundström, "Day trading returns across volatility states"**
- Umeå Economic Studies No. 861 (rev. 2017). It measures ORB returns across volatility states on long histories of S&P 500 futures and crude oil. The reported gap is about 150 bp/day (S&P 500) and about 200 bp/day (crude) between the highest and lowest volatility state — [RePEc](https://ideas.repec.org/p/hhs/umnees/0861.html); [SWOPEC](https://swopec.hhs.se/umnees/abs/umnees0861.htm)
- Zarattini, Barbon & Aziz (SSRN 4729284) summarise it as: "the profitability of ORB grows with the volatility of the underlying asset" — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Snippet-level: I did not read the full text. The size of the 150 bp/day figure, and how the volatility states are defined (probably realised or model-based, not the VIX), are unverified.

**Baltussen, Da, Lammers & Martens, "Hedging demand and market intraday momentum"**
- Journal of Financial Economics 142 (2021), 377–403. The sample covers more than 60 futures, 1974–2020 — [PDF](https://www3.nd.edu/~zda/intramom.pdf)
- Using a net gamma exposure (NGE) proxy for S&P 500 options:
  - Intraday momentum is "much more pronounced on negative NGE days".
  - "On days with positive NGE, however, there is no significant intraday momentum."
  - Between 1996 and May 2020 there were 2,930 negative-NGE days and 3,158 positive-NGE days.
  - NGE comes from SqueezeMetrics and OptionMetrics, neither of which is free.

  [PDF](https://www3.nd.edu/~zda/intramom.pdf)

**0DTE studies (snippet-level only)**
- Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation": market-maker inventory gamma in SPX 0DTE options is positive on average and is associated with lower future intraday volatility. Positive gamma strengthens intraday reversal and negative gamma strengthens momentum — [ResearchGate](https://www.researchgate.net/publication/377984312_0DTEs_Trading_Gamma_Risk_and_Volatility_Propagation)
- A separate paper (Adams et al.) finds a negative relation between 0DTE trading and realised S&P 500 volatility, summarised by Quantpedia — [Quantpedia](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/); [paper PDF](https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf)

**QQQ 5-minute ORB (Zarattini & Aziz 2023, "Can Day Trading Really Be Profitable?", SSRN 4416622)**
- The paper reports a 5-minute ORB on QQQ and TQQQ from 2016 to 2023. I found no VIX split in the material I could see. I did not read the full text — [SSRN](https://papers.ssrn.com/abstract=4416622)
- An independent replication on five indices with CFD data (January 2015 to June 2026) reports that the paper's gross returns are reproduced but are about zero net of costs. Snippet-level, not read in full — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235)

**Vendor and blog claims (unverified, no methodology)**
- A vendor states that QQQ's median daily range is 0.97% when VIX < 13 and 2.73% when VIX > 28 — [Vortex Capital](https://www.vortexcapitalgroup.com/insights/vix-adjusted-opening-range-position-sizing-qqq-nvda-and-tsla-before-the-bell)
- A blog review says "Beat the Market" performs better when VIX > 20 — [Quant Macro](https://quantmacro.substack.com/p/paper-review-an-effective-intraday)
- Treat both as illustrative only.

### Inferences
- The direction of the evidence is consistent: higher volatility goes with stronger continuation. This holds for realised volatility (Gao et al.; Lundström), for the VIX at the open (Zarattini et al.), and for dealer negative gamma (Baltussen et al.).
- For an ORB that holds from about 9:35 to 15:50, the most defensible hypothesis is therefore **"ORB expectancy is higher when the prior-day VIX is high"**, applied to both sides.
- QQQ having the weakest momentum R² in Gao et al. suggests the effect may be weaker on the Nasdaq 100 than on SPY. This needs to be tested, not assumed.
- Part of the "high VIX helps" effect is probably mechanical. The VIX, the opening range and realised volatility are all highly correlated. The user already found that a small opening range relative to recent days predicts more stop-outs. Any VIX filter must show value **beyond** the opening-range-size and realised-volatility (14/60-day) variables already studied.
- The gamma channel (Baltussen et al.; Dim–Eraker–Vilkov) suggests the VIX is only a noisy proxy for what actually drives continuation, which is dealer gamma sign. The proxy relationship between the VIX and dealer gamma is my inference, not a sourced finding.
- **Some of these conditioners have already failed on this robot.** The Zarattini et al. NR4/NR7 result and the Gao et al. first-half-hour momentum both fall under "day context" filters. `recherche/critique-v10.md` §3 lists those (gap, first-half-hour momentum, NR4/NR7) as already tried without success on the V10 Nasdaq data. They should not be revived as leads. Only implied-volatility measures are new (critique §4, Axe 4).

### Gaps
- No study found that tests a 5-minute ORB (S&P 500 or Nasdaq 100) split by VIX level, VIX daily change, overnight VIX change, VIX/VIX3M or VIX9D/VIX.
- No study found on whether the **change** in the VIX (T-1 or overnight) predicts ORB or intraday momentum success.
- These texts were not read in full: Lundström (2017), the QQQ ORB paper (SSRN 4416622), the 0DTE papers, and Rosa (2022, *Journal of Futures Markets* 42(12), cited by Zarattini as also finding returns improve with volatility) — [RePEc](https://ideas.repec.org/a/wly/jfutmk/v42y2022i12p2218-2234.html).
- The exact Sharpe values per VIX bucket in Zarattini et al. Fig. 8 are only quoted in the text at two points (about 1.5 for VIX > 6, about 3.5 for VIX > 40). The intermediate bars were not extracted from the chart.

## Q2. Do short trades work better in high-VIX or inverted-curve regimes, and long trades in low-VIX contango?

### Takeaway
The only direct test found is **null**: in Zarattini et al. (SPY intraday momentum), short-trade profitability is unrelated to the VIX, and restricting shorts to high-VIX days or bear markets does not help. Term-structure evidence (a VIX futures slope, close-to-close returns) points to **positive** next-day S&P 500 returns after backwardation, which argues against "short more when inverted". No study links the term structure to the 9:35–15:50 window.

### Cited Findings
- **Zarattini et al., Q19:** a regression of each short trade's PnL (bps) on the same-day average VIX finds "no significant relationship between VIX and short trade profitability". The p-value of the beta is 0.91. Note that the same-day average VIX is not known at entry — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **Zarattini et al., Q20:** "limiting short trades to high volatility environments does not benefit overall compounded performance" — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **Zarattini et al., Q21:** taking short intraday trend trades only when SPY is below its 100-, 150- or 200-day SMA means "sacrificing a substantial portion of overall profitability" — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **Zarattini et al., Q5:** both legs contributed positively, with the long leg "slightly more" over 2007–2024 — [PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **Fassas & Hourvouliades (2019), "VIX Futures as a Market Timing Indicator"**, J. Risk Financial Manag. 12(3):113 — [PDF](https://mdpi-res.com/d_attachment/jrfm/jrfm-12-00113/article_deploy/jrfm-12-00113-v2.pdf):
  - Sample: daily closes of spot VIX and the 7 nearest VIX futures, 4 January 2010 to 29 December 2017. The slope is fitted to the futures curve; it is not VIX/VIX3M.
  - Regression: R(t+K) = α + β·Slope⁺ + γ·Slope⁻.
  - At K = 1 day (close-to-close S&P 500): γ = −0.1687 (Newey–West SE 0.0492, significant at 1%); β = 0.0245 (SE 0.0208, not significant); adjusted R² = 0.009.
  - At K = 1 week: γ = −0.5084 (significant at 1%). At 1 month: −0.5479 (not significant). At 1 quarter: −1.1809 (significant at 1%).
  - Interpretation: "whenever … the VIX futures were in backwardation, the subsequent future return of S&P500 was positive", and contango gives "no meaningful market timing signal".
- **Cboe (S. Bauer, 26 July 2022):** the VIX futures curve has been in contango more than 80% of the time since 2010, and in backwardation less than 20%. On backwardation as a bearish signal: "Outside of some of the biggest and most memorable market selloffs the results don't pan out" — [Cboe Insights](https://www.cboe.com/insights/posts/inside-volatility-trading-is-vix-backwardation-necessarily-a-sign-of-a-future-down-market)
- **Johnson (2017, JFQA), "Risk Premia and the VIX Term Structure":** the slope of the VIX term structure predicts returns on variance assets (variance swaps, VIX futures, straddles). Predictability of S&P 500 index returns appears at horizons of 1 month to 1 year, and comes mainly from a higher-order principal component, not the slope. Snippet-level — [JFQA PDF](https://www.travislakejohnson.com/pdfs/Johnson%20VIXTS%202017%20(JFQA).pdf); [2012 WP](https://www.travislakejohnson.com/pdfs/Johnson%20VIXTS%202012%20(WP).pdf)
- **Own computation:** the share of days with VIX/VIX3M close ≥ 1 varies widely by year:

  | Year | Inverted days |
  |---|---|
  | 2018 | 53/251 |
  | 2019 | 13/252 |
  | 2020 | 53/253 |
  | 2021 | 2/252 |
  | 2022 | 15/251 |
  | 2023 | 0/250 |
  | 2024 | 9/252 |
  | 2025 | 29/250 |
  | 2026 (to 23 Nov) | 17/225 |

  Over 2018 to 23 November 2026 that is 191 of 2,236 days, about 8.5% — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv); [VIX3M CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv)
- **Own computation:** VIX9D/VIX ≥ 1 is much more frequent, for example 97/251 days in 2018, 95/251 in 2022 and 44/250 in 2025 — [VIX9D CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv)

### Inferences
- The user's observed long/short asymmetry (short win rate 39–45% vs long 51–54%) is consistent with the long-only drift that Zarattini et al. also see. The literature gives no support for fixing it with a VIX-based short filter.
- For Axe 1 of `critique-v10.md` ("find information that separates the shorts that hold from those that fail"), the VIX level is **not** a documented candidate. The only direct test is null. Gamma sign (Axe 3) is the better-motivated two-sided candidate.
- The term-structure evidence points to a contrarian next-day bounce after backwardation. If anything, that would hurt shorts and help longs on inverted days, which is the opposite of the hypothesis. However:
  - the evidence is close-to-close and 2010–2017;
  - it is based on futures, not the VIX/VIX3M ratio;
  - it does not isolate the 9:35–15:50 window.

  It is therefore a weak prior in either direction.
- "Long only in low-VIX contango" has no direct evidence. Low VIX also means small opening ranges, which the user already associates with more stop-outs.

### Gaps
- No study found that splits ORB or intraday momentum results by side **and** by VIX/VIX3M or VIX9D/VIX.
- No study found that tests the term structure against the open-to-close (rather than close-to-close) index return.
- A ResearchGate paper on S&P 500/CSI300 intraday momentum mentions a stronger effect "conditional on negative past returns", but the snippet is too fragmentary to use — [ResearchGate](https://www.researchgate.net/publication/356901732_THE_IMPACT_OF_INTRADAY_MOMENTUM_ON_STOCK_RETURNS_EVIDENCE_FROM_SP500_AND_CSI300)
- The Macrosynergy summary of the term-structure signal could not be fetched (HTTP 403 / bot check) — [Macrosynergy](https://macrosynergy.com/research/vix-term-structure-as-a-trading-signal/)

## Q3. VXN (Nasdaq 100 volatility) vs VIX: is VXN available and does it matter for the Nasdaq?

### Takeaway
VXN is freely available as a daily close from 2001 (FRED) or as OHLC from September 2009 (Cboe CSV). It moves almost one-for-one with the VIX: own computation gives a correlation of 0.92 on daily log changes and 0.94 on levels, with VXN about 17% above the VIX at the median. VXN's OPEN field is unreliable before 2023. No free VXN term structure (a 3-month or 9-day VXN) was found. Using the VIX family, which does have a term structure, loses little information.

### Cited Findings
- The Cboe file `VXN_History.csv` downloads at the same path as the VIX file. It has OHLC columns and runs from 2009-09-14 to 2026-11-23. Own download on 2026-11-24 — [VXN CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv)
- FRED series VXNCLS ("CBOE NASDAQ 100 Volatility Index", daily close) — [FRED VXNCLS](https://fred.stlouisfed.org/series/VXNCLS); [FRED CSV](https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXNCLS,VXVCLS,VIXCLS):
  - First value 2001-02-02 (54.89).
  - Last observation 2026-11-23 (36.31, which matches the Cboe CSV close).
  - Data are copyrighted by Cboe and reprinted with permission.
- Own computation, 2009-09-14 to 2026-11-23:

  | Statistic | Value |
  |---|---|
  | VXN/VIX median | 1.171 |
  | VXN/VIX minimum | 0.756 |
  | VXN/VIX maximum | 1.733 |
  | Correlation of daily log changes | 0.92 |
  | Correlation of levels | 0.943 |

  [VXN CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv); [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)
- Own computation: VXN's OPEN equals the prior day's CLOSE on about 30–40% of days from 2010 to 2021. For example:
  - 2015: 93/252
  - 2017: 102/251
  - 2022: 33/251
  - 2023–2026: 1–5 days per year

  So VXN opens before 2023 are mostly stale or carried forward — [VXN CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv)

### Inferences
- For a Nasdaq 100 CFD, VXN is the conceptually right level variable. However, with a 0.92 correlation of daily changes, a VIX-based and a VXN-based rule will select nearly the same days.
- Pre-register one of them (suggestion: the VIX, because the VIX3M/VIX9D ratios exist and the files share one calendar). Run VXN only as a robustness check, not as a separate hypothesis.
- If a level threshold is used, it must be relative (for example, a rolling median or percentile) and not an absolute number. VXN sits structurally about 17% above the VIX.

### Gaps
- No free VXN term-structure index (a 3-month or 9-day VXN) was found. I did not search exhaustively for one.
- No study found that compares VXN and the VIX as predictors of Nasdaq intraday momentum or ORB returns.

## Q4. What free historical data exists, and which input is truly known before 9:30 New York?

### Takeaway
All needed daily series are free from Cboe's CDN as CSV files (DATE, OPEN, HIGH, LOW, CLOSE). FRED mirrors the closes of VIX, VXN and VIX3M (as VXV). The only input that is defensibly known before 9:30 and clean is the **previous trading day's CLOSE**, for three reasons:
- The OPEN field's timestamp is not documented.
- OPEN is back-filled or stale in parts of several series.
- HIGH and LOW contain bad ticks.

No free intraday VIX history was found.

### Cited Findings

**Cboe history files**
- The Cboe VIX historical data page lists these files:
  - `VIX_History.csv` (1990 to present, "daily closing values")
  - `VIX9D_History.csv`
  - `VVIX_History.csv`
  - the old-methodology VXO archives

  It does **not** list VIX3M, VXN or VIX1D, and it does not define the OHLC columns or the calculation hours — [Cboe VIX historical data](https://www.cboe.com/tradable_products/vix/vix_historical_data/)
- Own download on 2026-11-24. All of these return HTTP 200 at `https://cdn.cboe.com/api/global/us_indices/daily_prices/<NAME>_History.csv`. The same files at `cdn-api.cboe.com` are byte-identical (checked with `cmp`):

  | Index | First row | Notes |
  |---|---|---|
  | VIX | 1990-01-02 | |
  | VIX3M | 2009-09-18 | |
  | VIX9D | 2011-01-04 | |
  | VXN | 2009-09-14 | |
  | VIX1D | 2022-05-13 | |
  | VIX6M | 2008-01-02 | |
  | VXV | n/a | The old name `VXV_History.csv` returns 403 |

  All series run to 2026-11-23 — [VIX](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv), [VIX3M](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv), [VIX9D](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv), [VXN](https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv), [VIX1D](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX1D_History.csv), [VIX6M](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX6M_History.csv)

**FRED mirrors**
- VIXCLS starts 1990-01-02, VXVCLS (VIX3M) starts 2007-12-04 and VXNCLS starts 2001-02-02, all as daily closes. FRED gives roughly 2 more years of VIX3M and 8 more years of VXN than the Cboe CSVs — [FRED CSV](https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXNCLS,VXVCLS,VIXCLS); [FRED VXNCLS](https://fred.stlouisfed.org/series/VXNCLS)
- FRED was checked through WebFetch only. Direct curl from this machine failed (connection error).

**Back-filled OHLC (own computation)**
These rows have OPEN = HIGH = LOW = CLOSE, which means only a close is stored:
- VIX: all of 1990–1991
- VIX9D: all of 2011–2012, and 221/252 days in 2013
- VIX6M: all of 2008–2012, and 229/252 days in 2013
- VIX1D: all of 2022, and 62/250 days in 2023

Source: the CSVs above.

**Stale opens (own computation)**
OPEN equals the prior CLOSE on:
- VXN: about a third of days through 2021 (see Q3)
- VIX: 73/253 days in 2008 and 84/252 in 2009, rare otherwise
- VIX9D: 41/252 days in 2021
- VIX6M: 37/253 in 2020 and 67/252 in 2021
- VIX3M: also on 2026-11-23 (OPEN 30.94 = prior CLOSE)

Source: the CSVs above.

**Bad ticks (own computation)**
- The VIX row for 2026-11-23 has OPEN 31.38, HIGH 35.08, **LOW 15.39**, CLOSE 26.62.
- Days with LOW < 0.8·min(OPEN, CLOSE) or HIGH > 1.25·max(OPEN, CLOSE): 14 (1992 to April 2016), 12 (April 2016 to November 2021), 7 (since November 2021).

Source: [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)

**Holiday rows (own computation)**
- From 2022 the VIX file contains rows on US equity-market holidays, for example 2023-06-19, 2024-01-15, 2024-07-04, 2024-11-28 and 2025-01-09.
- This gives 256–259 rows per year in 2022–2025, against about 250–252 in VIX3M.
- So VIX and VIX3M do not share a calendar — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv); [VIX3M CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv)

**Overnight values**
- Cboe began overnight dissemination of the VIX on 15 April 2016. Values are published every 15 seconds from 2:15 a.m. CT (3:15 a.m. ET) during the extended session. Snippet-level, from search results — [Cboe IR 2016](https://ir.cboe.com/news/news-details/2016/CBOE-to-Start-Overnight-Dissemination-of-CBOE-Volatility-Index-VIX-April-15-04-13-2016/default.aspx)
- Global trading hours for SPX and VIX options were extended to "nearly 24 hours" from 21 November 2021. Snippet-level, from search results — [Cboe IR 2021](https://ir.cboe.com/news/news-details/2021/Cboe-to-Extend-Global-Trading-Hours-for-VIX-and-SPX-Options-to-Nearly-24-Hours-Beginning-November-21-2021-06-15-2021/default.aspx)
- Own computation: the median |VIX OPEN / prior CLOSE − 1| is 2.1% (1992 to April 2016), 1.65% (April 2016 to November 2021) and 1.53% (since November 2021). This does not reveal whether OPEN is a pre-9:30 global-trading-hours print or the 9:30 value — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)

**Intraday VIX**
- Zarattini et al. used IQFeed 1-minute VIX data, a commercial feed. The Cboe history page refers "custom VIX options and futures data" to DataShop. It does not say whether intraday index values are available there or what they cost — [BTM PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download); [Cboe VIX historical data](https://www.cboe.com/tradable_products/vix/vix_historical_data/)

### Inferences

**Input that is safe from look-ahead at 9:30 New York**
- Use the CLOSE of the last row dated strictly before the trade date, restricted to the robot's own trading calendar (the previous NYSE session).
- For a ratio, use the last date that is present in **both** files and earlier than the trade date. Otherwise holiday rows in the VIX file would pair with stale VIX3M values.

**Input that is known before 9:30 but not backtestable for free**
- Live global-trading-hours VIX values (since 2016) and VIX futures quotes.
- They could be used in live trading, but a backtest would need paid intraday data. Mixing them in creates a gap between backtest and live behaviour.

**Inputs to avoid**
- Do not use OPEN, HIGH or LOW from the Cboe files, for the reasons above.
- Do not use the same-day CLOSE. That is look-ahead.

**Usable history for the robot's 2018–2026 NAS100 M1 data**
- VIX, VIX3M, VIX9D, VXN and VIX6M all cover the full window. VIX1D starts in 2022, with clean OHLC only from 2023.

### Gaps
- **Close timestamp and OPEN definition:** I did not retrieve Cboe's methodology document stating the exact timestamp of the daily CLOSE (4:15 p.m. ET at the end of the SPX options session is the usual assumption, but it was **not verified** here). The exact definition of the OPEN field is also unknown. A Cboe VIX options specification page indicates that regular hours end at 3:15 p.m. CT (4:15 p.m. ET) — [Cboe VIX options specs](https://cboe.com/tradable-products/vix/vix-options/specifications) — but that page describes the options, not the index close.
- **VIX index outside regular hours:** whether the VIX **index** is disseminated during the full post-2021 overnight session, or only from 3:15 a.m. ET, was not verified. The holiday rows since 2022 are consistent with index values being calculated during global trading hours on US holidays. That is an inference.
- **Free intraday VIX:** no free source of intraday VIX history was found. The search was not exhaustive (Stooq, Yahoo and broker feeds were not checked).
- **Undocumented URLs:** VIX3M, VXN, VIX1D and VIX6M are served at the CDN path but not linked from the Cboe history page, so those URLs could change without notice.
- **Which URLs were verified (as of 2026-11-24):**
  - **Fetched and read:**
    - the Cboe VIX historical data page and all six Cboe CSVs;
    - FRED, through WebFetch only;
    - the PDFs of Gao et al. (WP), Zarattini et al. "Beat the Market", Zarattini–Barbon–Aziz (SSRN 4729284), Baltussen et al. and Fassas & Hourvouliades;
    - the Cboe Insights backwardation article.
  - **Search results only** (link exists, content not opened): RePEc, SSRN, ResearchGate, Quantpedia, the Cboe IR press releases, the Cboe VIX options spec page, the Johnson JFQA PDF, the MQL5 blog, and the vendor and blog pages.
  - **Blocked:** the MDPI article page returned 403 (the paper was read through the mdpi-res.com PDF), and the Macrosynergy page returned 403.

## Q5. Simple, fully specified rules from the literature (no optimisation)

### Takeaway
The literature supports a single direction-agnostic hypothesis: **ORB works better when implied volatility is high relative to its recent history**. It does not support side-specific VIX filters or a VIX/VIX3M filter for an ORB. Those should be kept as secondary or exploratory tests, with correction for multiple testing.

### Cited Findings
- Higher volatility goes with stronger continuation:
  - Gao et al.: R² of the joint r1 + r12 regression rises from 0.6% to 3.3% from the low to the high first-half-hour volatility tercile; the out-of-sample Sharpe of η(r1) rises from 0.18 to 1.63 — [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
  - Zarattini et al.: Sharpe rises from about 1.5 for all days to about 3.5 when VIX at the open is above 40 — [BTM PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
  - Lundström: ORB returns are higher in high-volatility states (snippet-level) — [RePEc](https://ideas.repec.org/p/hhs/umnees/0861.html)
- Side-specific VIX filters (shorts only in high VIX, or only below the SMA) did not help in Zarattini et al. Q19–Q21 — [BTM PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- Term-structure backwardation is followed by **positive** close-to-close S&P 500 returns (2010–2017), and contango carries no signal — [Fassas & Hourvouliades](https://mdpi-res.com/d_attachment/jrfm/jrfm-12-00113/article_deploy/jrfm-12-00113-v2.pdf)
- Own computation: the VIX median over the 252 trading-day rows up to 2026-11-23 is 17.10, against a last close of 26.62. On that date the rule below would be "on" — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)

### Inferences

**The one primary rule to test (pre-registered, no parameter search)**
- **Name:** R1, "VIX above its 1-year median, both sides".
- **Inputs:** for trade date D (New York), let P be the previous NYSE session on which the CFD had a 9:30 open.
  - V = Cboe `VIX_History.csv` CLOSE on P.
  - M = median of the VIX CLOSE over the 252 NYSE sessions ending at P, inclusive. Drop VIX rows that fall on NYSE holidays.
- **Signal:** if V ≥ M, run the existing ORB unchanged (5-minute range, both directions, stop at 3x the range, exit at 15:50). If V < M, do not trade on day D.
- **Look-ahead check:** V and M are final by about 16:15 ET on P, more than 17 hours before 9:30 on D. No same-day data is used.
- **Which data judges the rule.** This follows the project's discipline, in `CLAUDE.md` and `recherche/critique-v10.md` §5:
  - **Do not judge R1 on the Nasdaq 2010–2026 history.** It has been seen in full, so a result there is only a candidate.
  - The planned judge is **S&P 500 Dukascopy 2018–2026 (bid and ask), V10 Confort**, which has never been loaded. The VIX is the native implied volatility of that index, which is a good fit. That makes the S&P 500 test cleaner for a VIX rule than a Nasdaq test would be.
  - Confirmation then comes from Nasdaq data after 19/11/2026 and from demo trades. Only about half of days are "on", so this accumulates slowly.
  - Costs: real spread + 1 point of slippage per execution, then a stress test at 2–3 points.
  - Write the rule and its criterion in the registry before looking, and judge once.
- **Evaluation:**
  - Compare "on" and "off" days separately for long and short trades: trade count, win rate, mean R per trade, profit factor and maximum drawdown in R.
  - Report a bootstrap by day, or a t-test, on the difference in mean R per trade.
  - Report 2018–2022 and 2023–2026 separately (0DTE era).
  - The pass/fail criterion has to be fixed in advance. Per `CLAUDE.md`, the user must choose whether it is total R or the win rate / share of losing days.
- **Incremental-value test (required):** regress per-trade R on:
  - the VIX-high dummy;
  - the relative opening range already used in `critique-v10.md` §2.2: the 9:30 range ÷ the average of the last 20 sessions, in quintiles;
  - 14-day and 60-day realised volatility.

  Alternatively, show the "on" vs "off" difference **within** quintiles of the relative range. If the VIX dummy loses significance once the relative range and realised volatility are included, R1 adds nothing.
- **Why this form:**
  - It follows the direction found in Gao, Zarattini and Lundström.
  - It uses the only clean pre-9:30 input, the T-1 close.
  - A rolling median avoids picking an absolute threshold and adapts to the VIX level drift between 2018 and 2026.
  - It keeps about half the sessions. Own computation: R1 is "on" for 1,149 of 2,236 sessions in 2018–2026 (51%). The session calendar is approximated by the VIX3M dates. Power is therefore much better than for an inversion rule.
- **Caveat on R1's distribution.** Because the VIX is persistent, "on" days bunch by year (own computation from the [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)):

  | Year | "On" sessions |
  |---|---|
  | 2018 | 217/251 |
  | 2019 | 99/252 |
  | 2020 | 193/253 |
  | 2021 | 40/252 |
  | 2022 | 189/251 |
  | 2023 | 17/250 |
  | 2024 | 130/252 |
  | 2025 | 144/250 |
  | 2026 (to 23 Nov) | 120/225 |

  That gives 738/1,259 for 2018–2022 and 411/977 for 2023–2026. So "on vs off" is partly a comparison between years: 2018, 2020 and 2022 against 2021 and 2023. A year-by-year breakdown, or year fixed effects in the regression, is needed to separate a VIX effect from a year effect.

**Secondary hypotheses (not supported by the literature; exploratory, Holm-corrected as a family)**
- **H2, side-specific:** take shorts only if V ≥ M; take longs always. This is the user's suggested example. Zarattini et al. Q19–Q20 found no such effect for SPY intraday momentum.
- **H3, term structure:** trade only if the VIX/VIX3M CLOSE ratio on P is below 1 (contango). An alternative is to forbid shorts when the ratio is ≥ 1, which is the contrarian reading of Fassas. Either way, only about 191 inverted days exist in 2018–2026.
- **H4, short-term term structure:** use VIX9D/VIX ≥ 1 on P. Inversion is more frequent here (about 20–40% of days in stressed years), so statistical power is better.
- **H5, Nasdaq level:** use VXN instead of the VIX in R1, as a robustness check only. The 0.92 correlation means it is not an independent test.

### Gaps
- None of these rules has a published ORB-specific backtest. All of them are untested hypotheses for this robot.
- No literature-based value was found for a VIX *change* rule (for example, a VIX up more than X% on T-1). That is left out deliberately rather than invented.

## Q6. Pitfalls: look-ahead, regime changes, multiple testing

### Takeaway
There are four main risks:
1. Silent look-ahead from the same-day CLOSE or the undocumented OPEN.
2. Calendar misalignment between the VIX and VIX3M files.
3. Too few inverted days to separate long from short.
4. Regime shifts (2020, the 0DTE era after 2022) that can flip the gamma-driven mechanism.

### Cited Findings
- **Same-day VIX is look-ahead.** Zarattini et al.'s short-side regression uses "the average VIX level on the same day", which is unknown at entry. Their regime chart uses the VIX at the open from paid 1-minute data, which is not equivalent to the Cboe CSV OPEN — [BTM PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **Full-sample terciles are look-ahead.** Gao et al. sort days into terciles using breakpoints from the full sample. Their volatility variable (first-half-hour realised volatility) is only known at 10:00 — [WP PDF](https://www.smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)
- **Data artefacts:** back-filled OHLC, stale opens, bad-tick lows and holiday rows are all present in the Cboe files (own computation; see Q4) — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)
- **Inverted days are clustered (own computation):**
  - 191 of 2,236 days (2018 to 23 November 2026) have VIX/VIX3M ≥ 1.
  - They concentrate in 2018 (53), 2020 (53) and 2025 (29), with 0 in 2023.
  - The result is effectively a test of three episodes, not 191 independent days — [VIX3M CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv)
- **0DTE and gamma regime:**
  - Momentum exists only on negative dealer-gamma days, 1996–2020 — [Baltussen et al.](https://www3.nd.edu/~zda/intramom.pdf)
  - 0DTE market-maker gamma is positive on average and strengthens reversal (snippet-level) — [Dim–Eraker–Vilkov](https://www.researchgate.net/publication/377984312_0DTEs_Trading_Gamma_Risk_and_Volatility_Propagation)
- **VIX1D history is short.** The free VIX1D file starts on 2022-05-13, and its OHLC is back-filled (O=H=L=C) for all of 2022 and 62 days of 2023 (own computation) — [VIX1D CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX1D_History.csv)
- **R1 "on" days cluster by year** (own computation; see the table in Q5): 217/251 in 2018, 40/252 in 2021, 17/250 in 2023 — [VIX CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)
- **Costs matter for ORB.** An independent replication of the QQQ ORB paper on five indices with CFD data reports gross returns reproduced but about zero net. Snippet-level, not read in full — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235)

### Inferences
- **Statistical power:** with about 95 trades per side on inverted days and a win rate near 45%, the standard error of the win rate is about 5 points. The 95% confidence interval is therefore about ±10 points, the same size as the long/short gap the user wants to explain. A VIX/VIX3M side-split cannot be conclusive on 2018–2026 data alone.
- **Multiple testing:** the candidate family is VIX vs VXN; level vs change vs VIX/VIX3M vs VIX9D/VIX; long vs short vs both; several thresholds. That easily reaches 20–50 tests, on top of the roughly 2,000 trials already run on the Nasdaq history (`CLAUDE.md`). Remedies:
  - pre-register R1 as the single confirmatory test, on data never used for the V10 (S&P 500 Dukascopy);
  - apply a Holm or Bonferroni correction to H2–H5;
  - never pick thresholds on the Nasdaq 2010–2026 history. A time split of the already-seen Nasdaq data is not a true out-of-sample test.
- **Regime breaks to report separately:** 2020 (COVID, extreme VIX with few days), 2022 (a bear market with the VIX mostly in contango: only 15 inverted days in 2022 despite the drawdown), and 2023–2026 (the 0DTE era, a lower VIX, and the 2025 inversion cluster).
- **The VIX does not include 0DTE options.** From general knowledge of the VIX methodology (not re-verified here; see Gaps), the VIX is built from options with roughly 23–37 days to expiry, and VIX1D exists to capture same-day expiries. The VIX is therefore a poor measure of the post-2022 0DTE gamma, and the free VIX1D history is too short to backtest 2018–2021.
- **Overlap with existing filters:** the VIX level is strongly linked to opening-range size and realised volatility. Reporting R1 without the incremental-value test from Q5 would re-discover the opening-range-size effect under another name.

### Gaps
- No source found that measures how 0DTE growth after 2022 changed ORB or intraday momentum returns on the Nasdaq 100 specifically. The 0DTE literature reviewed is about the S&P 500 and is snippet-level.
- The "23–37 days" VIX option window is stated from general knowledge of the VIX methodology and was not re-verified against Cboe's white paper in this session.
