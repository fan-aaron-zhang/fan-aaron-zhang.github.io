"""Pure Dashboard presentation helpers (no Streamlit dependency)."""
import pandas as pd

def score_band_color(value):
    """Display-only bands; no decision or scoring logic changes."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 'background-color: #eeeeee; color: #666666'
    if pd.isna(n):
        return 'background-color: #eeeeee; color: #666666'
    if n < 40:
        return 'background-color: #fce4e4; color: #802626'
    if n < 70:
        return 'background-color: #fff0cf; color: #755000'
    return 'background-color: #dbf2e2; color: #155b32'


def _style_action_table(df):
    """Only colour numeric scoring columns, preserving every other field."""
    return df.style.map(score_band_color, subset=['Overall', 'Tech', 'Quality']).format(
        {'Overall': lambda x: '—' if pd.isna(x) else f'{float(x):.1f}',
         'Tech': lambda x: '—' if pd.isna(x) else f'{float(x):.0f}',
         'Quality': lambda x: '—' if pd.isna(x) else f'{float(x):.1f}'})

