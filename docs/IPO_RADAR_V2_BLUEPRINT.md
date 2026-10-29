# IPO Radar 2.0 — Engineering & Investment Research Blueprint
Status: PROPOSAL / NOT DEPLOYED · 2026-10-30
Branch: feature/investment-agent-v2-plan
Owner: IPO Radar project

## 0. Scope and non-negotiable rules
- US: NASDAQ/NYSE. Germany: Xetra (XETR) and Frankfurt (XFRA). No other markets in the MVP.
- Exactly **two** top-level mobile views: Stock Opportunities and IPO Opportunities.
- English stock identifiers, Arabic UI; optional EUR/USD base currency; never confuse quote currency, reporting currency and base currency.
- Research-only agent: no broker access, no real-money order execution. 0–3 qualified weekly stock candidates, never pad to three.
- Prices/targets/profit are conditional; no claims of guaranteed profits, nor invented confidence probabilities.
- Keep existing PWA, GitHub repo, service worker and OneSignal integration. Protect keys and avoid public redistribution of licensed quotes.
- Existing production app remains on main. Implement and validate V2 separately, merge only with controlled rollout.

## 1. Verified baseline (2026-10-30)
- Files: index.html, scanner.py, sw.js, manifest.webmanifest, onesignal/OneSignalSDKWorker.js, .github/workflows/daily.yml, tests/test_scanner.py, data/signals.json.
- GitHub Actions scheduled scans run successfully, and GitHub Pages PWA is installed on Samsung; manual web push was received.
- Latest captured dataset: 160 research leads, mostly international IPO-related news, **not** 160 investable companies.
- SEC EDGAR and Finnhub source statuses: not_configured. Existing scanner does not include equity OHLCV, corporate fundamentals, risk scoring or recommendation lifecycle.
- OneSignal automatic push log reported "All included players are not subscribed". Confirm OneSignal audience/segment and subscription ID, then test without exposing secret. Prior app push test is not proof the scheduled push works.
- Existing data is repository JSON; unsuitable for private personalized trade data or scalable timeseries.

## 2. User-facing mobile design
Home: only two large cards:
1. Stock Opportunities — up to 3 weekly research setups, state, broker/exchange, ticker, last verified quote, entry zone, stop, target, horizon, R:R, net estimated outcome at user's capital; selector ALL/US/DE. A compact top bar permits settings, capital, alerts, evaluation history without extra main navigation.
2. IPO Opportunities — filings, announced/listed stage, official vs estimated event dates, valuation when documented, risk category, post-listing watching.
Detail drill-down, not extra home sections: evidence with source+as-of, chart, indicators, catalysts, risk, alternatives, recommendation timeline, cash-flow/risk calculator.
State labels: WATCH_ENTRY, ACTIVE_SIMULATED, TARGET_TOUCHED, STOP_TOUCHED, INVALIDATED, EXPIRED, CANCELLED, NO_DATA. User actual trades are separate from simulation, entered voluntarily.
Never label fictional/demo prices as current quotes; explicit SAMPLE/DATA_DELAYED/BLOCKED states.

## 3. Technology architecture and migration
PWA (existing URL) -> protected read API / Supabase Row Level Security -> PostgreSQL canonical objects and snapshots.
GitHub: code, CI, tests, release deployments, low-frequency scheduled batch research.
Python packages by responsibility:
- sources/us_sec.py, ipo_deutsche_boerse.py, price_vendor.py, fundamentals.py, news.py, macro.py, fx.py
- domain/instruments.py (ISIN, MIC, venue, local currency, primary listing, active/delisted, corporate actions)
- engine/validate.py, technicals.py, fundamentals.py, screen.py, score.py, risk.py, rank.py, ipo.py, lifecycle.py, backtest.py
- jobs/daily_eod.py, weekly_picks.py, intraday_monitor.py, ipo_refresh.py, push_dispatch.py
- api/ read-only authenticated outputs; ui/ PWA.
Persistence: instruments, exchange_sessions, quote_bars, fundamental_snapshots, news_events, filing_events, ipo_events, strategy_versions, evaluations, recommendations, recommendation_events, simulated_fills, user_trades, push_subscriptions, notifications, run_status.
Prefer PostgreSQL/Supabase to JSON for recommendation lifecycle, history, idempotency and concurrent job safety. Enforce primary keys and row-level security; aggregate raw OHLCV retention as licensing/storage permits.
First build v2 in a branch and staging environment. Production v1 keeps working until tests pass and end-to-end device notification is confirmed.
If intraday 5–15-min monitoring needs reliable cadence, migrate Python jobs to Cloud Run Jobs + Cloud Scheduler or equivalent; GitHub schedules have no timing SLA. Do not provision paid cloud services without owner approval.

