# ContagionLab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack financial network analysis platform that constructs networks from real market data using 5 methods, applies RMT noise filtering, computes systemic importance metrics, and runs Monte Carlo stress tests.

**Architecture:** Python analysis engine (data → filtering → networks → analysis → simulation) served via FastAPI, consumed by a React/TypeScript frontend with interactive network visualization.

**Tech Stack:** Python 3.11+, FastAPI, numpy, scipy, pandas, scikit-learn, statsmodels, networkx, yfinance, React 18, TypeScript, Vite, react-force-graph-2d, Recharts, Tailwind CSS

## Global Constraints

- Python 3.11+, no lower versions
- All code must have working comments explaining the math (see spec §14)
- Commit messages must be human-style, no conventional-commit format
- Feature branches per spec §15: `feat/data-layer`, `feat/rmt-filtering`, etc.
- No AI-generated README — write it like explaining to a colleague
- Tests use pytest, no other test framework

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `.gitignore`
- Create: `README.md`

**Depends on:** nothing

- [ ] **Step 1: Initialize git repo**

```bash
git init
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
venv/
.venv/
*.parquet
node_modules/
dist/
.pytest_cache/
.mypy_cache/
```

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p backend/app/routers backend/app/services backend/app/models backend/tests
mkdir -p frontend
touch backend/app/__init__.py
touch backend/app/routers/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 4: Create backend/requirements.txt**

```
fastapi>=0.104.0
uvicorn>=0.24.0
numpy>=1.24.0
scipy>=1.11.0
pandas>=2.1.0
scikit-learn>=1.3.0
statsmodels>=0.14.0
networkx>=3.2
yfinance>=0.2.30
pyarrow>=14.0
pytest>=7.4.0
httpx>=0.25.0
```

- [ ] **Step 5: Create backend/app/main.py (minimal)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ContagionLab",
    description="Financial network analysis and systemic risk simulation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 6: Create backend/tests/conftest.py**

```python
import pytest
```

- [ ] **Step 7: Write a test for the health endpoint**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 8: Run the test**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 9: Create README.md (skeleton)**

```markdown
# ContagionLab

Models global financial markets as networks. Identifies systemically
important assets and simulates how shocks propagate.

See `docs/superpowers/specs/` for the full design spec.

## Running

Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
Frontend: `cd frontend && npm install && npm run dev`
```

- [ ] **Step 10: Initial commit**

```bash
git add .
git commit -m "initial project structure — backend skeleton, health endpoint"
```

---

## Task 2: Data Layer

**Files:**
- Create: `backend/app/services/data_fetcher.py`
- Create: `backend/app/routers/assets.py`
- Create: `backend/tests/test_data_fetcher.py`

**Depends on:** Task 1

- [ ] **Step 1: Write the failing test for fetching prices**

```python
# backend/tests/test_data_fetcher.py
import pandas as pd
from app.services.data_fetcher import fetch_prices, get_returns


def test_fetch_prices_returns_dataframe():
    """fetch_prices should return a DataFrame with Date index and asset columns."""
    assets = ["SPY", "QQQ"]
    df = fetch_prices(assets, period="1y")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "SPY" in df.columns
    assert "QQQ" in df.columns


def test_get_returns_computes_log_returns():
    """get_returns should compute log returns: ln(P_t / P_{t-1})."""
    # Create a simple price series: [100, 110, 121]
    # Log returns: ln(110/100) ≈ 0.0953, ln(121/110) ≈ 0.0953
    prices = pd.DataFrame({"A": [100, 110, 121]})
    returns = get_returns(prices)
    assert len(returns) == 2
    assert abs(returns["A"].iloc[0] - 0.0953) < 0.001
    assert abs(returns["A"].iloc[1] - 0.0953) < 0.001
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_data_fetcher.py -v`
Expected: FAIL with "cannot import name 'fetch_prices'"

- [ ] **Step 3: Implement data_fetcher.py**

```python
# backend/app/services/data_fetcher.py
"""
Data fetching and return computation.

Uses yfinance to pull OHLCV data for a list of tickers.
Caches to parquet so we don't hammer the API on every run.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# where we stash downloaded data
CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def fetch_prices(assets: list[str], period: str = "2y") -> pd.DataFrame:
    """
    Fetch daily adjusted close prices for a list of assets.

    Returns a DataFrame with DatetimeIndex and one column per asset.
    If a parquet cache exists and is fresh (< 24h old), uses that instead.
    """
    cache_file = CACHE_DIR / f"prices_{'_'.join(sorted(assets))}_{period}.parquet"

    # use cache if it exists and is less than 1 day old
    if cache_file.exists():
        age_hours = (pd.Timestamp.now().timestamp() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            return pd.read_parquet(cache_file)

    # download from yfinance
    data = yf.download(assets, period=period, auto_adjust=True, progress=False)

    # yfinance returns multi-level columns when downloading multiple tickers
    # we want a flat DataFrame: Date index, one column per ticker
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        # single ticker — rename to column name
        prices = data[["Close"]].rename(columns={"Close": assets[0]})

    # drop any rows where all values are NaN (e.g. assets that started later)
    prices = prices.dropna(how="all")

    # cache it
    prices.to_parquet(cache_file)

    return prices


def get_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute log returns from prices.

    r_t = ln(P_t / P_{t-1})

    Log returns are additive over time and approximately equal to
    percentage returns for small changes. Standard in finance and
    econophysics — see Mantegna & Stanley, "An Introduction to
    Econophysics" (2000).
    """
    # shift(1) gives us P_{t-1} for each row
    returns = np.log(prices / prices.shift(1))

    # first row is NaN (no P_{t-1}), drop it
    return returns.dropna()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_data_fetcher.py -v`
