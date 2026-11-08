"""Portfolio completeness helper: do not silently value missing quotes at zero."""
from config import QTY_TOLERANCE

def complete_value(df):
    """Return (total, missing labels) without silently treating missing quotes as zero."""
    if df.empty:
        return 0.0, []
    positive = df[df["Shares"].fillna(0) > QTY_TOLERANCE]
    missing = positive.loc[positive["Status"] != "VALUED", "Stock / account"].tolist()
    return (None if missing else float(positive["Market value GBP"].sum())), missing

