# ContagionLab Design Spec

**Date:** 2026-08-28
**Author:** Alya Karim
**Status:** Approved for implementation

---

## 1. Overview

ContagionLab is a dynamic financial systemic-risk and shock-propagation engine. It models global financial markets as evolving networks, identifies systemically important assets, and simulates how financial shocks propagate across markets under different regimes.

**Project role:** Strong supporting project in portfolio (not flagship).

**Physics narrative:** Applied complex-systems thinking to financial markets — markets are interconnected systems where local shocks can generate nonlinear global effects. Random matrix theory (from nuclear/condensed matter physics) is used to filter noise from financial correlation matrices before network construction.

---

## 2. Goals & Non-Goals

### Goals
- Build financial networks using 5 different construction methods
- Compare methods to show which captures what
- Apply RMT filtering as a physics-native differentiator
- Compute centrality, community structure, and systemic importance
- Monte Carlo stress testing with interpretable distributions
- Full-stack: Python engine + FastAPI API + React/TypeScript frontend
- Demonstrate quantitative research thinking (hypotheses, methods, validation)

### Non-Goals (for v1)
- Crisis replay / historical episode reconstruction (Approach B)
- Composite fragility index (Approach C)
- Multiplex networks (equity + rates + FX + commodities)
- Agent-based modeling
- Real-time / streaming data
- Trading strategy generation

---

## 3. Architecture

### Three-layer design

```
┌─────────────────────────────────────────────┐
│              React + TypeScript              │
│  Interactive network visualization,          │
│  metric cards, comparison panels             │
└──────────────────┬──────────────────────────┘
                   │ REST API (JSON)
┌──────────────────▼──────────────────────────┐
│              FastAPI Backend                 │
│  /api/assets                                 │
│  /api/networks/build                         │
│  /api/networks/compare                       │
│  /api/stress-test/run                        │
│  /api/metrics/{asset_id}                     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Python Analysis Engine             │
│  contagionlab/                               │
│    ├── data/          (fetcher, cache)       │
│    ├── networks/      (construction methods) │
│    ├── filtering/     (RMT denoising)        │
│    ├── analysis/      (centrality, community)│
│    ├── simulation/    (Monte Carlo stress)   │
│    └── metrics/       (systemic importance)  │
└─────────────────────────────────────────────┘
```

### Data flow
1. User selects assets + method → API call
2. Backend fetches/caches price data (yfinance)
3. Compute returns → build correlation matrix
4. Optionally apply RMT filtering
5. Construct network (5 methods available)
6. Compute centrality metrics + community detection
7. Return network JSON + metrics to frontend
8. Frontend renders interactive graph

---

## 4. Network Construction Methods

| # | Method | Type | Python |
|---|---|---|---|
| 1 | Pearson correlation | Undirected, linear | `numpy.corrcoef` |
| 2 | Spearman rank correlation | Undirected, monotonic | `scipy.stats.spearmanr` |
| 3 | Partial correlation | Undirected, conditional | Precision matrix inversion |
| 4 | Graphical Lasso | Undirected, sparse | `sklearn.covariance.GraphicalLassoCV` |
| 5 | Granger causality | Directed, temporal | `statsmodels.tsa.stattools` |

### RMT Filtering (preprocessing)
Applies to methods 1-3 (correlation-based). Steps:
1. Compute eigenvalues of correlation matrix
2. Compute Marchenko-Pastur upper bound: λ₊ = σ²(1 + √(n/T))²
3. Replace all eigenvalues below λ₊ with their mean (trace-preserving)
4. Reconstruct denoised correlation matrix

### Edge construction
- Each method produces a weight
- Default: keep top-k edges per node (k = min(10, N-1) where N = number of assets)
- Alternative: threshold mode where user sets minimum |weight| (default 0.3)
- User selects mode and parameters via API

---

## 5. Network Analysis Metrics

### Centrality
- Degree centrality
- Betweenness centrality
- Eigenvector centrality
- PageRank

### Structural
- Network density
- Modularity (Louvain community detection)
- Average clustering coefficient
- Average path length
- Assortativity

### Systemic Importance Score
Composite per asset:
- Normalized eigenvector centrality
- Normalized betweenness centrality
- Normalized degree
- Sector connectivity count

Output: percentile ranking (0-100)

### Community Detection
Louvain method. If communities map to real sectors (tech, energy, finance) without being told, that's a strong validation result.

---

## 6. Stress Testing

### Model: Linear threshold + Monte Carlo
1. User selects: shock asset, shock magnitude (e.g., -20%), time horizon
2. Use dependency structure from chosen network method
3. Run 10,000 simulations
4. For each simulation: propagate shock through network using edge weights + Gaussian noise (σ = residual variance from dependency estimation)
5. Return distribution of responses per affected asset

### Output per asset
- Median conditional response
- 95% simulation interval [5th percentile, 95th percentile]
- Probability of negative response

### Physics analogy
Perturbation propagation through coupled oscillator system — each asset is a node with coupling strengths defined by network edges.

---

## 7. Data Layer

### Source
- yfinance (free, no API key)
- Cache to local parquet files

### Default asset universe (~50 assets)
- Tech: NVDA, AMD, MSFT, AAPL, GOOGL, META, AVGO
- Finance: JPM, BAC, GS, MS, C
- Energy: XOM, CVX, COP
- Commodities: GLD, USO, DBA
- Bonds: TLT, IEF, SHY, HYG
- Index ETFs: SPY, QQQ, IWM, XLF, XLE, SOXX

### User can customize asset list via API

---

## 8. Frontend (React + TypeScript)