Expected: PASS (note: the yfinance test will hit the network, that's fine for now)

- [ ] **Step 5: Create assets router**

```python
# backend/app/routers/assets.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/assets", tags=["assets"])

# default universe — roughly 30 assets across sectors
DEFAULT_UNIVERSE = {
    "tech": ["NVDA", "AMD", "MSFT", "AAPL", "GOOGL", "META", "AVGO"],
    "finance": ["JPM", "BAC", "GS", "MS", "C"],
    "energy": ["XOM", "CVX", "COP"],
    "commodities": ["GLD", "USO"],
    "bonds": ["TLT", "IEF", "SHY", "HYG"],
    "index": ["SPY", "QQQ", "IWM", "XLF", "XLE", "SOXX"],
}


@router.get("")
def list_assets():
    """Return available assets grouped by sector."""
    return {"universe": DEFAULT_UNIVERSE}
```

- [ ] **Step 6: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import assets

app.include_router(assets.router)
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "data layer — yfinance fetcher with parquet cache, log returns, assets endpoint"
```

---

## Task 3: RMT Filtering

**Files:**
- Create: `backend/app/services/rmt_filter.py`
- Create: `backend/tests/test_rmt_filter.py`

**Depends on:** Task 2

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rmt_filter.py
import numpy as np
from app.services.rmt_filter import compute_mp_upper_bound, filter_correlation_matrix


def test_mp_upper_bound():
    """
    Marchenko-Pastur upper bound: λ₊ = σ²(1 + √(N/T))²

    For N=50 assets, T=250 observations, σ²=1:
    λ₊ = (1 + √(50/250))² = (1 + √0.2)² ≈ (1 + 0.447)² ≈ 2.094
    """
    n, t = 50, 250
    sigma2 = 1.0
    lambda_plus = compute_mp_upper_bound(n, t, sigma2)
    assert abs(lambda_plus - 2.094) < 0.01


def test_filter_removes_noise_eigenvalues():
    """Filtered matrix should have fewer large eigenvalues than the raw one."""
    np.random.seed(42)
    n, t = 30, 100
    # generate random returns (pure noise)
    returns = np.random.randn(t, n)
    corr = np.corrcoef(returns, rowvar=False)

    filtered = filter_correlation_matrix(corr, t)

    # the filtered matrix should have all eigenvalues ≤ λ₊
    eigvals = np.linalg.eigvalsh(filtered)
    lambda_plus = compute_mp_upper_bound(n, t, 1.0)
    assert np.all(eigvals <= lambda_plus + 0.01)


def test_filter_preserves_trace():
    """Clipping should preserve tr(C) = N (trace-preserving)."""
    np.random.seed(42)
    n, t = 30, 100
    returns = np.random.randn(t, n)
    corr = np.corrcoef(returns, rowvar=False)
    original_trace = np.trace(corr)

    filtered = filter_correlation_matrix(corr, t)

    # trace should be approximately preserved (within numerical precision)
    assert abs(np.trace(filtered) - original_trace) < 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rmt_filter.py -v`
Expected: FAIL with "cannot import name 'compute_mp_upper_bound'"

- [ ] **Step 3: Implement rmt_filter.py**

```python
# backend/app/services/rmt_filter.py
"""
Random Matrix Theory filtering for correlation matrices.

The idea: empirical correlation matrices of financial returns are
heavily contaminated by noise. Most of the eigenvalues don't carry
real information about how assets are related.

The Marchenko-Pastur law tells us exactly what the eigenvalue
distribution should look like for a purely random matrix. Any
eigenvalue above the MP upper bound is likely genuine signal.

We clip the noise eigenvalues by replacing them with their mean.
This preserves the trace (total variance) while removing noise.

Reference: Laloux, Cizeau, Bouchaud, Potters,
"Noise Dressing of Financial Correlation Matrices",
Phys. Rev. Lett. 83, 1467 (1999)
"""

import numpy as np


def compute_mp_upper_bound(n: int, t: int, sigma2: float = 1.0) -> float:
    """
    Compute the Marchenko-Pastur upper bound.

    For a correlation matrix of N assets observed over T time steps,
    the noise eigenvalues fall within [λ₋, λ₊] where:

        λ₊ = σ²(1 + √(N/T))²

    When σ² = 1 (correlation matrix), this simplifies to:
        λ₊ = (1 + √(N/T))²

    Parameters
    ----------
    n : int
        Number of assets (rows of correlation matrix)
    t : int
        Number of observations (time steps)
    sigma2 : float
        Variance parameter. For correlation matrices, this is 1.0.
        For covariance matrices, estimate from the data.
    """
    q = n / t  # aspect ratio — key parameter in RMT
    lambda_plus = sigma2 * (1 + np.sqrt(q)) ** 2
    return lambda_plus


def filter_correlation_matrix(
    corr: np.ndarray,
    t: int,
    sigma2: float = 1.0,
) -> np.ndarray:
    """
    Denoise a correlation matrix using RMT eigenvalue clipping.

    Algorithm (Laloux et al. 1999):
    1. Eigendecompose the correlation matrix: C = U Λ U^T
    2. Find the MP upper bound λ₊
    3. Any eigenvalue ≤ λ₊ is noise → replace with mean of noise eigenvalues
    4. Reconstruct: C_clean = U Λ_clean U^T

    The trace-preserving step (replacing with mean, not zero) ensures
    that tr(C_clean) = tr(C) = N, so total variance is unchanged.

    Parameters
    ----------
    corr : np.ndarray
        NxN correlation matrix
    t : int
        Number of observations used to build the correlation matrix
    sigma2 : float
        Variance parameter (default 1.0 for correlation matrices)

    Returns
    -------
    np.ndarray
        Denoised NxN correlation matrix
    """
    n = corr.shape[0]
    lambda_plus = compute_mp_upper_bound(n, t, sigma2)

    # eigendecomposition — eigvalsh because correlation matrices are symmetric
    eigvals, eigvecs = np.linalg.eigh(corr)

    # identify noise eigenvalues (those within the MP bulk)
    noise_mask = eigvals <= lambda_plus

    # replace noise eigenvalues with their mean (trace-preserving)
    # this is the key step: we're not deleting them, we're replacing them
    # with the average noise level so that the total variance is preserved
    if np.any(noise_mask):
        noise_mean = np.mean(eigvals[noise_mask])
        eigvals[noise_mask] = noise_mean

    # reconstruct the cleaned correlation matrix
    # C_clean = U Λ_clean U^T
    corr_clean = eigvecs @ np.diag(eigvals) @ eigvecs.T

    # symmetrize (should already be symmetric, but numerical drift...)
    corr_clean = (corr_clean + corr_clean.T) / 2

    # clip diagonal to exactly 1 (correlation matrix property)
    np.fill_diagonal(corr_clean, 1.0)

    # clip off-diagonals to [-1, 1] (correlation bounds)
    corr_clean = np.clip(corr_clean, -1, 1)

    return corr_clean
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rmt_filter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rmt_filter.py backend/tests/test_rmt_filter.py
git commit -m "RMT filtering — Marchenko-Pastur eigenvalue clipping with trace preservation"
```

---

## Task 4: Network Construction Methods

**Files:**
- Create: `backend/app/services/network_builder.py`
- Create: `backend/tests/test_network_builder.py`

**Depends on:** Tasks 2, 3

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_network_builder.py
import numpy as np
import pandas as pd
from app.services.network_builder import (
    build_pearson_network,
    build_spearman_network,
    build_partial_correlation_network,
    build_graphical_lasso_network,
    build_granger_causality_network,
    correlation_to_network,
)
import networkx as nx


def _make_test_returns(n_assets=10, n_obs=200):
    """Generate synthetic correlated returns for testing."""
    np.random.seed(42)
    # create 3 latent factors to generate correlated returns
    factors = np.random.randn(n_obs, 3)
    loadings = np.random.randn(n_assets, 3)
    noise = np.random.randn(n_assets) * 0.5
    returns = factors @ loadings.T + noise
    tickers = [f"ASSET_{i}" for i in range(n_assets)]
    return pd.DataFrame(returns, columns=tickers)


def test_pearson_produces_network():
    """Pearson method should return a networkx Graph."""
    returns = _make_test_returns()
    G = build_pearson_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10
    assert len(G.edges) > 0


def test_spearman_produces_network():
    returns = _make_test_returns()
    G = build_spearman_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10


def test_partial_correlation_produces_network():
    returns = _make_test_returns()
    G = build_partial_correlation_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10


def test_graphical_lasso_produces_network():
    returns = _make_test_returns()
    G = build_graphical_lasso_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10


def test_granger_produces_directed_network():
    """Granger causality should return a DiGraph (directed)."""
    returns = _make_test_returns()
    G = build_granger_causality_network(returns, max_lag=2)
    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) == 10


