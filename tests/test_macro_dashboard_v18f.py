"""No live Yahoo access in these contract tests."""
from datetime import date, timedelta
import unittest
import pandas as pd
from core.macro_score import evaluate_macro_score
from core.dashboard_summary import prepare_display, is_current
from config import WATCHLIST


def prices(end, n=260, start=100.0, slope=0.2):
    idx=pd.bdate_range(end=end,periods=n)
    return pd.DataFrame({'Close':[start+slope*i for i in range(n)]}, index=idx)


class MacroAndDashboardTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,11,8)  # Sunday; last close Friday
        self.history={t:prices('2026-11-06',start=100) for t in ('SPY','QQQ','IWM','SMH')}
        self.history.update({'^VIX':prices('2026-11-06',start=15,slope=0.01),
                             '^TNX':prices('2026-11-06',start=40,slope=0.002),
                             'HYG':prices('2026-11-06',start=70,slope=0.1),
                             'LQD':prices('2026-11-06',start=105,slope=0.1)})

    def test_full_macro_score(self):
        r=evaluate_macro_score(self.history,as_of=self.today)
        self.assertIsInstance(r['score'],int)
        self.assertGreaterEqual(r['score'],0)
        self.assertLessEqual(r['score'],100)
        self.assertEqual(sum(r['components'].values()),r['score'])
        self.assertEqual(len(r['components']),4)

    def test_missing_vix_blocks(self):
        self.history['^VIX']=None
        r=evaluate_macro_score(self.history,as_of=self.today)
        self.assertIsNone(r['score'])
        self.assertEqual(r['status'],'Unknown')

    def test_old_macro_prices_block(self):
        self.history['^TNX']=prices('2026-10-15',start=40)
        r=evaluate_macro_score(self.history,as_of=self.today)
        self.assertIsNone(r['score'])

    def test_dashboard_all_22_once(self):
        rows=[{'Ticker':t,'Action':'Wait — setup'} for t in WATCHLIST]
        rows[0]['Action']='Buy on pullback'
        primary,wait=prepare_display(rows,{'NU'})
        self.assertEqual(len(primary)+len(wait),22)
        self.assertIn('NU',[r['Ticker'] for r in primary])
        self.assertIn(WATCHLIST[0],[r['Ticker'] for r in primary])
        self.assertEqual(len(wait),20)

    def test_dashboard_rejects_partial(self):
        with self.assertRaises(ValueError):
            prepare_display([{'Ticker':WATCHLIST[0],'Action':'Wait'}],set())

    def test_dashboard_fingerprint_validation(self):
        r={'tickers':WATCHLIST,'generated':str(date.today()),'workbook_fingerprint':'abc',
           'cash':5000,'fx_rate':1.3,'fx_date':'2026-11-06','total':100000}
        args=dict(fingerprint='abc',cash=5000,fx_rate=1.3,fx_date='2026-11-06',total=100000)
        self.assertTrue(is_current(r,**args))
        self.assertFalse(is_current(r,**dict(args,fingerprint='changed')))
        self.assertFalse(is_current(dict(r,tickers=WATCHLIST[:5]),**args))

if __name__=='__main__':unittest.main()
