"""Pure presentation column order helpers, independent of Streamlit."""
# Presentation only: action-relevant conclusions first, diagnostics last.
# This order does not affect calculation, weights, or model outputs.
TECHNICAL_DISPLAY_COLUMNS = [
    "Ticker", "Technical / 100", "Trend state", "Status",
    "Close USD", "Quote date",
    "Trend / 30", "Momentum / 25", "RS Market / 8", "RS Sector / 12",
    "RSI / 15", "Volume / 10",
    "Sector ETF", "RS 20D vs SPY pp", "RS 20D vs Sector pp",
    "Return 5D %", "Return 20D %", "MA20", "MA50", "RSI14", "ATR14 %",
]


def order_technical_columns(frame):
    """Arrange existing fields for readability without modifying score values."""
    preferred = [name for name in TECHNICAL_DISPLAY_COLUMNS if name in frame.columns]
    remainder = [name for name in frame.columns if name not in preferred]
    return frame.loc[:, preferred + remainder]