## 4. Data sourcing and licenses
- US prices/exchanges and DE XETRA/Frankfurt: compare EODHD (US, XETRA, F; delayed/EOD/intraday tiers) with licensed vendors; independently validate representative symbols in both markets before purchase. Price licensing must permit server-side automated analysis, storage, and public/private app display. Personal use ≠ permission to republish live quotes to a public GitHub Pages site.
- SEC EDGAR data.sec.gov (submissions and companyfacts) for US S-1, F-1, S-1/A, F-1/A, 424B4, 10-K, 10-Q, 8-K. Respect SEC fair-access and identify bot.
- US IPO calendar Nasdaq (indicative dates, not proof). German IPOs Deutsche Börse new companies/Neuemissionen, cash-market notifications and issuer prospectuses; BaFin prospectus approval is not an endorsement or price prediction.
- German fundamentals: verified issuer IR reports, Bundesanzeiger/Unternehmensregister documents where legally available, or vendor global fundamentals. Respect publishing restrictions and document lag.
- Macro events: Fed FOMC calendars, ECB meetings, official statistics. FX: timestamped ECB/EOD midrate or separately licensed feed; price target converted at scenario FX and FX sensitivities.
- Each data item stores vendor, URL/document ID, event_time, published_time, retrieved_time, exchange timezone, currency, license, and quality status. No unverified news→confirmed IPO conversion.
- Vendor price reference as checked 2026-10-30: EODHD global EOD $19.99/mo, global intraday $29.99/mo, fundamentals $59.99/mo, combined $99.99/mo (personal price list). Confirm endpoints, individual entitlements and permitted non-display use before paying. Twelve Data Basic free but limited, commercial/API usage permissions may differ.

## 5. Universe selection / eligibility / cross-market comparability
- Daily listing universe from provider's NASDAQ + NYSE and primary XETR + XFRA listings, not a handpicked brand list. Exclude ETFs, funds, warrants, ADR duplicates and non-equities by verified instrument type.
- Deduplicate cross-listed equities using ISIN and primary venue / distinct venue listing, while retaining executable venue/currency; explicitly surface foreign shares traded on Xetra vs German issuers.
- Example starting filters to tune historically: share price >= equivalent EUR 3, median daily turnover >= EUR 5m, 30d trading history, limited median bid-ask spread, auditable prices and splits, no current halts. Illiquid names / penny stocks are rejected. Fundamentals and spreads missing -> no actionable signal.
- Normalized metrics: ATR/close, spread %, EUR turnover using time-matched FX, sector-relative valuation/growth, volatility-adjusted momentum, estimated net R:R and exposure, not raw USD vs EUR prices.
- Use US/DE market calendar/timezone/DST independently, avoid evaluating incomplete daily candles and earnings dates outside session.