def test_correlation_to_network_top_k():
    """Top-k mode should keep at most k edges per node."""
    corr = np.eye(5)
    corr[0, 1] = corr[1, 0] = 0.9
    corr[0, 2] = corr[2, 0] = 0.8
    corr[0, 3] = corr[3, 0] = 0.7
    corr[0, 4] = corr[4, 0] = 0.6
    G = correlation_to_network(corr, ["A", "B", "C", "D", "E"], mode="top_k", k=2)
    # node A should have at most 2 edges
    assert G.degree("A") <= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_network_builder.py -v`
Expected: FAIL with "cannot import name 'build_pearson_network'"

- [ ] **Step 3: Implement network_builder.py**

```python
# backend/app/services/network_builder.py
"""
Network construction from financial return data.

Each method produces a weighted graph where:
- Nodes = assets
- Edges = relationships (correlation, causality, etc.)
- Edge weight = strength of relationship

The comparison between methods is the interesting part —
which one captures what? That's the research question.
"""

import numpy as np
import pandas as pd
import networkx as nx
from sklearn.covariance import GraphicalLassoCV
from statsmodels.tsa.stattools import grangercausalitytests


def correlation_to_network(
    corr: np.ndarray,
    tickers: list[str],
    mode: str = "top_k",
    k: int = 10,
    threshold: float = 0.3,
) -> nx.Graph:
    """
    Convert a correlation matrix to a networkx Graph.

    Two modes:
    - top_k: keep at most k edges per node (sorted by weight)
    - threshold: keep edges where |weight| > threshold

    We use absolute values for edge weights because negative
    correlations are just as informative as positive ones —
    two assets moving in opposite directions is a real relationship.
    """
    n = len(tickers)
    G = nx.Graph()
    G.add_nodes_from(tickers)

    # collect all edges with weights
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            w = corr[i, j]
            if abs(w) > 1e-10:  # skip zeros
                edges.append((tickers[i], tickers[j], abs(w), w))

    if mode == "top_k":
        # for each node, keep only its k strongest connections
        # this is more selective than a global threshold
        node_edges = {t: [] for t in tickers}
        for src, dst, abs_w, raw_w in edges:
            node_edges[src].append((abs_w, dst, raw_w))
            node_edges[dst].append((abs_w, src, raw_w))

        selected = set()
        for node in tickers:
            node_edges[node].sort(reverse=True)
            for abs_w, neighbor, raw_w in node_edges[node][:k]:
                edge_key = tuple(sorted([node, neighbor]))
                selected.add((edge_key[0], edge_key[1], raw_w))

        for src, dst, w in selected:
            G.add_edge(src, dst, weight=w)

    elif mode == "threshold":
        for src, dst, abs_w, raw_w in edges:
            if abs_w > threshold:
                G.add_edge(src, dst, weight=raw_w)

    return G


def build_pearson_network(returns: pd.DataFrame, **kwargs) -> nx.Graph:
    """
    Build network from Pearson correlation.

    Pearson correlation measures linear co-movement:
        ρ_ij = Cov(r_i, r_j) / (σ_i σ_j)

    This is the baseline — the simplest and most common method.
    Limitation: only captures linear relationships, and the
    empirical correlation matrix is heavily noise-dressed.
    """
    corr = returns.corr().values
    return correlation_to_network(corr, list(returns.columns), **kwargs)


def build_spearman_network(returns: pd.DataFrame, **kwargs) -> nx.Graph:
    """
    Build network from Spearman rank correlation.

    Spearman measures monotonic dependence using ranks instead of
    raw values. More robust to outliers and non-normality.

    Financial returns have fat tails (leptokurtic), so Pearson
    can be misleading. Spearman is a simple improvement.
    """
    from scipy.stats import spearmanr

    # spearmanr returns correlation matrix and p-value matrix
    corr, _ = spearmanr(returns.values)
    # for a single pair, spearmanr returns a scalar, so handle that
    if isinstance(corr, float):
        corr = np.array([[1.0, corr], [corr, 1.0]])
    return correlation_to_network(corr, list(returns.columns), **kwargs)


