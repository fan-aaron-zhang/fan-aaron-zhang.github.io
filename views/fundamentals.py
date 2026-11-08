"""On-demand Yahoo-only financial research, kept separate from execution advice."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from core.fundamentals import summarize_yahoo, QUALITY_MODEL_VERSION, BANK_MODEL_VERSION
from config import TECHNICAL_UNIVERSE, STOCK_GROUPS
from core.valuation_peers import peer_comparison


@st.cache_data(ttl=21600, max_entries=35, show_spinner=False)
def _load_fundamental(ticker, model_version):
    import yfinance as yf
    ticker_obj = yf.Ticker(ticker)
    errors = []
    def pull(attr):
        try:
            return getattr(ticker_obj, attr)
        except Exception as exc:
            errors.append(f"{attr}: {type(exc).__name__}")
            return None
    income = pull("quarterly_income_stmt")
    cashflow = pull("quarterly_cashflow")
    annual = pull("income_stmt")
    balance = pull("quarterly_balance_sheet")
    # Info contains current estimates: useful context but NOT historic point-in-time valuation.
    try:
        info = ticker_obj.get_info()
    except Exception as exc:
        errors.append(f"valuation metadata: {type(exc).__name__}")
        info = {}
    report = summarize_yahoo(ticker, income, cashflow, annual, info, balance_sheet=balance)
    return report, errors


def render_fundamental_research():
    st.subheader("Fundamental & valuation research")
    st.caption(f"Yahoo Finance only · 22-stock fixed universe · non-bank {QUALITY_MODEL_VERSION} · bank {BANK_MODEL_VERSION} · no valuation score yet")
    st.info("Experimental research only, NOT trading signals. A potentially stale score is shown with a clear warning, "
            "not treated as decision-ready. NU and SOFI use a partial banking/lending model. Valuation multiples are references.")
    tickers = st.multiselect("Companies for financial research", list(TECHNICAL_UNIVERSE),
                             default=[x for x in ("FN", "AMBA", "DDOG", "TMDX", "NU") if x in TECHNICAL_UNIVERSE],
                             key="fundamental_tickers")
    st.caption(f"Active financial models: **{QUALITY_MODEL_VERSION}** / **{BANK_MODEL_VERSION}**. "
               "Older exported F0.2/F0.3 reports are not evidence of this version. "
               "Data cache refreshes every 6 hours; use Clear cached financial data to force a new Yahoo fetch.")
    run = st.button("Load / refresh financial research", key="refresh_fundamentals")
    if st.button("Clear cached financial data", key="clear_fundamentals_cache"):
        _load_fundamental.clear()
        st.session_state.pop("financial_research", None)
        st.info("Cached Yahoo financial statements cleared. Press Load / refresh to fetch them again.")
        return
    key = tuple(tickers)
    if run:
        if not tickers:
            st.info("Choose at least one stock.")
            return
        with st.spinner("Reading public financial statements and current valuation references..."):
            results = []
            errors = {}
            for ticker in tickers:
                result, issues = _load_fundamental(ticker, (QUALITY_MODEL_VERSION, BANK_MODEL_VERSION))
                results.append(result)
                if issues:
                    errors[ticker] = issues
        st.session_state["financial_research"] = (key, results, errors)
    snapshot = st.session_state.get("financial_research")
    if not snapshot or snapshot[0] != key or any(r.get("Quality model") not in (QUALITY_MODEL_VERSION, BANK_MODEL_VERSION) for r in snapshot[1]):
        st.caption("Press Load once to fetch Yahoo financial statements. Results remain visible while this browser session is active.")
        return
    _, results, errors = snapshot
    summary = pd.DataFrame([{k: value for k, value in r.items() if k not in ("Components", "Valuation", "Notes", "Source audit", "Raw Yahoo rows")}
                            for r in results])
    headline = ["Ticker", "Quality / 100", "Status", "Freshness", "Business model",
                "Coverage %", "Latest quarter", "Latest Yahoo income column", "Quarter fallback", "Quarter age days", "Missing metrics"]
    st.dataframe(summary[headline + [c for c in summary.columns if c not in headline]],
                 hide_index=True, use_container_width=True,
                 column_config={
                     "Quality / 100": st.column_config.NumberColumn(help="Unvalidated research score. Potentially stale scores are NOT decision-ready; blank if data too old/missing."),
                     "Coverage %": st.column_config.NumberColumn(help="Share of 100 available scoring points; not data accuracy.", format="%.0f%%"),
                     "Revenue growth %": st.column_config.NumberColumn(help="Latest quarter year-on-year if 5 quarters exist; otherwise annual fiscal-year growth, labelled.", format="%.2f%%"),
                     "FCF margin %": st.column_config.NumberColumn(help="(Operating cash flow minus absolute capital expenditure) / quarterly revenue; mismatched reporting periods may invalidate it.", format="%.2f%%"),
                 })
    val_rows = [{"Ticker": r["Ticker"], **r["Valuation"]} for r in results]
    st.markdown("**Current valuation reference (no score)**")
    st.dataframe(pd.DataFrame(val_rows), hide_index=True, use_container_width=True)
    with st.expander("Peer valuation context (selected stocks only)", expanded=False):
        st.caption("Same Yahoo snapshot, nearest business-model subgroup only. "
                   "Requires an observed second ticker with a positive multiple. "
                   "Comparison excludes the target ticker from its reference median; "
                   "not a historical valuation percentile, fair value, or Buy/Sell score. "
                   "Different accounting, growth and profitability still limit comparability.")
        peers = pd.DataFrame(peer_comparison(results))
        if not peers.empty:
            st.dataframe(peers, hide_index=True, use_container_width=True)
        st.caption("For example, select BSY and PTC together to see industrial software peer multiples. "
                   "NU and SOFI may not be directly comparable even though in the same research bucket.")
    for r in results:
        with st.expander(f"{r['Ticker']}: methodology & limitations"):
            st.write(r["Notes"])
            st.write("Growth comparator:", r["Growth basis"])
            st.write("Quarter selection:", r.get("Quarter selection", "Unavailable"))
            if r.get("Quarter fallback"):
                st.warning("Used an earlier complete income quarter instead of the latest Yahoo column. This is a lagged, provisional research snapshot, not a current trading signal.")
            st.write("Weighted quality component points:", r["Components"])
            st.write("Freshness:", r["Freshness"], "— Quarter age:", r["Quarter age days"], "days")
            st.write("Missing indicators:", r["Missing metrics"])
            if r.get("Source audit"):
                st.markdown("**Yahoo field audit (why fields were/weren't usable)**")
                st.dataframe(pd.DataFrame(r["Source audit"]), hide_index=True, use_container_width=True)
                with st.expander("Show original Yahoo statement row names"):
                    st.json(r.get("Raw Yahoo rows", {}))
            st.write("Decision-ready:", r["Decision-ready"])
            if r["Business model"] in ("Bank", "Bank/lending hybrid"):
                st.caption("Bank B0.2: revenue growth /25 · ROE /30 · ROA /20 · equity/assets /25. "
                           "NOT a complete bank-quality assessment: credit losses and regulatory capital are missing.")
            else:
                st.caption("Non-bank F0.4: revenue growth /35 · operating margin /25 · net margin /20 · FCF margin /20. "
                           "FCF values require cash-flow period validation.")
            st.caption("Bank and non-bank scores are NOT comparable; both experimental and excluded from trade advice.")
            if r["Ticker"] in errors:
                st.warning("Some requested data were unavailable: " + "; ".join(errors[r["Ticker"]]))
    st.warning("The selected quarter is shown separately from Yahoo’s latest income column. A fallback score is provisional. Cash flow may be YTD, so FCF margins must not be treated as verified decision inputs. Yahoo quarter-end dates are not publication dates; quarterly statements can lag announcements. "
               "Scores flagged potentially stale are visible for research only, not ready for trade advice. "
               "Bank-specific metrics do not include credit quality; quarterly cashflows may be YTD.")
