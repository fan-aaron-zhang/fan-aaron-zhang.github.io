"""No network; shared-budget regression tests."""
import unittest
from core.portfolio_allocator import allocate_buy_candidates


def buy(ticker, technical, qty=20, price=100):
    return {"Ticker": ticker, "Action": "Buy on pullback", "Buy shares": qty,
            "Buy limit USD": price, "Buy amount GBP": qty * price,
            "Technical": technical, "Quality": 70, "Status": "Conditional research"}


class AllocatorTests(unittest.TestCase):
    def test_cash_never_double_spent(self):
        rows, info = allocate_buy_candidates([buy("A",80), buy("B",70)], 2500, 1)
        self.assertEqual([r["Buy shares"] for r in rows], [20,5])
        self.assertLessEqual(info["Proposed committed GBP"], 2500)
        self.assertEqual(info["Unallocated GBP"], 0)

    def test_priority_independent_of_selection_order(self):
        rows, _ = allocate_buy_candidates([buy("B",40), buy("A",90)], 1000, 1)
        self.assertEqual([r["Buy shares"] for r in rows], [0,10])

    def test_wait_not_changed(self):
        row = buy("A",90)
        row["Action"] = "Hold / wait"
        rows, _ = allocate_buy_candidates([row], 3000, 1)
        self.assertEqual(rows[0]["Buy shares"],0)
        self.assertEqual(rows[0]["Action"],"Hold / wait")

    def test_invalid_fx_blocks(self):
        rows, info = allocate_buy_candidates([buy("A",80)], 4000, None)
        self.assertFalse(info["Valid"])
        self.assertEqual(rows[0]["Buy shares"], 0)

    def test_reserve_and_no_hypothetical_sale_recycling(self):
        buy_row = buy("A",90,20,100)
        sell_row = {"Ticker":"B", "Action":"Trim on rebound", "Sell shares":50,"Sell amount GBP":10000}
        rows, info = allocate_buy_candidates([sell_row,buy_row], 500, 1, reserve_gbp=100)
        self.assertEqual(rows[1]["Buy shares"], 4)
        self.assertEqual(info["Proposed committed GBP"], 400)

    def test_rounding_never_overruns_cash(self):
        rows, info = allocate_buy_candidates([buy("A",95,30,120.01)], 121, 1)
        self.assertEqual(rows[0]["Buy shares"],1)
        self.assertLessEqual(info["Proposed committed GBP"],121)

if __name__ == '__main__':
    unittest.main()