def build_partial_correlation_network(returns: pd.DataFrame, **kwargs) -> nx.Graph:
    """
    Build network from partial correlations.

    Partial correlation between i and j, conditioning on all other
    variables, is derived from the precision matrix (inverse covariance):

        ρ̃_ij = -Θ_ij / √(Θ_ii * Θ_jj)

    where Θ = Σ⁻¹.

    The key insight: if A and B are correlated only because both
    correlate with C, the partial correlation between A and B is ~0.
    This removes indirect connections that Pearson can't distinguish.

    For world stock networks, this makes USA, Germany, Japan emerge
    as clear hubs — which matches economic reality better than
    Pearson MSTs. (See Millington & Niranjan, J. Applied Network Science, 2020)
    """
    cov = returns.cov().values
    # add small regularization to make matrix invertible
    # (empirical covariance can be singular when N > T)
    reg = 1e-6 * np.eye(cov.shape[0])
    prec = np.linalg.inv(cov + reg)

    # convert precision matrix to partial correlations
    # formula: ρ̃_ij = -Θ_ij / √(Θ_ii * Θ_jj)
    d = np.sqrt(np.diag(prec))
    # avoid division by zero
    d[d < 1e-10] = 1e-10
    partial_corr = -prec / np.outer(d, d)
    np.fill_diagonal(partial_corr, 1.0)
    partial_corr = np.clip(partial_corr, -1, 1)

    return correlation_to_network(partial_corr, list(returns.columns), **kwargs)


def build_graphical_lasso_network(returns: pd.DataFrame, **kwargs) -> nx.Graph:
    """
    Build network using Graphical Lasso.

    GLasso estimates a sparse precision matrix by adding an L1
    penalty to the log-likelihood:

        max log det(Θ) - tr(SΘ) - α||Θ||₁

    where S is the sample covariance and α controls sparsity.

    The result: most partial correlations are driven to exactly 0,
    leaving only the strongest direct relationships. This produces
    cleaner, more interpretable networks than raw partial correlation.

    sklearn's GraphicalLassoCV cross-validates α automatically.
    """
    model = GraphicalLassoCV(cv=5, random_state=42)
    model.fit(returns.values)

    prec = model.precision_
    d = np.sqrt(np.diag(prec))
    d[d < 1e-10] = 1e-10
    partial_corr = -prec / np.outer(d, d)
    np.fill_diagonal(partial_corr, 1.0)
    partial_corr = np.clip(partial_corr, -1, 1)

    return correlation_to_network(partial_corr, list(returns.columns), **kwargs)


def build_granger_causality_network(
    returns: pd.DataFrame,
    max_lag: int = 5,
    significance: float = 0.05,
    **kwargs,
) -> nx.Graph:
    """
    Build directed network from Granger causality.

    X Granger-causes Y if lagged values of X help predict Y
    beyond Y's own lags. We test this pairwise and keep
    statistically significant relationships.

    This gives us a DIRECTED graph — edges have arrows.
    A → B means "A helps predict B", not the reverse.

    The Helmholtz-Hodge-Kodaira decomposition can further
    split this into gradient (hierarchical) and rotational
    (cyclic) components. That's a nice extension for later.
    (See Wand, Kamps & Iyetomi, arXiv:2408.12839, 2024)
    """
    tickers = list(returns.columns)
    n = len(tickers)
    G = nx.DiGraph()
    G.add_nodes_from(tickers)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            # test: does column i Granger-cause column j?
            # grangercausalitytests expects a 2-column array
            try:
                data = returns.iloc[:, [i, j]].dropna().values
                result = grangercausalitytests(data, maxlag=max_lag, verbose=False)

                # check if any lag is significant
                for lag in range(1, max_lag + 1):
                    p_value = result[lag][0]["ssr_ftest"][1]
                    if p_value < significance:
                        # use the F-statistic as edge weight
                        f_stat = result[lag][0]["ssr_ftest"][0]
                        G.add_edge(tickers[i], tickers[j], weight=f_stat, p_value=p_value)
                        break  # keep the first significant lag

            except Exception:
                # some pairs may fail (e.g. constant series), skip them
                continue

    return G
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_network_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/network_builder.py backend/tests/test_network_builder.py
git commit -m "5 network construction methods — pearson, spearman, partial, gllasso, granger"
```

---

## Task 5: Network Analysis

**Files:**
- Create: `backend/app/services/analysis.py`
- Create: `backend/tests/test_analysis.py`

**Depends on:** Task 4

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_analysis.py
import networkx as nx
from app.services.analysis import compute_centrality, detect_communities, compute_systemic_importance


def _make_test_graph():
    """Create a simple test graph with known structure."""
    G = nx.Graph()
    # hub node connected to everyone
    G.add_edges_from([
        ("HUB", "A", {"weight": 0.8}),
        ("HUB", "B", {"weight": 0.7}),
        ("HUB", "C", {"weight": 0.6}),
        ("HUB", "D", {"weight": 0.5}),
        ("A", "B", {"weight": 0.3}),
    ])
    return G


def test_centrality_returns_dict():
    G = _make_test_graph()
    result = compute_centrality(G)
    assert isinstance(result, dict)
    assert "HUB" in result
    assert "degree" in result["HUB"]
    assert "betweenness" in result["HUB"]
    assert "eigenvector" in result["HUB"]
    assert "pagerank" in result["HUB"]


def test_hub_has_highest_centrality():
    G = _make_test_graph()
    result = compute_centrality(G)
    # HUB should have highest degree centrality (connected to 4 nodes)
    assert result["HUB"]["degree"] > result["A"]["degree"]


def test_communities_returns_list():
    G = _make_test_graph()
    communities = detect_communities(G)
    assert isinstance(communities, dict)
    assert "num_communities" in communities
    assert "assignment" in communities


def test_systemic_importance_returns_dict():
    G = _make_test_graph()
    result = compute_systemic_importance(G)
    assert isinstance(result, dict)
    assert "HUB" in result
    assert "score" in result["HUB"]
    assert "percentile" in result["HUB"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_analysis.py -v`
Expected: FAIL with "cannot import name 'compute_centrality'"

- [ ] **Step 3: Implement analysis.py**

