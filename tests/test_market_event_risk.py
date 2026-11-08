"""Offline deterministic V1.7 tests: no live Yahoo or Streamlit access."""
import unittest
from datetime import date, timedelta, datetime
import numpy as np
import pandas as pd
from config import WATCHLIST, REGIME_SYMBOLS, APP_VERSION
from core.event_risk import parse_earnings_calendar, parse_earnings_history, assess_earnings_risk
from core.market_regime import evaluate_market_regime


def samples(today=date(2026, 11, 6), trend='up', n=260):
    dates = pd.bdate_range(end=today, periods=n)
    x = np.arange(n)
    if trend == 'up':
        prices = 100 + .3*x
    elif trend == 'down':
        prices = 250 - .3*x
    else:
        prices = 120 + .01*x
    return {s: pd.DataFrame({'Close': prices}, index=dates) for s in REGIME_SYMBOLS}


class MarketEventTests(unittest.TestCase):
    def test_fixed_universe(self):
        self.assertEqual(len(WATCHLIST), 22)
        self.assertEqual(APP_VERSION, 'V1.8j-price-risk-scenarios')

    def test_supportive_trend(self):
        r = evaluate_market_regime(samples(), as_of=date(2026, 11, 8))
        self.assertEqual(r['regime'], 'Supportive')
        self.assertEqual(r['breadth_above_ma50'], 4)
        self.assertEqual(r['as_of'], '2026-11-06')

    def test_defensive_trend(self):
        r = evaluate_market_regime(samples(trend='down'), as_of=date(2026, 11, 8))
        self.assertEqual(r['regime'], 'Defensive')

    def test_stale_market_does_not_report_supportive(self):
        r = evaluate_market_regime(samples(), as_of=date(2026, 11, 20))
        self.assertEqual(r['status'], 'Stale')
        self.assertEqual(r['regime'], 'Unknown')

    def test_missing_benchmark_never_defaults_to_safe(self):
        missing = samples(); missing['SMH'] = None
        r = evaluate_market_regime(missing, as_of=date(2026, 11, 8))
        self.assertEqual(r['regime'], 'Unknown')

    def test_insufficient_aligned_history(self):
        short = samples(n=211)
        r = evaluate_market_regime(short, as_of=date(2026, 11, 8))
        self.assertEqual(r['regime'], 'Unknown')

    def test_calendar_parsing_list(self):
        self.assertEqual(parse_earnings_calendar({'Earnings Date': [date(2026,11,12),
            datetime(2026,11,13,8,0)]}), [date(2026,11,12), date(2026,11,13)])

    def test_calendar_unknown(self):
        r = assess_earnings_risk('NU', {}, today=date(2026,11,8))
        self.assertEqual(r['status'], 'Unknown')
        self.assertEqual(r['risk'], 'Unassessed')

    def test_calendar_within_7_days(self):
        r = assess_earnings_risk('NU', {'Earnings Date': date(2026, 11, 12)}, today=date(2026,11,8))
        self.assertEqual(r['status'], 'Within 7 days')
        self.assertEqual(r['days_until'], 4)

    def test_recent_calendar_date_unverified(self):
        r = assess_earnings_risk('NU', {'Earnings Date': date(2026, 11, 6)}, today=date(2026,11,8))
        self.assertEqual(r['status'], 'Recent (date unverified)')
        self.assertEqual(r['days_since'], 2)
        self.assertFalse(r['recent_confirmed_eps'])

    def test_recent_earnings_reported_eps(self):
        history = pd.DataFrame({'EPS Estimate':[0.5], 'Reported EPS':[0.62]},
                               index=pd.DatetimeIndex(['2026-11-05 16:00:00-05:00']))
        r = assess_earnings_risk('TMDX', {}, today=date(2026,11,8), earnings_history=history)
        self.assertEqual(r['status'], 'Recent (reported EPS)')
        self.assertEqual(r['last_event_date'], '2026-11-05')
        self.assertTrue(r['recent_confirmed_eps'])

    def test_eps_estimate_is_not_confirmation(self):
        history = pd.DataFrame({'EPS Estimate':[0.5], 'Reported EPS':[float('nan')]},
                               index=pd.DatetimeIndex(['2026-11-05']))
        r = assess_earnings_risk('TMDX', {}, today=date(2026,11,8), earnings_history=history)
        self.assertEqual(r['status'], 'Recent (date unverified)')
        self.assertFalse(r['recent_confirmed_eps'])

    def test_recent_window_expires(self):
        r = assess_earnings_risk('DDOG', {'Earnings Date': '2026-10-20'}, today=date(2026,11,8))
        self.assertEqual(r['status'], 'Unknown')

    def test_recent_and_future_shows_both_dates(self):
        history = pd.DataFrame({'Reported EPS':[1.0]}, index=pd.DatetimeIndex(['2026-11-05']))
        r = assess_earnings_risk('DDOG', {'Earnings Date':'2027-02-01'},
                                 today=date(2026,11,8), earnings_history=history)
        self.assertTrue(r['status'].startswith('Recent'))
        self.assertEqual(r['earnings_date'], '2027-02-01')

    def test_empty_history_stays_unknown(self):
        r = assess_earnings_risk('DDOG', None, today=date(2026,11,8), earnings_history=pd.DataFrame())
        self.assertEqual(r['status'], 'Unknown')

    def test_calendar_future(self):
        r = assess_earnings_risk('NU', {'Earnings Date': '2026-12-01'}, today=date(2026,11,8))
        self.assertEqual(r['status'], 'Later')


if __name__ == '__main__':
    unittest.main()
