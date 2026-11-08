"""Streamlit presentation of technical research metrics."""
import pandas as pd
import streamlit as st
from config import (TECHNICAL_UNIVERSE, SECTOR_BENCHMARKS, MARKET_BENCHMARK,
                    MODEL_VERSION, APP_VERSION, TECHNICAL_WEIGHTS)
from core.market_data import load_signal_history
from core.scoring import compute_technical

TECHNICAL_HELP = {
    "Ticker": "股票代码。",
    "Sector ETF": "行业比较基准；仅作为行业代理，某些股票不完全匹配该ETF。可在代码SECTOR_BENCHMARKS中修改。",
    "Quote date": "三组数据（个股、SPY、行业ETF）共有的最新交易日；不是实时价格。",
    "Close USD": "用于技术评分的复权收盘价，美元。",
    "Technical / 100": "技术总分（0–100）：趋势30 + 动量25 + 市场RS8 + 行业RS12 + RSI15 + 成交量10。不是买卖建议。",
    "Trend / 30": "趋势分：收盘高于MA20、MA20高于MA50、MA50上升各得10分。",
    "Momentum / 25": "动量分：5日上涨10分，20日上涨10分，20日涨幅超过5%另得5分。",
    "RS Market / 8": "市场相对强弱评分：20日收益超过SPY得4分；领先超过5个百分点再得4分。",
    "RS Sector / 12": "行业相对强弱评分：20日收益超过对应行业ETF得6分；领先超过5个百分点再得6分。",
    "RSI / 15": "14日RSI区间评分；和相对SPY/行业ETF的RS不是同一个指标。",
    "Volume / 10": "最新日成交量与前20个交易日平均量对比；放量且5日上涨给更高分。",
    "MA20": "最近20个交易日收盘价的简单平均。",
    "MA50": "最近50个交易日收盘价的简单平均。",
    "RSI14": "14日相对强弱指数，比较股票自身近期上涨/下跌动量；高于70或低于30不是直接买卖信号。",
    "Return 5D %": "股票最近5个交易日价格收益率。",
    "Return 20D %": "股票最近20个交易日价格收益率。",
    "RS 20D vs SPY pp": "股票20日收益率－SPY 20日收益率，单位为百分点。",
    "RS 20D vs Sector pp": "股票20日收益率－该股票行业ETF 20日收益率，单位为百分点。",
    "ATR14 %": "ATR14 ÷ 当前收盘价，波动风险参考，不计入总分。",
    "Status": "RESEARCH ONLY为有效研究评分；缺数据或日期过期时不出分。",
    "Trend state": "只描述技术趋势强弱，不代表买入、持有或卖出建议。",
}

def trend_state(value):
    if pd.isna(value):
        return "Unavailable"
    return ("Very Weak" if value < 25 else "Weak" if value < 45 else
            "Neutral" if value < 60 else "Strong" if value < 80 else "Very Strong")


def score_color(value):
    if value < 25: return "#af575d"
    if value < 45: return "#b87b3f"
    if value < 60: return "#657687"
    if value < 80: return "#347f96"
    return "#237c70"


from views.columns import order_technical_columns


def render_technical_help():
    with st.popover("ⓘ 指标说明 / Indicator guide"):
        st.markdown("**评分（不是买卖建议）**")
        for key in ["Technical / 100", "Trend / 30", "Momentum / 25",
                    "RS Market / 8", "RS Sector / 12", "RSI / 15", "Volume / 10"]:
            st.markdown(f"**{key}** — {TECHNICAL_HELP[key]}")
        st.markdown("**原始指标与风险**")
        for key in ["Sector ETF", "MA20", "MA50", "RSI14", "Return 5D %",
                    "Return 20D %", "RS 20D vs SPY pp", "RS 20D vs Sector pp",
                    "ATR14 %", "Quote date"]:
            st.markdown(f"**{key}** — {TECHNICAL_HELP[key]}")
        st.caption("表格列标题上的 ⓘ 也提供单项说明。")

