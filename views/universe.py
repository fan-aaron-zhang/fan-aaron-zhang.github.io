"""Zero-network stock universe overview."""
import pandas as pd
import streamlit as st
from config import STOCK_GROUPS, WATCHLIST, SECTOR_BENCHMARKS, VALUATION_PEERS


def render_universe():
    with st.expander(f"Research universe — {len(WATCHLIST)} US-listed stocks", expanded=False):
        rows = [{"Stock": ticker, "Research group": group,
                 "Technical RS proxy": SECTOR_BENCHMARKS.get(ticker),
                 "Valuation subgroup": VALUATION_PEERS.get(ticker)}
                for group, tickers in STOCK_GROUPS.items() for ticker in tickers]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("This fixed list is configured in config.py. All 22 can be screened even when not held. "
                   "Benchmarks are approximate. Valuation groups are descriptive only. "
                   "Only holdings in Portfolio.xlsx affect account risk and P/L.")
