"""D0.3: Explainable opportunity and price-level assessment.

A decision is a conditional plan and not a live executable order. Quality
scores are provisional Yahoo snapshots; valuation is *observed context*, not
an invented intrinsic value estimate. Weak technical score alone NEVER causes
an automatic trim. Deterministic core is independently testable.
"""
from __future__ import annotations
from datetime import date
import math

DECISION_VERSION = "D0.4-price-risk-scenarios"
from core.trade_scenarios import assess_price_scenario
NORMAL_SINGLE_GBP = 12000.0
HARD_SINGLE_GBP = 18000.0
INITIAL_TRANCHE_GBP = 3000.0
MAX_SWING_RATIO = 0.30


def _positive(x):
    try:
        v = float(x)
        return v if math.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def _number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _fresh(iso_day, today, max_days=5):
    try:
        lag = (today - date.fromisoformat(str(iso_day)[:10])).days
        return 0 <= lag <= max_days
    except (TypeError, ValueError):
        return False


def _valuation_context(financial):
    """Qualitative evidence; never claim a P/E multiple determines fair value."""
    f = financial or {}
    values = f.get("Valuation") or {}
    available = {k: _positive(v) for k, v in values.items()}
    available = {k: v for k, v in available.items() if v is not None}
    if not available:
        return "Unavailable", "No positive current Yahoo valuation multiple"
    view = ", ".join(f"{k} {v:.1f}x" for k, v in list(available.items())[:3])
    return "Observed (not fair value)", view


def _quality_context(financial):
    if not financial:
        return "Unavailable", None, "No financial research loaded"
    score = _number(financial.get("Quality / 100"))
    age = _number(financial.get("Quarter age days"))
    coverage = _number(financial.get("Coverage %"))
    if (score is None or coverage is None or coverage < 75 or age is None
            or age < -14 or age > 120 or financial.get("Quarter fallback")):
        return "Provisional / stale", score, (f"Quality coverage {coverage}%; quarter age {age} days; "
                                                 f"fallback={bool(financial.get('Quarter fallback'))}")
    return "Provisional / current", score, (f"Experimental {financial.get('Quality model')}: {score:.1f}/100, "
                                              f"coverage {coverage:.0f}%; quarterly age {age:.0f} days")


def _opportunity_evidence(price, ma20, ma50, atr, quality, financial):
    """Heuristic setup / observed valuation caution; never fair value.

    A price reference is NOT a forecast. Each returned level is derived only
    from visible price, moving averages and ATR. Avoid interpolating missing
    valuation or predicted returns.
    """
    v = (financial or {}).get("Valuation") or {}
    ev_sales = _positive(v.get("EV / Revenue"))
    fwd_pe = _positive(v.get("Forward P/E"))
    growth = _number((financial or {}).get("Revenue growth %"))
    negative_margin = _number((financial or {}).get("Operating margin %"))
    caution = []
    if ev_sales is not None and growth is not None and ev_sales >= 12 and growth < 25:
        caution.append(f"EV/revenue {ev_sales:.1f}x with revenue growth {growth:.1f}%: valuation caution")
    if fwd_pe is not None and fwd_pe >= 80:
        caution.append(f"Forward P/E {fwd_pe:.1f}x: high expectations")
    if negative_margin is not None and negative_margin < 0 and quality is not None and quality < 50:
        caution.append("Negative operating margin and weak provisional quality")
    # A tactical reference interval, not a statistical confidence interval.
    lower = round(max(0.01, min(price, ma20) - price * atr / 100 * 0.35), 2)
    recovery = round(max(price, ma20, ma50 or ma20), 2)
    risk_floor = round(max(0.01, price * (1 - atr / 100)), 2)
    if price < ma20:
        setup = "Below MA20 — wait for stabilization or reclaim"
        trigger = f"Daily close above MA20 (${ma20:.2f}) with improving trend/volume"
    else:
        setup = "At/above MA20 — trend confirmation still required"
        trigger = f"Hold MA20 (${ma20:.2f}) and re-evaluate momentum"
    return {
        "Opportunity setup": setup,
        "Reassessment trigger": trigger,
        "Technical support reference USD": lower,
        "Recovery reference USD": recovery,
        "One ATR downside scenario USD": risk_floor,
        "Valuation caution": "; ".join(caution) if caution else "No specific multiple-based flag (NOT proof of cheapness)",
        "Valuation caution flag": bool(caution),
    }


