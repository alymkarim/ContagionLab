"""
Macro data integration — adding VIX, Treasury yields, and dollar index.

The idea: standard financial networks only use stock/ETF returns.
But macro indicators like the VIX (volatility), Treasury yields (interest
rates), and the dollar index (currency strength) are critical for
understanding systemic risk.

For example:
- VIX spikes often precede equity drawdowns (fear → selling)
- Rising Treasury yields signal tightening financial conditions
- A strong dollar pressures emerging markets and commodities

By including these in the network, we can see how macro conditions
connect to equity markets and identify cross-asset contagion channels.

Physics analogy: this is like adding external fields to a spin system.
The macro indicators are not just another node — they're boundary
conditions that affect the entire system.

Data sources (all free via yfinance):
- VIX: ^VIX (CBOE Volatility Index)
- 10-Year Treasury: ^TNX
- 2-Year Treasury: ^IRX (actually 13-week, but close proxy)
- Dollar Index: DX-Y.NYB
- Gold: GC=F
- Oil: CL=F
- S&P 500: SPY (already included as equity)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional


# Macro tickers we can add to any network
MACRO_TICKERS = {
    "VIX": {
        "ticker": "^VIX",
        "name": "CBOE Volatility Index",
        "description": "Market fear gauge — spikes during crises",
        "category": "volatility",
    },
    "DGS10": {
        "ticker": "^TNX",
        "name": "10-Year Treasury Yield",
        "description": "Long-term interest rate — affects discount rates and valuations",
        "category": "rates",
    },
    "DGS2": {
        "ticker": "^IRX",
        "name": "13-Week Treasury Bill",
        "description": "Short-term rate proxy — reflects Fed policy expectations",
        "category": "rates",
    },
    "DXY": {
        "ticker": "DX-Y.NYB",
        "name": "US Dollar Index",
        "description": "Dollar strength — pressures EM and commodities",
        "category": "currency",
    },
    "GOLD": {
        "ticker": "GC=F",
        "name": "Gold Futures",
        "description": "Safe haven asset — rises during uncertainty",
        "category": "commodities",
    },
    "OIL": {
        "ticker": "CL=F",
        "name": "Crude Oil Futures",
        "description": "Energy prices — affects inflation and growth expectations",
        "category": "commodities",
    },
}


def get_macro_tickers() -> dict:
    """Return available macro tickers with metadata."""
    return MACRO_TICKERS


def fetch_macro_data(
    period: str = "1y",
    include: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Fetch macro indicator data from yfinance.

    Parameters
    ----------
    period : str
        Time period (e.g., '1y', '2y', '5y')
    include : list[str] | None
        Which macro indicators to include. If None, returns all.

    Returns
    -------
    pd.DataFrame
        DataFrame of adjusted close prices for macro indicators.
    """
    if include is None:
        include = list(MACRO_TICKERS.keys())

    tickers = [MACRO_TICKERS[k]["ticker"] for k in include if k in MACRO_TICKERS]

    if not tickers:
        return pd.DataFrame()

    data = yf.download(tickers, period=period, progress=False, auto_adjust=True)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]
        prices.columns = tickers[:1]

    # Rename columns to friendly names
    rename_map = {}
    for key, info in MACRO_TICKERS.items():
        if info["ticker"] in prices.columns:
            rename_map[info["ticker"]] = key
    prices = prices.rename(columns=rename_map)

    return prices


def merge_with_equity(
    equity_prices: pd.DataFrame,
    macro_prices: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge macro data with equity price data.

    Aligns on dates and forward-fills missing macro values
    (markets closed on different days).
    """
    if macro_prices.empty:
        return equity_prices

    # Forward fill macro data (some markets close earlier)
    macro_filled = macro_prices.ffill()

    # Merge on date index
    merged = equity_prices.join(macro_filled, how="inner")

    # Drop columns with too many NaNs
    merged = merged.dropna(axis=1, thresh=int(len(merged) * 0.8))

    return merged


def get_macro_summary(
    macro_prices: pd.DataFrame,
) -> dict:
    """
    Compute summary statistics for macro indicators.
    """
    if macro_prices.empty:
        return {}

    summary = {}
    for col in macro_prices.columns:
        prices = macro_prices[col].dropna()
        if len(prices) < 2:
            continue

        returns = np.log(prices / prices.shift(1)).dropna()

        summary[col] = {
            "current": round(float(prices.iloc[-1]), 4),
            "start": round(float(prices.iloc[0]), 4),
            "change_pct": round(float((prices.iloc[-1] / prices.iloc[0] - 1) * 100), 2),
            "volatility": round(float(returns.std() * np.sqrt(252)), 4),
            "name": MACRO_TICKERS.get(col, {}).get("name", col),
            "description": MACRO_TICKERS.get(col, {}).get("description", ""),
            "category": MACRO_TICKERS.get(col, {}).get("category", "unknown"),
        }

    return summary
