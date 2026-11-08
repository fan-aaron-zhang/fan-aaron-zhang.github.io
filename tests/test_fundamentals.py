"""Pure offline financial normalization tests: zero internet calls."""
from datetime import date
import pandas as pd
from core.fundamentals import summarize_yahoo, _interp, SCALES


def fixture():
    cols = pd.to_datetime(['2026-09-30','2026-06-30','2026-03-31','2025-12-31','2025-09-30'])
    inc = pd.DataFrame([[120,115,110,108,100],[24,20,18,17,15],[15,12,11,9,8]],
                       index=['Total Revenue','Operating Income','Net Income'],columns=cols)
    cf = pd.DataFrame([[23,22,20,18,17],[-6,-5,-4,-4,-3]],
                      index=['Operating Cash Flow','Capital Expenditure'],columns=cols)
    annual = pd.DataFrame([[440,400]],index=['Total Revenue'],columns=pd.to_datetime(['2025-12-31','2024-12-31']))
    return inc, cf, annual


def test_quality_and_valuation():
    inc, cf, annual = fixture()
    r = summarize_yahoo('FN', inc, cf, annual, {'forwardPE':23.8,'enterpriseToRevenue':4.2},date(2026,11,8))
    assert r['Status'].startswith('PROVISIONAL')
    assert r['Coverage %'] == 100
    assert r['Revenue growth %'] == 20
    assert r['Operating margin %'] == 20
    assert r['FCF margin %'] == round((23-6)/120*100,2)
    assert 0 <= r['Quality / 100'] <= 100
    assert r['Valuation']['Forward P/E']==23.8


def test_bank_missing_data_is_not_scored():
    a,b,c=fixture()
    r=summarize_yahoo('NU',a,b,c,{},date(2026,11,8))
    assert r['Status']=='Insufficient bank coverage' and r['Quality / 100'] is None


def test_stale_missing_and_no_imputation():
    a,b,c=fixture()
    old=summarize_yahoo('FN',a,b,c,{},date(2027,6,1))
    assert old['Quality / 100'] is None
    missing=summarize_yahoo('FN',a.iloc[:1],b.iloc[:1],c,{},date(2026,11,8))
    assert missing['Quality / 100'] is None
    assert missing['Coverage %'] < 75


def test_scales_bounded():
    for knots in SCALES.values():
        assert 0 <= _interp(-100, knots) <= 35
        assert _interp(100, knots) == knots[-1][1]


def test_stale_warning_keeps_research_score_but_never_decision_ready():
    a,b,c=fixture()
    result=summarize_yahoo('TMDX',a,b,c,{},date(2027,2,1))
    assert result['Quality / 100'] is not None
    assert result['Freshness']=='Potentially stale'
    assert result['Status']=='PROVISIONAL — potentially stale'
    assert not result['Decision-ready']


def test_bank_has_distinct_conditional_model():
    a,b,c=fixture()
    bal=pd.DataFrame([[25,23],[200,190]],index=['Stockholders Equity','Total Assets'],
                     columns=pd.to_datetime(['2026-09-30','2026-06-30']))
    meta={'returnOnEquity':0.21,'returnOnAssets':0.03}
    result=summarize_yahoo('NU',a,b,c,meta,date(2026,11,8),balance_sheet=bal)
    assert result['Business model']=='Bank'
    assert result['Quality model']=='B0.2-experimental'
    assert result['Coverage %']==100
    assert result['Equity/assets %']==12.5
    assert result['Quality / 100'] is not None
    assert not result['Decision-ready']


def test_bank_no_roe_blocks_score():
    a,b,c=fixture()
    bal=pd.DataFrame([[25],[200]],index=['Stockholders Equity','Total Assets'],
                     columns=pd.to_datetime(['2026-09-30']))
    result=summarize_yahoo('NU',a,b,c,{'returnOnAssets':0.02},date(2026,11,8),balance_sheet=bal)
    assert result['Quality / 100'] is None
