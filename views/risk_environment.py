"""V1.7a lightweight market regime, upcoming and recent earnings watch."""
from datetime import date
import pandas as pd
import streamlit as st
import yfinance as yf
from config import WATCHLIST, REGIME_SYMBOLS, EVENT_NEAR_DAYS, EVENT_WATCH_DAYS
from core.market_data import load_signal_history
from core.market_regime import evaluate_market_regime
from core.event_risk import assess_earnings_risk


@st.cache_data(ttl=6 * 3600, max_entries=40, show_spinner=False)
def _load_calendar(ticker):
    try:
        calendar = yf.Ticker(ticker).calendar
        if isinstance(calendar, dict):
            return calendar, None
        return None, "Yahoo calendar not a recognized dictionary"
    except Exception as exc:
        return None, f"Yahoo calendar unavailable ({type(exc).__name__})"


@st.cache_data(ttl=6 * 3600, max_entries=40, show_spinner=False)
def _load_earnings_history(ticker):
    try:
        history = yf.Ticker(ticker).get_earnings_dates(limit=12)
        if isinstance(history, pd.DataFrame):
            return history, None
        return None, "Yahoo earnings_dates not available"
    except Exception as exc:
        return None, f"Yahoo earnings_dates unavailable ({type(exc).__name__})"


def render_risk_environment():
    st.divider()
    st.subheader("Market Regime & Event Risk")
    st.caption("V1.7a · Descriptive market context and indicative Yahoo earnings history/calendar. "
               "No stock orders or investment recommendation.")
    with st.expander("Market regime — 4 ETF proxies", expanded=True):
        with st.spinner("Loading cached ETF daily history..."):
            histories, issues = {}, []
            for ticker in REGIME_SYMBOLS:
                frame, issue = load_signal_history(ticker)
                histories[ticker] = frame
                if issue:
                    issues.append(f"{ticker}: {issue}")
            evaluation = evaluate_market_regime(histories)
        if evaluation["regime"] == "Unknown":
            st.warning("Market regime unavailable: " + evaluation["reason"])
        else:
            a, b, c, d = st.columns(4)
            a.metric("Market context", evaluation["regime"])
            b.metric("SPY 20D volatility", f'{evaluation["spy_20d_realized_vol_pct"]:.1f}%')
            c.metric("ETFs above MA50", f'{evaluation["breadth_above_ma50"]}/4')
            d.metric("Volatility flag", evaluation["risk_volatility"])
            st.caption(f'Daily close through {evaluation["as_of"]} · {evaluation["reason"]}. '
                       "Volatility is historical, annualized; not implied volatility.")
            st.dataframe(pd.DataFrame(evaluation["components"]), hide_index=True, use_container_width=True)
            st.caption("ETF proxies: SPY broad large-cap, QQQ growth/tech, IWM small-cap, SMH semiconductors. "
                       "These are overlapping exposures, NOT independent market breadth.")
            if evaluation["risk_volatility"] == "Elevated":
                st.warning("High realized SPY volatility: consider heightened position-sizing and gap-risk review. "
                           "This is not a sell signal.")
        st.caption("Rule M0.1: Supportive = SPY above rising MA50 and MA200, "
                   "with at least 3/4 proxies above MA50; Defensive = SPY below MA200 "
                   "and (below MA50 or breadth <=1); otherwise Mixed. "
                   "Requires aligned daily data no older than 5 calendar days.")
    with st.expander("Earnings event watch — selected stocks", expanded=False):
        st.caption("Checks recent 7-day post-earnings and upcoming 14-day windows. Yahoo dates can be missing or estimated. "
                   "UNKNOWN is not a safe/no-event status. "
                   "Confirm important dates with company investor relations before placing orders.")
        selected = st.multiselect("Check Yahoo earnings calendars", list(WATCHLIST),
                                  default=["FN", "DDOG", "TMDX", "NU"],
                                  key="v17_event_tickers")
        if not selected:
            st.info("Select stocks to check calendar dates.")
        elif st.button("Check selected earnings dates", key="v17_event_check"):
            if len(selected) > 8:
                st.warning("For reliability, check up to 8 tickers per request; choose the most relevant holdings.")
            else:
                records = []
                with st.spinner("Checking Yahoo indicative earnings dates..."):
                    for ticker in selected:
                        calendar, error = _load_calendar(ticker)
                        history, history_error = _load_earnings_history(ticker)
                        report = assess_earnings_risk(ticker, calendar, earnings_history=history,
                                                      near_days=EVENT_NEAR_DAYS,
                                                      watch_days=EVENT_WATCH_DAYS)
                        records.append({"Ticker": ticker, "Status": report["status"],
                                        "Recent earnings": report["last_event_date"],
                                        "Days since": report["days_since"],
                                        "Reported EPS present": report["recent_confirmed_eps"],
                                        "Next earnings (indicative)": report["earnings_date"],
                                        "Days until": report["days_until"],
                                        "Event risk": report["risk"],
                                        "Data note": "; ".join(x for x in
                                                     (report["reason"], error, history_error) if x)})
                st.session_state["v17_event_result"] = {"tickers": tuple(selected), "records": records,
                                                         "checked_on": str(date.today())}
        saved = st.session_state.get("v17_event_result")
        if saved:
            st.caption(f'Calendar checked {saved["checked_on"]}; '
                       'refresh after new disclosures or when your selected list changes.')
            if tuple(selected) != saved["tickers"]:
                st.info("Selection changed. Click the button to refresh these calendars.")
            else:
                st.dataframe(pd.DataFrame(saved["records"]), hide_index=True, use_container_width=True)
        st.caption("'Recent (reported EPS)' is third-party evidence, not confirmation from an official filing. "
                   "'Recent (date unverified)' must not be treated as a confirmed report. "
                   "Yahoo might have no history at all; UNKNOWN means unassessed. "
                   "Do not interpret 'Later' as an absence of mergers, FDA decisions, guidance, "
                   "regulatory changes or other catalysts. Those are outside Yahoo's earnings calendar.")
