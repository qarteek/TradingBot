"""
Command line entry point for the Binance Futures Testnet trading bot.

Examples
--------
Market order:
    python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Stop-Limit order (bonus order type):
    python -m bot.cli --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 \\
        --price 64000 --stop-price 64500

API credentials are read from --api-key/--api-secret, or from the
BINANCE_API_KEY / BINANCE_API_SECRET environment variables if omitted.
"""

from __future__ import annotations

import argparse
import os
import sys

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, DEFAULT_BASE_URL
from .logging_config import setup_logging
from .orders import build_request_summary, build_response_summary, place_order
from .validators import ValidationError

# ANSI colors for a friendlier CLI (bonus: enhanced UX). Degrades gracefully
# on terminals that don't render them -- they're just extra characters.
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, type=float, help="Order quantity")
    parser.add_argument("--price", type=float, default=None, help="Limit price (required for LIMIT/STOP)")
    parser.add_argument("--stop-price", type=float, default=None, help="Stop trigger price (required for STOP)")

    parser.add_argument("--api-key", default=os.environ.get("BINANCE_API_KEY"), help="Binance Testnet API key")
    parser.add_argument("--api-secret", default=os.environ.get("BINANCE_API_SECRET"), help="Binance Testnet API secret")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL (default: Futures Testnet)")

    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip the confirmation prompt and place the order immediately.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and print the order summary WITHOUT sending it to Binance.",
    )
    return parser


def _confirm(prompt: str) -> bool:
    reply = input(f"{prompt} [y/N]: ").strip().lower()
    return reply in ("y", "yes")


def main(argv=None) -> int:
    logger = setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # Uppercase early so validators.py sees normalized input either way.
        side = args.side.upper()
        order_type = args.order_type.upper()

        if not args.dry_run and (not args.api_key or not args.api_secret):
            raise ValidationError(
                "Missing API credentials. Provide --api-key/--api-secret or set "
                "BINANCE_API_KEY/BINANCE_API_SECRET environment variables "
                "(or use --dry-run to test without credentials)."
            )

        # Validate + build a clean params dict up front so we can show the
        # user a summary before ever touching the network.
        from .validators import validate_order_params
        params = validate_order_params(
            symbol=args.symbol,
            side=side,
            order_type=order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )

        print(build_request_summary(params))

        if args.dry_run:
            print(f"\n{_YELLOW}[DRY RUN] Order was validated but NOT sent to Binance.{_RESET}")
            logger.info("Dry-run completed for %s %s %s", params["symbol"], params["side"], params["order_type"])
            return 0

        if not args.yes and not _confirm("\nSend this order to Binance Futures Testnet?"):
            print(f"{_YELLOW}Order cancelled by user.{_RESET}")
            logger.info("Order cancelled by user before submission.")
            return 0

        client = BinanceFuturesClient(api_key=args.api_key, api_secret=args.api_secret, base_url=args.base_url)
        result = place_order(
            client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )

        if result.success:
            print()
            print(build_response_summary(result.response))
            print(f"\n{_GREEN}SUCCESS: order placed successfully.{_RESET}")
            return 0
        else:
            print(f"\n{_RED}FAILED: {result.error}{_RESET}")
            return 1

    except ValidationError as exc:
        print(f"{_RED}Invalid input: {exc}{_RESET}", file=sys.stderr)
        logger.warning("Validation error: %s", exc)
        return 2
    except BinanceAPIError as exc:
        print(f"{_RED}Binance API error: {exc}{_RESET}", file=sys.stderr)
        logger.error("Binance API error: %s", exc)
        return 3
    except BinanceNetworkError as exc:
        print(f"{_RED}Network error: {exc}{_RESET}", file=sys.stderr)
        logger.error("Network error: %s", exc)
        return 4
    except KeyboardInterrupt:
        print(f"\n{_YELLOW}Cancelled by user (Ctrl+C).{_RESET}")
        return 130
    except Exception as exc:  # noqa: BLE001 - top-level safety net for CLI usage
        print(f"{_RED}Unexpected error: {exc}{_RESET}", file=sys.stderr)
        logger.exception("Unexpected error in CLI")
        return 1


if __name__ == "__main__":
    sys.exit(main())