## 6. Deterministic technical + fundamental research
Indicators for daily OHLCV with proper adjusted history (not mixed adjusted raw): EMA20/50, SMA200, RSI14, MACD 12/26/9, ATR14, 20d relative volume, support/resistance and validated breakout/pullback rules; minimum warm-up periods.
Fundamentals: revenue/EPS change, FCF, margin, leverage/net debt, liquidity runway, earnings date, sector multiples (sector-specific for banks/insurers), revision trends if available. Avoid false precision where German reporting cadence differs.
News AI: extract and classify event, ticker/ISIN identity, facts vs opinion, official vs press, published timestamp, direct evidence, expected channel of influence, bull/bear narrative. AI can summarize and propose hypotheses only; never invent datapoints, compute indicators itself, or execute trades.
Pre-proposal gates: live/stale data validation, security type, market cap/liquidity/spread, no known large earnings/Fed event unaccounted for, gross & after-cost R:R, risk/reward tolerances, position sizing, sector and currency concentration.
Illustrative 100-point score, empirically calibrated before release: technical setup 25; fundamental strength 20; valuation 10; catalysts/news verified 15; execution quality/liquidity 15; downside/risk context 15. Score is a ranking index, NOT probability of profitability.
For first simulation: >=78, data completeness >=90%, expected reward/risk >=2 gross and >=1.5 after costs; hard gates override score. No forcing 3 recommendations. Tune only via out-of-sample backtests.

## 7. Research proposal math / lifecycle
Candidate includes ISIN, issuer, symbol, MIC, exchange, trade currency, price/source/as-of, entry [low,high], take-profit target, planned stop, hold_period_days, expiry date, score components, data quality, rationale/countercase, known catalyst times, strategy version.
Gross potential reward % = (target - planned entry)/planned entry * 100.
Gross loss % = (entry - stop)/entry * 100; gross R:R = (target-entry)/(entry-stop) for long ideas.
Position size = min(available cash, risk_budget / effective_per-share stop-risk) allowing whole shares by default, incorporating expected spread, slippage and FX conversions; stop orders may gap through stop.
Net scenarios account commission, venue fees, spread and FX spread/conversion; taxes are shown separately and require user assumptions.
Score produces research shortlist (0–3 weekly), not purchase instructions. The proposal can be WAIT_ENTRY, ACTIVE_SIMULATED, INVALIDATED, EXPIRED, TARGET_TOUCHED, STOP_TOUCHED; publish every transition with reason, price timestamp and evidence.
Simulation: realistic fills. Touching entry is not a fill guarantee; if both stop and target are hit within the same OHLC bar use conservative adverse-first handling or lower-frequency data to disambiguate. Keep prospective research outcomes separate from user-submitted actual orders; never invent actual positions.

## 8. IPO watch and classification
Lifecycles: RUMOURED -> ANNOUNCED -> FILED -> AMENDED -> PRICE_RANGE -> PRICED -> FIRST_TRADE -> POST_IPO_WATCH -> WITHDRAWN. Missing steps allowed; no assumed listing date or offering price.
Classify by transaction type: primary IPO vs spin-off, direct listing, uplisting, dual listing, secondary placements. Not every new German admission is an IPO.
IPO quality pillars: business/market 20; disclosed financial health 20; valuation vs peer 20; governance/insiders 10; proceeds/free float 10; official filing quality 10; catalysts plus timing 10. If essential prospectus metrics missing, return INSUFFICIENT_DATA instead of score.
Follow through first trading sessions: volatility, relative volume, lock-up date, underwriting mechanics, executable spread, price vs issue. Never force buying on first trading day.
Notifications for material confirmed state transitions and post-IPO technically qualified setup only.

## 9. Monitoring, notifications and data quality
Batch cadence: after US & DE session closes scan EOD; full strategy ranking each Sunday with latest completed bars; IPO filings/news daily. During active session monitor open research setups every 15–30 min initially only if license and quote timeliness permit; quotes with 15-min lag cannot support near-real-time execution alarms.
OneSignal V1 retains web push. Fix observed "All included players are not subscribed" using explicit subscription targeting, subscription status check or segment correction; test manual and automated separately. No API key in PWA/repo. Event dedup uses immutable recommendation_id + event_type + strategy_version / event_window, delivered_at, retriable error logs; no "push_sent" without provider acceptance.
Price triggers require market venue and measured timestamp; "approaching stop" uses defined ATR-based warning band. Alerts must label DATA_DELAYED and NOT_EXECUTION_RECOMMENDATION.
Three types: weekly pick report, validated material IPO event, monitoring state transition. Weekly report may say "no qualified candidates". User controls mute hours, type and sensitivity.
Fail-closed: no scoring/actions on stale/incomplete data; stale inputs are flagged and logged. Keep data/source freshness UI visible.