def render_technical_research(swing_accounts):
    st.divider()
    st.subheader("Daily technical research scores")
    st.caption(f"Technical model version: {MODEL_VERSION} · UI/software: {APP_VERSION}")
    st.caption("Research-only, unvalidated scores. Market benchmark: SPY; sector benchmark varies by ticker. "
               "Closing prices only. No trading orders.")
    symbols = list(TECHNICAL_UNIVERSE.keys())
    current = set(swing_accounts)
    chosen = st.multiselect("Stocks to study", symbols,
                            default=[ticker for ticker in symbols if ticker in current])
    if not chosen:
        st.info("Choose a ticker to calculate its research score.")
        return
    if not st.toggle("Show technical research", value=False):
        st.info("Switch on technical research to fetch daily history and calculate scores.")
        return
    with st.spinner("Fetching adjusted daily OHLCV (Yahoo Finance)..."):
        market, market_error = load_signal_history(MARKET_BENCHMARK)
        # Fetch each unique sector ETF once (further requests benefit from cache).
        sector_data = {}
        for ticker in chosen:
            sector_symbol = SECTOR_BENCHMARKS.get(ticker)
            if sector_symbol and sector_symbol not in sector_data:
                sector_data[sector_symbol] = load_signal_history(sector_symbol)
        data_rows = []
        histories = {}
        for ticker in chosen:
            data, issue = load_signal_history(TECHNICAL_UNIVERSE[ticker])
            histories[ticker] = data
            sector_symbol = SECTOR_BENCHMARKS.get(ticker)
            sector_history, sector_error = sector_data.get(sector_symbol, (None, "No sector mapping"))
            report = compute_technical(ticker, data, market, sector_history, sector_symbol)
            if issue:
                report["Status"] = f"Stock unavailable: {issue}"
            elif market_error:
                report["Status"] = f"SPY unavailable: {market_error}"
            elif sector_error:
                report["Status"] = f"{sector_symbol or 'Sector'} unavailable: {sector_error}"
            data_rows.append(report)
    scored = pd.DataFrame(data_rows)
    render_technical_help()
    # Visual classification ONLY: strength of trend, not a buy/sell instruction.
    scored["Trend state"] = scored["Technical / 100"].map(trend_state)
    def score_cell(value):
        if pd.isna(value):
            return ""
        return f"background-color: {score_color(float(value))}; color: #ffffff; font-weight: 700"
    display_scored = order_technical_columns(scored)
    colored = display_scored.style.map(score_cell, subset=["Technical / 100"])
    st.caption("Column order: overall conclusion → data status → component scores → underlying indicators.")
    st.caption("Trend strength colours: very weak (0–24) · weak (25–44) · "
               "neutral (45–59) · strong (60–79) · very strong (80–100). "
               "Colours are NOT buy/sell recommendations.")
    st.dataframe(
        colored, hide_index=True, use_container_width=True,
        column_config={col: st.column_config.Column(help=description)
                       for col, description in TECHNICAL_HELP.items()
                       if col in display_scored.columns},
    )
    valid = scored[scored["Technical / 100"].notna()]
    if not valid.empty:
        st.caption("Weights: Trend 30 + Momentum 25 + Market RS vs SPY 8 + "
                   "Sector RS 12 + RSI 15 + Volume 10 = 100. "
                   "Sector benchmarks are approximate proxies; ATR is context only.")
        ticker = st.selectbox("Inspect underlying indicators", valid["Ticker"].tolist())
        selected = scored[scored.Ticker == ticker].iloc[0]
        st.write({col: selected[col] for col in ["Sector ETF", "Trend / 30", "Momentum / 25",
                 "RS Market / 8", "RS Sector / 12", "RS 20D vs SPY pp",
                 "RS 20D vs Sector pp", "RSI / 15", "Volume / 10", "ATR14 %"]})
        st.caption("点击 ⓘ 指标说明，可随时查看计算规则。")
        history = histories.get(ticker)
        if history is not None:
            display = pd.DataFrame({"Close USD": history.Close,
                                    "MA20": history.Close.rolling(20).mean(),
                                    "MA50": history.Close.rolling(50).mean()}).tail(100)
            st.line_chart(display)
    else:
        st.warning("No valid current scores. Check benchmark dates, history coverage and network access.")
    st.info("Research scores are NOT buy/sell recommendations. "
            "Next step: backtest the separate market and sector RS components.")

