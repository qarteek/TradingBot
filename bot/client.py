"""
Low-level client for the Binance Futures Testnet (USDT-M) REST API.

Implemented with plain `requests` calls (no python-binance dependency)
so that every request/response is fully visible and loggable. Handles:
    - HMAC-SHA256 request signing
    - Timestamp / recvWindow handling
    - Structured error handling for network & API errors
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when Binance returns a well-formed error response (e.g. {"code": -1121, "msg": ...})."""

    def __init__(self, code: Any, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised for connection issues, timeouts, or DNS failures reaching the testnet host."""


class BinanceFuturesClient:
    """
    Thin, signed REST wrapper around the Binance Futures Testnet API.

    Only the endpoints needed by this project are implemented:
        - GET  /fapi/v1/ping           (connectivity check)
        - GET  /fapi/v2/account        (account sanity check / auth check)
        - POST /fapi/v1/order          (place an order)
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
    ):
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be provided.")

        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    def _signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW_MS
        params["signature"] = self._sign(params)
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        if signed:
            params = self._signed_params(params)

        logger.debug("HTTP %s %s | params=%s", method, url, _redact(params))

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out: %s", url, exc)
            raise BinanceNetworkError(f"Request to {url} timed out after {REQUEST_TIMEOUT_S}s") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error reaching %s: %s", url, exc)
            raise BinanceNetworkError(f"Could not connect to {url}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error for %s: %s", url, exc)
            raise BinanceNetworkError(f"Unexpected network error calling {url}: {exc}") from exc

        logger.debug("HTTP %s %s -> status=%s body=%s", method, url, response.status_code, response.text)

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error("Non-JSON response from %s (status %s): %s", url, response.status_code, response.text)
            raise BinanceAPIError(response.status_code, f"Non-JSON response body: {response.text}") from exc

        if response.status_code >= 400 or (isinstance(payload, dict) and "code" in payload and payload.get("code", 0) < 0):
            code = payload.get("code", response.status_code)
            msg = payload.get("msg", str(payload))
            logger.error("Binance API returned error: code=%s msg=%s", code, msg)
            raise BinanceAPIError(code, msg)

        return payload

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def ping(self) -> Dict[str, Any]:
        """Basic connectivity check against the testnet host."""
        return self._request("GET", "/fapi/v1/ping")

    def get_account(self) -> Dict[str, Any]:
        """Fetch account info; also doubles as an auth sanity check."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Place an order on Binance Futures Testnet (USDT-M).

        Supports MARKET, LIMIT, and STOP (stop-limit) order types.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP":
            # Stop-Limit: triggers a LIMIT order once stopPrice is reached.
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Never write the signature to logs in full; keep just a short prefix for traceability."""
    redacted = dict(params)
    if "signature" in redacted:
        sig = str(redacted["signature"])
        redacted["signature"] = f"{sig[:6]}...redacted"
    return redacted