## 10. Backtesting and release acceptance
- Historical, survivorship-bias-safe market universe, including delisted securities; timestamp when each SEC/fundamental/news disclosure actually became public. No look-ahead.
- Rolling walk-forward train/validation/test; no hyperparameter tuning on final test. Split calendars and earnings across time, not random daily row splits.
- Fill assumptions: next tradable bar, explicit limit order nonfills, spread/slippage/fees, FX and realistic gaps; model partial fills if necessary; corporate actions correct.
- Measure number of recommendations, fill rate, winners, mean/median realized modeled return, expectancy, profit factor, max drawdown, tail losses, turnover, calibration by score, cost sensitivity, cumulative net return. Compare USD candidates to S&P 500 in USD, EUR candidates to DAX in EUR, total portfolio in selected base currency using time-matched FX.
- Evaluate US vs DE and overall; also stock categories / sector / market regimes. At least one extended walk-forward historical period plus 8–12 weeks forward paper simulation before claiming any demonstrated ability.
- Reliability tests: duplicate push, vendor throttling, no data, stale prices, FX holiday, US/DE DST divergence, wide spreads, stock splits, delisted shares, multi-listed ISINs, catastrophic gaps, both target and stop same candle, unverified rumors.
- Tests/coverage gates, logs/health dashboard, versioned strategy, documented incident recovery.

## 11. Implementation order
P0 — snapshot baseline + branch spec (this document). No production deployment change.
P1 — fix OneSignal targeting/reliability; authenticated private storage; US/DE source adapters, instrument identifier master and quote quality gates.
P2 — technical indicators + fundamentals + score explanations + 0–3 weekly research engine + fair-market ranker + two-card PWA UI.
P3 — recommendation event ledger, market-calendar monitoring, risk calculator, state-based push notifications and performance tracking.
P4 — official IPO US/DE workflow + classification and post-listing watch.
P5 — proper walk-forward backtest, alert tests, 8–12 weeks paper trading, vendor/licensing cost review.
Beyond: expand markets via configuration + adapters; no change to core domain models.

## 12. Decision on vendors/budget
Free design phase: official SEC/Fed/ECB/Deutsche Börse public documents and test/delayed price plans where licensing permits; label demonstration and never claim current executable signals.
Economic starter: test one global-data provider without purchasing blindly; EOD for weekly screening, separate intraday only if matching alert expectations and license. For complete global fundamentals plus price data the $99.99/mo personal EODHD tier is a possible reference, NOT approved for public redistribution. Paid plan activation requires owner's explicit approval.
Infrastructure: GitHub Actions/Pages + OneSignal existing free tier while testing; Supabase Free initially 500MB subject to suspension, or another managed Postgres as needed. Advanced regular monitoring can migrate to Cloud Run + Scheduler. Model API has metered usage separate from ChatGPT subscription.

## Public source references (verified 2026-10-30)
- SEC JSON API and policies: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- NASDAQ IPO listings: https://www.nasdaq.com/market-activity/ipos
- Deutsche Börse new companies: https://www.cashmarket.deutsche-boerse.com/cash-de/Daten-Tech/statistiken/Neue-Unternehmen
- BaFin prospectuses: https://bafin.de/DE/Aufsicht/Prospekte/Wertpapiere/ErstellungBilligung/erstellung_billigung_node.html
- EODHD pricing, exchanges, personal/commercial limits: https://eodhd.com/pricing ; https://eodhd.com/list-of-stock-markets ; https://eodhd.com/financial-apis/terms-conditions
- Twelve Data pricing and limitations: https://twelvedata.com/pricing
- Fed: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- ECB: https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
- GitHub schedule semantics: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- Supabase free plan: https://supabase.com/pricing

## Definition of done for V2
A user sees two sections only, with trusted US/DE data, timestamped executable-price limitations, comparable ranking, documented score and risks, at most 3 weekly research candidates, accurate state lifecycle and push alerts tested end-to-end, plus 3-month forward simulation stats and no invented historical profits. Until then all candidates are labelled TEST/RESEARCH and alerts are conditional.