```python
# backend/app/services/analysis.py
"""
Network analysis metrics.

Computes centrality measures, community structure, and a composite
systemic importance score for each node in the network.

The physics connection: eigenvector centrality is essentially the
principal eigenvector of the adjacency matrix — same mathematics
as finding the dominant mode in a vibrating system.
"""

import networkx as nx
from networkx.algorithms.community import louvain_communities
import numpy as np


def compute_centrality(G: nx.Graph) -> dict:
    """
    Compute centrality metrics for every node.

    Returns a dict: {node: {degree, betweenness, eigenvector, pagerank}}

    Degree: fraction of nodes this node is connected to.
            Simple but informative — high degree = many direct connections.

    Betweenness: fraction of shortest paths that pass through this node.
                 High betweenness = bridge/bottleneck. This node controls
                 information flow between different parts of the network.

    Eigenvector: connection to other important nodes.
                 Not just "who do you know" but "who do your contacts know."
                 Mathematically: the principal eigenvector of the adjacency matrix.
                 Same as PageRank with damping=1.

    PageRank: random walk centrality. If you start a random walk on the
              network, how likely are you to visit this node? Includes
              a damping factor (default 0.85) so the walk doesn't get stuck.
    """
    # eigenvector centrality can fail to converge on some graphs,
    # so we wrap it in a try/except
    try:
        eig_centrality = nx.eigenvector_centrality(G, max_iter=1000, weight="weight")
    except nx.PowerIterationFailedConvergence:
        eig_centrality = {n: 0.0 for n in G.nodes()}

    degree_centrality = nx.degree_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G, weight="weight")
    pagerank = nx.pagerank(G, weight="weight")

    result = {}
    for node in G.nodes():
        result[node] = {
            "degree": degree_centrality.get(node, 0.0),
            "betweenness": betweenness_centrality.get(node, 0.0),
            "eigenvector": eig_centrality.get(node, 0.0),
            "pagerank": pagerank.get(node, 0.0),
        }

    return result


def detect_communities(G: nx.Graph) -> dict:
    """
    Detect communities using the Louvain method.

    Louvain optimizes modularity Q, which measures how much more
    densely connected nodes are within communities compared to
    what you'd expect from a random graph.

    Q = (1/2m) Σ_ij [A_ij - k_i k_j / (2m)] δ(c_i, c_j)

    where A_ij is adjacency, k_i is degree, m is total edges,
    and δ(c_i, c_j) = 1 if i,j are in the same community.

    If communities map to real sectors (tech, finance, etc.)
    without being told, that's a strong result.
    """
    communities_list = louvain_communities(G, weight="weight", resolution=1, seed=42)

    assignment = {}
    for idx, community in enumerate(communities_list):
        for node in community:
            assignment[node] = idx

    return {
        "num_communities": len(communities_list),
        "assignment": assignment,
        "sizes": [len(c) for c in communities_list],
    }


def compute_systemic_importance(G: nx.Graph) -> dict:
    """
    Compute a composite systemic importance score per node.

    The score combines:
    - Eigenvector centrality (connection to important nodes)
    - Betweenness centrality (bridge/bottleneck role)
    - Degree centrality (number of direct connections)
    - Community size (larger community = more systemic exposure)

    Each component is normalized to [0, 1] across all nodes,
    then averaged. The result is a percentile ranking.

    This is analogous to an order parameter in statistical
    mechanics — a single number that captures the "importance"
    of a node in the system.
    """
    centrality = compute_centrality(G)
    communities = detect_communities(G)

    # normalize each metric to [0, 1]
    def normalize(values: dict) -> dict:
        vals = list(values.values())
        min_val = min(vals)
        max_val = max(vals)
        if max_val - min_val < 1e-10:
            return {k: 0.0 for k in values}
        return {k: (v - min_val) / (max_val - min_val) for k, v in values.items()}

    eig_norm = normalize({n: c["eigenvector"] for n, c in centrality.items()})
    bet_norm = normalize({n: c["betweenness"] for n, c in centrality.items()})
    deg_norm = normalize({n: c["degree"] for n, c in centrality.items()})

    # community size factor: nodes in larger communities get a boost
    community_size = {}
    for node, comm_id in communities["assignment"].items():
        community_size[node] = communities["sizes"][comm_id]
    comm_norm = normalize(community_size)

    # composite score: equal weights
    result = {}
    scores = {}
    for node in G.nodes():
        score = (
            0.3 * eig_norm[node]
            + 0.3 * bet_norm[node]
            + 0.25 * deg_norm[node]
            + 0.15 * comm_norm[node]
        )
        scores[node] = score

    # convert to percentiles
    sorted_nodes = sorted(scores.keys(), key=lambda n: scores[n])
    n = len(sorted_nodes)
    for rank, node in enumerate(sorted_nodes):
        result[node] = {
            "score": scores[node],
            "percentile": round(rank / n * 100, 1),
        }

    return result
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analysis.py backend/tests/test_analysis.py
git commit -m "network analysis — centrality metrics, Louvain communities, systemic importance score"
```

---

## Task 6: Monte Carlo Stress Testing

**Files:**
- Create: `backend/app/services/simulation.py`
- Create: `backend/tests/test_simulation.py`

**Depends on:** Task 4

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_simulation.py
import networkx as nx
import numpy as np
from app.services.simulation import run_stress_test


def _make_test_network():
    G = nx.Graph()
    G.add_edges_from([
        ("NVDA", "AMD", {"weight": 0.8}),
        ("NVDA", "QQQ", {"weight": 0.5}),
        ("AMD", "QQQ", {"weight": 0.4}),
    ])
    return G


def test_stress_test_returns_results():
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-0.2, n_sims=1000)
    assert "NVDA" in results  # shocked asset should be in results
    assert "AMD" in results
    assert "QQQ" in results
    assert "median" in results["AMD"]
    assert "ci_95" in results["AMD"]
    assert "prob_negative" in results["AMD"]


def test_stress_test_shock_propagates_proportionally():
    """Stronger connections should produce larger responses."""
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-0.2, n_sims=5000)

    # AMD has weight 0.8 to NVDA, QQQ has weight 0.5
    # so AMD should have a larger median response (more negative)
    assert results["AMD"]["median"] < results["QQQ"]["median"]