### Views
1. **Network Graph** — Force-directed layout (vis.js or react-force-graph)
   - Node size = systemic importance
   - Edge thickness = correlation strength
   - Color = community (Louvain)
   - Click node → sidebar with metrics

2. **Comparison Panel** — Side-by-side of two methods
   - Same assets, same window, different construction
   - Edge overlap (Jaccard), centrality divergence

3. **Stress Test Panel** — Configure and run
   - Select shock asset, magnitude, horizon
   - Results as distribution plots

4. **Metric Dashboard** — Grid of metric cards
   - Network density, modularity, avg clustering
   - Systemic fragility score

---

## 9. API Endpoints

```
GET  /api/assets                          — list available assets
POST /api/networks/build                  — build network
POST /api/networks/compare                — compare two methods
POST /api/stress-test/run                 — run Monte Carlo
GET  /api/metrics/{asset_id}              — asset metrics
```

---

## 10. Tech Stack

### Backend
- Python 3.11+
- FastAPI + uvicorn
- numpy, scipy, pandas, polars (optional for speed)
- scikit-learn (GraphicalLassoCV)
- statsmodels (Granger causality)
- networkx (graph algorithms)
- yfinance (data)
- pyarrow/parquet (caching)

### Frontend
- React 18+ with TypeScript
- Vite (bundler)
- vis.js or react-force-graph-2d (network visualization)
- Recharts or D3 (distribution plots)
- Tailwind CSS (styling)

---

## 11. Project Structure

```
contagionlab/
├── backend/
│   ├── app/
│   │   ├── main.py              (FastAPI app)
│   │   ├── routers/
│   │   │   ├── assets.py
│   │   │   ├── networks.py
│   │   │   └── stress_test.py
│   │   ├── services/
│   │   │   ├── data_fetcher.py
│   │   │   ├── network_builder.py
│   │   │   ├── rmt_filter.py
│   │   │   ├── analysis.py
│   │   │   └── simulation.py
│   │   └── models/
│   │       └── schemas.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── superpowers/specs/
│       └── 2026-08-28-contagionlab-design.md
└── README.md
```

---

## 12. Key Differentiators (What makes this NOT a tutorial project)

1. **RMT filtering** — Physics-native noise reduction before network construction
2. **Method comparison** — Not just one network, but 5 methods compared head-to-head
3. **Partial correlation** — Removes indirect connections (most projects stop at Pearson)
4. **Directed networks** — Granger causality shows temporal precedence, not just correlation
5. **Uncertainty quantification** — Monte Carlo produces distributions, not point estimates
6. **Intellectual honesty** — README explicitly states: "does not claim statistical dependence establishes causal contagion"

---

## 13. Hypotheses to Test (Research Angle)

1. **H1:** Financial network density increases during market stress
2. **H2:** Assets with high pre-crisis centrality transmit larger shocks
3. **H3:** RMT-filtered networks produce more stable centrality rankings than raw correlation
4. **H4:** Partial correlation networks reveal more interpretable community structure
5. **H5:** Granger causality network connectivity spikes before major drawdowns

---

## 14. Code Style: Human, Not AI

This project must look like a physicist wrote it. Not a language model.

### Working comments
Every non-trivial function gets a comment block explaining the math. Not docstrings — inline reasoning. Show your work.

```python
# Example: RMT eigenvalue clipping
# The Marchenko-Pastur law says that for a random correlation matrix
# of N assets observed over T time steps, the eigenvalues of the noise
# bulk fall within [λ₋, λ₊] where:
#   λ₊ = σ²(1 + √(N/T))²
# Any eigenvalue above λ₊ is likely real signal, not noise.
# We clip the noise eigenvalues by replacing them with their mean.
# This preserves the trace (= N) so total variance is unchanged.
# Reference: Laloux et al., Phys. Rev. Lett. 83, 1467 (1999)
```

### Commit messages
Write them like a human. No "feat: add X", no conventional-commit格式. Write what you actually did.

```
implement RMT eigenvalue clipping for correlation matrices
fix edge case where N > T in graphical lasso
add comparison panel to frontend — still rough
```

### README
Write it like you're explaining to a colleague, not marketing a product. Include the limitations section prominently. Show the math. Reference the papers you drew from.

---

## 15. Git Branching Strategy

### Branch structure
```
main                          ← stable, deployable
├── feat/data-layer           ← yfinance fetcher + parquet cache
├── feat/rmt-filtering        ← Marchenko-Pastur denoising
├── feat/network-methods      ← Pearson, Spearman, partial, GLasso, Granger
├── feat/analysis             ← centrality, community, systemic importance
├── feat/stress-test          ← Monte Carlo simulation
├── feat/api                  ← FastAPI endpoints
├── feat/frontend             ← React + TypeScript
└── integration               ← merge feature branches here
```

### Workflow
1. Create feature branch from `main`
2. Work on that feature in isolation
3. Merge into `integration` when ready
4. `integration` merges into `main` when stable

### Commit frequency
Commit when you finish a logical unit of work — a function, a test, a component. Don't wait until it's "done."

---

## 16. Success Criteria

- [ ] 5 network construction methods implemented and producing distinct networks
- [ ] RMT filtering demonstrably reduces noise eigenvalues
- [ ] Community detection recovers known sector structure
- [ ] Monte Carlo stress test produces interpretable distributions with confidence intervals
- [ ] Frontend renders interactive network with clickable nodes
- [ ] API endpoints return valid JSON for all operations
- [ ] README is intellectually careful about limitations
- [ ] Code passes lint/typecheck
