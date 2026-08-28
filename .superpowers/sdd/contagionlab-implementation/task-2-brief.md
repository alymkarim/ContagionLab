# Task 2: Data Layer

**Files:**
- Create: `backend/app/services/data_fetcher.py`
- Create: `backend/app/routers/assets.py`
- Create: `backend/tests/test_data_fetcher.py`

**Depends on:** Task 1

## Steps

1. Write failing test `backend/tests/test_data_fetcher.py`:
   - `test_fetch_prices_returns_dataframe` — fetch SPY, QQQ for 1y period, assert DataFrame with those columns
   - `test_get_returns_computes_log_returns` — create price series [100, 110, 121], assert log returns ≈ 0.0953

2. Run test to verify it fails (cannot import)

3. Implement `backend/app/services/data_fetcher.py`:
   - `fetch_prices(assets, period)` — uses yfinance, caches to parquet in `backend/cache/`, returns DataFrame
   - `get_returns(prices)` — computes ln(P_t / P_{t-1}), drops first NaN row
   - Working comments explaining log returns, caching, yfinance MultiIndex handling

4. Run test to verify it passes

5. Create `backend/app/routers/assets.py`:
   - `GET /api/assets` — returns default universe grouped by sector (tech, finance, energy, commodities, bonds, index)
   - DEFAULT_UNIVERSE dict with ~30 tickers

6. Register router in `backend/app/main.py`

7. Commit: `git add backend/ && git commit -m "data layer — yfinance fetcher with parquet cache, log returns, assets endpoint"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
