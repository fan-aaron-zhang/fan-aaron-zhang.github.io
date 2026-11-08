"""Offline display-contract regression tests."""
import unittest
import pandas as pd
from core.dashboard_presentation import score_band_color, _style_action_table
from pathlib import Path

class DashboardClarityTests(unittest.TestCase):
    def test_band_colours_and_missing(self):
        self.assertIn("#fce4e4", score_band_color(39))
        self.assertIn("#fff0cf", score_band_color(40))
        self.assertIn("#dbf2e2", score_band_color(70))
        self.assertIn("#eeeeee", score_band_color(None))
        self.assertIn("#eeeeee", score_band_color(float("nan")))

    def test_no_held_column_and_valuation_is_data_only(self):
        source=(Path(__file__).resolve().parents[1]/"views"/"landing.py").read_text()
        self.assertNotIn("'Held':",source)
        self.assertIn("'Data only'",source)
        self.assertIn("ⓘ How to read Overall, Valuation, Risk, Plan & Review",source)

    def test_only_score_columns_are_coloured(self):
        row={"Overall":None,"Tech":20,"Quality":None,"Action":"Wait"}
        styler=_style_action_table(pd.DataFrame([row]))
        self.assertEqual(set(styler.ctx.keys()),set())  # styles materialise on render
        html=styler.to_html()
        self.assertIn("#fce4e4",html)
        self.assertIn("#eeeeee",html)

if __name__=="__main__": unittest.main()
