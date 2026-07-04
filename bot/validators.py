"""
Validation helpers for CLI input.

Kept deliberately independent of argparse/click/typer so the same
validation logic can be reused by any front-end (CLI, tests, future UI).
"""

from __future__ import annotations

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}
# Simple, permissive symbol check: 6-20 uppercase letters/digits, e.g. BTCUSDT
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    """Raised when CLI-provided order parameters are invalid."""


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol must not be empty.")
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a format like 'BTCUSDT' "
            "(5-20 uppercase letters/digits)."
        )
    return symbol


def validate_side(side: str) -> str:
    side = (side or "").strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = (order_type or "").strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity: float) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.") from exc
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive, got {quantity}.")
    return quantity


def validate_price(price, *, required: bool, field_name: str = "price"):
    if price is None:
        if required:
            raise ValidationError(f"{field_name} is required for this order type.")
        return None
    try:
        price = float(price)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a number, got '{price}'.") from exc
    if price <= 0:
        raise ValidationError(f"{field_name} must be positive, got {price}.")
    return price


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    stop_price: float | None = None,
) -> dict:
    """
    Run all validations for a full order request and return a clean,
    normalized dict of parameters. Raises ValidationError on the first
    problem found.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)

    clean_price = validate_price(price, required=(clean_type in ("LIMIT", "STOP")))
    clean_stop_price = None
    if clean_type == "STOP":
        clean_stop_price = validate_price(stop_price, required=True, field_name="stop_price")

    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
        "price": clean_price,
        "stop_price": clean_stop_price,
    }