def test_stress_test_confidence_intervals():
    """95% CI should bracket the median."""
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-0.2, n_sims=5000)
    for asset, data in results.items():
        assert data["ci_95"][0] <= data["median"] <= data["ci_95"][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_simulation.py -v`
Expected: FAIL with "cannot import name 'run_stress_test'"

- [ ] **Step 3: Implement simulation.py**

```python
# backend/app/services/simulation.py
"""
Monte Carlo stress testing for financial networks.

Given a shock to one asset, we simulate how it propagates
through the network based on the dependency structure.

Model: linear threshold
    response_j = weight_ij * shock_i + ε

where ε ~ N(0, σ²_residual) captures unexplained variance.

This is the simplest credible propagation model. More sophisticated
approaches (DebtRank, fire-sale amplification) require balance sheet
data we don't have. For a supporting project, this is the right level.

Physics analogy: this is a perturbation analysis of a coupled system.
Each asset is a node with coupling strengths defined by edge weights.
The shock is a perturbation, and we observe the system's response.
"""

import numpy as np
import networkx as nx


def run_stress_test(
    G: nx.Graph,
    shock_asset: str,
    shock_magnitude: float,
    n_sims: int = 10000,
    noise_std: float = 0.02,
) -> dict:
    """
    Run Monte Carlo stress test on the network.

    For each simulation:
    1. For each asset connected to the shock asset:
       response = weight * shock_magnitude + noise
    2. For assets not directly connected but reachable through
       intermediate nodes: propagate through the path

    We use a single-hop model for simplicity: only directly
    connected assets respond. Multi-hop propagation would require
    path-finding and is a natural extension.

    Parameters
    ----------
    G : nx.Graph
        Network with edge weights
    shock_asset : str
        Node to shock
    shock_magnitude : float
        e.g. -0.2 for a 20% drop
    n_sims : int
        Number of Monte Carlo simulations
    noise_std : float
        Standard deviation of the noise term.
        This represents unexplained variance — the part of
        each asset's movement that isn't explained by the
        network dependency. Default 2%.

    Returns
    -------
    dict
        {asset: {median, ci_95, prob_negative}}
    """
    neighbors = list(G.neighbors(shock_asset))
    results = {}

    for neighbor in neighbors:
        weight = G.edges[shock_asset, neighbor].get("weight", 0.0)

        # generate n_sims responses
        # deterministic component: weight * shock
        # stochastic component: Gaussian noise
        responses = weight * shock_magnitude + np.random.normal(0, noise_std, n_sims)

        results[neighbor] = {
            "median": float(np.median(responses)),
            "ci_95": [
                float(np.percentile(responses, 2.5)),
                float(np.percentile(responses, 97.5)),
            ],
            "prob_negative": float(np.mean(responses < 0)),
        }

    # also include the shocked asset itself (100% response)
    results[shock_asset] = {
        "median": shock_magnitude,
        "ci_95": [shock_magnitude, shock_magnitude],
        "prob_negative": 1.0 if shock_magnitude < 0 else 0.0,
    }

    return results
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_simulation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/simulation.py backend/tests/test_simulation.py
git commit -m "Monte Carlo stress testing — linear threshold propagation with noise"
```

---

## Task 7: FastAPI Endpoints

**Files:**
- Create: `backend/app/routers/networks.py`
- Create: `backend/app/routers/stress_test.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/models/schemas.py`

**Depends on:** Tasks 2-6

- [ ] **Step 1: Create Pydantic schemas**

```python
# backend/app/models/schemas.py
from pydantic import BaseModel


class NetworkBuildRequest(BaseModel):
    assets: list[str]
    method: str  # pearson, spearman, partial_correlation, graphical_lasso, granger
    period: str = "2y"
    top_k: int = 10
    use_rmt: bool = False


class StressTestRequest(BaseModel):
    assets: list[str]
    method: str = "pearson"
    period: str = "2y"
    shock_asset: str
    shock_magnitude: float = -0.2
    n_sims: int = 10000
```

- [ ] **Step 2: Create networks router**

```python
# backend/app/routers/networks.py
from fastapi import APIRouter
from app.models.schemas import NetworkBuildRequest
from app.services.data_fetcher import fetch_prices, get_returns
from app.services.network_builder import (
    build_pearson_network,
    build_spearman_network,
    build_partial_correlation_network,
    build_graphical_lasso_network,
    build_granger_causality_network,
)
from app.services.rmt_filter import filter_correlation_matrix
from app.services.analysis import compute_centrality, detect_communities, compute_systemic_importance
import networkx as nx
import numpy as np

router = APIRouter(prefix="/api/networks", tags=["networks"])

METHOD_MAP = {
    "pearson": build_pearson_network,
    "spearman": build_spearman_network,
    "partial_correlation": build_partial_correlation_network,
    "graphical_lasso": build_graphical_lasso_network,
    "granger": build_granger_causality_network,
}


def graph_to_json(G: nx.Graph) -> dict:
    """Convert networkx graph to JSON-serializable dict."""
    nodes = []
    for node in G.nodes():
        nodes.append({"id": node})

    edges = []
    for src, dst, data in G.edges(data=True):
        edges.append({
            "source": src,
            "target": dst,
            "weight": data.get("weight", 0.0),
        })

    return {"nodes": nodes, "edges": edges}


@router.post("/build")
def build_network(req: NetworkBuildRequest):
    """Build a financial network using the specified method."""
    prices = fetch_prices(req.assets, req.period)
    returns = get_returns(prices)

    build_fn = METHOD_MAP.get(req.method)
    if not build_fn:
        return {"error": f"Unknown method: {req.method}. Choose from {list(METHOD_MAP.keys())}"}

    if req.method == "granger":
        G = build_fn(returns)
    else:
        G = build_fn(returns, top_k=req.top_k)

    # optionally apply RMT filtering before network construction
    if req.use_rmt and req.method in ("pearson", "spearman", "partial_correlation"):
        corr = returns.corr().values
        filtered = filter_correlation_matrix(corr, len(returns))
        from app.services.network_builder import correlation_to_network
        G = correlation_to_network(filtered, list(returns.columns), top_k=req.top_k)

    centrality = compute_centrality(G)
    communities = detect_communities(G)
    systemic = compute_systemic_importance(G)

    return {
        "network": graph_to_json(G),
        "metrics": {
            "density": nx.density(G),
            "num_edges": G.number_of_edges(),
            "num_nodes": G.number_of_nodes(),
        },
        "centrality": centrality,
        "communities": communities,
        "systemic_importance": systemic,
        "method": req.method,
    }
```

- [ ] **Step 3: Create stress test router**

```python
# backend/app/routers/stress_test.py
from fastapi import APIRouter
from app.models.schemas import StressTestRequest
from app.services.data_fetcher import fetch_prices, get_returns
from app.services.network_builder import (
    build_pearson_network,
    build_spearman_network,
    build_partial_correlation_network,
    build_graphical_lasso_network,
    build_granger_causality_network,
)
from app.services.simulation import run_stress_test

router = APIRouter(prefix="/api/stress-test", tags=["stress-test"])

METHOD_MAP = {
    "pearson": build_pearson_network,
    "spearman": build_spearman_network,
    "partial_correlation": build_partial_correlation_network,
    "graphical_lasso": build_graphical_lasso_network,
    "granger": build_granger_causality_network,
}


@router.post("/run")
def run_simulation(req: StressTestRequest):
    """Run Monte Carlo stress test on the network."""
    prices = fetch_prices(req.assets, req.period)
    returns = get_returns(prices)

    build_fn = METHOD_MAP.get(req.method)
    if not build_fn:
        return {"error": f"Unknown method: {req.method}"}

    G = build_fn(returns)

    results = run_stress_test(
        G,
        shock_asset=req.shock_asset,
        shock_magnitude=req.shock_magnitude,
        n_sims=req.n_sims,
    )

    return {
        "results": results,
        "shock_asset": req.shock_asset,
        "shock_magnitude": req.shock_magnitude,
        "n_sims": req.n_sims,
    }
```

- [ ] **Step 4: Register routers in main.py**

Update `backend/app/main.py`:

```python
from app.routers import assets, networks, stress_test

app.include_router(assets.router)
app.include_router(networks.router)
app.include_router(stress_test.router)
```

- [ ] **Step 5: Test the API manually**

```bash
cd backend && uvicorn app.main:app --reload
# in another terminal:
curl -X POST http://localhost:8000/api/networks/build \
  -H "Content-Type: application/json" \
  -d '{"assets": ["SPY","QQQ","NVDA","AMD","JPM"], "method": "pearson"}'
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "FastAPI endpoints — /api/networks/build, /api/stress-test/run, Pydantic schemas"
```

---

## Task 8: React Frontend Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`

**Depends on:** Task 7

- [ ] **Step 1: Initialize the Vite React project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install react-force-graph-2d recharts tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Configure Tailwind CSS**

Update `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Update `frontend/src/index.css`:

```css
@import "tailwindcss";
```

- [ ] **Step 3: Create API client**

```typescript
// frontend/src/api/client.ts
const API_BASE = '/api';

export interface NetworkResponse {
  network: {
    nodes: { id: string }[];
    edges: { source: string; target: string; weight: number }[];
  };
  metrics: {
    density: number;
    num_edges: number;
    num_nodes: number;
  };
  centrality: Record<string, {
    degree: number;
    betweenness: number;
    eigenvector: number;
    pagerank: number;
  }>;
  communities: {
    num_communities: number;
    assignment: Record<string, number>;
    sizes: number[];
  };
  systemic_importance: Record<string, {
    score: number;
    percentile: number;
  }>;
  method: string;
}

export interface StressTestResponse {
  results: Record<string, {
    median: number;
    ci_95: [number, number];
    prob_negative: number;
  }>;
  shock_asset: string;
  shock_magnitude: number;
  n_sims: number;
}

export async function buildNetwork(
  assets: string[],
  method: string,
  period: string = '2y',
  topK: number = 10,
  useRmt: boolean = false,
): Promise<NetworkResponse> {
  const res = await fetch(`${API_BASE}/networks/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assets, method, period, top_k: topK, use_rmt: useRmt }),
  });
  return res.json();
}

export async function runStressTest(
  assets: string[],
  shockAsset: string,
  shockMagnitude: number = -0.2,
  method: string = 'pearson',
  nSims: number = 10000,
): Promise<StressTestResponse> {
  const res = await fetch(`${API_BASE}/stress-test/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assets,
      method,
      shock_asset: shockAsset,
      shock_magnitude: shockMagnitude,
      n_sims: nSims,
    }),
  });
  return res.json();
}
```

- [ ] **Step 4: Create minimal App.tsx**

```tsx
// frontend/src/App.tsx
import { useState } from 'react'
import { buildNetwork, type NetworkResponse } from './api/client'

