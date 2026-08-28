import numpy as np
import pandas as pd
import pytest

from app.services.data_fetcher import fetch_prices, get_returns


def test_fetch_prices_returns_dataframe():
    """Fetch SPY and QQQ for 1y period, assert DataFrame with correct columns."""
    prices = fetch_prices(["SPY", "QQQ"], period="1y")
    assert isinstance(prices, pd.DataFrame)
    assert not prices.empty
    assert "SPY" in prices.columns
    assert "QQQ" in prices.columns


def test_get_returns_computes_log_returns():
    """Create price series [100, 110, 121], assert log returns ≈ 0.0953."""
    # ln(110/100) = ln(1.1) ≈ 0.09531
    # ln(121/110) = ln(1.1) ≈ 0.09531
    prices = pd.Series([100.0, 110.0, 121.0])
    returns = get_returns(prices)
    assert len(returns) == 2
    np.testing.assert_almost_equal(returns.iloc[0], np.log(110 / 100), decimal=4)
    np.testing.assert_almost_equal(returns.iloc[1], np.log(121 / 110), decimal=4)
