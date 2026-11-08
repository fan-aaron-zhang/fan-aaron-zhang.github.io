"""Cross-sectional, same-snapshot Yahoo valuation context (NOT investment advice)."""
from __future__ import annotations
import math
from collections import defaultdict
from statistics import median
from config import VALUATION_PEERS

METRICS = ("Forward P/E", "Trailing P/E", "EV / Revenue", "P / Sales")

def _valid_positive(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
        return v if math.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def peer_comparison(reports):
    """Compare ONLY same subgroup, same metric, with at least 2 observed peers.

    No peer's metric is constructed/inferred; every report is an observed Yahoo
    snapshot. A comparison is descriptive, not an attractive-price signal.
    """
    observed = defaultdict(list)
    for report in reports:
        ticker = report.get("Ticker")
        group = VALUATION_PEERS.get(ticker)
        if not group:
            continue
        for metric in METRICS:
            value = _valid_positive(report.get("Valuation", {}).get(metric))
            if value is not None:
                observed[(group, metric)].append((ticker, value))
    rows = []
    for report in reports:
        ticker = report.get("Ticker")
        group = VALUATION_PEERS.get(ticker, "Unknown")
        for metric in METRICS:
            value = _valid_positive(report.get("Valuation", {}).get(metric))
            candidates = observed[(group, metric)]
            # Exclude target from its own comparator to avoid a misleading median.
            other_values = [v for t, v in candidates if t != ticker]
            peer_med = median(other_values) if other_values else None
            rows.append({
                "Ticker": ticker, "Peer subgroup": group, "Metric": metric,
                "Yahoo multiple": round(value, 2) if value is not None else None,
                "Other observed peers": len(other_values),
                "Other-peer median": round(peer_med, 2) if peer_med is not None else None,
                "vs other peers %": round(100 * (value / peer_med - 1), 1)
                    if value is not None and peer_med is not None else None,
                "Context": "Descriptive only" if value is not None and peer_med is not None
                    else "No comparable peer in current selection",
            })
    return rows