const DEFAULT_ASSETS = ['SPY', 'QQQ', 'NVDA', 'AMD', 'JPM', 'BAC', 'XOM', 'GLD', 'TLT']

function App() {
  const [data, setData] = useState<NetworkResponse | null>(null)
  const [method, setMethod] = useState('pearson')
  const [loading, setLoading] = useState(false)

  const handleBuild = async () => {
    setLoading(true)
    try {
      const result = await buildNetwork(DEFAULT_ASSETS, method)
      setData(result)
    } catch (err) {
      console.error('Failed to build network:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-4">ContagionLab</h1>
      <p className="text-gray-400 mb-8">
        Financial network analysis and systemic risk simulation
      </p>

      <div className="flex gap-4 mb-8">
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2"
        >
          <option value="pearson">Pearson Correlation</option>
          <option value="spearman">Spearman Rank</option>
          <option value="partial_correlation">Partial Correlation</option>
          <option value="graphical_lasso">Graphical Lasso</option>
          <option value="granger">Granger Causality</option>
        </select>

        <button
          onClick={handleBuild}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded px-4 py-2"
        >
          {loading ? 'Building...' : 'Build Network'}
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded p-4">
            <h3 className="text-sm text-gray-400">Nodes</h3>
            <p className="text-2xl">{data.metrics.num_nodes}</p>
          </div>
          <div className="bg-gray-800 rounded p-4">
            <h3 className="text-sm text-gray-400">Edges</h3>
            <p className="text-2xl">{data.metrics.num_edges}</p>
          </div>
          <div className="bg-gray-800 rounded p-4">
            <h3 className="text-sm text-gray-400">Density</h3>
            <p className="text-2xl">{data.metrics.density.toFixed(3)}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "frontend scaffold — Vite + React + TypeScript, API client, basic layout"
```

---

## Task 9: Network Visualization Component

**Files:**
- Create: `frontend/src/components/NetworkGraph.tsx`

**Depends on:** Task 8

- [ ] **Step 1: Create the NetworkGraph component**

```tsx
// frontend/src/components/NetworkGraph.tsx
import { useRef, useEffect } from 'react'
import type { NetworkResponse } from '../api/client'

// colors for communities — keep it simple, no need for 50 colors
const COMMUNITY_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#22c55e', // green
  '#f59e0b', // amber
  '#a855f7', // purple
  '#06b6d4', // cyan
  '#f97316', // orange
  '#ec4899', // pink
]

interface Props {
  data: NetworkResponse
}

export default function NetworkGraph({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !data) return

    // simple force-directed layout using vanilla canvas
    // react-force-graph-2d would be nicer but let's keep deps minimal
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height

    // initialize positions randomly
    const nodes = data.network.nodes.map((n) => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * 300,
      y: height / 2 + (Math.random() - 0.5) * 300,
      vx: 0,
      vy: 0,
    }))

    const nodeMap = new Map(nodes.map((n) => [n.id, n]))

    // simple force simulation
    const animate = () => {
      ctx.clearRect(0, 0, width, height)

      // repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x
          const dy = nodes[j].y - nodes[i].y
          const dist = Math.sqrt(dx * dx + dy * dy) + 1
          const force = 5000 / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          nodes[i].vx -= fx
          nodes[i].vy -= fy
          nodes[j].vx += fx
          nodes[j].vy += fy
        }
      }

      // attraction along edges
      for (const edge of data.network.edges) {
        const src = nodeMap.get(edge.source)
        const dst = nodeMap.get(edge.target)
        if (!src || !dst) continue
        const dx = dst.x - src.x
        const dy = dst.y - src.y
        const dist = Math.sqrt(dx * dx + dy * dy) + 1
        const force = (dist - 100) * 0.01
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        src.vx += fx
        src.vy += fy
        dst.vx -= fx
        dst.vy -= fy
      }

      // center gravity
      for (const node of nodes) {
        node.vx += (width / 2 - node.x) * 0.001
        node.vy += (height / 2 - node.y) * 0.001
        // damping
        node.vx *= 0.9
        node.vy *= 0.9
        node.x += node.vx
        node.y += node.vy
      }

      // draw edges
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)'
      ctx.lineWidth = 1
      for (const edge of data.network.edges) {
        const src = nodeMap.get(edge.source)
        const dst = nodeMap.get(edge.target)
        if (!src || !dst) continue
        ctx.beginPath()
        ctx.moveTo(src.x, src.y)
        ctx.lineTo(dst.x, dst.y)
        ctx.stroke()
      }

      // draw nodes
      for (const node of nodes) {
        const community = data.communities.assignment[node.id] ?? 0
        const color = COMMUNITY_COLORS[community % COMMUNITY_COLORS.length]
        const systemic = data.systemic_importance[node.id]
        const radius = 5 + (systemic?.percentile ?? 0) / 10

        ctx.beginPath()
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
        ctx.fillStyle = color
        ctx.fill()

        // label
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
        ctx.font = '10px monospace'
        ctx.fillText(node.id, node.x + radius + 3, node.y + 3)
      }

      requestAnimationFrame(animate)
    }

    const animId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animId)
  }, [data])

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={600}
      className="bg-gray-950 rounded border border-gray-700"
    />
  )
}
```

- [ ] **Step 2: Wire it into App.tsx**

Add import and render `<NetworkGraph data={data} />` in the App component.

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "network graph visualization — force-directed layout, community colors, node sizing"
```

