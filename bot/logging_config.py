"""
Centralized logging configuration for the trading bot.

Logs go to BOTH the console (human-friendly, INFO+) and a rotating
log file (detailed, DEBUG+) so that every API request, response, and
error is auditable after the fact.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_CONFIGURED = False


def setup_logging(log_file: str = LOG_FILE, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the root application logger.

    Idempotent: calling this multiple times will not add duplicate handlers.
    """
    global _CONFIGURED

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)

    if _CONFIGURED:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: keeps logs from growing unbounded,
    # captures full detail (DEBUG) including raw request/response bodies.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler: keeps stdout readable, only INFO+ and no payload noise.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    _CONFIGURED = True
    return logger


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """
    Convenience accessor used by other modules.

    Ensures every module logger is nested *under* the configured
    "trading_bot" logger (e.g. "bot.orders" -> "trading_bot.bot.orders")
    so that log records propagate up to the handlers configured in
    setup_logging(). Without this, module-level loggers created via
    __name__ (e.g. "bot.client") would be siblings of "trading_bot"
    rather than children, and their records would silently vanish into
    the unconfigured root logger.
    """
    if not _CONFIGURED:
        setup_logging()
    if name == "trading_bot" or name.startswith("trading_bot."):
        return logging.getLogger(name)
    return logging.getLogger(f"trading_bot.{name}")
