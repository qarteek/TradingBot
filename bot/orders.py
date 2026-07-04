"""
Order placement logic: sits between the CLI layer and the low-level
REST client. Responsible for:
    - building an order request summary
    - calling the client
    - logging the outcome
    - formatting a human-readable response summary
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from .logging_config import get_logger
from .validators import validate_order_params

logger = get_logger(__name__)


@dataclass
class OrderResult:
    success: bool
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def build_request_summary(params: Dict[str, Any]) -> str:
    lines = [
        "Order Request Summary",
        "----------------------",
        f"  Symbol      : {params['symbol']}",
        f"  Side        : {params['side']}",
        f"  Type        : {params['order_type']}",
        f"  Quantity    : {params['quantity']}",
    ]
    if params.get("price") is not None:
        lines.append(f"  Price       : {params['price']}")
    if params.get("stop_price") is not None:
        lines.append(f"  Stop Price  : {params['stop_price']}")
    return "\n".join(lines)


def build_response_summary(response: Dict[str, Any]) -> str:
    lines = [
        "Order Response",
        "--------------",
        f"  Order ID       : {response.get('orderId')}",
        f"  Status         : {response.get('status')}",
        f"  Executed Qty   : {response.get('executedQty')}",
    ]
    avg_price = response.get("avgPrice")
    if avg_price is not None:
        lines.append(f"  Avg Price      : {avg_price}")
    return "\n".join(lines)


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderResult:
    """
    Validate inputs, place the order via the client, and return an
    OrderResult capturing success/failure plus request/response detail.

    Raises `ValidationError` before ever touching the network if inputs
    are invalid, so bad requests never reach the API or the logs as
    "attempted" calls.
    """
    params = validate_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    logger.info(
        "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        params["symbol"], params["side"], params["order_type"],
        params["quantity"], params["price"], params["stop_price"],
    )

    try:
        response = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
    except BinanceAPIError as exc:
        logger.error("Order rejected by Binance: %s", exc)
        return OrderResult(success=False, request=params, error=str(exc))
    except BinanceNetworkError as exc:
        logger.error("Network failure while placing order: %s", exc)
        return OrderResult(success=False, request=params, error=str(exc))

    logger.info(
        "Order accepted: orderId=%s status=%s executedQty=%s",
        response.get("orderId"), response.get("status"), response.get("executedQty"),
    )
    return OrderResult(success=True, request=params, response=response)