def evaluate_candidate(ticker, technical, *, current_close, price_date, fx_rate,
                       fx_date, cash_gbp, holding_shares, holding_value_gbp,
                       swing_value_gbp, total_portfolio_gbp, regime, event,
                       financial=None, ledger_ok=True, as_of=None):
    today = as_of or date.today()
    tech = technical or {}
    finance = financial or {}
    market = (regime or {}).get("regime", "Unknown")
    evt = (event or {}).get("status", "Unknown")
    qstate, quality, qreason = _quality_context(finance)
    vstate, vreason = _valuation_context(finance)
    result = {
        "Ticker": ticker, "Action": "Wait", "Buy limit USD": None,
        "Buy shares": 0, "Buy amount GBP": None, "Sell limit USD": None,
        "Sell shares": 0, "Sell amount GBP": None,
        "Technical": tech.get("Technical / 100"), "Quality": quality,
        "Quality status": qstate, "Valuation status": vstate,
        "Market": market, "Earnings": evt, "Status": "Conditional research",
        "Rationale": "", "Invalidation": "", "Review": "Routine",
        "Model": DECISION_VERSION, "Price date": price_date,
        "As of": today.isoformat(), "Valuation evidence": vreason,
        "Quality evidence": qreason,
        "Scenario status": "Not computed", "Scenario version": "P0.1-reference-scenarios",
        "Scenario entry USD": None, "1.5 ATR adverse USD": None,
        "MA recovery reference USD": None, "Reward / shock reference": None,
        "Stress loss GBP": None, "Scenario explanation": "Awaiting valid price inputs",
        "Opportunity setup": "Not assessed", "Reassessment trigger": "Refresh data",
        "Technical support reference USD": None, "Recovery reference USD": None,
        "One ATR downside scenario USD": None, "Valuation caution": "Not assessed",
    }
    price, fx = _positive(current_close), _positive(fx_rate)
    cash = _number(cash_gbp)
    qty_held = _number(holding_shares)
    stock_value = _number(holding_value_gbp)
    swing = _positive(swing_value_gbp)
    total = _positive(total_portfolio_gbp)
    atr = _positive(tech.get("ATR14 %"))
    score = _number(tech.get("Technical / 100"))
    ma20 = _positive(tech.get("MA20"))
    ma50 = _positive(tech.get("MA50"))
    missing = []
    if not ledger_ok: missing.append("Position ledger mismatch")
    if (price is None or fx is None or cash is None or cash < 0 or qty_held is None or
            qty_held < 0 or stock_value is None or stock_value < 0 or swing is None or total is None):
        missing.append("Portfolio, market price or FX incomplete")
    if not _fresh(price_date, today) or not _fresh(fx_date, today):
        missing.append("Market close / FX not recent")
    if tech.get("Status") != "RESEARCH ONLY" or not _fresh(tech.get("Quote date"), today):
        missing.append("Technical data unavailable or stale")
    if score is None or not 0 <= score <= 100 or atr is None or ma20 is None:
        missing.append("Missing technical score, ATR or MA20")
    if market not in {"Supportive", "Mixed", "Defensive"} or not _fresh((regime or {}).get("as_of"), today):
        missing.append("Market regime unavailable or stale")
    if evt == "Unknown" or not _fresh((event or {}).get("checked_on"), today, 1):
        missing.append("Earnings event unknown or not checked today")
    if missing:
        result.update(Action="Review data", Status="Blocked", Review="Data review",
                      Rationale="; ".join(missing), Invalidation="Refresh facts, position and event data")
        return result

    # Standalone scenario always available for full-data holdings and watchlist.
    # The sell/hold thesis may differ from a buy thesis; these levels are
    # descriptive rather than orders. A buy plan below updates entry and size.
    result.update(assess_price_scenario(price=price, atr_pct=atr,
                  ma20=ma20, ma50=ma50, fx_gbp_usd=fx))
    opportunity = _opportunity_evidence(price, ma20, ma50, atr, quality, finance)
    result.update({k: v for k, v in opportunity.items() if k != "Valuation caution flag"})
    valuation_caution = opportunity["Valuation caution flag"]

    # All future changes to quantities must originate from verified portfolio facts.
    shares = math.floor(qty_held + 1e-8)
    ratio = swing / total
    overweight = stock_value > NORMAL_SINGLE_GBP
    above_hard = stock_value > HARD_SINGLE_GBP
    weak = score < 40
    strong = score >= 68 and (ma50 is None or price >= ma50)
    high_vol = atr >= 9
    days_until = _number((event or {}).get("days_until"))
    days_since = _number((event or {}).get("days_since"))
    upcoming = evt in {"Within 7 days", "Within 14 days"} or (days_until is not None and 0 <= days_until <= 21)
    recent = evt.startswith("Recent") or (days_since is not None and 0 <= days_since <= 7)
    event_risk = upcoming or recent
    uncertainty = "Earnings soon/recent" if event_risk else ("Financial metrics provisional" if qstate != "Provisional / current" else "")
    result["Review"] = "Review suggested" if (event_risk or high_vol or above_hard or qstate != "Provisional / current") else "Routine"
    result["Invalidation"] = "Recompute after earnings/news, >1 ATR price move, or a position/cash update"
    qtext = f"Technical {score:.0f}/100; Quality {quality if quality is not None else 'N/A'} ({qstate}); "
    rtext = f"Market {market}; event {evt}; {vreason}."

    # High concentration is itself a concrete risk: size the reduction based on
    # exposure ABOVE the user's usual £12k reference, not a fixed 25% sale.
    if shares > 0 and above_hard:
        excess_gbp = stock_value - NORMAL_SINGLE_GBP
        sale_qty = min(shares, max(1, math.ceil(excess_gbp * fx / price)))
        limit = round(price, 2)  # last close REFERENCE, not guaranteed fill
        result.update(Action="Reduce now — risk", **{"Sell limit USD": limit,
                      "Sell shares": sale_qty, "Sell amount GBP": round(sale_qty * limit / fx, 2)},
                      Status="Review suggested",
                      Rationale=qtext + f"Holding £{stock_value:,.0f} exceeds £18k exceptional ceiling; reduce ~£{excess_gbp:,.0f} exposure toward £12k reference. " + rtext,
                      Invalidation="Limit is previous daily close, not a live execution price; verify current quote")
        return result

    if shares > 0 and overweight and (weak or event_risk or market == "Defensive"):
        excess_gbp = stock_value - NORMAL_SINGLE_GBP
        sale_qty = min(shares, max(1, math.ceil(excess_gbp * fx / price)))
        # A rebound reference near MA20 (if realistically reachable), with
        # the ATR anchor otherwise. Never manufacture a valuation target.
        rebound = max(price * (1 + min(atr * 0.35, 4.0) / 100),
                      ma20 if ma20 <= price * 1.12 else price)
        limit = round(rebound, 2)
        result.update(Action="Trim on rebound", **{"Sell limit USD": limit,
                      "Sell shares": sale_qty, "Sell amount GBP": round(sale_qty * limit / fx, 2)},
                      Review="Review suggested", Status="Conditional research",
                      Rationale=qtext + f"£{stock_value:,.0f} holding exceeds £12k normal concentration reference; reduce toward it if rebound occurs. " + rtext)
        return result

    # Event window takes precedence over a weak technical score for routine
    # names, so NU/FN display their actual earnings risk explicitly.
    if event_risk:
        result.update(Action="Hold / wait — event" if shares else "Wait — event",
                      Review="Review suggested",
                      Rationale=qtext + "Near earnings or recent earnings; new buys paused. " + rtext)
        return result

    # A weak trend *by itself* is not enough to sell a normal-sized name.
    # This explicitly fixes the former automatic AMBA 25% trim.
    if shares and weak:
        result.update(Action="Hold / watch", Rationale=qtext +
                      "Weak trend alone is not a reason to sell a non-concentrated position. " + rtext)
        return result

    if ratio > MAX_SWING_RATIO + 1e-9 or market == "Defensive":
        result.update(Action="Hold / wait", Rationale=qtext +
                      ("Swing allocation above 30% reference. " if ratio > MAX_SWING_RATIO else "Defensive regime; no new buys. ") + rtext)
        return result

    # Prevent an appearance of fully integrated evidence where one factor is
    # too old or completely absent. Financial & valuation inputs can be
    # imperfect, but never silently omitted in a numeric BUY recommendation.
    if qstate != "Provisional / current" or vstate == "Unavailable":
        result.update(Action="Hold / wait" if shares else "Wait — research",
                      Rationale=qtext + "Not enough current quality/valuation evidence for a new buy. " + rtext)
        return result

    # Positive quality is not a claim of cheapness. Bank scores are provisional
    # and omit NPL/loan loss quality, so they cannot justify an autonomous buy.
    bank = finance.get("Business model") in {"Bank", "Bank/lending hybrid"}
    if bank:
        result.update(Action="Hold / wait" if shares else "Wait — bank review",
                      Review="Review suggested",
                      Rationale=qtext + "Bank/lender quality lacks credit-loss and funding-risk data; defer new buys. " + rtext)
        return result

    if valuation_caution:
        result.update(Action="Hold / wait" if shares else "Wait — valuation",
                      Rationale=qtext + opportunity["Valuation caution"] + ". Price-level review alone is insufficient to justify entry. " + rtext)
        return result

    if not strong or quality is None or quality < 55:
        result.update(Action="Hold / wait" if shares else "Wait — setup",
                      Rationale=qtext + "Entry trend/quality combination not strong enough. " + rtext)
        return result

    # Entry is LAST-CLOSE based; never an intraday quote. A pullback is
    # preferable for Mixed markets or extended prices relative to MA20.
    if market == "Mixed" or price > ma20 * 1.025:
        target = min(price * (1 - min(atr * 0.40, 5.0) / 100), ma20 * 1.01)
        action = "Buy on pullback"
    else:
        target = price
        action = "Buy near last close"
    buy_limit = round(max(0.01, target), 2)
    headroom = max(0.0, NORMAL_SINGLE_GBP - stock_value)
    budget = min(INITIAL_TRANCHE_GBP if market == "Supportive" else 1500.0, cash, headroom)
    if high_vol: budget = min(budget, 1500.0)
    # Risk per candidate: stress scenario of 1.5 ATR against the entry.
    # £150 or 0.5% of Swing value, whichever is smaller; a stress-budget
    # heuristic NOT a promise of bounded downside (gaps can be larger).
    stress_budget_gbp = min(150.0, 0.005 * max(0.0, swing))
    if atr > 0 and buy_limit > 0:
        budget = min(budget, stress_budget_gbp / (1.5 * atr / 100))
    # Price limit may be reached later with materially different FX; recompute.
    # Cash-to-stock rotation leaves the swing allocation unchanged, but the
    # stock exposure must remain under the 30% total allocation reference.
    max_additional_equity = max(0.0, MAX_SWING_RATIO * total - (swing - cash))
    budget = min(budget, max_additional_equity)
    buy_qty = min(math.floor(budget * fx / buy_limit), math.floor(cash * fx / buy_limit))
    if buy_qty < 1:
        result.update(Action="Hold / wait" if shares else "Wait — sizing",
                      Rationale=qtext + "No capacity under cash and £12k single-name reference. " + rtext)
        return result
    result.update(assess_price_scenario(price=price, atr_pct=atr,
                   ma20=ma20, ma50=ma50, limit=buy_limit,
                   quantity=buy_qty, fx_gbp_usd=fx))
    result.update(Action=action, **{"Buy limit USD": buy_limit, "Buy shares": buy_qty,
                  "Buy amount GBP": round(buy_qty * buy_limit / fx, 2)},
                  Status="Conditional research", Rationale=qtext +
                  f"T1.0 and provisional financial quality align; £{budget:,.0f} capped entry budget. " +
                  "Valuation multiple is observed, NOT a verified fair-value signal. "
                  "A 1.5-ATR adverse move is budgeted as a stress proxy, not capped loss. " + rtext)
    return result
