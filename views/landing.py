"""V1.8f action-first Dashboard: all 22 names and one authoritative batch.

Do NOT turn technical triage into portfolio-aware trading actions.
Detailed investigations use the exact same saved batch and export records.
"""
from datetime import date
import json
import pandas as pd
import streamlit as st
from config import WATCHLIST
from core.dashboard_summary import is_current, prepare_display
from core.dashboard_presentation import _style_action_table
from core.overall_score import calculate_overall, overall_explanation, OVERALL_VERSION
from views.decisions import generate_research_batch


def _summary_row(r, positions, financial, portfolio, earnings):
    stock = r['Ticker']
    f = financial or {}
    portfolio = portfolio or {}
    # A numeric valuation score is NOT available: use descriptive, honest status.
    caution = r.get('Valuation caution', '')
    valuation = 'Caution' if caution and caution != 'No specific multiple-based flag (NOT proof of cheapness)' else (
        'Data only' if r.get('Valuation status','').startswith('Observed') else 'Unknown')
    event = str(r.get('Earnings','Unknown'))
    earnings = earnings or {}
    days_until = earnings.get('days_until')
    recent = event.startswith('Recent')
    due_soon = isinstance(days_until,(int,float)) and 0 <= days_until <= 21
    event_risk = recent or due_soon or event.startswith('Within')
    risk_label = 'Unknown' if event == 'Unknown' else 'Event watch' if event_risk else ('Check' if r.get('Review') != 'Routine' else 'No flag*')
    action = str(r.get('Action','Wait'))
    buy = r.get('Buy shares') or 0
    sell = r.get('Sell shares') or 0
    if buy:
        plan = f"Buy {int(buy)} @ ${float(r['Buy limit USD']):,.2f} (limit)"
    elif sell:
        plan = f"Sell {int(sell)} @ ${float(r['Sell limit USD']):,.2f} (limit)"
    else:
        plan = '—'
    return {'Stock':stock,
            'Action':action, 'Overall':calculate_overall(r.get('Technical'), r.get('Quality')), 'Position':round(float(portfolio.get('shares') or 0),2), 'Tech':r.get('Technical'),
            'Quality':r.get('Quality'), 'Valuation':valuation,
            'Event':event,'Risk':risk_label,
            'Plan':plan,'Review':r.get('Review',''),
            'Reason':r.get('Rationale','')}




