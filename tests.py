import unittest
from unittest.mock import patch, MagicMock
import datetime
# Import functions and data from your app
# Note: Ensure your app.py doesn't run the UI immediately upon import. 
# Ideally, wrap the UI code in `if __name__ == "__main__":` in app.py, 
# but for now, we will test the logic functions directly if they are accessible.
from app import (
    calculate_all, 
    predict_wedding_month, 
    check_mars_dosha_smart, 
    NAKSHATRAS, 
    RASHIS, 
    SUN_TRANSIT_DATES,
    get_working_model
)

class TestVedicMatcher(unittest.TestCase):

    # --- TEST 1: PREVENT REGRESSION ON WEDDING DATES ---
    def test_wedding_dates_data_exists(self):
        """Ensure SUN_TRANSIT_DATES dictionary was not accidentally deleted."""
        self.assertTrue(len(SUN_TRANSIT_DATES) == 12, "Regression: SUN_TRANSIT_DATES is missing or incomplete.")
        self.assertEqual(predict_wedding_month(0), "Oct 17 - Nov 15", "Logic Error: Aries wedding month calculation incorrect.")

    # --- TEST 2: PREVENT REGRESSION ON SANSKRIT NAMES ---
    def test_rashi_names(self):
        """Ensure Sanskrit names are present in the RASHIS list."""
        self.assertIn("Mesha", RASHIS[0], "Regression: Sanskrit name 'Mesha' missing from Aries.")
        self.assertIn("Kanya", RASHIS[5], "Regression: Sanskrit name 'Kanya' missing from Virgo.")

    # --- TEST 3: CRITICAL CALCULATION LOGIC (NADI) ---
    def test_nadi_healthy_initialization(self):
        """
        Regression Fix Test: Ensure n_reason is defined even when Nadi is healthy.
        Scenario: Ashwini (0) vs Krittika (2) -> Different Nadi (0 vs 2) -> Healthy.
        """
        try:
            score, bd, logs, _, _ = calculate_all(0, 0, 2, 0)
            nadi_score = bd[7][2] # Index 7 is Nadi
            nadi_reason = bd[7][4]
            self.assertEqual(nadi_score, 8, "Nadi score should be 8 for different Nadis.")
            self.assertEqual(nadi_reason, "Healthy", "Regression: 'Healthy' reason not correctly assigned.")
        except UnboundLocalError:
            self.fail("CRITICAL REGRESSION: n_reason variable was not initialized in calculate_all().")

    # --- TEST 4: DOSHA CANCELLATION LOGIC ---
    def test_same_nakshatra_exception(self):
        """Test specific exception for Rohini (Index 3). Same star usually bad, but Rohini is allowed."""
        # Rohini is index 3.
        score, bd, logs, _, _ = calculate_all(3, 1, 3, 1)
        nadi_score = bd[7][2]
        self.assertEqual(nadi_score, 8, "Rohini-Rohini match should get 8 points (Exception).")
        self.assertTrue(any(l['Attribute'] == 'Nadi' for l in logs), "Logs should reflect the Nadi exception.")

    # --- TEST 5: MARS DOSHA LOGIC ---
    def test_mars_dosha_check(self):
        """Verify Mars logic returns Tuple (Bool, String) and handles 7th house."""
        # Case: Mars in 7th from Moon
        is_dosha, msg = check_mars_dosha_smart(0, 180) # Moon at 0, Mars at 180 (7th house)
        self.assertTrue(is_dosha)
        self.assertIn("Active Energy", msg, "Message should be user-friendly (Active Energy), not panic-inducing.")

        # Case: Mars in Own Sign (Aries/Scorpio) cancellation
        # Moon in Cancer (90deg), Mars in Aries (0deg) -> 10th house (Safe)
        # Let's test specific cancellation: Moon in Libra (180), Mars in Aries (0) -> 7th house but Mars is Own Sign
        is_dosha, msg = check_mars_dosha_smart(6, 0) 
        self.assertFalse(is_dosha, "Mars in Aries (Own Sign) should cancel 7th house Dosha.")
        self.assertIn("Balanced", msg)

    # --- TEST 6: AI MODEL AUTO-DETECT (MOCKING) ---
    @patch('google.generativeai.list_models')
    def test_ai_model_discovery(self, mock_list_models):
        """
        Simulate Google API response to ensure we pick the first available text model.
        We mock the API so this test runs without a real key/internet.
        """
        # Mock response object structure
        mock_model_1 = MagicMock(); mock_model_1.name = "models/gemini-1.5-flash"; mock_model_1.supported_generation_methods = ['generateContent']
        mock_model_2 = MagicMock(); mock_model_2.name = "models/gemini-pro"; mock_model_2.supported_generation_methods = ['generateContent']
        
        mock_list_models.return_value = [mock_model_1, mock_model_2]
        
        # Run function with dummy key
        selected_model = get_working_model("dummy_key")
        
        # It should pick the first one in the list that matches our criteria
        self.assertEqual(selected_model, "models/gemini-1.5-flash", "Model Hunter failed to pick the first valid model.")

if __name__ == '__main__':
    unittest.main()
