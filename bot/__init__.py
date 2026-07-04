"""
trading_bot.bot
~~~~~~~~~~~~~~~
A small, reusable package for placing orders on the Binance Futures
Testnet (USDT-M).

Modules:
    client.py          -> low-level signed REST client for the Futures API
    orders.py           -> higher-level order placement / formatting logic
    validators.py       -> CLI input validation helpers
    logging_config.py   -> centralized logging configuration
    cli.py              -> command line entry point
"""

__version__ = "1.0.0"
