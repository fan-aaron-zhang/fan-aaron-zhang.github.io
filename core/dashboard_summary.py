"""Pure presentation contracts; no Streamlit dependency."""
from datetime import date
from config import WATCHLIST

def is_current(saved, *, fingerprint, cash, fx_rate, fx_date, total):
    return bool(saved and tuple(saved.get('tickers', ())) == WATCHLIST
                and saved.get('generated') == str(date.today())
                and saved.get('workbook_fingerprint') == fingerprint
                and saved.get('cash') == cash
                and saved.get('fx_rate') == fx_rate
                and saved.get('fx_date') == fx_date
                and saved.get('total') == total)


def prepare_display(rows, positions):
    """Pure action-first split; every ticker appears exactly once."""
    indexed = {str(r['Ticker']):r for r in rows}
    if set(indexed) != set(WATCHLIST) or len(rows) != len(WATCHLIST):
        raise ValueError('Full 22-name integrated review required')
    major, waiting = [], []
    for ticker in WATCHLIST:
        r = indexed[ticker]
        held = ticker in positions
        action = str(r.get('Action','Wait'))
        is_wait = (action.lower().startswith(('wait','hold / wait'))
                   or action in {'Hold / watch','Hold / wait'})
        # Held names ALWAYS visible, even Hold/Wait.
        (waiting if is_wait and not held else major).append(r)
    # Meaningful actions first, then held names; keep all 22 accounted for.
    def priority(row):
        action = str(row.get('Action','')).lower()
        if action.startswith(('buy','trim','reduce')): return (0, row['Ticker'])
        if action.startswith('review data'): return (1, row['Ticker'])
        return (2, row['Ticker'])
    major.sort(key=priority)
    waiting.sort(key=lambda r: (-(r.get('Technical') or 0),r['Ticker']))
    return major, waiting


