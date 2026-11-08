from datetime import date
import pandas as pd
from core.fundamentals import summarize_yahoo

def make_data():
    cols=pd.to_datetime(['2026-09-30','2026-06-30','2026-03-31','2025-12-31','2025-09-30'])
    inc=pd.DataFrame([[120,110,100,90,80],[10,9,8,7,6],[8,7,6,5,4]],index=['Total Revenue','Operating Income As Reported','Net Income'],columns=cols)
    cf=pd.DataFrame([[15,14,13,12,11],[-4,-3,-3,-3,-2]],index=['Cash Flow From Continuing Operating Activities Net','Purchase Of PPE'],columns=cols)
    return inc,cf,pd.DataFrame()

def test_alternative_yahoo_labels_are_auditable():
    inc,cf,annual=make_data()
    r=summarize_yahoo('BSY',inc,cf,annual,{},date(2026,11,8))
    assert r['Coverage %']==100
    assert r['Quality / 100'] is not None
    rows={x['Field']:x for x in r['Source audit']}
    assert rows['Operating income']['Yahoo row']=='Operating Income As Reported'
    assert rows['Capital expenditure']['Usable']

def test_sofi_requires_separate_financial_model():
    inc,cf,annual=make_data()
    r=summarize_yahoo('SOFI',inc,cf,annual,{},date(2026,11,8))
    assert r['Status']=='Insufficient bank coverage'
    assert r['Business model']=='Bank/lending hybrid'
    assert r['Quality model']=='B0.2-experimental'
    assert r['Quality / 100'] is None

def test_missing_fields_preserve_blank_score_and_source_audit():
    inc,cf,annual=make_data()
    r=summarize_yahoo('IRDM',inc.iloc[:1],cf.iloc[:0],annual,{},date(2026,11,8))
    assert r['Status']=='Insufficient field coverage'
    assert r['Quality / 100'] is None
    assert any(x['Yahoo row']=='Not mapped' for x in r['Source audit'])
