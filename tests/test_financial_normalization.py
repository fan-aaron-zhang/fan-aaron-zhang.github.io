"""Regression tests for period alignment and financial schema handling (offline)."""
from datetime import date
import pandas as pd
from core.fundamentals import summarize_yahoo

NOW = date(2026, 11, 8)
QUARTERS = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])


def inc():
    return pd.DataFrame([[120, 118, 110, 105, 100], [24, 23, 21, 20, 18], [12, 11, 9, 8, 7]],
                        index=[' total-revenue ', 'operating income as reported', 'Net Income'],
                        columns=QUARTERS)


def cf():
    return pd.DataFrame([[18, 19, 17, 18, 15], [-6, -5, -5, -4, -3]],
                        index=['Operating Cash Flow', 'Capital Expenditure'], columns=QUARTERS)


def test_case_punctuation_aliases_recover_bsy():
    report = summarize_yahoo('BSY', inc(), cf(), pd.DataFrame(), {}, NOW)
    assert report['Quality / 100'] is not None
    assert report['Coverage %'] == 100
    assert report['Operating margin %'] == 20
    assert report['Revenue growth %'] == 20


def test_ptc_cashflow_earlier_quarter_is_not_assumed_latest():
    cash = cf().loc[:, QUARTERS[1:]]
    report = summarize_yahoo('PTC', inc(), cash, pd.DataFrame(), {}, NOW)
    assert report['FCF margin %'] is None
    assert report['Coverage %'] == 80
    assert report['Quality / 100'] is not None
    audit = {line['Field']: line for line in report['Source audit']}
    assert audit['Operating cash flow']['Reason'] == 'Quarter missing from this statement'
    assert audit['Operating cash flow']['Usable'] is False


def test_irdm_missing_raw_fields_no_invented_score():
    income = inc().iloc[:1].copy()
    report = summarize_yahoo('IRDM', income, pd.DataFrame(), pd.DataFrame(), {}, NOW)
    assert report['Quality / 100'] is None
    assert report['Coverage %'] == 35
    assert report['Missing metrics'] == 'Operating margin, Net margin, FCF margin'
    assert {a['Reason'] for a in report['Source audit']} >= {'Yahoo row absent or unmapped', 'Statement empty or unavailable'}


def test_sofi_bank_route_only_scores_with_adequate_inputs():
    info = {'returnOnEquity': .16, 'returnOnAssets': .015}
    balance = pd.DataFrame([[18], [160]], index=['Stockholders Equity', 'Total Assets'],
                           columns=pd.to_datetime(['2026-09-30']))
    report = summarize_yahoo('SOFI', inc(), cf(), pd.DataFrame(), info, NOW, balance_sheet=balance)
    assert report['Quality / 100'] is not None
    assert report['Business model'] == 'Bank/lending hybrid'
    assert report['Decision-ready'] is False
    assert 'ROE %' in report and 'FCF margin %' not in report
