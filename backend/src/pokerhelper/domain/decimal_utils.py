"""Exact-decimal construction and canonical formatting."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN, getcontext
import re
from typing import Final

from .errors import fail


getcontext().prec = max(getcontext().prec, 50)

ZERO: Final = Decimal("0")
ONE: Final = Decimal("1")
CENTI_BB: Final = Decimal("0.01")

_PLAIN_DECIMAL = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


def as_decimal(value: Decimal | int | str, *, path: str = "value") -> Decimal:
    """Return a finite exact Decimal and reject binary floats and booleans."""

    if isinstance(value, bool) or isinstance(value, float):
        fail(
            "SCHEMA_DECIMAL_FLOAT_FORBIDDEN",
            path,
            "Canonical decimal values must be supplied as strings, integers, or Decimal values.",
            details={"receivedType": type(value).__name__},
        )
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        candidate = value.strip()
        if not _PLAIN_DECIMAL.fullmatch(candidate):
            fail(
                "SCHEMA_DECIMAL_INVALID",
                path,
                "Expected a plain finite decimal without exponent notation.",
                details={"received": value},
            )
        try:
            result = Decimal(candidate)
        except InvalidOperation:
            fail(
                "SCHEMA_DECIMAL_INVALID",
                path,
                "Expected a valid finite decimal.",
                details={"received": value},
            )
    else:
        fail(
            "SCHEMA_DECIMAL_INVALID_TYPE",
            path,
            "Expected a decimal string, integer, or Decimal value.",
            details={"receivedType": type(value).__name__},
        )

    if not result.is_finite():
        fail(
            "SCHEMA_DECIMAL_NON_FINITE",
            path,
            "NaN and infinite decimal values are not supported.",
        )
    return ZERO if result == ZERO else result


def normalized_decimal(value: Decimal | int | str, *, path: str = "value") -> str:
    """Format semantically equivalent decimals as identical plain strings."""

    number = as_decimal(value, path=path)
    if number == ZERO:
        return "0"
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text.startswith("."):
        text = f"0{text}"
    elif text.startswith("-."):
        text = f"-0{text[1:]}"
    return text


def floor_to_increment(
    value: Decimal | int | str,
    increment: Decimal | int | str,
    *,
    path: str = "value",
) -> Decimal:
    number = as_decimal(value, path=path)
    step = as_decimal(increment, path="increment")
    if step <= ZERO:
        fail("SCHEMA_INCREMENT_NOT_POSITIVE", "increment", "Increment must be positive.")
    units = (number / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step

