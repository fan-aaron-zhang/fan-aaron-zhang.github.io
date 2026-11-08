import unittest
import pandas as pd
from core.overall_score import calculate_overall, overall_explanation, OVERALL_VERSION
from core.dashboard_presentation import _style_action_table

class OverallScoreTests(unittest.TestCase):
    def test_weighting_and_bounds(self):
        self.assertEqual(calculate_overall(20, 80), 44.0)
        self.assertEqual(calculate_overall(100, 100), 100.0)
        self.assertEqual(calculate_overall(0, 0), 0.0)

    def test_missing_invalid_no_imputation(self):
        for bad in [None, float('nan'), float('inf'), -1, 101, 'bad', True]:
            self.assertIsNone(calculate_overall(bad, 50))
            self.assertIsNone(calculate_overall(50, bad))
        self.assertIn('withheld', overall_explanation(None, 70))
        self.assertIn('valuation', overall_explanation(80, 70))

    def test_all_three_score_columns_coloured(self):
        df = pd.DataFrame([{'Overall':44.0, 'Tech':20, 'Quality':80, 'Action':'Wait'}])
        html = _style_action_table(df).to_html()
        self.assertIn('#fff0cf', html)
        self.assertIn('#fce4e4', html)
        self.assertIn('#dbf2e2', html)
        self.assertIn('O0.1', OVERALL_VERSION)

if __name__ == '__main__': unittest.main()