---

## Task 10: Integration Test & README

**Files:**
- Modify: `README.md`
- Create: `backend/tests/test_integration.py`

**Depends on:** Tasks 1-9

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_integration.py
"""End-to-end test: build a network and run stress test."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_pipeline():
    # build network
    resp = client.post("/api/networks/build", json={
        "assets": ["SPY", "QQQ", "NVDA", "AMD"],
        "method": "pearson",
        "period": "1y",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "network" in data
    assert len(data["network"]["nodes"]) == 4

    # run stress test
    resp = client.post("/api/stress-test/run", json={
        "assets": ["SPY", "QQQ", "NVDA", "AMD"],
        "method": "pearson",
        "shock_asset": "NVDA",
        "shock_magnitude": -0.2,
        "n_sims": 1000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "NVDA" in data["results"]
```

- [ ] **Step 2: Run integration test**

Run: `cd backend && python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Write the full README**

```markdown
# ContagionLab

Financial network analysis and systemic risk simulation.

Models global financial markets as networks, identifies systemically
important assets, and simulates how financial shocks propagate.

## What this does

1. Takes a list of financial assets (stocks, ETFs, bonds)
2. Downloads their price history
3. Builds a network where edges represent statistical relationships
4. Computes centrality metrics and community structure
5. Runs Monte Carlo stress tests to simulate shock propagation

## Network construction methods

Five ways to define "relationship" between assets:

| Method | What it captures | Key difference |
|--------|-----------------|----------------|
| Pearson | Linear co-movement | Baseline — most common, but noisy |
| Spearman | Monotonic dependence | More robust to outliers |
| Partial | Direct relationships only | Removes indirect connections |
| Graphical Lasso | Sparse direct relationships | L1-regularized, cleaner networks |
| Granger Causality | Predictive relationships | Directed — "A helps predict B" |

## Random Matrix Theory filtering

Empirical correlation matrices are heavily contaminated by noise.
The Marchenko-Pastur law tells us what the eigenvalue distribution
should look like for a purely random matrix. We clip noise eigenvalues
before building networks.

This is a physics technique (developed in nuclear physics by Wigner,
applied to finance by Laloux et al. 1999) that gives us a principled
way to separate signal from noise.

## Running

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Limitations

- Statistical dependence does not establish causal contagion
- Linear threshold model is a simplification of real propagation mechanisms
- yfinance data has survivorship bias (delisted assets are missing)
- Granger causality requires long time series for reliable results
- RMT assumes i.i.d. observations (financial returns violate this)

## References

- Laloux, Cizeau, Bouchaud, Potters (1999). "Noise Dressing of Financial Correlation Matrices." Phys. Rev. Lett. 83, 1467.
- Mantegna, R.N. & Stanley, H.E. (2000). "An Introduction to Econophysics." Cambridge University Press.
- Caccioli, F. (2025). "Understanding Financial Contagion: A Complexity Modeling Perspective." arXiv:2502.14551.
- Millington, T. & Niranjan, M. (2020). "Partial correlation financial networks." Applied Network Science.
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "integration test + full README with limitations and references"
```

---

## Task 11: Merge to main

**Depends on:** Tasks 1-10

- [ ] **Step 1: Create integration branch and merge**

```bash
git checkout -b integration
git merge feat/data-layer --no-ff
git merge feat/rmt-filtering --no-ff
git merge feat/network-methods --no-ff
git merge feat/analysis --no-ff
git merge feat/stress-test --no-ff
git merge feat/api --no-ff
git merge feat/frontend --no-ff
```

- [ ] **Step 2: Run all tests**

```bash
cd backend && python -m pytest tests/ -v
```

- [ ] **Step 3: Merge integration to main**

```bash
git checkout main
git merge integration --no-ff
git tag v0.1.0
```

- [ ] **Step 4: Final commit message**

```
contagionlab v0.1.0 — full stack, 5 network methods, RMT filtering, Monte Carlo stress test
```
