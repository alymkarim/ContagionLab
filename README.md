# ContagionLab

ContagionLab is a financial contagion analysis tool that builds correlation networks from asset return data and simulates how shocks propagate through those networks. It lets you compare six network construction methods, apply Random Matrix Theory filtering to reduce noise, run Monte Carlo stress tests, replay historical crises, and monitor systemic fragility over time.

The project has a FastAPI backend that fetches market data via yfinance, builds networks using networkx, and serves results over HTTP. The frontend is a React + TypeScript app that renders an interactive force-directed graph, displays centrality metrics, and provides crisis analysis and fragility monitoring.

## Network Methods

ContagionLab supports six methods for constructing a correlation network from asset returns:

| Method | Type | What It Measures | Best For |
|---|---|---|---|
| **Pearson** | Undirected | Linear correlation between raw returns | Baseline comparison; fast and simple |
| **Spearman** | Undirected | Rank-based monotonic correlation | Heavy-tailed data; outlier robustness |
| **Partial Correlation** | Undirected | Direct pairwise dependence after controlling for all other assets | Removing spurious correlations from common factors |
| **Graphical Lasso** | Undirected | Sparse precision matrix via L1-regularized maximum likelihood | High-dimensional settings (many assets relative to observations) |
| **Granger Causality** | Directed | Whether asset A helps predict asset B beyond B's own past | Temporal lead-lag relationships |
| **Tail Dependence** | Undirected | Probability of extreme co-movements (crashes together) | Hidden systemic risk — assets with low average correlation but high crash co-movement |

Each method produces a weighted graph where nodes are assets and edges encode the strength of the measured relationship. For the undirected methods, the `top_k` mode limits each node to at most *k* edges, keeping only the strongest connections.

**How to choose a method:** Pearson is a reasonable starting point. Switch to Spearman if your data has outliers or fat tails. Partial correlation and Graphical Lasso are better when you want to isolate direct relationships (they strip out effects mediated through third assets). Granger causality is the only directed method and is useful when you care about predictive timing rather than simultaneous co-movement. Tail dependence reveals hidden systemic risk — assets that don't move together on average but crash together during extremes.

## Crisis Replay

ContagionLab can replay historical market crises and show how the network topology changed. This validates the model — if the network looks "different" during crises, it's capturing real systemic risk.

Available crises:
- **2008 Global Financial Crisis** — Lehman Brothers collapse, global credit freeze
- **2020 COVID-19 Crash** — fastest bear market in history (34% in 23 trading days)
- **2022 Rate Hike Selloff** — Fed raises rates from 0% to 5.5%, tech stocks collapse

For each crisis, the tool shows three network phases:
1. **Pre-crisis** — baseline network topology before the event
2. **During crisis** — how correlations spiked and the network densified
3. **Post-crisis** — recovery and return to normal

The comparison reveals whether the crisis produced the classic contagion signature: higher density, tighter clustering, and shorter path lengths.

## Fragility Index

The fragility index is a composite score that summarizes systemic health in a single number. It combines five components:

| Component | Weight | What It Measures |
|---|---|---|
| Network density | 0.25 | How connected assets are (more connections = more systemic risk) |
| Clustering coefficient | 0.20 | Tightness of local cliques (concentrated risk) |
| Average path length | 0.20 | How fast shocks can propagate (shorter = faster contagion) |
| Spectral gap | 0.15 | Algebraic connectivity (smaller = more fragile) |
| Volatility | 0.20 | Average return uncertainty |

The index is computed over a rolling window (default 60 days) and provides:
- **Current fragility score** (0-1)
- **Regime classification** — resilient, normal, or stressed
- **Trend** — increasing, stable, or decreasing

Physics analogy: this is like an order parameter for a spin system — a single number capturing the collective behavior of many interacting components.

Real-world correlation matrices are noisy. When you estimate correlations from finite samples, many eigenvalues reflect sampling noise rather than genuine co-movements. Random Matrix Theory (RMT) provides a principled way to separate signal from noise.

The approach, introduced by Laloux et al. (1999), works as follows:

1. Compute the eigenvalue spectrum of the sample correlation matrix.
2. The Marchenko-Pastur law gives an upper bound for eigenvalues that could arise from pure noise: λ₊ = (1 + √(N/T))², where N is the number of assets and T is the number of observations.
3. Eigenvalues below λ₊ are replaced by their average (the mean of the noise eigenvalues). This preserves the trace of the matrix (the sum of eigenvalues equals N), keeping it a valid correlation matrix.
4. Eigenvalues above λ₊ are kept unchanged — these carry genuine signal about asset co-movements.
5. The filtered correlation matrix is reconstructed from the modified eigenvalues and eigenvectors.

You can toggle RMT filtering in the API with `use_rmt: true`. It applies to all correlation-based methods (Pearson, Spearman, Partial Correlation, Graphical Lasso) but not to Granger causality, which operates on a different principle.

## Running the Project

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the test suite
python -m pytest tests/ -v

# Start the API server
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. API docs are at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend

