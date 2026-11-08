"""The research table should show conclusions before component details."""
import unittest
import pandas as pd
from views.columns import order_technical_columns


class DisplayOrderTests(unittest.TestCase):
    def test_conclusions_first(self):
        input_frame = pd.DataFrame([{
            "MA50": 100.0, "Ticker": "FN", "Trend / 30": 20,
            "Technical / 100": 72, "RSI14": 63.0,
            "Trend state": "Strong", "Status": "RESEARCH ONLY",
            "Quote date": "2026-11-06", "Close USD": 327.13,
        }])
        original = input_frame.copy(deep=True)
        displayed = order_technical_columns(input_frame)
        self.assertEqual(displayed.columns[:6].tolist(), [
            "Ticker", "Technical / 100", "Trend state", "Status",
            "Close USD", "Quote date"])
        pd.testing.assert_frame_equal(input_frame, original)
        self.assertEqual(displayed.iloc[0]["Technical / 100"], 72)


if __name__ == "__main__":
    unittest.main()
