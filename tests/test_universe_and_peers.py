import unittest
from config import (WATCHLIST, STOCK_GROUPS, SECTOR_BENCHMARKS, MARKET_SYMBOLS,
                    VALUATION_PEERS, TECHNICAL_UNIVERSE)
from core.valuation_peers import peer_comparison

class UniverseAndPeerTests(unittest.TestCase):
    def test_exact_22(self):
        self.assertEqual(len(WATCHLIST), 22)
        self.assertEqual(len(set(WATCHLIST)), 22)
        self.assertTrue({'PTC', 'PATH', 'AOSL', 'COIN', 'TEM', 'MANU'}.issubset(WATCHLIST))
        self.assertFalse({'RPI', 'FTC', 'IQE', 'UL'} & set(WATCHLIST))
        self.assertEqual(set(WATCHLIST), set(TECHNICAL_UNIVERSE))
        self.assertEqual(set(WATCHLIST), set(SECTOR_BENCHMARKS))
        self.assertEqual(set(WATCHLIST), set(VALUATION_PEERS))
        for ticker in WATCHLIST:
            self.assertEqual(MARKET_SYMBOLS[ticker], (ticker, 'USD', 1.0))
    def test_peers_only_same_subgroup(self):
        reports = [
            {'Ticker':'BSY','Valuation':{'Forward P/E':20}},
            {'Ticker':'PTC','Valuation':{'Forward P/E':30}},
            {'Ticker':'CRWD','Valuation':{'Forward P/E':10}},
        ]
        out=peer_comparison(reports)
        bsy=next(r for r in out if r['Ticker']=='BSY' and r['Metric']=='Forward P/E')
        self.assertEqual(bsy['Other observed peers'],1)
        self.assertEqual(bsy['Other-peer median'],30)
        self.assertAlmostEqual(bsy['vs other peers %'],-33.3)
        crwd=next(r for r in out if r['Ticker']=='CRWD' and r['Metric']=='Forward P/E')
        self.assertIsNone(crwd['Other-peer median'])
    def test_empty_negative_and_missing(self):
        rows=peer_comparison([{'Ticker':'BSY','Valuation':{'Forward P/E':-3}},
                              {'Ticker':'PTC','Valuation':{'Forward P/E':None}}])
        self.assertTrue(all(r['Other-peer median'] is None for r in rows))
