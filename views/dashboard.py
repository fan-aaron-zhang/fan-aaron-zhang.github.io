"""Five-tab Streamlit navigation for Swing Quant V1.5a.4.

All portfolio and technical calculations are inherited unchanged from V1.5a.3.
The two future tabs intentionally contain no unvalidated trading signals.
"""
import io
import hashlib
from datetime import date
import pandas as pd
import streamlit as st
from config import EXCLUDED_SHEETS, QTY_TOLERANCE, SECTOR_GROUPS, APP_VERSION, MODEL_VERSION
from core.portfolio import (numeric, analyse_sheet, read_cash_from_summary,
                            classify_account)
from core.market_data import get_daily_close, build_valuation
from core.risk import complete_value
from views.technical import render_technical_research
from views.fundamental_diagnostic import render_fundamental_diagnostic
from views.fundamentals import render_fundamental_research
from views.universe import render_universe
from views.risk_environment import render_risk_environment
from views.decisions import render_decisions
from views.landing import render_landing


def render_dashboard():
    with st.sidebar:
        st.subheader("Portfolio data")
        uploaded = st.file_uploader("Upload Portfolio.xlsx (read only)", type=["xlsx"])
        st.caption("Excel is read-only and stays separate from the scoring model.")
        st.caption(f"Software: {APP_VERSION} · Technical model: {MODEL_VERSION}")
        st.caption("Pricing: last available daily close; no live execution quotes.")
        st.caption("Alan Junior ISA is excluded from your portfolio totals.")

    landing_tab, quant_tab, decisions_tab, portfolio_tab, evaluation_tab, data_tab = st.tabs([
        "Dashboard", "Quant Analysis", "Trade Decisions", "Portfolio & Risk",
        "Model Evaluation", "Data & Settings",
    ])
    with landing_tab:
        st.caption("Action-first overview of the integrated 22-stock research; Wait names are foldable.")
    with quant_tab:
        render_universe()
        render_fundamental_research()
        render_risk_environment()
    with decisions_tab:
        st.subheader("Trade Decisions")
        st.info("Upload Portfolio.xlsx to generate portfolio-aware conditional research plans. No orders are placed.")
    with evaluation_tab:
        st.subheader("Model Evaluation")
        st.info("Not yet implemented. Historical validation, forward testing, "
                "Rank IC and model comparisons will be added in V1.5b and later.")
    with data_tab:
        render_fundamental_diagnostic()
        st.divider()

    if uploaded is None:
        with landing_tab:
            render_landing()
        with quant_tab:
            render_technical_research([])
        with portfolio_tab:
            st.info("Upload your Portfolio.xlsx using the sidebar to view positions and risk.")
        with data_tab:
            st.subheader("Data & Settings")
            st.info("Upload your latest Excel workbook. Swing cash is read from Summary → Cash → column G.")
        return

    try:
        workbook = pd.ExcelFile(io.BytesIO(uploaded.getvalue()), engine="openpyxl")
        cash, cash_source = read_cash_from_summary(workbook)
        results, details, warnings = [], {}, []
        today = date.today()
        for sheet_name in workbook.sheet_names:
            if sheet_name in EXCLUDED_SHEETS:
                continue
            frame = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
            summary, audit, issues = analyse_sheet(sheet_name, frame, today)
            summary["Group"] = classify_account(sheet_name, summary["Account type"])
            results.append(summary)
            details[sheet_name] = audit
            warnings.extend(f"{sheet_name}: {issue}" for issue in issues)
        if not results:
            with data_tab:
                st.error("No supported trading worksheets found.")
            with quant_tab:
                render_technical_research([])
            return

        with data_tab:
            st.subheader("Data & Settings")
            st.caption(f"Uploaded workbook: {uploaded.name}")
            result_df = pd.DataFrame(results)
            unknown = result_df.loc[result_df["Group"] == "Unclassified", "Stock / account"].tolist()
            if unknown:
                st.warning("Unclassified trading sheets (excluded from ratios): " + ", ".join(unknown))
    
            swing = result_df[result_df["Group"] == "Swing"].copy()
            core = result_df[result_df["Group"] == "Core ETF"].copy()
            junior = result_df[result_df["Group"] == "Junior ISA"].copy()
            if cash is None:
                st.error("Swing cash could not be verified from Excel: " + cash_source)
            else:
                st.caption(f"Cash source: {cash_source} = £{cash:,.2f}. Never entered manually or inferred from trades.")
    
            st.subheader("Swing — positions and historical GBP costs")
            st.caption("Only Swing securities are analysed. Core ETFs are valued for allocation; Alan Junior ISA is excluded from all totals.")
            st.dataframe(swing[["Stock / account", "Summary shares", "Calculated shares", "Status",
                                 "Avg cost GBP/share", "Remaining cost GBP", "Realised P/L GBP"]],
                         hide_index=True, use_container_width=True,
                         column_config={"Remaining cost GBP": st.column_config.NumberColumn(format="£%.2f"),
                                        "Realised P/L GBP": st.column_config.NumberColumn(format="£%.2f")})
            if (swing["Status"] != "MATCH").any():
                st.warning("Swing ledger is not fully reconciled; some values or ratios may be unavailable.")

        with portfolio_tab:
            st.subheader("Swing — market value and unrealised GBP P/L")
            with st.spinner("Retrieving last available market closes and GBP/USD..."):
                fx_rate, fx_date, fx_error = get_daily_close("GBPUSD=X")
                if fx_rate is not None and not (0.5 < fx_rate < 2.5):
                    fx_rate, fx_error = None, "Implausible GBP/USD rate"
                swing_val = build_valuation(swing, fx_rate, fx_date)
                # Only core ETFs with known symbols are actively quoted.
                core_val = build_valuation(core[core["Stock / account"] != "HSBC-ETF"], fx_rate, fx_date)
    
            if fx_rate is None:
                st.warning(f"GBP/USD unavailable: {fx_error}. USD positions cannot be valued.")
            else:
                st.caption(f"1 GBP = {fx_rate:.5f} USD (FX daily close: {fx_date}). Equity prices are previous available closes, not execution quotes.")
    
            st.dataframe(swing_val[["Stock / account", "Shares", "Price", "Quote currency", "Price date",
                                    "Cost GBP", "Market value GBP", "Unrealised P/L GBP",
                                    "Unrealised return %", "Status", "Note"]],
                         hide_index=True, use_container_width=True,
                         column_config={"Market value GBP": st.column_config.NumberColumn(format="£%.2f"),
                                        "Unrealised P/L GBP": st.column_config.NumberColumn(format="£%.2f"),
                                        "Cost GBP": st.column_config.NumberColumn(format="£%.2f"),
                                        "Unrealised return %": st.column_config.NumberColumn(format="%.2f%%")})
    
            swing_value, missing_swing = complete_value(swing_val)
            core_quoted_value, missing_core = complete_value(core_val)
    
            # HSBC Dynamic is intentionally a *snapshot* from the Excel holding sheet,
            # NOT a current NAV. Only use it when the share ledger is reconciled.
            hsbc_rows = core[core["Stock / account"] == "HSBC-ETF"]
            hsbc_snapshot = None
            if len(hsbc_rows) == 1:
                hsbc_row = hsbc_rows.iloc[0]
                if (hsbc_row["Status"] == "MATCH" and
                        numeric(hsbc_row["Excel value GBP (snapshot)"]) is not None):
                    hsbc_snapshot = float(hsbc_row["Excel value GBP (snapshot)"])
            if len(hsbc_rows) != 1 or hsbc_snapshot is None:
                missing_core.append("HSBC-ETF snapshot")
            if not core.empty and (core["Status"] != "MATCH").any():
                missing_core.extend(core.loc[core["Status"] != "MATCH", "Stock / account"].tolist())
    
            st.divider()
            st.subheader("Swing risk dashboard")
            # The Junior ISA belongs to Alan. Never count it as available portfolio capital.
            total_swing = swing_value + cash if swing_value is not None and cash is not None else None
            total_core = core_quoted_value + hsbc_snapshot if core_quoted_value is not None and hsbc_snapshot is not None and not missing_core else None
            total_holding = total_swing + total_core if total_swing is not None and total_core is not None else None
    
            alloc = (100 * total_swing / total_holding
                     if total_swing is not None and total_holding is not None and total_holding > 0 else None)
            cash_ratio = (100 * cash / total_swing if total_swing is not None and total_swing > 0 else None)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Swing cash (Excel)", f"£{cash:,.2f}" if cash is not None else "Unavailable")
            c2.metric("Swing invested market value", f"£{swing_value:,.2f}" if swing_value is not None else "Unavailable")
            c3.metric("Cash / Swing", f"{cash_ratio:.2f}%" if cash_ratio is not None else "Unavailable")
            c4.metric("Swing / Invested portfolio", f"{alloc:.2f}%" if alloc is not None else "Unavailable")
    
            if alloc is None:
                problems = []
                if missing_swing: problems.append("Missing Swing prices: " + ", ".join(missing_swing))
                if missing_core: problems.append("Missing Core ETF values: " + ", ".join(sorted(set(missing_core))))
                if cash is None: problems.append(cash_source)
                st.warning("Cannot calculate a reliable 30% allocation ratio. " + "; ".join(problems))
            elif alloc > 30:
                st.error(f"Swing allocation {alloc:.2f}% exceeds your 30% ceiling.")
            elif alloc >= 27:
                st.warning(f"Swing allocation {alloc:.2f}% is close to the 30% ceiling.")
            else:
                st.success(f"Swing allocation {alloc:.2f}% is below the 30% ceiling.")
    
            st.metric("Total holding (excl. Alan Junior ISA)", f"£{total_holding:,.2f}" if total_holding is not None else "Unavailable")
            st.caption("Core valuation: VWRP.L = last available GBP close; HSBC Dynamic = Excel workbook snapshot, NOT a fresh fund NAV. "
                       "These valuations may be from different dates. Alan Junior ISA is always excluded. "
                       "Your wider bank cash holdings are not included in the invested-portfolio allocation denominator.")
    
            if swing_value is not None and total_swing is not None and total_swing > 0:
                positions = swing_val[(swing_val["Shares"].fillna(0) > QTY_TOLERANCE) & (swing_val["Status"] == "VALUED")].copy()
                positions["% of Swing incl cash"] = positions["Market value GBP"] / total_swing * 100
                positions = positions.sort_values("Market value GBP", ascending=False)
                st.subheader("Swing position concentration")
                st.dataframe(positions[["Stock / account", "Market value GBP", "% of Swing incl cash"]],
                             hide_index=True, use_container_width=True,
                             column_config={"Market value GBP": st.column_config.NumberColumn(format="£%.2f"),
                                            "% of Swing incl cash": st.column_config.NumberColumn(format="%.2f%%")})
                # Broad exposure groups for diversification checks; not performance forecasts.
                positions["Sector"] = positions["Stock / account"].map(SECTOR_GROUPS).fillna("Other / review")
                sectors = positions.groupby("Sector", as_index=False)["Market value GBP"].sum()
                sectors["% of Swing incl cash"] = sectors["Market value GBP"] / total_swing * 100
                st.subheader("Swing sector concentration")
                st.dataframe(sectors.sort_values("Market value GBP", ascending=False),
                             hide_index=True, use_container_width=True,
                             column_config={"Market value GBP": st.column_config.NumberColumn(format="£%.2f"),
                                            "% of Swing incl cash": st.column_config.NumberColumn(format="%.2f%%")})
                pl_total = float(positions["Unrealised P/L GBP"].sum())
                st.metric("Swing unrealised P/L (GBP)", f"£{pl_total:,.2f}")
            else:
                st.info("Position concentration / aggregate Swing P&L withheld until all nonzero Swing holdings are valued.")

        workbook_fingerprint = hashlib.sha256(uploaded.getvalue()).hexdigest()[:16]
        with decisions_tab:
            render_decisions(swing, swing_val, cash_gbp=cash,
                             swing_value_gbp=total_swing, total_portfolio_gbp=total_holding,
                             fx_rate=fx_rate, fx_date=fx_date, allocation_pct=alloc,
                             workbook_fingerprint=workbook_fingerprint)

        with landing_tab:
            render_landing(workbook_fingerprint=workbook_fingerprint, cash_gbp=cash,
                           fx_date=fx_date, fx_rate=fx_rate,
                           total_portfolio_gbp=total_holding, allocation_pct=alloc,
                           swing=swing, swing_val=swing_val, swing_value_gbp=total_swing,
                           holdings=swing.loc[(swing["Calculated shares"].fillna(0) > 0) &
                                              (swing["Status"] == "MATCH"), "Stock / account"].tolist())

        with quant_tab:
            render_technical_research(swing["Stock / account"].tolist())

        with data_tab:
            st.divider()
            st.subheader("Transaction cost audit (Swing only)")
            available = swing["Stock / account"].tolist()
            if available:
                selected = st.selectbox("Choose Swing stock", available)
                st.dataframe(pd.DataFrame(details[selected]), hide_index=True, use_container_width=True)
            with st.expander(f"Data quality warnings ({len(warnings)})"):
                if warnings:
                    for issue in warnings:
                        st.write("- " + issue)
                else:
                    st.success("No transaction warnings")
            st.caption("Read-only, manually uploaded workbook. No automatic order execution. Moving weighted-average GBP cost is not a UK tax/Section 104 calculation.")
    except Exception as exc:
        with data_tab:
            st.error(f"Workbook analysis failed: {type(exc).__name__}: {exc}")
        with portfolio_tab:
            st.warning("Portfolio results unavailable. Review the workbook in Data & Settings.")
        with quant_tab:
            st.info("The technical research panel uses market data separately from the portfolio workbook.")
            render_technical_research([])
