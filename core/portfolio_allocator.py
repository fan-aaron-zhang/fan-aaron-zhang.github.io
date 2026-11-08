"""Allocate *candidate* buy proposals against one shared verified cash balance.

This is an allocation safety layer, not an optimization or prediction model.
Original single-name suggestions are retained as 'standalone' fields for audit.
Only selected candidates participate; no orders are sent.
"""
from __future__ import annotations
import math

ALLOCATOR_VERSION = "A0.1-shared-cash"


def _safe_nonnegative(value):
    try:
        number = float(value)
        if not math.isfinite(number) or number < 0:
            return None
        return number
    except (ValueError, TypeError):
        return None


def allocate_buy_candidates(reports, cash_gbp, fx_gbp_usd, reserve_gbp=0.0):
    """Return updated copies and a summary. Require whole USD shares; no FX guesses.

    Priority ranks the chosen *buy-eligible* proposals by available technical
    then quality evidence, and breaks ties by ticker. Rank ≠ fair value.
    Does not convert Hold/Wait into Buy and does not spend anticipated proceeds.
    """
    rows = [dict(r) for r in reports]
    cash = _safe_nonnegative(cash_gbp)
    fx = _safe_nonnegative(fx_gbp_usd)
    reserve = _safe_nonnegative(reserve_gbp)
    valid = cash is not None and fx is not None and fx > 0 and reserve is not None
    spendable = max(0.0, cash - reserve) if valid else 0.0
    candidates = []
    for idx, row in enumerate(rows):
        qty = _safe_nonnegative(row.get("Buy shares"))
        price = _safe_nonnegative(row.get("Buy limit USD"))
        amount = _safe_nonnegative(row.get("Buy amount GBP"))
        eligible = (row.get("Action") in {"Buy on pullback", "Buy near last close"}
                    and qty is not None and price is not None and price > 0
                    and amount is not None and qty >= 1 and row.get("Status") != "Blocked")
        row["Standalone buy shares"] = int(qty) if qty is not None else 0
        row["Standalone buy amount GBP"] = amount
        row["Shared-cash rank"] = None
        row["Allocation status"] = "No buy proposal" if not eligible else "Pending allocation"
        # Never preserve a standalone order when shared allocation unavailable.
        row["Buy shares"] = 0
        row["Buy amount GBP"] = None
        if eligible:
            candidates.append(idx)
    candidates.sort(key=lambda i: (-(_safe_nonnegative(rows[i].get("Technical")) or 0),
                                   -(_safe_nonnegative(rows[i].get("Quality")) or 0),
                                   str(rows[i].get("Ticker", ""))))
    total_spend = 0.0
    for rank, idx in enumerate(candidates, 1):
        row = rows[idx]
        row["Shared-cash rank"] = rank
        if not valid:
            row["Allocation status"] = "Blocked — cash/FX invalid"
            continue
        price = float(row["Buy limit USD"])
        desired = int(row["Standalone buy shares"])
        # Decimal quantities are not supported for new US equity orders.
        affordable = int(math.floor(max(0.0, spendable - total_spend) * fx / price + 1e-9))
        quantity = max(0, min(desired, affordable))
        if quantity:
            cost = quantity * price / fx
            total_spend += cost
            row["Buy shares"] = quantity
            row["Buy amount GBP"] = round(cost, 2)
            row["Allocation status"] = ("Allocated in full" if quantity == desired else "Partially allocated")
        else:
            row["Allocation status"] = "No shared cash left"
    return rows, {
        "Model": ALLOCATOR_VERSION,
        "Available cash GBP": cash,
        "Cash reserve GBP": reserve,
        "Selected buy candidates": len(candidates),
        "Proposed committed GBP": round(total_spend, 2),
        "Unallocated GBP": round(max(0.0, (cash or 0) - total_spend), 2),
        "Valid": valid,
        "Basis": "Selected buy proposals only; no reinvestment of hypothetical sales; prior-close/FX estimates",
    }
