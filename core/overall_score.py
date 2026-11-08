"""Experimental, descriptive dashboard composite, NOT a trade decision rule.

O0.1 combines two existing 0-100 components. No defensible numerical
valuation score currently exists, so do not pretend it is included.
The score must never be used for order selection or position sizing.
"""
import math

OVERALL_VERSION = 'O0.1-tech-quality-experimental'


def _valid(value):
    if isinstance(value, bool):
        return None
    try:
        val = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return val if math.isfinite(val) and 0 <= val <= 100 else None


def calculate_overall(technical, quality):
    """Return score or None; require BOTH inputs rather than impute missing data."""
    tech, fundamental = _valid(technical), _valid(quality)
    if tech is None or fundamental is None:
        return None
    return round(0.60 * tech + 0.40 * fundamental, 1)


def overall_explanation(technical, quality):
    """Reason for missing score or transparent calculation basis."""
    if _valid(technical) is None:
        return 'Missing/invalid Technical score; Overall withheld'
    if _valid(quality) is None:
        return 'Missing/invalid Quality score; Overall withheld'
    return ('60% Technical T1.0 + 40% experimental Quality; valuation, macro, '
            'event and holdings are assessed separately in Action, not scored here')
