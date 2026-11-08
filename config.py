"""Swing Quant V1.6d: fixed 22-name US-listed research universe.

Ticker additions are occasional code edits, not interactive onboarding.
The group is a practical business-model peer classification, NOT a guarantee of
comparability. Sector ETF mappings are approximate technical RS proxies.
"""
MODEL_VERSION = "T1.0"
APP_VERSION = "V1.8j-price-risk-scenarios"
TECHNICAL_WEIGHTS = {"Trend": 30, "Momentum": 25, "RS Market": 8, "RS Sector": 12, "RSI": 15, "Volume": 10}

# Primary US market symbols only; no UK-listed RPI, FTC, IQE or defensive UL.
STOCK_GROUPS = {
    "AI infrastructure / semiconductors": ("FN", "ALAB", "AMBA", "AOSL"),
    "Cloud software / cybersecurity": ("DDOG", "NET", "CRWD", "S", "PATH"),
    "Medical devices": ("TMDX", "PODD", "ISRG", "IRTC"),
    "Digital banking / fintech": ("NU", "SOFI"),
    "Industrial software": ("BSY", "PTC"),
    "Aerospace / communications": ("JOBY", "IRDM"),
    "AI healthcare / diagnostics": ("TEM",),
    "Crypto exchange": ("COIN",),
    "Sports / entertainment": ("MANU",),
}
WATCHLIST = tuple(ticker for tickers in STOCK_GROUPS.values() for ticker in tickers)
SECTOR_GROUPS = {ticker: group for group, tickers in STOCK_GROUPS.items() for ticker in tickers}
TECHNICAL_UNIVERSE = {ticker: ticker for ticker in WATCHLIST}

# For the technical model's RS Sector ONLY. Match quality varies: especially
# FN/SMH, JOBY/ITA, IRDM/ITA, TEM/IHI, COIN/FINX, MANU/XLY.
SECTOR_BENCHMARKS = {
    "FN": "SMH", "ALAB": "SMH", "AMBA": "SMH", "AOSL": "SMH",
    "DDOG": "SKYY", "NET": "SKYY", "CRWD": "CIBR", "S": "CIBR", "PATH": "IGV",
    "TMDX": "IHI", "PODD": "IHI", "ISRG": "IHI", "IRTC": "IHI",
    "NU": "FINX", "SOFI": "FINX", "BSY": "IGV", "PTC": "IGV",
    "JOBY": "ITA", "IRDM": "ITA", "TEM": "IHI", "COIN": "FINX", "MANU": "XLY",
}
# Some groups cover distinct business economics. Do not make claims that their
# valuation multiples are like-for-like. Only these narrow groups may display
# mechanically comparable Yahoo snapshot multiples; no valuation score.
VALUATION_PEERS = {
    "FN": "Diversified AI hardware (insufficient close peers)",
    "ALAB": "Semiconductor", "AMBA": "Semiconductor", "AOSL": "Semiconductor",
    "DDOG": "Cloud platform", "NET": "Cloud platform",
    "CRWD": "Cybersecurity", "S": "Cybersecurity",
    "PATH": "Automation software", "BSY": "Industrial software", "PTC": "Industrial software",
    "TMDX": "Medtech", "PODD": "Medtech", "ISRG": "Medtech", "IRTC": "Medtech",
    "NU": "Digital banking (bank-specific)", "SOFI": "Digital banking (bank-specific)",
    "JOBY": "eVTOL (special)", "IRDM": "Satellite telecom (special)",
    "TEM": "AI diagnostics (special)", "COIN": "Crypto exchange (special)",
    "MANU": "Sports franchise (special)",
}
EXCLUDED_SHEETS = {"Summary", "Annual Audition", "Compliance", "News of the week"}
TRADE_ACTIONS = {"OPEN": 1, "BUY": 1, "SELL": -1}
QTY_TOLERANCE = 0.0001
MARKET_SYMBOLS = {ticker: (ticker, "USD", 1.0) for ticker in WATCHLIST}
MARKET_SYMBOLS.update({
    "VWRP (T212 ISA)": ("VWRP.L", "GBP", 1.0),
    "VWRP (HL-Junior ISA)": ("VWRP.L", "GBP", 1.0),
})
MARKET_BENCHMARK = "SPY"

# V1.7: descriptive market-risk inputs; not a forecast or automatic trade trigger.
REGIME_VERSION = "M0.1-research"
MACRO_VERSION = "M0.2-price-proxy-experimental"
EVENT_VERSION = "E0.2-recent-earnings"
REGIME_SYMBOLS = ("SPY", "QQQ", "IWM", "SMH")
EVENT_NEAR_DAYS = 7
EVENT_WATCH_DAYS = 14
