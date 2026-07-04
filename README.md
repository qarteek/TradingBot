# Binance Futures Testnet Trading Bot

A Python CLI tool for placing orders on Binance Futures Testnet (USDT-M). Built this as an assignment to practice structuring a small trading tool properly — separate API layer, input validation, logging, error handling — instead of just throwing everything into one script.

## What it does

- Places MARKET, LIMIT, and STOP-Limit orders (BUY or SELL) on the Futures Testnet
- Validates everything you type before it ever hits the network
- Prints a summary of what you're about to send, then what came back (order ID, status, filled quantity, avg price)
- Logs every request/response to a file so you can go back and see exactly what happened if something breaks

## Project layout

```
trading_bot/
├── bot/
│   ├── client.py          # talks to the Binance API (signing requests, sending them)
│   ├── orders.py          # order placement logic, formats the summaries you see printed
│   ├── validators.py      # checks your inputs before anything is sent
│   ├── logging_config.py  # sets up the logger
│   └── cli.py             # the actual command line tool
├── scripts/
│   └── mock_binance_server.py   # see note below
├── tests/
│   └── test_validators.py
├── logs/
│   └── trading_bot.log
├── requirements.txt
└── .env.example
```

## Getting set up

**1. Testnet account**

Go to https://testnet.binancefuture.com and log in with your GitHub account. Once you're in, find the API Key section and generate a key + secret. There's also a faucet on there to top up your paper USDT balance if you need margin to actually place orders.

**2. Install stuff**

```bash
cd trading_bot
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Only real dependency is `requests`. Kept it minimal on purpose.

**3. Set your API keys**

```bash
export BINANCE_API_KEY="your_key_here"
export BINANCE_API_SECRET="your_secret_here"
```

Or just pass them in every time with `--api-key` and `--api-secret` if you don't want to export anything. There's a `.env.example` file showing the variable names, but heads up — this doesn't auto-load a `.env` file, you actually need to export the vars or pass the flags. Didn't want to add python-dotenv just for that.

## Using it

Run everything from inside the `trading_bot/` folder.

Market order:
```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

Limit order:
```bash
python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

Stop-limit order (this is the bonus 3rd order type I added):
```bash
python -m bot.cli --symbol ETHUSDT --side SELL --type STOP --quantity 0.5 --price 3200 --stop-price 3250
```

By default it'll show you the order summary and ask "are you sure?" before actually sending it. A few flags that are handy:

- `-y` — skip the confirmation, just send it
- `--dry-run` — validates and prints the summary but never touches the network (good for testing your inputs without needing keys at all)
- `--base-url` — point it somewhere else if you need to (defaults to the real testnet URL)

Try the dry run first if you want to see how it behaves without any credentials:
```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

## Running tests

```bash
python -m unittest discover -s tests -v
```

16 tests, mostly around the validation logic (bad symbols, negative quantities, missing prices for limit orders, that kind of thing).

## Error handling / exit codes

Wanted this to be scriptable so I split errors into a few buckets with different exit codes:

- `0` — worked fine (or was a dry run / you cancelled)
- `2` — something you typed was invalid, caught before any API call
- `3` — Binance itself rejected the order
- `4` — network problem (timeout, connection refused, etc.)

## About the log files included here

I included a `logs/trading_bot.log` with entries from a market order, a limit order, a stop-limit order, plus one validation error and one network error, so you can see what the logging actually looks like.

Small thing worth flagging honestly: I generated these against a tiny local mock server (`scripts/mock_binance_server.py`) instead of the real testnet, because the machine I built this on has locked-down network access and literally can't reach testnet.binancefuture.com. The mock just returns fake-but-realistic responses (order IDs, fill status, etc.) so I could still exercise the whole client → sign → send → log pipeline for real, just against a stand-in instead of the actual matching engine.

If you run this with your own real testnet keys, it'll hit the actual Binance testnet by default — nothing to change, `--base-url` already points there. You'd get real logs from real orders. To replicate what's in the included log file yourself using the mock:

```bash
# one terminal
python scripts/mock_binance_server.py --port 8000

# another terminal
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --api-key demoKey --api-secret demoSecret --base-url http://127.0.0.1:8000 -y
```

## A few assumptions I made

- I only check that the symbol *looks* right (uppercase letters/numbers, reasonable length) rather than checking it against Binance's actual list of tradeable pairs — didn't seem worth fetching and caching that just for this. If you typo a symbol, Binance will reject it (exit code 3) instead of it getting caught locally (exit code 2), but either way it won't silently fail.
- LIMIT and STOP orders default to `GTC` (good-til-cancelled) since nothing was specified about time-in-force.
- The confirmation prompt before sending, and the colored success/fail messages, aren't strictly required — added them since the assignment mentioned enhanced CLI UX as a bonus.
