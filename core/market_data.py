"""Yahoo daily data access only; never cache uploaded workbook contents."""
import math
import pandas as pd
import streamlit as st
import yfinance as yf
from config import MARKET_SYMBOLS, QTY_TOLERANCE
from core.portfolio import numeric


@st.cache_data(ttl=900, max_entries=40, show_spinner=False)
def get_daily_close(ticker):
    """Last available regular-session CLOSE, not live/real-time pricing."""
    try:
        history = yf.Ticker(ticker).history(
            period="7d", interval="1d", auto_adjust=False,
            prepost=False, actions=False, timeout=12,
            raise_errors=False,
        )
        if history is None or history.empty or "Close" not in history:
            return None, None, "No quote returned"
        valid = history["Close"].dropna()
        if valid.empty:
            return None, None, "No valid closing prices"
        price = float(valid.iloc[-1])
        if not math.isfinite(price) or price <= 0:
            return None, None, "Invalid market price"
        stamp = valid.index[-1]
        quote_day = str(stamp.date()) if hasattr(stamp, "date") else str(stamp)
        return price, quote_day, None
    except Exception as exc:
        return None, None, f"Quote unavailable ({type(exc).__name__})"

def build_valuation(ledger_df, fx_rate, fx_date):
    valuation_rows = []
    quotes = {}
    for _, record in ledger_df.iterrows():
        name = record["Stock / account"]
        shares = numeric(record["Calculated shares"])
        cost = numeric(record["Remaining cost GBP"])
        status = record["Status"]
        entry = MARKET_SYMBOLS.get(name)
        quote, quote_date, currency = None, None, None
        note = ""
        if status not in {"MATCH", "NO SUMMARY"} or shares is None or cost is None:
            note = "Ledger requires review"
        elif shares <= QTY_TOLERANCE:
            note = "No current holding"
        elif entry is None:
            note = "No verified quote mapping (manual fund NAV required)"
        else:
            symbol, currency, divisor = entry
            if symbol not in quotes:
                quotes[symbol] = get_daily_close(symbol)
            raw_price, quote_date, failure = quotes[symbol]
            if raw_price is None:
                note = failure or "Quote unavailable"
            elif currency == "USD" and (fx_rate is None or fx_rate <= 0):
                note = "GBP/USD exchange rate unavailable"
            else:
                quote = raw_price / divisor
                value = shares * quote / fx_rate if currency == "USD" else shares * quote
                if math.isfinite(value):
                    pl = value - cost
                    valuation_rows.append({
                        "Stock / account": name, "Shares": shares,
                        "Symbol": symbol, "Price": quote, "Quote currency": currency,
                        "Price date": quote_date,
                        "Cost GBP": cost, "Market value GBP": value,
                        "Unrealised P/L GBP": pl,
                        "Unrealised return %": (pl / cost * 100) if cost > 0 else None,
                        "Status": "VALUED",
                        "Note": ("USD converted using FX close " + str(fx_date)) if currency == "USD" else "GBP quote",
                    })
                    continue
                note = "Invalid valuation"
        valuation_rows.append({
            "Stock / account": name, "Shares": shares,
            "Symbol": entry[0] if entry else "",
            "Price": None, "Quote currency": currency,
            "Price date": quote_date,
            "Cost GBP": cost, "Market value GBP": None,
            "Unrealised P/L GBP": None,
            "Unrealised return %": None, "Status": "NOT VALUED",
            "Note": note,
        })
    return pd.DataFrame(valuation_rows)

@st.cache_data(ttl=3600, max_entries=32, show_spinner=False)
def load_signal_history(symbol):
    """Adjusted OHLCV daily bars. Never save uploaded portfolio to cache."""
    try:
        data = yf.Ticker(symbol).history(
            period="18mo", interval="1d", auto_adjust=True,
            actions=False, prepost=False, timeout=15, raise_errors=False,
        )
        required = {"Open", "High", "Low", "Close", "Volume"}
        if data is None or data.empty or not required.issubset(data.columns):
            return None, "Missing OHLCV data"
        data = data[["Open", "High", "Low", "Close", "Volume"]].copy()
        data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
        data = data[~data.index.duplicated(keep="last")].sort_index()
        data = data.apply(pd.to_numeric, errors="coerce")
        data = data.dropna(subset=["Close", "High", "Low", "Volume"])
        data = data[(data.Close > 0) & (data.High >= data.Low) & (data.Volume >= 0)]
        if len(data) < 100:
            return None, f"Insufficient history: {len(data)} daily bars"
        return data, None
    except Exception as exc:
        return None, f"Data unavailable ({type(exc).__name__})"

