"""Lightweight, deterministic checks; no Yahoo calls."""
import unittest
from config import WATCHLIST
from core.watchlist_scan import screen_from_technicals, triage
from core.portfolio_allocator import allocate_buy_candidates


def technical(score, close=90, ma20=100, ma50=105, ret20=-13, status="RESEARCH ONLY"):
    return {"Technical / 100":score,"Status":status,"Close USD":close,
            "MA20":ma20,"MA50":ma50,"Return 20D %":ret20,"Quote date":"2026-11-06"}

class WatchlistTests(unittest.TestCase):
    def test_watchlist_complete(self):
        rows=screen_from_technicals({"FN":technical(75,110,100,105,12)}, holdings={"AMBA"})
        self.assertEqual(len(rows),22)
        self.assertEqual(set(x["Ticker"] for x in rows),set(WATCHLIST))
        self.assertEqual(rows[0]["Ticker"],"FN")
        self.assertEqual(rows[0]["Screen"],"Research candidate")
    def test_no_false_buy_on_weak_held_stock(self):
        label,reason,_=triage(technical(20), held=True)
        self.assertEqual(label,"Risk review")
        self.assertIn("Held position",reason)
        label,_,_=triage(technical(20), held=False)
        self.assertEqual(label,"Wait")
    def test_missing_is_not_clear(self):
        self.assertEqual(triage(technical(None,status="UNAVAILABLE"))[0],"Data unavailable")
        self.assertEqual(triage(technical(80,status="STALE"))[0],"Data unavailable")
    def test_three_buy_candidates_share_budget(self):
        # Mock buy proposals solely for testing; never displayed as live opportunities.
        orders=[{"Ticker":name,"Action":"Buy on pullback","Buy shares":30,
                 "Buy limit USD":100,"Buy amount GBP":3000,"Technical":90-i*5,
                 "Quality":70,"Status":"Conditional research"}
                for i,name in enumerate(("DDOG","AMBA","NU"))]
        rows, summary=allocate_buy_candidates(orders,4500,1)
        self.assertEqual([r["Buy shares"] for r in rows],[30,15,0])
        self.assertLessEqual(summary["Proposed committed GBP"],4500)
        self.assertEqual(summary["Unallocated GBP"],0)
    def test_all_wait_spends_zero(self):
        rows,summary=allocate_buy_candidates([{"Ticker":"FN","Action":"Hold / wait","Buy shares":0}],9000,1.3)
        self.assertEqual(summary["Proposed committed GBP"],0)
        self.assertEqual(rows[0]["Buy shares"],0)

if __name__ == "__main__": unittest.main()
