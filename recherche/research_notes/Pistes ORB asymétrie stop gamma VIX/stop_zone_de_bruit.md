# Volatility-calibrated stops and "noise area" boundaries for opening-range / intraday momentum strategies on US equity indices

Research notes, 2026-11-24. Scope: the goal is to replace a stop set at a fixed multiple of the 5-minute opening range (OR) with a stop scaled on recent volatility or noise. The robot is a 5-min ORB at 9:30 NY on a Nasdaq 100 CFD, with the stop at 3 x OR and an exit at 15:50.

Source grading used below:
- **[P]** primary source, read in full (PDF text extracted).
- **[P-code]** primary code page, read through a summarising fetch tool; exact code lines quoted by the tool.
- **[S]** secondary or practitioner source, fetched.
- **[snippet]** search-result snippet only, not fetched; treat as unverified.

---

## 1. Zarattini, Aziz & Barbon, "Beat the Market" (SPY): noise-area definition, entries, trailing stops (VWAP), volatility sizing, results, robustness, follow-ups (QQQ / NQ / ES)

### Takeaway
The Noise Area is a time-of-day band around the open, set with the default parameters L = 14 days and VM = 1:
- **Width** at minute HH:MM is the 14-day mean of |Close(HH:MM)/Open(9:30) − 1|.
- **Gap adjustment:** the band is anchored on max/min(today's 9:30 open, yesterday's 16:00 close).

How the strategy uses it:
- **Entries:** only on band breaks, checked at HH:00/HH:30 from 10:00.
- **Exits:** at the opposite band (base model). In the improved model, a trailing stop at max(current band, VWAP) for longs (min for shorts).
- **Sizing:** targets 2% daily volatility using a 14-day standard deviation of daily returns, with leverage capped at 4.

Reported results on SPY, May 2007 to April 2024:
- 19.6% a year, Sharpe 1.33, maximum drawdown 25%, net of $0.0035/share commission plus $0.001/share slippage.
- The same rules on Nasdaq futures, Jan 2007 to Sep 2024, gave Sharpe 1.23 (cost assumptions not stated).

Robustness to lookback (5 to 90 days) and VM is reported as flat-to-favourable by the authors themselves. Independent follow-ups are thin.

### Cited Findings

