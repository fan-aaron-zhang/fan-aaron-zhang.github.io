"""Offline tests for calculation consistency; no Streamlit, brokerage or live internet."""
import unittest
from datetime import date, timedelta
import numpy as np
import pandas as pd
from config import (MARKET_BENCHMARK, MODEL_VERSION, TECHNICAL_WEIGHTS,
                    SECTOR_BENCHMARKS)
from core.portfolio import analyse_sheet, classify_account, numeric, parse_date
from core.scoring import compute_technical


class CoreTests(unittest.TestCase):
    def test_fixed_configuration(self):
        self.assertEqual(MODEL_VERSION, 'T1.0')
        self.assertEqual(sum(TECHNICAL_WEIGHTS.values()), 100)
        self.assertEqual(MARKET_BENCHMARK, 'SPY')
        self.assertEqual(SECTOR_BENCHMARKS['FN'], 'SMH')

    def test_portfolio_weighted_average(self):
        # Frame columns A–G, with row 2 as summary and physical rows 3–5 as trades.
        frame = pd.DataFrame([
            [None] * 7,
            [None, 'Swing', 6, None, None, None, None],
            [date(2026, 1, 1), 'OPEN', 10, 10, None, 12, 100],
            [date(2026, 1, 2), 'BUY', 10, None, None, 14, 140],
            [date(2026, 1, 3), 'SELL', 14, None, None, 18, 210],
        ])
        summary, audit, issues = analyse_sheet('TEST', frame, date(2026, 11, 7))
        self.assertEqual(summary['Status'], 'MATCH')
        self.assertAlmostEqual(summary['Remaining cost GBP'], 72)
        self.assertAlmostEqual(summary['Avg cost GBP/share'], 12)
        self.assertAlmostEqual(summary['Realised P/L GBP'], 42)
        self.assertEqual(len(audit), 3)
        self.assertEqual(issues, [])

    def test_account_scope(self):
        self.assertEqual(classify_account('VWRP (HL-Junior ISA)', 'ETF'), 'Junior ISA')
        self.assertEqual(classify_account('VWRP (T212 ISA)', 'ETF'), 'Core ETF')
        self.assertEqual(classify_account('FN', 'Swing'), 'Swing')

    def test_numeric_unicode(self):
        self.assertEqual(numeric('72\u2060780'), 72780.0)
        self.assertEqual(parse_date('2026-11-07'), date(2026, 11, 7))

    def test_technical_score_deterministic(self):
        # Latest available bar in our artificial data is today. No internet required.
        days = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=160)
        k = np.arange(160)
        def data(mult, bump):
            close = pd.Series((100 + .2*k + np.sin(k/8)*3 + bump)*mult, index=days)
            return pd.DataFrame({'Close': close, 'High': close*1.02,
                                 'Low': close*.98, 'Volume': [1000000]*160}, index=days)
        result = compute_technical('FN', data(1,0), data(.9,1), data(1.12,2), 'SMH')
        self.assertEqual(result['Technical / 100'], 72)
        self.assertEqual(result['Status'], 'RESEARCH ONLY')
        self.assertEqual(sum(result[c] for c in [
            'Trend / 30', 'Momentum / 25', 'RS Market / 8',
            'RS Sector / 12', 'RSI / 15', 'Volume / 10']), 72)


if __name__ == '__main__':
    unittest.main()
