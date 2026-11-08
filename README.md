# Swing Quant V1.8j — Trade Price & Risk Scenarios

**Upgrade directly from your tested V1.8h.** V1.8i's peer-multiple buy veto is **not included**. This is a small, conservative upgrade of the existing Streamlit project; the 22-stock Action-first Dashboard, O0.1 Overall, T1.0 Technical, F0.5/B0.2 provisional Quality, M0.2 Macro, earnings risk, portfolio and shared-cash allocator are retained.

## What changed

- New pure calculator: `core/trade_scenarios.py`, version **P0.1-reference-scenarios**. Based on a candidate entry/reference price, ATR14 (%), and observed MA20/MA50, it describes:
  - `Scenario entry USD`: current daily close for Hold/Wait, or **conditional buy limit** where a buy proposal exists.
  - `1.5 ATR adverse USD`: hypothetical price 1.5 ATR below entry, **not** a stop-loss or maximum possible loss; gaps can be much larger.
  - `MA recovery reference USD`: nearest MA20 or MA50 **above entry**, if one exists. An average below entry is never presented as upside.
  - `Reward / shock reference`: hypothetical distance to that MA divided by 1.5 ATR adverse move, **not expected returns, intrinsic value or a validated R/R forecast**. Missing when no positive MA reference exists.
  - `Stress loss GBP`: candidate buy-share count multiplied by the 1.5 ATR shock, converted using the FX snapshot; this is *not* a loss cap.
- **D0.4-price-risk-scenarios** replaces the previously ineffective sizing proxy (which virtually never constrained normal £1,500–£3,000 tranches). New candidate buys are also limited by the **smaller of £150 or 0.5% of Swing value** of the hypothetical 1.5 ATR shock. This is a conservative configurable heuristic; no broker stop or real-world loss limit is implied.
- The stress-loss figure is recalculated **after** the shared-cash allocator determines final shares, keeping the Trade Decisions tables and ChatGPT snapshot consistent with the actual allocation.
- Trade Decisions' fourth table (`Price & execution conditions`) contains these new scenario columns. The detailed expander explains caveats. Dashboard remains unchanged and uncluttered. JSON export includes scenario fields automatically in `trading_plan`.
- No cross-company valuation score or peer premium veto. Current Yahoo valuation observations and existing simple caution checks remain in D0.4, with limits stated; the system **cannot yet estimate fair value**.
- No automatic transactions, uploads, spreadsheet writes or orders. Continue to record **only real executed trades** in your existing Excel.

## Deployment

1. Unzip the package. Upload its **contents** to the root of the existing private GitHub `swing-quant` repository, preserving `core/`, `views/`, and `tests/`. Replace same-name files.
2. Commit to the branch connected to Streamlit. Check root `config.py` has `APP_VERSION = "V1.8j-price-risk-scenarios"`.
3. Open Streamlit and confirm **Software V1.8j-price-risk-scenarios**. If version sticks, check Streamlit branch/`app.py`, deployment logs, then reboot.
4. Upload current Portfolio.xlsx; click **Scan & assess all 22 stocks**. Confirm Dashboard retains 22-name coverage and O0.1 colour coding.
5. Open **Trade Decisions**, select actual held tickers and inspect **Price & execution conditions** and detailed expanders. For a `Wait` name, the scenario is for research **only**, not an implied order.
6. Export one stock JSON and verify scenario entries match the detailed table; if a buy proposal exists, the snapshot's `Stress loss GBP` must use the **shared-cash allocated** shares, not the standalone proposal.

## Limitations to understand

1. No fair-value valuation or reliable upper target; the MA recovery reference is *purely technical* and might be absent in a strong trend above both moving averages. Do not infer zero potential upside.
2. 1.5 ATR is a normal-volatility stress scenario, not a tail-risk estimate. Event gaps can exceed it considerably.
3. The same simple valuation caution and bank/lending conservative buy blocks of V1.8h are retained. This release does **not** claim to make every Wait actionable.
4. The trade engine may suggest Hold/Wait despite an appealing scenario. An R/R number does **not** independently trigger a trade.
5. The shared-cash allocator has offline test coverage; if all 22 stocks are Wait in live data, its live multi-Buy path remains unobserved.

## Tests

Run `PYTHONPATH=. python -m pytest -q` and `python -m compileall -q app.py config.py core views tests`. Offline tests exercise pricing math, no-UP reference, fail-closed behavior, old AMBA no-mechanical-trim regression and buy sizing under the 1.5 ATR shock. Cloud Yahoo API calls require deployment to validate.
