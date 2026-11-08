"""Swing Quant modular app: five tabs, technical model T1.0."""
import streamlit as st
from config import APP_VERSION, MODEL_VERSION
from views.dashboard import render_dashboard

st.set_page_config(page_title="Swing Quant", layout="wide")
st.title("Swing Quant")
st.caption(f"Software {APP_VERSION} · Technical research model {MODEL_VERSION} (unvalidated)")
st.caption("Decision-support research only. No brokerage connection or automated trading.")
render_dashboard()
