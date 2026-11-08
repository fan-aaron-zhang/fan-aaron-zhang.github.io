"""Navigation contract smoke tests; avoid dependency on a live Streamlit server."""
import unittest
from pathlib import Path
from config import APP_VERSION, MODEL_VERSION

class NavigationContract(unittest.TestCase):
    def test_app_version_and_model(self):
        self.assertEqual(APP_VERSION, "V1.8j-price-risk-scenarios")
        self.assertEqual(MODEL_VERSION, "T1.0")

    def test_navigation_and_read_only_upload(self):
        src = (Path(__file__).resolve().parents[1] / "views" / "dashboard.py").read_text()
        for heading in ["Quant Analysis", "Trade Decisions", "Portfolio & Risk",
                        "Model Evaluation", "Data & Settings"]:
            self.assertIn(heading, src)
        self.assertIn('st.sidebar', src)
        self.assertIn('read only', src)
        self.assertIn('render_technical_research([])', src)

if __name__ == '__main__':
    unittest.main()