def render_landing(*, workbook_fingerprint=None, cash_gbp=None, fx_date=None,
                   fx_rate=None, total_portfolio_gbp=None, allocation_pct=None,
                   holdings=(), swing=None, swing_val=None, swing_value_gbp=None):
    st.subheader('Investment Dashboard')
    st.caption('22-stock action overview · portfolio-aware · previous daily closes, not live execution quotes')
    saved = st.session_state.get('v18_full_results')
    valid = is_current(saved, fingerprint=workbook_fingerprint, cash=cash_gbp,
                       fx_rate=fx_rate, fx_date=fx_date, total=total_portfolio_gbp)
    macro = saved.get('macro') if valid else None
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Swing cash',f'£{cash_gbp:,.0f}' if cash_gbp is not None else 'Upload Excel')
    c2.metric('Swing allocation',f'{allocation_pct:.1f}%' if allocation_pct is not None else 'Unknown')
    c3.metric('Macro score',f"{macro['score']}/100" if macro and macro.get('score') is not None else 'Not assessed')
    c4.metric('Macro status',macro.get('status','Unknown') if macro else 'Not assessed')
    if workbook_fingerprint is None:
        st.info('Upload your latest Portfolio.xlsx to enable the full 22-stock action report. No transactions are modified.')
        return
    if st.button('Scan & assess all 22 stocks', type='primary', key='v18f_full_scan'):
        try:
            with st.spinner('Assessing 22 stocks, including Yahoo financial and earnings evidence. Initial load may take time...'):
                batch = generate_research_batch(WATCHLIST, swing, swing_val,
                    cash_gbp=cash_gbp, swing_value_gbp=swing_value_gbp,
                    total_portfolio_gbp=total_portfolio_gbp, fx_rate=fx_rate,
                    fx_date=fx_date, allocation_pct=allocation_pct,
                    workbook_fingerprint=workbook_fingerprint)
            st.session_state['v18_full_results'] = batch
            st.session_state['v18_results'] = batch
            st.rerun()
        except Exception as exc:
            st.error(f'22-stock assessment failed ({type(exc).__name__}): {exc}')
    if not valid:
        st.info('Click Scan & assess all 22 stocks. The report is recreated if the Excel, FX, date or stock coverage changes.')
        return
    if macro and macro.get('score') is None:
        st.warning('Macro proxy data unavailable: score withheld, NOT interpreted as a safe environment.')
    st.caption(f"Decision date {saved['generated']} · {len(saved['rows'])}/22 evaluated · macro {saved.get('macro',{}).get('model','—')} · models are research heuristics")
    financials = {t: (saved['snapshots'].get(t,{}).get('facts',{}).get('financial') or {}) for t in WATCHLIST}
    held=set(holdings)
    major,waiting=prepare_display(saved['rows'],held)
    def present(items):
        return pd.DataFrame([_summary_row(r,held,financials.get(r['Ticker']),
            saved['snapshots'].get(r['Ticker'],{}).get('facts',{}).get('portfolio'),
            saved['snapshots'].get(r['Ticker'],{}).get('model_assessment',{}).get('earnings')) for r in items])
    st.markdown('**Actions — priority & existing holdings**')
    with st.expander('ⓘ How to read Overall, Valuation, Risk, Plan & Review', expanded=False):
        st.markdown('''**Overall (O0.1)** is an **experimental two-factor composite**, computed as **60% Technical + 40% Quality**, only when both scores exist. It is **not** a validated opportunity ranking, and **does not yet score valuation**. Market, earnings, concentration and cash constraints remain separately reflected in **Action**. NU/SOFI use a different Quality model; cross-sector Overall comparisons are provisional. A missing component produces **—**, never an invented score.

**Valuation** is **not a valuation score**: **Caution** means a predefined multiple/profitability warning fired; **Data only** means positive valuation multiples are available but attractiveness is *not* assessed; **Unknown** means usable multiples are unavailable. A missing caution is not evidence that a stock is cheap.

**Risk** is an **event/review flag**, not a probability: **Event watch** means a recent earnings event or a dated earnings event within 21 days; **Check** means another review flag is present; **No flag*** means no *specific* event warning was found; **Unknown** means event evidence is insufficient. None means risk-free.

**Plan** displays only a *conditional limit research proposal*: e.g. `Buy 10 @ $180 (limit)` means a suggested maximum of 10 shares at a USD limit of $180, **not an order already placed**, and **—** means no supported numeric plan. GBP total and sizing rationale are in Trade Decisions.

**Review** is the **level of human verification**, not an action: **Routine** = ordinary monitoring; **Review suggested** = check events, volatility, position or data before considering a trade; **Data review** = essential information missing or unreliable. A stock may be Wait even with Routine status.''')
    st.caption('Overall (O0.1), Technical and Quality use red <40, amber 40–69.9, green ≥70; missing values grey. Overall = 60% Tech + 40% experimental Quality ONLY. This is not a valuation score or a Buy/Sell instruction; bank vs non-bank comparisons remain provisional.')
    st.caption('All held stocks stay visible. The rows below use integrated decisions, not the earlier technical-only screen.')
    if major:
        st.dataframe(_style_action_table(present(major).drop(columns=['Reason'])),hide_index=True,use_container_width=True)
    else:
        st.success('No immediate trade candidates or held-stock actions. Waiting can be a valid decision.')
    with st.expander(f'Other Wait stocks — {len(waiting)} (click to expand)',expanded=False):
        if waiting:
            st.dataframe(_style_action_table(present(waiting).drop(columns=['Reason'])),hide_index=True,use_container_width=True)
        else:
            st.caption('No low-priority unheld Wait stocks.')
    st.caption(f"All {len(major)+len(waiting)} stocks covered. Risk is an event/review flag, not a numerical probability. '*' means no specific model warning, NOT no risk. A blank Plan means no justified numeric trade proposal.")
    alloc=saved.get('allocation') or {}
    st.caption(f"Shared cash: proposed £{alloc.get('Proposed committed GBP',0):,.0f} of £{cash_gbp:,.0f}; "
               "cash is shared across all 22 assessed candidates, with no assumed sale proceeds.")
    st.divider()
    st.markdown('**Quick review & ChatGPT handoff**')
    tickers=[r['Ticker'] for r in major]+[r['Ticker'] for r in waiting]
    chosen=st.selectbox('Review stock',tickers,key='v18f_focus')
    record=next(r for r in saved['rows'] if r['Ticker']==chosen)
    st.write(f"**{chosen}: {record['Action']}** — {record.get('Rationale','')}")
    st.caption(f"Overall: {calculate_overall(record.get('Technical'), record.get('Quality')) if calculate_overall(record.get('Technical'), record.get('Quality')) is not None else '—'} / 100 (O0.1, experimental). {overall_explanation(record.get('Technical'), record.get('Quality'))}.")
    st.caption(f"Reassess: {record.get('Reassessment trigger','Refresh current evidence')}. Price date {record.get('Price date','—')}.")
    payload=saved.get('snapshots',{}).get(chosen)
    if payload:
        text=json.dumps(payload,indent=2,ensure_ascii=False,default=str)
        st.download_button('Export selected stock for ChatGPT (JSON)',text,
                           file_name=f"swing_quant_{chosen}_{saved['generated']}.json",
                           mime='application/json',key='v18f_export')
    st.caption('Detailed opportunity, sizing, risk and data evidence are in Trade Decisions and Quant Analysis.')
