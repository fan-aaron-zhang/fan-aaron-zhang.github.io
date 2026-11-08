from datetime import date
import pandas as pd
from core.fundamentals import summarize_yahoo
from core.research_snapshot import make_research_snapshot

NOW=date(2026,11,8)
Q=pd.to_datetime(['2026-09-30','2026-06-30','2026-03-31','2025-12-31','2025-09-30'])


def test_newest_placeholder_falls_back_to_complete_quarter():
    inc=pd.DataFrame([[float('nan'),110,100,90,80],
                      [float('nan'),20,18,15,12],
                      [float('nan'),11,10,9,8]],
                     index=['Total Revenue','Operating Income','Net Income'],columns=Q)
    cf=pd.DataFrame([[21,20,19,18],[-4,-4,-3,-3]],
                    index=['Operating Cash Flow','Capital Expenditure'], columns=Q[1:])
    yr=pd.DataFrame([[400,300]],index=['Total Revenue'],columns=pd.to_datetime(['2025-12-31','2024-12-31']))
    r=summarize_yahoo('BSY',inc,cf,yr,{},NOW)
    assert r['Latest quarter']=='2026-06-30'
    assert r['Latest Yahoo income column']=='2026-09-30'
    assert r['Quarter fallback'] is True
    assert r['Coverage %']==100
    assert r['Operating margin %']==round(20/110*100,2)
    assert r['FCF margin %']==round((21-4)/110*100,2)
    assert r['Quality / 100'] is not None
    audit={row['Field']:row for row in r['Source audit']}
    assert audit['Operating income']['Aligned quarter']=='2026-06-30'


def test_missing_cashflow_does_not_cross_mix():
    inc=pd.DataFrame([[130,120,110,100,90],[26,24,22,20,18],[13,12,11,10,9]],
                     index=['Total Revenue','Operating Income','Net Income'],columns=Q)
    cf=pd.DataFrame([[22,21],[-5,-4]],index=['Operating Cash Flow','Capital Expenditure'],columns=Q[1:3])
    r=summarize_yahoo('PTC',inc,cf,pd.DataFrame(),{},NOW)
    assert r['Latest quarter']=='2026-09-30'
    assert r['Quarter fallback'] is False
    assert r['FCF margin %'] is None
    assert r['Coverage %']==80


def test_no_eligible_quarter_cannot_invent_missing_fields():
    inc=pd.DataFrame([[float('nan'),120],[float('nan'),float('nan')],[float('nan'),float('nan')]],
                     index=['Total Revenue','Operating Income','Net Income'],columns=Q[:2])
    r=summarize_yahoo('IRDM',inc,pd.DataFrame(),pd.DataFrame(),{},NOW)
    assert r['Quality / 100'] is None
    assert r['Coverage %']==0


def test_handoff_schema_does_not_fabricate_actions():
    r=make_research_snapshot(' bsy ', financial_research={'score':70})
    assert r['ticker']=='BSY'
    assert r['trading_plan']=={}
    assert 'financial' in r['facts']
