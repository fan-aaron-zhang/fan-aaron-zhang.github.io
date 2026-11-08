"""Integrated, evidence-qualified trade decisions. No broker interaction."""
from datetime import date
import pandas as pd
import streamlit as st
from config import WATCHLIST, SECTOR_BENCHMARKS, MARKET_BENCHMARK, REGIME_SYMBOLS, EVENT_NEAR_DAYS, EVENT_WATCH_DAYS
from core.market_data import load_signal_history, get_daily_close
from core.scoring import compute_technical
from core.market_regime import evaluate_market_regime
from core.macro_score import evaluate_macro_score, MACRO_SYMBOLS
from core.event_risk import assess_earnings_risk
from core.decision_engine import evaluate_candidate, DECISION_VERSION
from core.portfolio_allocator import allocate_buy_candidates, ALLOCATOR_VERSION
from core.fundamentals import QUALITY_MODEL_VERSION, BANK_MODEL_VERSION
from views.fundamentals import _load_fundamental
from core.research_snapshot import make_research_snapshot
from core.overall_score import calculate_overall, overall_explanation, OVERALL_VERSION
from views.risk_environment import _load_calendar, _load_earnings_history
import json


def generate_research_batch(selected, swing, swing_val, *, cash_gbp, swing_value_gbp,
                            total_portfolio_gbp, fx_rate, fx_date, allocation_pct,
                            workbook_fingerprint):
    """Shared 22-stock or selection-wide analysis. Fetches data once per ticker.

    Both Dashboard and Trade Decisions consume the SAME immutable session result.
    This is deliberately synchronous/on-demand, never a background promise.
    """
    if not selected or any(t not in WATCHLIST for t in selected):
        raise ValueError("Invalid stock selection")
    if any(v is None for v in (cash_gbp, swing_value_gbp, total_portfolio_gbp, fx_rate, allocation_pct)):
        raise ValueError("Verified holdings, FX, cash and allocation are required")
    rows, snapshots = [], {}
    histories = {sym: load_signal_history(sym)[0] for sym in MACRO_SYMBOLS}
    regime = evaluate_market_regime(histories)
    macro = evaluate_macro_score(histories)
    spy = histories[MARKET_BENCHMARK]
    sectors = {SECTOR_BENCHMARKS[t]: load_signal_history(SECTOR_BENCHMARKS[t])[0]
               for t in selected}
    positions = {str(r["Stock / account"]): r for _, r in swing.iterrows()}
    values = {str(r["Stock / account"]): r for _, r in swing_val.iterrows()}
    for ticker in selected:
        try:
            price, price_date, _ = get_daily_close(ticker)
            raw, _ = load_signal_history(ticker)
            sector_symbol = SECTOR_BENCHMARKS[ticker]
            technical = compute_technical(ticker, raw, spy, sectors[sector_symbol], sector_symbol)
            calendar, _ = _load_calendar(ticker)
            earnings_history, _ = _load_earnings_history(ticker)
            event = assess_earnings_risk(ticker, calendar, earnings_history=earnings_history,
                                         near_days=EVENT_NEAR_DAYS, watch_days=EVENT_WATCH_DAYS)
            ledger_row, val_row = positions.get(ticker), values.get(ticker)
            shares = float(ledger_row["Calculated shares"]) if ledger_row is not None and pd.notna(ledger_row["Calculated shares"]) else 0.0
            val = float(val_row["Market value GBP"]) if val_row is not None and pd.notna(val_row["Market value GBP"]) else (0.0 if shares == 0 else None)
            ledger_ok = ledger_row is None or ledger_row["Status"] == "MATCH"
            # An adjusted technical close and raw market close may differ due
            # to dividends/splits. If that mismatch is large, don't size.
            tech_close = technical.get("Close USD")
            mismatch = (price is not None and tech_close is not None and
                        abs(price / tech_close - 1) > 0.10)
            if mismatch:
                ledger_ok = False
            try:
                financial, financial_errors = _load_fundamental(ticker, (QUALITY_MODEL_VERSION, BANK_MODEL_VERSION))
            except Exception as exc:
                financial = {}
                financial_errors = [f"Yahoo financial retrieval: {type(exc).__name__}"]
            report = evaluate_candidate(ticker, technical, current_close=price,
                  price_date=price_date, fx_rate=fx_rate, fx_date=fx_date,
                  cash_gbp=cash_gbp, holding_shares=shares, holding_value_gbp=val,
                  swing_value_gbp=swing_value_gbp, total_portfolio_gbp=total_portfolio_gbp,
                  regime=regime, event=event, financial=financial, ledger_ok=ledger_ok)
            if mismatch:
                report["Rationale"] += "; adjusted/unadjusted price mismatch >10%; review corporate actions"
            if financial_errors:
                report["Financial data warnings"] = "; ".join(financial_errors)
            rows.append(report)
            # Export essential numerical research evidence only. Raw Yahoo
            # row listings and transactions are unnecessary for handoff.
            finance_summary = {k: v for k, v in financial.items()
                               if k not in {"Raw Yahoo rows", "Source audit", "Notes"}}
            snapshots[ticker] = make_research_snapshot(ticker,
                price_facts={"last_unadjusted_close_usd": price, "price_date": price_date,
                             "technical": technical},
                financial_research=finance_summary,
                portfolio_facts={"shares": shares, "market_value_gbp": val,
                                 "swing_cash_gbp": cash_gbp, "swing_allocation_pct": allocation_pct,
                                 "fx_gbp_usd": fx_rate, "fx_date": fx_date},
                model_assessment={"market": regime, "macro": macro, "earnings": event,
                                  "financials_and_valuation": "Yahoo F0.5/B0.2 incorporated as provisional, not fair value"},
                trading_plan=report,
                timestamps={"generated_on": str(date.today()), "software": "V1.8j"})
        except Exception as exc:
            # One bad Yahoo record must not erase the other 21 stock decisions.
            # Do NOT substitute a technical-only Buy/Sell for a failed full review.
            error = f"{type(exc).__name__}: {str(exc)[:180]}"
            fallback = evaluate_candidate(
                ticker, {"Status":"UNAVAILABLE"}, current_close=None,
                price_date=None, fx_rate=fx_rate, fx_date=fx_date,
                cash_gbp=cash_gbp, holding_shares=0,
                holding_value_gbp=0, swing_value_gbp=swing_value_gbp,
                total_portfolio_gbp=total_portfolio_gbp,
                regime=regime, event={"status":"Unknown"}, financial={})
            fallback["Rationale"] = "Full research unavailable: " + error
            fallback["Review"] = "Data review"
            rows.append(fallback)
            snapshots[ticker] = make_research_snapshot(
                ticker, price_facts={"price_date":None,"technical":{}},
                financial_research={},
                portfolio_facts={"swing_cash_gbp":cash_gbp,
                                 "data_error":"Per-stock data retrieval failed"},
                model_assessment={"market":regime,"macro":macro,
                                  "earnings":{"status":"Unknown"}},
                trading_plan=fallback,
                timestamps={"generated_on":str(date.today()),"software":"V1.8j"})
    # Allocate *all selected* buy proposals together; never assume the
    # same cash can finance multiple independent purchase plans.
    allocated_rows, allocation = allocate_buy_candidates(rows, cash_gbp, fx_rate)
    for row in allocated_rows:
        ticker = row["Ticker"]
        if int(row.get("Buy shares") or 0)>0:
            from core.trade_scenarios import assess_price_scenario
            pf=(snapshots.get(ticker) or {}).get("facts",{}).get("portfolio",{})
            pricefacts=(snapshots.get(ticker) or {}).get("facts",{}).get("market",{})
            tech=pricefacts.get("technical") or {}
            row.update(assess_price_scenario(
                price=pricefacts.get("last_unadjusted_close_usd"),
                atr_pct=tech.get("ATR14 %"), ma20=tech.get("MA20"), ma50=tech.get("MA50"),
                limit=row.get("Buy limit USD"), quantity=row.get("Buy shares"),
                fx_gbp_usd=pf.get("fx_gbp_usd")))
        overall = calculate_overall(row.get("Technical"), row.get("Quality"))
        # Dashboard/export only: Overall must never alter actions or orders.
        row["Overall"] = overall
        if ticker in snapshots:
            snapshots[ticker]["trading_plan"] = dict(row)
            snapshots[ticker]["model_assessment"]["overall"] = {
                "score": overall, "model": OVERALL_VERSION,
                "basis": overall_explanation(row.get("Technical"), row.get("Quality")),
                "note": "Experimental descriptive composite; not an order trigger or fair value"}
            snapshots[ticker]["model_assessment"]["shared_cash_allocation"] = allocation
    return {"tickers": tuple(selected), "rows": allocated_rows, "macro": macro,
            "allocation": allocation, "snapshots": snapshots,
            "generated": str(date.today()), "workbook_fingerprint": workbook_fingerprint,
            "cash": cash_gbp, "fx_date": fx_date, "fx_rate": fx_rate,
            "total": total_portfolio_gbp}