npm install
npm run dev
```

The dev server starts at `http://localhost:5173` and proxies API requests to the backend.

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/assets` | List available tickers grouped by sector |
| POST | `/api/networks/build` | Build a correlation network and return graph + metrics |
| POST | `/api/stress-test/run` | Build a network and run Monte Carlo stress propagation |
| GET | `/api/crisis/list` | List available historical crises |
| POST | `/api/crisis/analyze` | Run crisis replay analysis (pre/during/post networks) |
| POST | `/api/fragility/compute` | Compute rolling fragility index over time |

#### POST /api/networks/build

```json
{
  "assets": ["SPY", "QQQ", "TLT", "GLD"],
  "method": "pearson",
  "period": "1y",
  "top_k": 3,
  "use_rmt": false
}
```

Returns the graph (nodes, edges) plus centrality metrics, community detection results, and systemic importance scores.

#### POST /api/stress-test/run

```json
{
  "assets": ["SPY", "QQQ", "TLT", "GLD"],
  "method": "pearson",
  "period": "1y",
  "shock_asset": "SPY",
  "shock_magnitude": -0.2,
  "n_sims": 1000
}
```

Returns per-asset stress test results: median response, 95% confidence interval, and probability of negative outcome.

## Limitations

These are real constraints, not future roadmap items:

- **Single-step propagation only.** The stress test propagates shocks one hop: only direct neighbours of the shocked asset are affected. Multi-step cascading (shock → neighbour → neighbour's neighbour) is not modelled.
- **Linear threshold model.** The transmission equation x_j = w * shock + noise assumes a linear relationship between edge weight and shock transmission. Real contagion is often nonlinear — correlations spike during crises (the "correlation breakdown" problem).
- **Static network.** The network is built from a fixed historical window. It does not update in real time or adapt to changing market conditions.
- **No transaction costs or market microstructure.** The stress test is a theoretical model. It does not account for liquidity, bid-ask spreads, or position limits.
- **yfinance rate limits.** The data source (Yahoo Finance via yfinance) can throttle or block requests if you hit it too hard. Cached responses are reused for 24 hours.
- **Granger causality requires long time series.** With short periods (e.g. 5 days), the F-tests in Granger causality are unreliable. Use longer windows (6mo+) for this method.
- **Graphical Lasso assumes Gaussianity.** The L1-regularized estimator fits a Gaussian graphical model. Non-Gaussian tails are not captured.
- **RMT filtering is approximate.** The Marchenko-Pastur bound is exact only in the limit N, T → ∞ with N/T fixed. For small sample sizes, the noise/signal separation is approximate.
- **No portfolio optimisation.** This tool analyses network structure and contagion risk. It does not suggest portfolio weights or hedging strategies.

## Project Structure

```
contagionlab/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── models/schemas.py    # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── networks.py      # POST /api/networks/build
│   │   │   ├── stress_test.py   # POST /api/stress-test/run
│   │   │   ├── crisis.py        # GET /api/crisis/list, POST /api/crisis/analyze
│   │   │   ├── fragility.py     # POST /api/fragility/compute
│   │   │   └── assets.py        # GET /api/assets
│   │   └── services/
│   │       ├── data_fetcher.py     # yfinance data fetching + parquet cache
│   │       ├── network_builder.py  # 6 network construction methods
│   │       ├── rmt_filter.py       # Random Matrix Theory filtering
│   │       ├── simulation.py       # Monte Carlo stress test engine
│   │       ├── analysis.py         # Centrality, communities, systemic importance
│   │       ├── tail_dependence.py  # Copula-based tail dependence
│   │       ├── crisis_replay.py    # Historical crisis analysis
│   │       └── fragility.py        # Rolling fragility index
│   ├── tests/                   # 27 tests (unit + integration)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main UI with input, results, crisis, fragility
│   │   ├── api/client.ts        # API client functions
│   │   └── components/
│   │       ├── NetworkGraph.tsx      # Force-directed graph visualization
│   │       ├── MetricsPanel.tsx      # Centrality, communities, systemic importance
│   │       ├── StressTestPanel.tsx   # Shock selector + magnitude slider
│   │       ├── StressTestResults.tsx # Bar chart with CI whiskers
│   │       ├── CrisisReplay.tsx      # Crisis selector + pre/during/post comparison
│   │       ├── FragilityGauge.tsx    # Fragility score + regime + sparkline
│   │       └── MiniNetworkGraph.tsx  # Lightweight graph for crisis phases
│   └── package.json
└── README.md
```

## References

- Laloux, L., Cizeau, P., Bouchaud, J.-P., & Potters, M. (1999). "Random Matrix Theory of Financial Correlations." *Int. J. Theor. Appl. Finance*, 2, 391-397.
- Marcenko, V. A., & Pastur, L. A. (1967). "Distribution of Eigenvalues for Some Sets of Random Matrices." *Math. USSR-Sbornik*, 1, 457-483.
- Mantegna, R. N. (2000). "Hierarchical Structure in Financial Markets." *The European Physical Journal B*, 11, 193-197.
- Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models and Cross-spectral Methods." *Econometrica*, 37(3), 424-438.
- Friedman, J., Hastie, T., & Tibshirani, R. (2008). "Sparse Inverse Covariance Estimation with the Graphical Lasso." *Biostatistics*, 9(3), 432-441.
- Lauritzen, S. L. (1996). *Graphical Models*. Oxford University Press.
- Joe, H. (1997). *Multivariate Models and Dependence Concepts*. Chapman & Hall.
- Patton, A. J. (2006). "Modelling Asymmetric Exchange Rate Dependence." *International Economic Review*, 47(2), 527-556.
- Billio, M., Getmansky, M., Lo, A. W., & Pelizzon, L. (2012). "Measuring Systemic Risk in the Finance and Insurance Sectors." *Journal of Financial Economics*, 103(3), 535-559.
