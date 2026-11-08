"""On-demand Yahoo-only source diagnostics; no account data or SEC contact."""
import pandas as pd
import streamlit as st
from config import WATCHLIST
from core.fundamental_sources import check_yahoo


def render_fundamental_diagnostic():
    st.subheader("Yahoo financial data diagnostic")
    st.caption("Yahoo Finance only · no login, SEC contact or portfolio upload needed")
    with st.expander("What this diagnostic can and cannot confirm"):
        st.write("Checks whether Yahoo returns quarterly income, cash flow and balance "
                 "sheet frames. A response marked Available does not prove correct "
                 "quarterly accounting periods, latest publication, or metric comparability.")
    selected = st.multiselect("Tickers to test", list(WATCHLIST),
                              default=[t for t in ("FN", "AMBA", "DDOG", "TMDX", "NU") if t in WATCHLIST],
                              key="source_diagnostic_tickers")
    if st.button("Check Yahoo data coverage", key="run_fundamentals"):
        if not selected:
            st.info("Select one or more tickers.")
            return
        with st.spinner("Checking Yahoo financial statements..."):
            results = [check_yahoo(t) for t in selected]
        st.session_state["yahoo_diagnostic_snapshot"] = (tuple(selected), results)
    snapshot = st.session_state.get("yahoo_diagnostic_snapshot")
    if snapshot is None or snapshot[0] != tuple(selected):
        st.caption("Choose stocks and run the test only when needed; no bulk automatic requests.")
        return
    _, results = snapshot
    st.dataframe(pd.DataFrame([{k: v for k, v in item.items() if k != "Details"}
                               for item in results]), hide_index=True, use_container_width=True)
    for item in results:
        with st.expander(f"{item['Ticker']} — {item['Status']}"):
            st.dataframe(pd.DataFrame(item["Details"]), hide_index=True, use_container_width=True)
    st.warning("'Available' means statements could be fetched, NOT that the figures are "
               "current or validated for scoring. Yahoo can lag company earnings reports.")
