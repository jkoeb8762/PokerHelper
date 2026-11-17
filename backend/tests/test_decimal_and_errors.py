from __future__ import annotations

from decimal import Decimal
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import DomainError, as_decimal, normalized_decimal


class DecimalAndErrorTests(unittest.TestCase):
    def test_ERR_001_decimal_normalization(self) -> None:
        self.assertEqual("2.5", normalized_decimal("02.500"))
        self.assertEqual("0", normalized_decimal("-0.000"))
        self.assertEqual(Decimal("2.5"), as_decimal("2.5"))

    def test_ERR_002_float_and_non_finite_values_fail(self) -> None:
        values = [2.5, "NaN", "Infinity", "1e-3"]
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(DomainError):
                    as_decimal(value)  # type: ignore[arg-type]

    def test_ERR_003_structured_error_shape(self) -> None:
        try:
            as_decimal(0.5, path="smallBlindBb")
        except DomainError as error:
            payload = error.to_dict()
        else:
            self.fail("Expected DomainError")
        self.assertEqual("SCHEMA_DECIMAL_FLOAT_FORBIDDEN", payload["code"])
        self.assertEqual("smallBlindBb", payload["path"])
        self.assertIn("message", payload)
        self.assertEqual("float", payload["details"]["receivedType"])


if __name__ == "__main__":
    unittest.main()

