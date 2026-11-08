"""Offline, repeatable data-source diagnostic tests (no external requests)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.fundamental_sources import sec_headers, cik_index, sec_coverage, check_sec, check_yahoo


def test_sec_header():
    assert 'SwingQuantResearch' in sec_headers('user@example.org')['User-Agent']
    try:
        sec_headers('invalid')
        assert False
    except ValueError:
        pass


def test_cik_lookup():
    assert cik_index({'0': {'cik_str': 1212, 'ticker': 'FN', 'title': 'Example'}})['FN'] == 1212


def test_sec_coverage():
    data = {'facts': {'us-gaap': {'NetIncomeLoss': {'units': {'USD': [
        {'filed': '2026-07-01', 'end': '2026-06-30', 'form': '10-Q', 'val': 10}]}}}}}
    out = sec_coverage(data)
    assert next(x for x in out if x['Metric'] == 'Net income')['Availability'] == 'Present'
    assert next(x for x in out if x['Metric'] == 'Revenue')['Availability'] == 'Not found'


def test_sec_missing_ticker():
    assert check_sec('FN', {}, {})['Status'] == 'Ticker not found'


def test_yahoo_empty():
    class Empty:
        columns = []
        index = []
    class StubTicker:
        quarterly_income_stmt = Empty()
        quarterly_cashflow = Empty()
        quarterly_balance_sheet = Empty()
    result = check_yahoo('FN', ticker_factory=lambda _: StubTicker())
    assert result['Status'] == 'Unavailable'
    assert result['Statements present'] == 0


def test_yahoo_present():
    class FakeFrame:
        columns = ['2026-06-30']
        index = ['Revenue']
    class StubTicker:
        quarterly_income_stmt = FakeFrame()
        quarterly_cashflow = FakeFrame()
        quarterly_balance_sheet = FakeFrame()
    result = check_yahoo('FN', ticker_factory=lambda _: StubTicker())
    assert result['Status'] == 'Available'
    assert result['Statements present'] == 3
