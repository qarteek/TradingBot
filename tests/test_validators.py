"""
Small unit test suite for the validation layer and order summary
formatting. Run with:

    python -m pytest tests/ -v

or, without pytest installed:

    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validators import (  # noqa: E402
    ValidationError,
    validate_order_params,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)
from bot.orders import build_request_summary, build_response_summary  # noqa: E402


class TestValidators(unittest.TestCase):
    def test_valid_symbol(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")

    def test_invalid_symbol_empty(self):
        with self.assertRaises(ValidationError):
            validate_symbol("")

    def test_invalid_symbol_bad_chars(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTC-USDT!")

    def test_valid_side(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")

    def test_invalid_side(self):
        with self.assertRaises(ValidationError):
            validate_side("HOLD")

    def test_valid_quantity(self):
        self.assertEqual(validate_quantity("0.01"), 0.01)

    def test_invalid_quantity_negative(self):
        with self.assertRaises(ValidationError):
            validate_quantity(-5)

    def test_invalid_quantity_non_numeric(self):
        with self.assertRaises(ValidationError):
            validate_quantity("abc")

    def test_price_required_for_limit(self):
        with self.assertRaises(ValidationError):
            validate_price(None, required=True)

    def test_price_optional_for_market(self):
        self.assertIsNone(validate_price(None, required=False))

    def test_full_market_order_params(self):
        params = validate_order_params("btcusdt", "buy", "market", "0.01")
        self.assertEqual(params["symbol"], "BTCUSDT")
        self.assertEqual(params["order_type"], "MARKET")
        self.assertIsNone(params["price"])

    def test_full_limit_order_params(self):
        params = validate_order_params("btcusdt", "sell", "limit", "0.01", price="65000")
        self.assertEqual(params["price"], 65000.0)

    def test_limit_order_missing_price_raises(self):
        with self.assertRaises(ValidationError):
            validate_order_params("btcusdt", "sell", "limit", "0.01")

    def test_stop_order_requires_both_prices(self):
        with self.assertRaises(ValidationError):
            validate_order_params("btcusdt", "sell", "stop", "0.01", price="3200")


class TestSummaries(unittest.TestCase):
    def test_request_summary_contains_key_fields(self):
        params = validate_order_params("btcusdt", "buy", "market", "0.01")
        summary = build_request_summary(params)
        self.assertIn("BTCUSDT", summary)
        self.assertIn("BUY", summary)
        self.assertIn("MARKET", summary)

    def test_response_summary_contains_order_id(self):
        response = {"orderId": 123, "status": "FILLED", "executedQty": "0.01", "avgPrice": "60000"}
        summary = build_response_summary(response)
        self.assertIn("123", summary)
        self.assertIn("FILLED", summary)


if __name__ == "__main__":
    unittest.main()
