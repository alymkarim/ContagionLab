"""
Data fetcher service using yfinance with local parquet caching.

Fetches adjusted closing prices for requested tickers and computes
log returns — the standard transformation for modelling financial
time series because log returns are approximately normally distributed
and time-additive (the return over [t, t+2] equals the sum of the
two single-period returns).
"""

import hashlib
import logging
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Directory for cached parquet files, keyed by ticker set + period
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(tickers: Sequence[str], period: str) -> str:
    """Build a deterministic filename from tickers + period.

    We hash the sorted tickers and the period string so the same
    request always maps to the same file, regardless of the order
    in which tickers are supplied.
    """
    blob = "|".join(sorted(tickers)) + f"|{period}"
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def fetch_prices(
    tickers: Sequence[str],
    period: str = "1y",
    *,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch adjusted closing prices via yfinance, caching to parquet.

    Parameters
    ----------
    tickers : list[str]
        Ticker symbols, e.g. ["SPY", "QQQ"].
    period : str
        yfinance period string — "1y", "6mo", "5d", etc.
    use_cache : bool
        When True (the default), a local parquet file is used if it
        exists and is less than 1 day old.

    Returns
    -------
    pd.DataFrame
        Index of datetime, one column per ticker containing adjusted
        close prices.  If yfinance returns a MultiIndex (happens when
        more than one ticker is requested), we extract the "Close"
        level so the caller gets a clean ticker-keyed DataFrame.
    """
    cache_file = _CACHE_DIR / f"{_cache_key(tickers, period)}.parquet"

    # Serve from cache when fresh (< 1 day old)
    if use_cache and cache_file.exists():
        age_hours = (pd.Timestamp.now().timestamp() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            logger.info("Serving prices from cache (%s)", cache_file.name)
            return pd.read_parquet(cache_file)

    # --- yfinance download -------------------------------------------------
    # yfinance returns a DataFrame whose shape depends on the number of
    # tickers:
    #   • 1 ticker  → single-level columns: Open, High, Low, Close, ...
    #   • N tickers → MultiIndex columns: (Price, Ticker) pairs
    # We normalise both cases so the caller always gets a flat
    # DataFrame indexed by datetime with one column per ticker.
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)

    if raw.empty:
        raise ValueError(f"No data returned for tickers {tickers} with period={period}")

    # Handle MultiIndex columns (multiple tickers)
    if isinstance(raw.columns, pd.MultiIndex):
        # Extract the 'Close' level — column structure is (Price, Ticker)
        prices = raw["Close"]
    else:
        # Single ticker — yfinance gives flat columns, wrap in DataFrame
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})

    # Forward-fill small gaps (weekends / holidays already removed by
    # yfinance, but some holidays differ across exchanges)
    prices = prices.ffill()

    # Persist for future requests
    prices.to_parquet(cache_file)
    logger.info("Cached %d rows to %s", len(prices), cache_file.name)

    return prices


def get_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Compute continuously-compounded (log) returns from a price series.

    Log returns are defined as:

        r_t = ln( P_t / P_{t-1} )

    Advantages over simple returns:
      - Time-additive:  r[t, t+2] = r[t, t+1] + r[t+1, t+2]
      - Better statistical properties (closer to normal distribution)
      - Symmetric:  a +10 % gain followed by a -10 % loss yields
        a slightly negative cumulative return, which matches reality.

    The first row is dropped because ln(P_0 / P_{-1}) is undefined
    — there is no previous observation.
    """
    # ln(P_t / P_{t-1}) is equivalent to ln(1 + simple_return)
    # but computed directly from prices to avoid intermediate rounding.
    shifted = prices.shift(1)
    returns = np.log(prices / shifted)
    # Drop the first row which is NaN (no P_{t-1} for t=0)
    return returns.iloc[1:]