def render_decisions(swing, swing_val, *, cash_gbp, swing_value_gbp,
                     total_portfolio_gbp, fx_rate, fx_date, allocation_pct, workbook_fingerprint):
    st.subheader("Trade Decisions — shared-cash conditional plans")
    st.caption(f"V1.8j · {DECISION_VERSION} · {ALLOCATOR_VERSION}. Daily closes, not live quotes or broker orders. "
               "Yahoo quality and valuation are integrated as provisional evidence, not verified fair-value estimates.")
    current = swing[(swing["Calculated shares"].fillna(0) > 0) & (swing["Status"] == "MATCH")]["Stock / account"].tolist()
    defaults = [ticker for ticker in current if ticker in WATCHLIST][:4]
    # Landing page passes a pending shortlist across reruns. Never mutate a
    # Streamlit widget key after the widget has been instantiated.
    pending = st.session_state.pop("v18_pending_shortlist", None)
    if pending:
        st.session_state["v18_decision_tickers"] = [x for x in pending if x in WATCHLIST][:5]
    selected = st.multiselect("Stocks to review in detail (up to 5 per run)", list(WATCHLIST),
                              default=defaults, key="v18_decision_tickers")
    if len(selected) > 5:
        st.warning("Select no more than five for a quick, reliable check. Your research universe still contains all 22 stocks.")
        return
    if not selected:
        st.info("Choose one or more stocks. Actual positions and Swing cash are taken from your uploaded Excel.")
        return
    if cash_gbp is None or swing_value_gbp is None or total_portfolio_gbp is None or fx_rate is None:
        st.warning("Portfolio, FX or core valuation is incomplete. Numeric trade plans cannot be trusted.")
        return
    if allocation_pct is None:
        st.warning("Cannot verify Swing allocation. Trade plans unavailable.")
        return
    st.caption(f"Available Swing cash £{cash_gbp:,.2f} · Swing allocation {allocation_pct:.1f}% "
               f"(includes cash) · 1 GBP = {fx_rate:.4f} USD, dated {fx_date}. "
               "Maximum entry budget £3k per candidate (£1.5k if market Mixed), not a target allocation.")
    if st.button("Generate conditional plans", key="v18_generate"):
        full = st.session_state.get("v18_full_results")
        if (full and full.get("generated") == str(date.today())
                and full.get("workbook_fingerprint") == workbook_fingerprint
                and full.get("fx_date") == fx_date and full.get("fx_rate") == fx_rate
                and full.get("cash") == cash_gbp and full.get("total") == total_portfolio_gbp):
            # Reuse the complete batch; never allow dashboard and detail to disagree.
            st.session_state["v18_results"] = full
        else:
            with st.spinner("Checking selected stocks; this may take longer the first time..."):
                st.session_state["v18_results"] = generate_research_batch(
                    selected, swing, swing_val, cash_gbp=cash_gbp,
                    swing_value_gbp=swing_value_gbp, total_portfolio_gbp=total_portfolio_gbp,
                    fx_rate=fx_rate, fx_date=fx_date, allocation_pct=allocation_pct,
                    workbook_fingerprint=workbook_fingerprint)
    saved = st.session_state.get("v18_results")
    if not saved:
        st.info("Plans are generated only when requested. No orders are created.")
        return
    if (saved.get("workbook_fingerprint") != workbook_fingerprint or
            saved.get("cash") != cash_gbp or saved.get("fx_date") != fx_date or
            saved.get("fx_rate") != fx_rate or saved.get("total") != total_portfolio_gbp or
            saved.get("generated") != str(date.today())):
        st.warning("Portfolio, valuation, FX or date changed since this plan was generated. Generate a new plan.")
        return
    if not set(selected).issubset(set(saved["tickers"])):
        st.warning("Selection changed. Generate new plans before using displayed results.")
        return
    m=saved.get('macro') or {}
    st.caption(f"Macro M0.2: {m.get('score', 'N/A')}/100 · {m.get('status','Unknown')} · "
               f"as of {m.get('as_of','N/A')} (independent risk context, NOT a forecast)")
    with st.expander('Macro factor contributions and limitations'):
        st.write(m.get('components', {}))
        st.caption(m.get('reason', 'No macro data available'))
    st.caption(f"Generated {saved['generated']} · prices are last-close/MA/ATR references, NOT validated fair values. "
               "Buy proposals share the same cash across the saved assessment batch (up to 22 names).")
    allocation = saved.get("allocation", {})
    a1, a2, a3 = st.columns(3)
    a1.metric("Shared cash", f"£{allocation.get('Available cash GBP', 0):,.0f}")
    a2.metric("Batch buys allocated", f"£{allocation.get('Proposed committed GBP', 0):,.0f}")
    a3.metric("Unallocated cash", f"£{allocation.get('Unallocated GBP', 0):,.0f}")
    st.caption("Shared-cash allocation applies to all stocks in the saved batch (22 if scanned from Dashboard). "
               "Priority is a simple heuristic, not an optimized portfolio or order instruction.")
    df = pd.DataFrame([r for r in saved["rows"] if r["Ticker"] in selected])
    cols = ["Ticker", "Action", "Buy limit USD", "Buy shares", "Buy amount GBP",
            "Sell limit USD", "Sell shares", "Sell amount GBP", "Allocation status", "Technical", "Quality", "Market", "Earnings", "Review", "Status"]
    st.markdown("**1. Decision summary — action, USD limits and GBP allocation**")
    st.dataframe(df[["Ticker", "Action", "Buy limit USD", "Buy shares", "Buy amount GBP",
                     "Sell limit USD", "Sell shares", "Sell amount GBP", "Allocation status", "Review"]],
                 hide_index=True, use_container_width=True)
    st.markdown("**2. Opportunity assessment — summary scores (not directly comparable across industries)**")
    st.dataframe(df[["Ticker", "Technical", "Quality", "Quality status", "Valuation status",
                     "Market", "Earnings", "Valuation caution"]], hide_index=True, use_container_width=True)
    st.markdown("**3. Position & risk — portfolio limits and events**")
    position_rows = []
    for ticker in df["Ticker"]:
        snapshot = saved.get("snapshots", {}).get(ticker, {})
        pf = snapshot.get("facts", {}).get("portfolio", {})
        position_rows.append({"Stock": ticker, "Shares held":pf.get("shares"),
                              "Market value GBP":pf.get("market_value_gbp"),
                              "Cash GBP":pf.get("swing_cash_gbp"),
                              "Swing allocation %":pf.get("swing_allocation_pct"),
                              "Review":next(r.get("Review") for r in saved["rows"] if r["Ticker"]==ticker)})
    st.dataframe(pd.DataFrame(position_rows), hide_index=True, use_container_width=True)
    st.markdown("**4. Price & execution conditions — technical references, not fair values**")
    st.caption("1.5 ATR is a *hypothetical adverse price move*, not a stop or maximum loss. MA recovery references are not price targets; ratios are descriptive only.")
    st.dataframe(df[["Ticker", "Technical support reference USD", "Recovery reference USD",
                     "Scenario entry USD", "1.5 ATR adverse USD",
                     "MA recovery reference USD", "Reward / shock reference",
                     "Stress loss GBP", "Reassessment trigger", "Invalidation"]],hide_index=True,use_container_width=True)
    st.markdown("**Detailed rationale (optional)**")
    for _, r in df.iterrows():
        with st.expander(f"{r['Ticker']} — {r['Action']} · why / limitations"):
            st.write(r["Rationale"])
            st.write("**Quality evidence:**", r["Quality evidence"])
            st.write("**Valuation evidence:**", r["Valuation evidence"])
            st.write("**Opportunity setup:**", r["Opportunity setup"])
            st.write("**Reassessment trigger:**", r["Reassessment trigger"])
            st.write("**Reference levels (USD, not fair values):**",
                     {"Technical support": r["Technical support reference USD"],
                      "Recovery": r["Recovery reference USD"],
                      "One-ATR downside scenario": r["One ATR downside scenario USD"]})
            st.write("**Price/risk scenario (research only):**",
                     {"Entry reference":r.get("Scenario entry USD"),
                      "1.5 ATR adverse USD":r.get("1.5 ATR adverse USD"),
                      "MA recovery USD":r.get("MA recovery reference USD"),
                      "Reward/shock (not expected return)":r.get("Reward / shock reference"),
                      "Stress loss GBP":r.get("Stress loss GBP")})
            st.caption(r.get("Scenario explanation",""))
            st.write("**Valuation caution:**", r["Valuation caution"])
            st.write("**Shared cash allocation:**", r.get("Allocation status"))
            if r.get("Standalone buy shares", 0):
                st.write("**Standalone proposal (before shared budget):**",
                         {"Shares": int(r["Standalone buy shares"]),
                          "Amount GBP": r.get("Standalone buy amount GBP"),
                          "Rank": r.get("Shared-cash rank")})
            st.write("**Invalidation:**", r["Invalidation"])
            if r.get("Financial data warnings"):
                st.warning(r["Financial data warnings"])
            st.caption(f"Price date: {r['Price date']}. Model {r['Model']}. "
                       "Review official company announcements when relevant. Quality and valuation are provisional; "
                       "this is a conditional plan, not an automatic stop, take-profit or executable order.")
    st.divider()
    st.subheader("Research handoff — single-stock JSON")
    chosen = st.selectbox("Snapshot ticker", selected, key="v18_export_ticker")
    payload = json.dumps(saved["snapshots"][chosen], indent=2, ensure_ascii=False, default=str)
    st.download_button("Download snapshot for ChatGPT", payload,
                       file_name=f"swing_quant_{chosen}_{saved['generated']}.json", mime="application/json",
                       key="v18_download")
    with st.expander("Copyable text (optional)"):
        st.code(payload, language="json")
    st.caption("The snapshot contains position figures, not your full transaction history. "
               "Uploading it to ChatGPT is your choice; no API connection or automated transfer.")
