# Task 4: Network Construction Methods

**Files:**
- Create: `backend/app/services/network_builder.py`
- Create: `backend/tests/test_network_builder.py`

**Depends on:** Tasks 2, 3

## Steps

1. Write failing tests in `backend/tests/test_network_builder.py`:
   - `_make_test_returns(n_assets=10, n_obs=200)` — helper generating synthetic correlated returns via 3 latent factors
   - `test_pearson_produces_network` — assert returns nx.Graph with 10 nodes and edges
   - `test_spearman_produces_network` — same
   - `test_partial_correlation_produces_network` — same
   - `test_graphical_lasso_produces_network` — same
   - `test_granger_produces_directed_network` — assert returns nx.DiGraph
   - `test_correlation_to_network_top_k` — assert node A has at most 2 edges when k=2

2. Run tests to verify they fail (cannot import)

3. Implement `backend/app/services/network_builder.py`:
   - `correlation_to_network(corr, tickers, mode, k, threshold)` — converts correlation matrix to nx.Graph, supports top_k and threshold modes
   - `build_pearson_network(returns, **kwargs)` — numpy corrcoef
   - `build_spearman_network(returns, **kwargs)` — scipy.stats.spearmanr
   - `build_partial_correlation_network(returns, **kwargs)` — precision matrix inversion, partial correlation formula
   - `build_graphical_lasso_network(returns, **kwargs)` — sklearn GraphicalLassoCV
   - `build_granger_causality_network(returns, max_lag, significance, **kwargs)` — statsmodels grangercausalitytests, returns DiGraph
   - Working comments explaining each method, what it captures, and its limitations

4. Run tests to verify they pass

5. Commit: `git add backend/app/services/network_builder.py backend/tests/test_network_builder.py && git commit -m "5 network construction methods — pearson, spearman, partial, gllasso, granger"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
