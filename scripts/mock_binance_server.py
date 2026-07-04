"""
A tiny local mock of the Binance Futures Testnet REST API.

WHY THIS EXISTS
----------------
This script is a *development aid only* -- it is NOT part of the trading
bot's core deliverable. It exists so that:

  1. The bot's HTTP/signing/logging code path can be exercised end-to-end
     without needing live Binance Testnet credentials or network access
     (useful in sandboxed / offline environments).
  2. Example log files can be generated for review.

It implements just enough of the real API surface (ping, account, order)
with plausible response shapes to drive the CLI. It does NOT validate
signatures and does NOT simulate real market behavior -- it is a stub,
not a matching engine. Point the bot at the real
https://testnet.binancefuture.com for genuine testnet behavior.

Usage:
    python scripts/mock_binance_server.py --port 8000
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

_order_counter = 1000


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet down default stderr access logs
        pass

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/fapi/v1/ping":
            self._send_json({})
        elif parsed.path == "/fapi/v2/account":
            self._send_json({
                "totalWalletBalance": "15000.00000000",
                "availableBalance": "14875.00000000",
                "assets": [{"asset": "USDT", "walletBalance": "15000.00000000"}],
            })
        else:
            self._send_json({"code": -1, "msg": "Unknown endpoint"}, status=404)

    def do_POST(self):
        global _order_counter
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length else ""
        params = {k: v[0] for k, v in parse_qs(raw_body).items()}

        if parsed.path != "/fapi/v1/order":
            self._send_json({"code": -1, "msg": "Unknown endpoint"}, status=404)
            return

        symbol = params.get("symbol", "UNKNOWN")
        side = params.get("side", "BUY")
        order_type = params.get("type", "MARKET")
        quantity = params.get("quantity", "0")
        price = params.get("price")

        _order_counter += 1
        order_id = _order_counter

        # Simulate an immediate fill for MARKET orders, NEW (open) for LIMIT/STOP.
        if order_type == "MARKET":
            status = "FILLED"
            executed_qty = quantity
            avg_price = price or "60000.00"
        else:
            status = "NEW"
            executed_qty = "0"
            avg_price = "0.00"

        response = {
            "orderId": order_id,
            "symbol": symbol,
            "status": status,
            "clientOrderId": f"mock-{uuid.uuid4().hex[:12]}",
            "side": side,
            "type": order_type,
            "origQty": quantity,
            "executedQty": executed_qty,
            "avgPrice": avg_price,
            "price": price or "0.00",
            "updateTime": int(time.time() * 1000),
        }
        self._send_json(response)


def main():
    parser = argparse.ArgumentParser(description="Run the local mock Binance Futures server.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), MockHandler)
    print(f"Mock Binance Futures server listening on http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