**Paper identity and data**
- "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Carlo Zarattini (Concretum Research), Andrew Aziz (Peak Capital Trading / Bear Bull Traders), Andrea Barbon (Univ. St. Gallen / SFI). First version May 10, 2024; the version read is February 3, 2025 (SFI Research Paper 24-97). [P] — [PDF, Alexandria Univ. St. Gallen](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content); [SFI listing](https://www.sfi.ch/fr/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy)
- Data: SPY and VIX 1-minute OHLCV from IQFeed, May 2007 to April 2024; backtests in Matlab R2023a. [P] — [PDF §2](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

**Noise Area, exact definition (§3)** — [P] — [PDF §3, pp. 6-7](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
1. For each past day t−i (i = 1..14) and each time-of-day HH:MM: move(t−i, 9:30→HH:MM) = | Close(t−i, HH:MM) / Open(t−i, 9:30) − 1 |.
2. σ(t, 9:30→HH:MM) = (1/14) × Σ(i=1..14) move(t−i, 9:30→HH:MM). This is a separate average for every minute of the day, using only the previous 14 days.
3. Without gap adjustment: UpperBound = Open(t, 9:30) × (1 + σ), LowerBound = Open(t, 9:30) × (1 − σ).
4. With the gap adjustment that the paper uses:
   - UpperBound(t, HH:MM) = max(Open(t, 9:30), Close(t−1, 16:00)) × (1 + σ(t, 9:30→HH:MM))
   - LowerBound(t, HH:MM) = min(Open(t, 9:30), Close(t−1, 16:00)) × (1 − σ(t, 9:30→HH:MM))
   - After a gap down, the upper boundary is pushed up by the gap size; after a gap up, the lower boundary is pushed down.
- The boundaries are time-varying: average movement from the open grows over the day, peaking at 16:00. In the paper's simplified example, the move needed by 10:30 was −0.30%, half of what was needed by 15:30. [P] — [PDF p. 8](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- The authors present the time-varying boundaries as what sets the model apart from the volatility-breakout systems of Crabel (1990) and Kaufman (2020), and from academic intraday momentum models (Rosa; Baltussen et al.). [P] — [PDF p. 8](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Volatility Multiplier (§4.4):** UB = max(Open, Close(t−1)) × (1 + VM × σ) and LB = min(Open, Close(t−1)) × (1 − VM × σ). The paper uses VM = 1. [P] — [PDF §4.4, p. 21](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

**Entries and exits** — [P] — [PDF pp. 9, 11-14, 20-21](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Entry:** long if price is above the Noise Area, short if below.
- **Timing:** trading is restricted to HH:00 and HH:30 to limit overtrading. In the Figure 2 examples, trades execute at 10:30 although price had left the area a few minutes earlier. The first possible position is at 10:00 (§4.3).
- **Base exit:** at the market close (16:00), or on a cross of the opposite boundary, in which case the position is closed and reversed. Stop losses are also triggered only at the semi-hourly checks.
- **Improved exit:** a trailing stop at the current band, combined with VWAP:
  - Long trailing stop = max(UpperBound(t, HH:MM), VWAP(t, HH:MM))
  - Short trailing stop = min(LowerBound(t, HH:MM), VWAP(t, HH:MM))
  - VWAP is computed from market-hours data only (footnote 2).
- **Worked example (20 January 2022):** with the opposite-band stop the day lost −2.19%; with the upper band as trailing stop, −0.31%; with max(VWAP, UB), roughly break-even.

**Sizing and costs** — [P] — [PDF pp. 10, 15, 24-25](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Base sizing:** Shares(t) = AUM(t−1) / Open(t, 9:30), i.e. 100% notional.
- **Dynamic sizing:** Shares(t) = AUM(t−1) × min(4, σ_target / σ_SPY,t) / Open(t, 9:30).
  - σ_target = 2% daily.
  - σ_SPY,t = sample standard deviation (divisor 13) of the 14 daily returns ret(t−1)…ret(t−14).
  - Leverage is capped at 4x, "in line with mainstream brokerage policies".
- **Commission:** $0.0035/share. It falls to $0.0020 on about 20% of days, when trailing monthly volume exceeds 300,000 shares.
- **Slippage:** $0.001/share, from a live test in April 2024: over 1,000 market orders and more than $50M notional, mean slippage about $0.001 and median $0.0005 versus the minute's open price.

**Headline results, main body (SPY, May 2007 to April 2024, net of costs)** — [P] — [PDF Tables 1-4, A1](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

| Version | Total return | IRR | Vol | Sharpe | Daily hit ratio | MDD | Skew | Worst day |
|---|---|---|---|---|---|---|---|---|
| Opposite-band stop, 1x | 178% | 6.2% | 10.9% | 0.61 | 54% | 21% | −1.24 | −10.3% |
| Current band + VWAP, 1x | 380% | 9.7% | 7.7% | 1.24 | 43% | 12% | +1.29 | −4.8% |
| Current band + VWAP, dynamic sizing | 1,985% | 19.6% | 14.3% | 1.33 | 43% | 25% | +1.22 | −4.5% |
| SPY buy & hold | 227% | 7.2% | 20.2% | 0.45 | 54% | 56% | 0.08 | −10.9% |

- **Annualised alpha** of the dynamic version: 19.6%, beta −0.07.
- **Trade-level statistics** (Table 4):
  - Trades rise from 5,494 (opposite band) to 7,668 (band + VWAP); trades per day from 1.3 to 1.8.
  - Trade-level hit ratio falls from 53% to 37%. This is distinct from the 43% daily hit ratio above.
  - Average PnL per share: $0.10 and $0.09.
  - Worst trade: −8.6% (opposite band), −4.0% (band + VWAP, 1x), −2.9% (dynamic sizing).

**Further investigations, main body** — [P] — [PDF §4.1-4.5, pp. 17-24](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **VIX at the open:** Sharpe is about 1.50 when VIX > 6 (sic) and about 3.50 when VIX > 40. It falls again at higher VIX, where observations are few.
- **Daily patterns** (Table 5; unconditional row: 2,620 observations, 12 bps, t = 5.34, Sharpe 1.7). This "Sharpe 1.7" is a different calculation from the 1.33 portfolio Sharpe; do not mix them.
  - NR4: 660 observations, 22 bps, t = 5.14, hit 45%, Sharpe 3.2.
  - NR7: 367 observations, 16 bps, t = 3.07, Sharpe 2.5.
  - Inside days: 5 bps, t = 0.85.
  - Trend days: −2 bps, t = −0.24.
- **VM sweep:** total return falls as VM rises; the best risk-adjusted VM is about 1.5. The paper keeps VM = 1 "to maintain simplicity", although it is "not the most efficient setting".
- **Gamma proxy:** regressing strategy returns (bps) on the previous day's RSI(5) of SPY gives β = −3.25, p = 0.001. Higher RSI goes with lower momentum PnL, read by the authors as dealer long gamma.
- **Day of week:** Wednesday is best (18 bps, t = 3.42, Sharpe 2.4). Monday is not significant, which the authors relate to the first position only coming at 10:00, unlike the 5-minute ORB.

**Robustness and extensions, FAQ appendix (samples differ from the main body)** — [P] — [PDF FAQ Q6, Q13-Q15, Q18, Q22, Q24, pp. 31-42](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Q6, lookback for σ** (dynamic version; sample end not stated in the table):

| Lookback (days) | Total return | IRR | Sharpe | MDD |
|---|---|---|---|---|
| 5 | 1,856% | 19.1% | 1.31 | 21% |
| 10 | 1,570% | 18.0% | 1.23 | 23% |
| **14** | 2,108% | 19.9% | 1.35 | 23% |
| 20 | 2,060% | 19.7% | 1.33 | 23% |
| 25 | 2,189% | 20.2% | 1.35 | 23% |
| 30 | 1,941% | 19.4% | 1.31 | 23% |
| 60 | 1,842% | 19.0% | 1.31 | 25% |
| 90 | 2,757% | 21.7% | 1.50 | 13% |

  - The authors: Sharpe is "largely unaffected"; the best values are at 90 days.
- **Q14, the authors' answer to over-optimisation:** the ex-post optimal lookback (90 days, Sharpe 1.35 → 1.50) and VM (1.5, Sharpe 1.35 → 1.55) are not the published defaults.
- **Q13, futures, Jan 2007 to Sep 2024** (33 markets, 21 commodities and 12 equity indices; no cost assumptions given):

| Market | Total return | CAGR | Vol | Sharpe | MDD | Hit ratio | Skew |
|---|---|---|---|---|---|---|---|
| Nasdaq | 1,533% | 16.8% | 13.6% | 1.23 | 26% | 43% | 2.1 |
| S&P 500 | 2,501% | 19.8% | 14.9% | 1.32 | 23% | 43% | 2.9 |
| Russell | — | — | — | 0.45 | — | — | — |
| S&P 400 MidCap | — | — | — | 0.80 | — | — | — |

  - Average Sharpe across the 33 markets: 0.60. Diversified portfolio: 1.65. Only 2 instruments had a negative total return.
- **Q15, I-Star market-impact slippage** (Kissell large-cap parameters): Sharpe 1.17 versus 1.33, alpha still above 15%.
- **Q18, intraday seasonality:** trend continuation from 10:00 to noon, a pause at lunch, resumption from 14:00 to the close.
- **Q22, May 2007 to December 2024 sample:**

| Version | Total return | IRR | Vol | Sharpe | Hit ratio | MDD | Trades |
|---|---|---|---|---|---|---|---|
| Opposite band, 1x | 169% | 5.8% | 10.7% | 0.58 | 54% | 21% | — |
| Current band + VWAP, 1x | 393% | 9.5% | 7.6% | 1.23 | 44% | 12% | — |
| Current band + VWAP, dynamic | 2,382% | 19.9% | 14.3% | 1.35 | 44% | 25% | 7,964 |
| VWAP-only trailing stop, dynamic | 1,846% | 18.3% | 15.5% | 1.17 | 46% | 27% | 6,728 |

  - Note: this VWAP-only Sharpe of 1.17 and the I-Star Sharpe of 1.17 (Q15) are two different results.
- **Q24, post-publication:** 2024 +32.2%; January 2025 −1.2%.

**Reference code (Concretum Python)** — [P-code] — [Concretum Python backtest page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- Move from the open: `move_open = (close / open_price - 1).abs()`.
- Rolling σ per minute-of-day: `rolling(window=14, min_periods=13).mean()`, then `sigma_open = ...shift(1)`, so day t uses only earlier days.
- Previous close is dividend-adjusted (`prev_close_adjusted = prev_close - dividend`); bands are `max/min(open_price, prev_close_adjusted) * (1 ± band_mult * sigma_open)`.
- VWAP: cumulative (volume × HLC/3) / cumulative volume, reset each day.
- Timestamps: `min_from_open = minutes since 9:30 + 1`; trades happen where `min_from_open % 30 == 0`.
- Data: the Polygon loader keeps 9:30-15:59 bars. Per the summariser, the code does not handle early closes or fill missing minutes.
- Sizing volatility: `spy_ret.iloc[d - 15:d - 1].std()`. The summarising tool read this slice as 14 returns ending at day d−2, i.e. one extra day of lag versus the paper's formula. **This reading is not verified** against the raw code.

**Follow-ups and recognition**
- Á. Maróy, "Improvements to Intraday Momentum Strategies Using Parameter Optimization and Different Exit Strategies" (SSRN 5095349, announced 22 Jan 2025). [S, abstract only]
  - Per the forum abstract, the best exits ("VWAP", "VWAP & Ladder", "Ladder") give Sharpe above 3.0 and annualised returns above 50%, after optimising "all parameters".
  - Instruments, sample and out-of-sample protocol are not stated in the abstract; SSRN returned 403. — [Bear Bull Traders forum post](https://forums.bearbulltraders.com/topic/4002-improvements-to-intraday-momentum-strategies-using-parameter-optimization-and-different-exit-strategies/)
- The paper took 4th place at the Quantpedia Awards 2025. [snippet, page title only] — [FSI St. Gallen news](https://fsi.unisg.ch/de/newsdetail/news/quantpedia-awards-2025-fsis-barbon-and-team-secure-4th-place-with-intraday-momentum-strategy/)
- The authors publish a free TradingView indicator ("Concretum Bands") with adjustable VM and lookback. [P] — [PDF FAQ Q3](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

**For the adjacent axes (long/short asymmetry, VIX), from the same paper** — [P] — [PDF FAQ Q5, Q19-Q21](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Q5: both legs contributed positively on SPY; the long leg contributed slightly more.
- Q19: regressing short-trade PnL on the same-day average VIX shows no relation (p = 0.91).
- Q20: limiting shorts to high-VIX days does not improve compounded performance.
- Q21: taking shorts only below the 100, 150 or 200-day SMA "sacrific[es] a substantial portion of overall profitability".

### Inferences
- **Same object as the robot's diagnostic.** The noise width at 9:35, σ(9:30→9:35), is the 14-day mean absolute 5-minute move from the open. That is a close cousin of the robot's own "20-day average opening range". The robot's diagnostic (OR_today / OR_avg20 in the bottom quintile) therefore measures how far today's OR undershoots normal opening noise.
- **Tightening, not widening, is what the paper rewards.** Going from the wide opposite-band stop to the current band + VWAP stop:
  - lowered the daily hit ratio (54% → 43%) and the trade-level hit ratio (53% → 37%);
  - raised the trade count by about 40%;
  - doubled the Sharpe, flipped skew from −1.24 to +1.29, and halved the worst day.
  - In other words, the wide "outside the noise" stop had the worst left tail.
- **Entry timing differs from the robot's.** The paper's semi-hourly trading grid and first entry at 10:00 mean it is not a 9:35 ORB. Reusing the Noise Area for a 9:35 entry is an adaptation; see question 5.
- **NQ evidence is the closest to the robot.** The Nasdaq futures result (Sharpe 1.23, MDD 26%) is about one notch below ES (1.32). No costs are stated, so it cannot be compared directly with a CFD with spread.

### Gaps
- Maróy's full paper (exit definitions, instruments, in-sample vs out-of-sample) could not be read: SSRN returned 403.
- No independent, peer-reviewed replication of the Noise Area strategy on QQQ, NQ or a Nasdaq 100 CFD with explicit costs was found. The NQ and ES futures numbers are the authors' own FAQ results without stated costs.
- The FAQ lookback table (Q6) does not state its sample end date.
- The paper does not explain how VWAP is defined for futures or CFDs (no consolidated volume) or how early-close sessions are handled.

---

## 2. Other volatility-scaled stop rules for ORB / intraday breakouts: ATR stops (which ATR, length, fraction), Crabel stretch, Williams volatility breakout, Kaminski & Lo

### Takeaway
- **The only published, ORB-specific volatility stops with explicit defaults come from the same research group:**
  - 10% of the daily 14-day ATR from the entry price, exit at the close, in the stocks-in-play paper of Zarattini, Barbon & Aziz (2024).
  - An in-sample "best" of 5% of ATR14 with an end-of-day exit, on QQQ/TQQQ, in Zarattini & Aziz (2023/2025).
- Both are much tighter than 3 x OR. They come from tests with zero or ETF-level costs.
- Crabel's "stretch" (10-day mean of min(High − Open, Open − Low)) is the classic noise-from-the-open unit, but the sources found use it as an entry offset, not as a stop.
- Kaminski & Lo give the theory: stops cost expected return under a random walk and add value only if momentum is present.

### Cited Findings

**Zarattini & Aziz, "Can Day Trading Really Be Profitable?" (QQQ/TQQQ)**
- First version April 24, 2023; the version read is September 22, 2025. [P] — [Concretum PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf); [SSRN 4416622](https://papers.ssrn.com/abstract=4416622)
- **Base rules:** [P] — [PDF §2, Table 1](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
  - Direction = the first 5-minute candle; no trade on a doji.
  - Entry at the open of the second 5-minute candle.
  - Stop at the low of the first candle for a long (high for a short), so R ≈ 1 OR from the entry.
  - Target 10R or end of day; 1% risk per trade; 4x leverage cap.
  - Commission $0.0005/share and **no slippage**. Sample January 1, 2016 to February 17, 2023.
- **QQQ results:** [P] — [PDF pp. 6-8, 13](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
  - 1,795 trades, win rate 24%, average +0.13R per trade.
  - The text says 675% total, 31% a year, Sharpe 1.12. Table 2 says 676%, 33% a year, vol 29%, Sharpe 1.13, MDD 22% (internal discrepancy in the paper).
  - Annualised alpha 33%, p = 0.0025.
- **TQQQ results:** 1,484% total, 48% a year (the text says 46%), vol 39%, Sharpe 1.19, MDD 28%, +0.18R per trade. [P] — [PDF pp. 10-13](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
- **ATR sensitivity (§4):** [P] — [PDF §4, pp. 13-14](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
  - The OR-extreme stop was replaced by "a fraction of the 14-day average true range (ATR)", reasoning that "a fixed percentage of the ATR should be a better and more stable representation of the volatility … during the day".
  - Targets from 1R to 10R and end of day were swept.
  - Best average PnL in R (Figure 7 heatmap): "tight stop losses (5% of the 14-day ATR)" with an end-of-day exit. On TQQQ: +9,350%, alpha 93%, from January 2016 to February 2023.
  - The authors warn this "can … be considered unrealistic as our model assumed no slippage". Example: TQQQ ATR14 ≈ $1.60 at ≈ $25, so the stop is about $0.08 wide.
- **Leverage cap:** 60% of QQQ trades were sized about 40% below the 1%-risk size, because tight stops plus 1% risk hit the 4x cap. The unconstrained version made 1,630%. [P] — [PDF pp. 9-10](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)

**Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy for the U.S. Equity Market" (stocks in play)**
- Dated February 16, 2024; SFI 24-98; SSRN 4729284. [P] — [PDF, Alexandria Univ. St. Gallen](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- The paper states that "a common approach is to set the stop loss at a percentage of the 14-day average true range (ATR)". [P] — [PDF p. 6](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- **Rules:** [P] — [PDF §2.1, §4](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
  - Direction = the first 5-minute candle.
  - Entry by stop order at the 5-minute high (bullish candle) or low (bearish candle).
  - **Stop loss at 10% of ATR distance from the executed entry price.**
  - Flat at 16:00 if not stopped; 1% capital risk per trade; 4x cap.
  - Commission $0.0035/share; universe of about 7,000 US stocks, 2016 to 2023.
  - Filters use the previous 14 days: price > $5, average volume ≥ 1M, ATR14 > $0.50.
- **Results:** [P] — [PDF Tables 1-2, Fig. 4](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
  - All eligible stocks: 29% total, 3.2% a year, Sharpe 0.48, hit 41.4%, MDD 13%.
  - Top-20 by opening-range relative volume (≥ 100%): 1,637% total, 41.6% a year, vol 14.8%, Sharpe 2.81, hit 48.4%, MDD 12%.
  - By relative volume: average PnL −0.02R when it is below 100%, +0.08R above 100%, +0.38R above 30x.
- **ATR definition:** the paper's footnote describes Wilder's (1978) ATR as an average of true range over typically 14 sessions, with true range including the previous close. It does not say whether a simple mean or Wilder smoothing is used. [P] — [PDF p. 6, fn. 1](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- **Literature cited in the paper's review (secondary for us):** [P, as cited] — [PDF pp. 4-5](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
  - Tsai et al. (2018), on the DJIA, S&P 500 and Nasdaq: the largest ORB profits come from opening ranges of about 5 minutes; no stop or target was tested.
  - Lundström (2017), on crude oil and S&P 500 futures: ORB profitability grows with volatility.
  - Wu et al. (2020), on Taiwan index futures 2007-2018 with a genetic algorithm: a profit target hurt; adding a stop loss improved profitability.

**Independent replication on index CFDs (practitioner, self-published)** — [S] — [MQL5 blog, T.-P. Krueger, 25 Sep 2026](https://www.mql5.com/en/blogs/post/776235)
- Replicates the QQQ ORB above unchanged (stop = other side of the first candle, 10R or session close) on NQ, SPX, Dow, DAX and FTSE CFDs, cash session, January 2015 to June 2026, about 2,900 sessions each.
- Costs are charged per trade as spread plus slippage: NQ 2.5 points, SPX 0.8 points. Trades with initial risk below 2x round-trip cost are skipped.

| Market | Gross avg R | Gross t | Gross hit | Net avg R | Net t |
|---|---|---|---|---|---|
| NQ | +0.131 | 2.9 | 23.2% | +0.002 | 0.0 |
| SPX | +0.119 | 2.4 | — | −0.081 | −1.6 |

- On NQ, the rule beats a random direction by +0.124R net (t = 2.1).
- The page reports two different gross figures for the FTSE (internal inconsistency).

**Crabel "stretch"** — [S] — [Oxford Strategies, Crabel ORB implementation](https://oxfordstrat.com/?p=4778)
- Noise(i) = min(High(i) − Open(i), Open(i) − Low(i)); Stretch = SMA(Noise, 10) × multiple (1 in that implementation).
- Long entry is a buy stop at Open + Stretch; short entry a sell stop at Open − Stretch. Attributed to Crabel (1990), *Day Trading with Short Term Price Patterns and Opening Range Breakout*.
- That implementation's stop (Entry ∓ 6 × ATR(20)) is a **daily-bar, multi-day** rule on 42 futures. It is not an intraday ORB stop.
- Search snippets describe the stretch as a "10-day average of the differences between the open … and the closest extreme". [snippet] — [TradingView, PumpC ORB Stretch](https://www.tradingview.com/script/hzvhXCy9-PumpC-Opening-Range-Breakout-ORB-Stretch-Range)

**Kaminski & Lo, "When Do Stop-Loss Rules Stop Losses?"**
- *Journal of Financial Markets* 18 (2014) 234-254, DOI 10.1016/j.finmar.2013.07.001.
- They give an analytical framework for the effect of stop-loss rules on a strategy's expected return and volatility. Empirically, on a buy-and-hold in index futures using daily data: "certain stop-loss policies can increase expected return while substantially reducing volatility" at longer sampling frequencies. [S, abstract] — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html)
- Per the working-paper abstract: under the random walk hypothesis, simple 0/1 stop-loss rules always decrease expected return; in the presence of momentum they can add value. [snippet] — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876); [SIFR working paper](https://ideas.repec.org/p/hhs/sifrwp/0063.html)

### Inferences
- **Which ATR.** Every ORB paper found uses the **daily** ATR(14), computed from previous sessions, expressed as a percentage (5-10%) and applied as a fixed distance from the entry. None uses an intraday ATR or a fraction of today's range.
- **Approximate size versus the robot's stop.** In the QQQ example, TQQQ ATR ≈ 6.4% of price, so QQQ ATR ≈ 2.1% of price. That puts 10% of ATR at about 0.2% of price and 5% at about 0.1%. Both are almost certainly less than 1 x a typical 5-minute OR, so far tighter than 3 x OR. To be checked on the robot's own data.
- **Kaminski & Lo framing.** An ORB is an intraday momentum bet. Whether a tight or wide stop adds value depends on whether price keeps going against the position after the stop level is touched (momentum, where a tight stop helps) or reverts (noise, where a tight stop hurts). The robot's observation (37-43% full-stop rate on small-OR days) does not by itself say which regime applies.
- **Costs on a CFD.** The Krueger replication is the most relevant cost evidence for a Nasdaq 100 CFD robot. Even a stop at 1 x OR roughly zeroes the net edge once about 2.5 NQ points of round-trip cost are charged. Rules from the tight-ATR stop family therefore need the robot's own spread model before any conclusion.

### Gaps
- **Larry Williams volatility breakout** (entry = Open ± k × previous day's range, with k "usually below 1" and k = 0.5 called "classic"): only unfetched search snippets were found. Williams' original stop rules for S&P futures were not verified. — [snippet] [TradingView script](https://in.tradingview.com/script/ZHInQrDP-Larry-Williams-Volatility-Breakout-Jayadev-Rana/); [WH SelfInvest](https://www.whselfinvest.de/en/trading_strategies_56_volatility_break_out_larry_williams_free.php)
- Crabel's own stop rules for intraday ORB (from the 1990 book) could not be checked. Only third-party implementations were found.
- Whether Zarattini et al. use Wilder smoothing or a simple mean for ATR14 is not stated.
- Kaminski & Lo's full text was not read. Per the abstract, the test is a buy-and-hold on daily index-futures data, with gains reported "at longer sampling frequencies". It is not intraday.
- **[snippet]** QuantConnect has a community recreation of the stocks-in-play ORB with an ATR-based stop, not fetched. — [QuantConnect research 18444](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)

---

## 3. Evidence that volatility-scaled stops reduce stop-outs without destroying expectancy (intraday index strategies)

### Takeaway
Only one published comparison of an OR-based stop with an ATR-based stop was found: Zarattini & Aziz §4 on TQQQ, OR-extreme stop (≈ 1 x OR) versus % of ATR14, giving 1,484% versus 9,350%. It is in-sample and assumes zero slippage. No comparison was found with realistic costs, out of sample, or for stops wider than 1 x OR, which is the robot's regime.

The evidence that does exist points the other way from the premise:
- In Concretum's work, the volatility- or noise-calibrated stops that improved results were tighter. They increased stop-outs and lowered hit ratios while raising R-expectancy or Sharpe.
- The widest, "outside-the-noise" stop (the opposite band) had the worst skew and tail.
- The literature therefore does not show that fewer stop-outs means better expectancy, and the tight-stop results are fragile to costs on CFDs.

### Cited Findings
- **Beat the Market (SPY):** going from the opposite-band stop to current band + VWAP (both noise-calibrated, the second much tighter):
  - daily hit ratio fell 54% → 43%; trades rose 5,494 → 7,668;
  - Sharpe rose 0.61 → 1.24; skew went −1.24 → +1.29; worst day −10.3% → −4.8%. [P] — [PDF pp. 11-14, Table A1](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Beat the Market, VWAP-only stop:** this looser stop lowered the trade count (7,964 → 6,728) and raised the hit ratio (44% → 46%), but cut Sharpe from 1.35 to 1.17 (May 2007 to Dec 2024). [P] — [PDF FAQ Q22](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **QQQ/TQQQ ORB:** the 5%-of-ATR14 stop with end-of-day exit maximised average R across a stop × target grid.
  - On TQQQ it gave +9,350% (January 2016 to February 2023), versus +1,484% for the base OR-extreme stop with a 10R target.
  - It is in-sample, assumes no slippage, and the authors flag that it may be unrealistic. [P] — [PDF §4](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
- **QQQ ORB, base version:** the stop is about 1 x OR, the win rate is only 24% and the average is +0.13R. Expectancy comes from the right tail (up to 10R), not from the hit rate. [P] — [PDF p. 8](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
- **Stocks-in-play ORB:** with a 10% ATR14 stop, the hit ratio was 41-48%. The authors attribute the profitability to the relative-volume selection, not to the stop width. [P] — [PDF Tables 1-2](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- **Krueger replication, NQ CFD:** gross +0.131R, net +0.002R with about 2.5 points of cost at a 1 x OR stop. Cost per R grows as the stop tightens. [S] — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235)
- **Kaminski & Lo:** stop-loss rules reduce expected return under a random walk and can add value only with momentum. [snippet] — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876)
- **Prior-day compression (NR4) days** were the best subset for the noise-area strategy on SPY: 22 bps, t = 5.14, Sharpe 3.2, against 12 bps unconditional. NR4/NR7 measure prior *daily* ranges, not today's opening range. [P] — [PDF Table 5](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

### Inferences
- **The robot's evidence is the opposite of the published one.** Its own plateau sits at 2.5-4 OR. Concretum's optimum sits at 5-10% of ATR14, which this note estimates (unverified, see question 2) to be at or below about 1 OR. The two are not necessarily contradictory: they come from different cost structures and different payoff shapes.
  - The Concretum tests have near-zero costs, 1%-risk sizing and a 4x cap that limits position size when stops are tight.
  - The robot trades a CFD with spread.
  - The robot's empirical plateau is therefore the better guide to the width level. The literature's useful contribution is the **unit**: something known before the open and scaled to recent noise, in place of today's OR alone.
- **Small-OR days are, in average-OR units, below the plateau.** The robot sees bottom-quintile days at OR ≈ 0.55-0.6 x the 20-day average OR. On those days, 3 x OR_today ≈ 1.65-1.8 x the average OR, below the 2.5-4 plateau measured in "typical OR" units.
  - This fits the observed 37-43% full-stop rate.
  - It suggests the problem is the unit (today's OR), not the multiplier.
  - This is computed from the robot's own in-sample numbers, not from the literature.
- **What to measure.** The right test is the change in expectancy per trade (in account %, not only in R) and in tail risk when stops are widened on small-OR days, not the change in stop-out frequency. Beat the Market shows that a lower hit rate can coexist with a doubled Sharpe.
- **No conclusion about small-OR days should be drawn from the NR4 result.**
  - NR4/NR7 compress the prior daily range, while the robot's diagnostic compresses today's 5-minute OR.
  - `recherche/critique-v10.md` records that NR4/NR7 "rien n'a tenu" on the robot.
  - The robot's bottom-quintile OR days are its weakest: +0.12 R per day in 2018-2026 and −0.06 R in 2010-2017.
  - Whether to widen the stop on those days or skip them is open; only a pre-registered test can settle it.

### Gaps
- No published study compares the stop-out frequency and expectancy of OR-multiple stops against ATR- or noise-scaled stops on SPY/QQQ/ES/NQ or the index CFDs with realistic costs, out of sample, or for stops wider than 1 x OR. The only comparison found (TQQQ, Zarattini & Aziz §4) is in-sample, zero-slippage and limited to tight stops.
- No published data on ORB stop-outs conditional on OR size relative to its average.
- The Concretum ATR-stop heatmap (QQQ/TQQQ Figure 7) is only shown graphically; no numerical table of average R per stop fraction is given.

---

## 4. Look-ahead traps: what is known at 9:35 NY, gap handling, holidays and half days

### Takeaway
Everything the noise area or ATR rules need is known at 9:35 NY, as long as:
- σ and ATR use only completed prior sessions (t−1 … t−14, shifted by one day);
- the gap anchor is the previous day's **16:00 cash close**, and today's anchor the 9:30 price;
- bar timestamps (start vs end of bar) are handled consistently;
- early-close sessions are excluded from the per-minute averages for minutes after their close.

The traps specific to CFDs (broker daily bars and closes, tick-volume VWAP, DST) are not covered by any source found.

### Cited Findings
- The σ formula uses days t−1 to t−14 only. The bands use Open(t, 9:30) and Close(t−1, 16:00), both known at 9:30. [P] — [PDF §3](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Concretum's code applies `shift(1)` to the per-minute rolling mean, so the current day is excluded, with `min_periods=13`. [P-code] — [Concretum Python page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- Concretum's code defines `min_from_open = minutes since 9:30 + 1` and trades when it is divisible by 30. With bars stamped at their start, the "10:00" decision uses the bar stamped 9:59, i.e. the price at 10:00. [P-code] — [Concretum Python page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- The sizing volatility in the paper uses ret(t−1) to ret(t−14). The code reportedly lags one more day; that reading is unverified. [P] / [P-code] — [PDF p. 15](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content); [code page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- The previous close is adjusted for SPY dividends on ex-dates in the code. [P-code] — [Concretum Python page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- VWAP is computed from market-hours data only. [P] — [PDF fn. 2](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Per the summariser, the reference code keeps 9:30-15:59 bars, does not handle early closes, and does not fill missing minutes. [P-code] — [Concretum Python page](https://www.concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/)
- The stocks-in-play paper computes all filters (volume, ATR14) "over the previous 14 days … to avoid making decisions based on hindsight". [P] — [PDF §2.1](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- The QQQ ORB enters at the open of the second 5-minute candle (9:35), after the opening range is complete; the stop is known at entry. [P] — [PDF Table 1](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)
- Krueger's CFD replication restricts to the cash session and skips trades whose initial risk is below 2x round-trip cost. [S] — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235)

### Inferences
These points are unsourced; they are flagged as practitioner reasoning.

- **Gap anchor on a CFD.** A Nasdaq 100 CFD trades almost 23 hours a day. Its broker "daily close" (often at the server's midnight or 17:00 NY) is **not** Close(t−1, 16:00). The gap adjustment must use the price at 16:00 NY from the M1 series, and "Open(t, 9:30)" must be the price of the 9:30 NY M1 bar. Both must come from the same instrument as the trades.
- **ATR on a CFD.** An ATR14 from broker D1 bars mixes overnight and cash-session ranges. To follow the papers, which use ETF or stock sessions, build daily H/L/C from 9:30-16:00 M1 bars. True range then includes the previous 16:00 close, which brings the overnight gap in.
- **VWAP on a CFD.** CFD "volume" is tick volume. A VWAP built from it is an approximation of the paper's VWAP. Using futures or QQQ volume as a proxy would need time alignment.
- **DST.** In the weeks when the US and the broker's server time zone switch daylight saving time on different dates (March, and late October to early November), "9:30 NY" moves by one hour in server time. Per-minute σ averaging must be keyed on NY time, not server time.
- **Early-close sessions** (the US cash market closes at 13:00 ET on some holiday-adjacent days):
  - for minute offsets after 13:00, exclude those days from σ, or require at least 13 of 14 valid observations as the code does;
  - skip trading those days, or force the exit before the early close.
- **Holidays.** Rolling windows should count trading sessions, not calendar days.
- **Within-bar ordering.** With M1 bars, a stop and the 15:50 exit, or a stop and the entry, can fall in the same bar. Use conservative fill ordering (stop first).
- **Parameter choice.** VM = 1.5 or a 90-day lookback was chosen ex post by the authors (FAQ Q14). Using them as defaults would import look-ahead in parameter choice. Keep L = 14 and VM = 1.

### Gaps
- No source discusses CFD-specific session definitions, broker daily-bar conventions, or VWAP from tick volume for the noise-area method.
- No source specifies how to handle the 15:50 exit (versus 16:00) when σ is calibrated on closes up to 16:00. Using σ for minute offsets up to 15:50 is a natural choice, but not sourced.

---

## 5. One or two simple, fully specified rules with literature defaults (no optimisation), testable on S&P 500 and Nasdaq data

### Takeaway
Two rules can be specified with only published default parameters:
- **(A) Noise-area stop, "NA-14":** the opposite Concretum boundary, L = 14, VM = 1, gap-anchored, widening through the day.
- **(B) ATR-percentage stop, "ATR-10":** a fixed distance of 10% of the daily ATR14 from the fill.

Rule A is the only one built on typical noise rather than on today's OR. However, nothing shows that the pure noise band is wider than 3 x OR on small-OR days; early in the session it is probably narrower.

That is why Rule A is specified in **floor form**: the stop is the farther of (entry ∓ 3 x OR) and the opposite noise band. This adds no new parameter, and it matches the "au moins égal à une mesure du bruit" wording of Axe 2 in `recherche/critique-v10.md`.

Rule B is a tight-stop regime, far from the robot's 2.5-4 OR plateau, and needs the CFD cost model before any conclusion.

A third, data-driven floor (C) follows directly from the robot's diagnostic, but its parameters are in-sample and it is listed as such.

### Cited Findings
Parameter provenance:
- **Noise area:** lookback 14 days, VM = 1, σ per minute-of-day from |Close(HH:MM)/Open(9:30) − 1|; UB/LB anchored on max/min(Open(t, 9:30), Close(t−1, 16:00)). [P] — [PDF §3, §4.4](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Opposite-band exit:** the paper's base exit ("crossover to the opposite boundary"). Stops are evaluated only at HH:00/HH:30; positions are closed at the close. Result at 1x on SPY 2007-2024: Sharpe 0.61, hit 54%, MDD 21%, skew −1.24. [P] — [PDF pp. 9-11, Table 1](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Optional volatility sizing:** σ_target 2% daily; σ = 14-day standard deviation of daily returns; leverage cap 4. [P] — [PDF p. 15](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **ATR stop:** 10% of the 14-day ATR from the executed entry price; exit at the close; 1% risk per trade; 4x cap (stocks-in-play ORB). [P] — [PDF §2.1](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- **The 5% ATR14 variant** is an ex-post heatmap optimum without slippage; it is not a default. [P] — [PDF §4](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf)

### Inferences
The rule specifications below are this note's construction: adapting the papers' parameters to a 9:35 ORB stop is not something the papers do.

**Rule A — "NA-14" noise-area stop for the ORB (floor form is the default)**
- **Inputs, all known by 9:35 NY:**
  - O_t = price at 9:30:00 NY (open of the 9:30 M1 bar).
  - C_{t−1} = previous session's 16:00 NY price (close of the 15:59 M1 bar).
  - For each minute offset k = 1…380 (9:31…15:50): σ_t(k) = (1/14) Σ_{i=1..14} | P_{t−i}(9:30+k) / O_{t−i} − 1 |.
    - P_{t−i}(9:30+k) is the close of the M1 bar ending at 9:30+k.
    - The sum runs over the 14 most recent full sessions, excluding today; require ≥ 13 valid values, as in the reference code.
  - UB_t(k) = max(O_t, C_{t−1}) × (1 + 1.0 × σ_t(k)); LB_t(k) = min(O_t, C_{t−1}) × (1 − 1.0 × σ_t(k)).
- **Entry:** unchanged (the robot's 5-min ORB).
- **Update times:** τ ∈ {9:35, 10:00, 10:30, …, 15:30}, i.e. the paper's HH:00/HH:30 grid plus the entry time. E is the executed entry price and OR_t today's 9:30-9:35 range.
- **Stop, floor form (default):**
  - At each τ, set a resting stop order at:
    - long: S_t(τ) = min(E − 3 × OR_t, LB_t(τ));
    - short: S_t(τ) = max(E + 3 × OR_t, UB_t(τ)).
  - It executes intraday like the current stop, and is moved only at the next τ.
  - σ_t(k) is not strictly monotonic in k, so the stop may move in either direction between updates, but never nearer than 3 x OR.
- **R and sizing (default):**
  - R_t = max over τ of |E − S_t(τ)|. It is known at entry, because every σ_t(τ) is known at 9:35.
  - Lots are sized so that a loss of R_t equals the usual risk per trade. A stop-out then never exceeds 1R, before gaps and slippage.
  - Consequence: lots shrink on every day where the band at a later τ lies beyond 3 x OR, not only on small-OR days.
  - The paper itself sizes by a volatility target, not by stop distance, so this choice is not from the literature.
- **Pure variant (not default):**
  - Long: exit when the M1 close at a τ is below LB_t(τ). Short: exit when it is above UB_t(τ).
  - This is the paper's base opposite-band exit, without the reversal. It can be narrower than today's stop early in the session.
- **Time exit:** 15:50 (robot); the paper exits at 16:00.
- **Notes:**
  - At 9:35 the band sits only about σ_t(5) beyond min(O_t, C_{t−1}). It widens through the day, consistent with the paper's observation that noise grows toward 16:00 (−0.30% by 10:30 vs about 2x that by 15:30 in its example).
  - On small-OR days, nothing found shows the band beyond 3 x OR at 9:35-10:00. The floor form protects that case; whether the band exceeds 3 x OR later in the day is an empirical question for the robot's data.
  - On gap-up days the long band is anchored below the previous close, so it is very wide; the mirror case applies to shorts on gap-down days.
  - The paper's "current band + VWAP" trailing stop cannot be used as the initial stop for a 9:35 ORB entry. Price at 9:35 is usually inside the Noise Area, so the current band (UB for a long) would sit above price and exit immediately. It becomes usable only after price closes beyond the current band.
  - The paper's base-model profile (hit 54%, skew −1.24, worst SPY day −10.3% at 1x) comes from entries at 10:00 or later on a band break, where the opposite band is about 2σ from the entry. It does **not** transfer to a 9:35 entry near the open, so no expected profile is claimed.
- **Testing:** report the full-stop rate by OR/avgOR quintile, expectancy in account %, skew and worst day versus 3 x OR.
  - Project constraint (from `recherche/critique-v10.md` and the repo CLAUDE.md): NAS100 2010 → 18/11/2026 has already been seen in full, so it can describe but not judge.
  - The designated judge is the never-loaded Dukascopy US500 2018-2026 bid/ask data, with the rule written in advance and judged once. US30 2024-2026 is reserved for an idea that does not depend on the breakout edge.
  - Costs per the project method: real spread + 1 point slippage per fill, then 2-3 points as a stress test.
- **Sizing effect.** The robot's lot size is set from the stop distance at constant risk (Confort profile: stop x3, lots ÷3). Any rule that widens the stop (Rule A in floor form, or Rule C) means smaller lots on the days it widens. The end-of-day payoff in R therefore shrinks on exactly the days whose stop is widened. This is why expectancy must be judged in account %, not in stop-out rate.

**Rule B — "ATR-10" fixed volatility stop**
- **ATR14:** from the 14 completed cash sessions t−1…t−14, TR_j = max(H_j, C_{j−1}) − min(L_j, C_{j−1}), with H/L/C taken from 9:30-16:00 M1 data.
  - Default: **ATR14 = simple mean of the 14 TR values**, the literal reading of "ATR over the previous 14 days". Wilder's smoothing is a variant; the paper does not say which it uses.
- **Stop:** distance D = 0.10 × ATR14 from the executed entry price, fixed for the day; exit at 15:50 if not stopped.
- **Sizing (paper):** risk 1% of equity at D, leverage cap 4x.
- **Cost check before testing:** compute cost/R = (round-trip spread + 2 x 1 point slippage) / D on the CFD. Krueger's 2.5-point NQ cost was enough to zero a 1 x OR stop, and D is likely smaller than 1 x OR (see question 2).
- **Do not substitute the 5% variant as a default.**

**Rule C — data-driven floor (NOT literature; in-sample, flag as such)**
- D_t = max(3 × OR_t, 2.5 × mean(OR_{t−1…t−20})).
- Rationale: on bottom-quintile days, 3 × OR_t ≈ 1.65-1.8 average ORs, below the robot's 2.5-4 plateau expressed in average-OR units. The floor lifts those days to the plateau's lower edge and leaves other days unchanged.
- Both 2.5 and the 20-day window come from the robot's own already-seen NAS100 backtest (2010-2026, fully seen).
  - The only clean judge is the never-loaded US500 Dukascopy 2018-2026 data, used once with the rule frozen in advance; then NAS100 data from 19/11/2026 and demo trades.
  - Note that the 2.5-4 OR plateau was measured on NAS100 and may not transfer to US500 in the same units.
- **Closest literature-unit alternative:** replace mean(OR) with the Crabel stretch (10-day SMA of min(H−O, O−L)) or with the Concretum noise width O_t × σ_t(k). The multiplier would still have to be set, which this research did not find in any source.

### Gaps
- None of the three rules has a published backtest as an ORB stop on index data with CFD costs. A only has the analogous "opposite-band" result on SPY from 10:00 entries; B only has stock and leveraged-ETF ORB results with zero or low costs.
- No literature default exists for a multiplier on a pre-open noise unit (stretch or σ) used as an ORB stop. The VM = 1 default applies to entry boundaries in Beat the Market, not to stops placed around an ORB entry price.
