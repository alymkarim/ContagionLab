# ContagionLab

ContagionLab is a financial contagion analysis tool that builds correlation networks from asset return data and simulates how shocks propagate through those networks. It lets you compare six network construction methods, apply Random Matrix Theory filtering to reduce noise, run Monte Carlo stress tests, replay historical crises, and monitor systemic fragility over time.

The project has a FastAPI backend that fetches market data via yfinance, builds networks using networkx, and serves results over HTTP. The frontend is a React + TypeScript app that renders an interactive force-directed graph, displays centrality metrics, and provides crisis analysis and fragility monitoring.

### Why "ContagionLab"?

In epidemiology, contagion describes how a disease spreads through a population: patient zero infects their contacts, who infect theirs, and so on. Financial markets work the same way. When one asset crashes, the shock spreads through the network of correlations to other assets. The stronger the connection, the faster and deeper the transmission.

"Contagion" captures what this tool measures: the spread of financial shocks across interconnected assets. "Lab" reflects what it is: a space to experiment, test hypotheses, and explore what happens under different conditions. You pick the assets, choose the method, simulate the crash, and observe the aftermath. That is the lab.

The term "systemic contagion" is also used in economics and policy circles (Billio et al. 2012, Battiston et al. 2012) to describe the failure of one institution triggering cascading failures across the financial system. The 2008 crisis was a textbook case: Lehman Brothers collapsed, and the contagion spread through counterparty relationships, credit markets, and correlated asset holdings until the entire system was at risk.

## Mathematical Foundations

### Correlation and Dependence

The starting point is measuring how assets move together. Given two asset return series $r_i$ and $r_j$, we need a number between -1 and 1 that captures their co-movement. This number is the correlation coefficient, and there are several ways to compute it.

**Pearson correlation** measures linear dependence:

$$\rho_{ij} = \frac{\text{Cov}(r_i, r_j)}{\sigma_i \sigma_j}$$

where $\text{Cov}(r_i, r_j) = \mathbb{E}[(r_i - \mu_i)(r_j - \mu_j)]$ is the covariance and $\sigma_i$, $\sigma_j$ are the standard deviations. Pearson correlation assumes returns are jointly Gaussian. If the relationship is nonlinear or the data has heavy tails, this measure breaks down.

**Spearman correlation** fixes the heavy tails problem by working with ranks instead of raw values. It converts each return series to its rank (1st smallest, 2nd smallest, ...) and then computes Pearson correlation on the ranks. This makes it robust to outliers and non-normal distributions. The formula is:

$$\rho_s = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$

where $d_i$ is the difference between the ranks of corresponding observations.

**Partial correlation** removes indirect connections. In a market, SPY and TLT might appear correlated simply because both are influenced by VIX. Partial correlation answers: "If we control for the effect of every other asset, are A and B still directly related?" Mathematically, it is derived from the precision matrix $\Omega = \Sigma^{-1}$, where $\Sigma$ is the covariance matrix. The partial correlation between assets $i$ and $j$ is:

$$\tilde{\rho}_{ij} = -\frac{\omega_{ij}}{\sqrt{\omega_{ii} \omega_{jj}}}$$

where $\omega_{ij}$ is the $(i,j)$ entry of the inverse covariance matrix. This is zero when $i$ and $j$ are conditionally independent given all other assets.

**Graphical Lasso** is a regularized version of partial correlation. When you have many assets relative to observations (e.g., 50 stocks with 252 daily returns), the sample covariance matrix is poorly conditioned and its inverse is unreliable. The Graphical Lasso adds an L1 penalty to the log-likelihood:

$$\hat{\Omega} = \arg\max_{\Omega \succ 0} \left[ \log \det \Omega - \text{tr}(S \Omega) - \lambda \|\Omega\|_1 \right]$$

where $S$ is the sample covariance matrix and $\lambda$ is the regularization parameter. The L1 penalty ($\|\Omega\|_1 = \sum_{i,j} |\omega_{ij}|$) forces many entries of the precision matrix to exactly zero, producing a sparse network where only the strongest direct relationships survive.

### Directed Relationships: Granger Causality

Correlation is symmetric (if A correlates with B, B correlates with A). But sometimes we want to know if A helps predict B. Granger causality tests this by running a regression:

$$r_B(t) = \alpha + \sum_{k=1}^{p} \beta_k r_B(t-k) + \sum_{k=1}^{p} \gamma_k r_A(t-k) + \epsilon_t$$

If the coefficients $\gamma_k$ are jointly significantly different from zero (tested via F-test), then A "Granger-causes" B: past values of A contain information about B's future that B's own past does not. This produces directed edges in the network, pointing from the predictor to the predicted.

### Tail Dependence: Measuring Crash Co-movement

Standard correlation measures average co-movement. But crises are about extreme co-movement. Two assets might have low average correlation (0.2) but high tail dependence: when one crashes, the other crashes too. This is the "hidden systemic risk" that standard correlation misses.

The lower tail dependence coefficient is defined as:

$$\lambda_L = \lim_{q \to 0} P\left(X_2 \leq F_2^{-1}(q) \mid X_1 \leq F_1^{-1}(q)\right)$$

In words: given that asset 1 is in its worst q% of returns, what is the probability that asset 2 is also in its worst q%? If $\lambda_L = 0$, the assets are independent in the tails. If $\lambda_L = 1$, they always crash together.

We estimate this empirically using the lower quadrant dependency: count how often both assets fall below their q-th percentile simultaneously, divided by how often each falls below it individually.

Copula theory (Joe, 1997; Patton, 2006) provides the formal framework. A copula separates the marginal distributions of each asset from their dependence structure. The Gaussian copula assumes a specific form for the dependence, but the empirical tail dependence estimate makes no distributional assumptions.

### Network Construction

Each method above produces an $N \times N$ matrix (correlation, partial correlation, tail dependence). To turn this into a network:

1. Each asset becomes a node.
2. Each pair $(i, j)$ gets an edge with weight equal to the matrix entry $\rho_{ij}$.
3. In `top_k` mode, each node keeps only its $k$ strongest edges, discarding weaker connections. This produces a sparse, interpretable network.

The resulting graph $G = (V, E)$ has $|V| = N$ nodes and $|E|$ weighted edges. The edge weight encodes relationship strength: thicker edges mean stronger co-movement.

### Network Analysis

Once the network is built, we compute several metrics:

**Centrality measures** identify the most important nodes:

- *Degree centrality*: number of connections. A highly connected asset is a hub.
- *Betweenness centrality*: how often a node lies on shortest paths between other nodes. A node with high betweenness is a bridge between clusters. If it fails, the network fragments.
- *Eigenvector centrality*: not just how many connections, but how important those connections are. A node connected to other important nodes scores higher.
- *PageRank*: a variant of eigenvector centrality that accounts for the direction and weight of edges. Originally designed for ranking web pages.

**Community detection** uses the Louvain algorithm, which optimizes modularity $Q$:

$$Q = \frac{1}{2|E|} \sum_{ij} \left[ A_{ij} - \frac{k_i k_j}{2|E|} \right] \delta(c_i, c_j)$$

where $A_{ij}$ is the adjacency matrix, $k_i$ is the degree of node $i$, and $\delta(c_i, c_j) = 1$ if nodes $i$ and $j$ are in the same community. The algorithm greedily merges communities to maximize $Q$. Higher modularity means the network has well-defined clusters: assets within a cluster are tightly connected, while assets across clusters are loosely connected.

**Systemic importance** is a composite score blending eigenvector centrality and community membership. An asset is systemically important if it is highly connected (centrality) and sits at the center of a large community.

### Random Matrix Theory Filtering

Real-world correlation matrices are noisy. When you estimate correlations from finite samples, many eigenvalues reflect sampling noise rather than genuine co-movements. Random Matrix Theory (RMT) provides a principled way to separate signal from noise.

The Marchenko-Pastur law (Marcenko and Pastur, 1967) gives the distribution of eigenvalues for a random matrix. If $X$ is an $N \times T$ matrix of i.i.d. random variables with zero mean and unit variance, the eigenvalues of $\frac{1}{T} X X^T$ fall in the interval:

$$\left[\left(1 - \sqrt{\frac{N}{T}}\right)^2, \left(1 + \sqrt{\frac{N}{T}}\right)^2\right]$$

In finance, $N$ is the number of assets and $T$ is the number of return observations. Eigenvalues above the upper bound $\lambda_+ = (1 + \sqrt{N/T})^2$ are statistically significant and carry genuine information about asset co-movements. Eigenvalues below $\lambda_+$ are consistent with pure noise.

The filtering procedure (Laloux et al., 1999):

1. Compute the eigenvalue decomposition of the sample correlation matrix: $C = U \Lambda U^T$.
2. Identify eigenvalues $\lambda_i < \lambda_+$.
3. Replace these noise eigenvalues with their average: $\tilde{\lambda}_i = \frac{1}{N_{\text{noise}}} \sum_{\lambda_j < \lambda_+} \lambda_j$.
4. Reconstruct the filtered correlation matrix: $\tilde{C} = U \tilde{\Lambda} U^T$.

This preserves the trace of the matrix (the sum of eigenvalues equals $N$), so it remains a valid correlation matrix. The noise eigenvalues are "folded" into the signal, reducing the dimensionality of the genuine co-movement space.

You can toggle RMT filtering with `use_rmt: true`. It applies to all correlation-based methods but not to Granger causality, which operates on a different principle.

### Monte Carlo Stress Testing

The stress test simulates how a shock in one asset propagates through the network. The model is a linear threshold propagation:

For each simulation $s = 1, \ldots, N_{\text{sim}}$:

1. Initialize all asset returns to zero.
2. Set the shocked asset's return to the specified magnitude: $r_{\text{shock}} = -0.2$ (a 20% drop).
3. For each neighbor $j$ of the shocked asset, transmit a fraction of the shock proportional to the edge weight: $r_j = w_{ij} \cdot r_{\text{shock}} + \epsilon_j$, where $\epsilon_j \sim \mathcal{N}(0, \sigma^2)$ is noise.
4. Repeat for one more hop: neighbors of neighbors absorb a fraction of their neighbors' shock.

After $N_{\text{sim}}$ runs, we compute for each asset:
- **Median response**: the 50th percentile of simulated returns.
- **95% confidence interval**: the range from the 2.5th to 97.5th percentile.
- **Probability of negative outcome**: fraction of simulations where the asset ends negative.

This is a simplified version of the DebtRank framework (Battiston et al., 2012), which models iterative contagion through the full network. Our version uses single-step propagation for interpretability.

### Fragility Index: An Order Parameter for Markets

The fragility index is a composite score that summarizes systemic health in a single number. It combines five components:

| Component | Weight | What It Measures |
|---|---|---|
| Network density | 0.25 | How connected assets are. More connections = more contagion channels. |
| Clustering coefficient | 0.20 | Tightness of local cliques. High clustering = concentrated risk. |
| Average path length | 0.20 | How fast shocks can propagate. Shorter paths = faster contagion. |
| Spectral gap | 0.15 | Algebraic connectivity of the graph Laplacian. Smaller = more fragile. |
| Volatility | 0.20 | Average return uncertainty. |

Each component is normalized to [0, 1] across historical windows, then combined with the weights above.

**Physics analogy**: this is like an order parameter for a spin system. In statistical mechanics, an order parameter is a single number that captures the collective behavior of many interacting components. In a ferromagnet, the magnetization per spin tells you whether the system is ordered (all spins aligned) or disordered (random). Low fragility corresponds to a disordered, resilient market where assets move independently. High fragility corresponds to an ordered, fragile market where everything is correlated and one shock can cascade through the entire system.

The spectral gap deserves special attention. The graph Laplacian $L = D - A$ (where $D$ is the degree matrix and $A$ is the adjacency matrix) encodes the connectivity structure. Its second smallest eigenvalue $\lambda_2$ (the Fiedler value) measures algebraic connectivity: how well-connected the graph is. A small $\lambda_2$ means the graph is barely connected and fragile. A large $\lambda_2$ means the graph is robust and resilient.

The fragility index is computed over a rolling window (default 60 days) and provides:
- **Current fragility score** (0-1)
- **Regime classification**: resilient, normal, or stressed
- **Trend**: increasing, stable, or decreasing

When fragility spikes, the network is about to undergo a regime change. This is analogous to a phase transition in physics: the system shifts from one qualitative state to another.

### Crisis Replay: Validating the Model

The crisis replay feature builds networks for specific historical periods and compares them. For each crisis (2008 GFC, 2020 COVID, 2022 Rate Hike), the tool computes networks for three phases:

1. **Pre-crisis**: baseline network topology before the event.
2. **During crisis**: how correlations spiked and the network densified.
3. **Post-crisis**: recovery and return to normal.

The comparison reveals whether the crisis produced the classic contagion signature: higher density, tighter clustering, and shorter path lengths. This validates the model: if the network looks "different" during crises, it is capturing real systemic risk.

**Physics analogy**: this is like observing a phase transition. In normal markets, the network is sparse (low density). During crises, correlations spike, the network densifies, and systemic risk rises. This is analogous to a ferromagnetic transition in a spin system, where increasing temperature causes spins to align, increasing the order parameter.

## Network Methods

ContagionLab supports six methods for constructing a correlation network from asset returns:

| Method | Type | What It Measures | Best For |
|---|---|---|---|
| **Pearson** | Undirected | Linear correlation between raw returns | Baseline comparison. Fast and simple. |
| **Spearman** | Undirected | Rank-based monotonic correlation | Heavy-tailed data. Outlier robustness. |
| **Partial Correlation** | Undirected | Direct pairwise dependence after controlling for all other assets | Removing spurious correlations from common factors. |
| **Graphical Lasso** | Undirected | Sparse precision matrix via L1-regularized maximum likelihood | High-dimensional settings (many assets relative to observations). |
| **Granger Causality** | Directed | Whether asset A helps predict asset B beyond B's own past | Temporal lead-lag relationships. |
| **Tail Dependence** | Undirected | Probability of extreme co-movements (crashes together) | Hidden systemic risk. Assets with low average correlation but high crash co-movement. |

Each method produces a weighted graph where nodes are assets and edges encode the strength of the measured relationship. For the undirected methods, the `top_k` mode limits each node to at most $k$ edges, keeping only the strongest connections.

**How to choose a method:** Pearson is a reasonable starting point. Switch to Spearman if your data has outliers or fat tails. Partial correlation and Graphical Lasso are better when you want to isolate direct relationships (they strip out effects mediated through third assets). Granger causality is the only directed method and is useful when you care about predictive timing rather than simultaneous co-movement. Tail dependence reveals hidden systemic risk: assets that don't move together on average but crash together during extremes.

## Macro Data Integration

ContagionLab can include macroeconomic indicators alongside equity assets in the network. The available indicators are:

- **VIX** (^VIX): CBOE Volatility Index. Market fear gauge. Spikes during crises.
- **10-Year Treasury** (^TNX): Long-term interest rate. Affects discount rates and valuations.
- **13-Week T-Bill** (^IRX): Short-term rate proxy. Reflects Fed policy expectations.
- **Dollar Index** (DX-Y.NYB): Dollar strength. Pressures emerging markets and commodities.
- **Gold** (GC=F): Safe haven asset. Rises during uncertainty.
- **Oil** (CL=F): Energy prices. Affects inflation and growth expectations.

When the macro toggle is enabled, these indicators are merged with equity returns and included in the network. This reveals cross-asset contagion channels: how macro conditions connect to equity markets.

**Physics analogy**: this is like adding external fields to a spin system. The macro indicators are not just another node. They are boundary conditions that affect the entire system.

## Crisis Replay

ContagionLab can replay historical market crises and show how the network topology changed. This validates the model: if the network looks "different" during crises, it is capturing real systemic risk.

Available crises:
- **2008 Global Financial Crisis**: Lehman Brothers collapse, global credit freeze.
- **2020 COVID-19 Crash**: fastest bear market in history (34% in 23 trading days).
- **2022 Rate Hike Selloff**: Fed raises rates from 0% to 5.5%, tech stocks collapse.

For each crisis, the tool shows three network phases:
1. **Pre-crisis**: baseline network topology before the event.
2. **During crisis**: how correlations spiked and the network densified.
3. **Post-crisis**: recovery and return to normal.

The comparison reveals whether the crisis produced the classic contagion signature: higher density, tighter clustering, and shorter path lengths.

## Fragility Index

The fragility index is a composite score that summarizes systemic health in a single number. It combines five components:

| Component | Weight | What It Measures |
|---|---|---|
| Network density | 0.25 | How connected assets are. More connections = more systemic risk. |
| Clustering coefficient | 0.20 | Tightness of local cliques. Concentrated risk. |
| Average path length | 0.20 | How fast shocks can propagate. Shorter = faster contagion. |
| Spectral gap | 0.15 | Algebraic connectivity. Smaller = more fragile. |
| Volatility | 0.20 | Average return uncertainty. |

The index is computed over a rolling window (default 60 days) and provides:
- **Current fragility score** (0-1)
- **Regime classification**: resilient, normal, or stressed.
- **Trend**: increasing, stable, or decreasing.

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
| GET | `/api/macro/tickers` | List available macro indicators |
| POST | `/api/macro/fetch` | Fetch macro data and merge with equity prices |
| POST | `/api/macro/network` | Build network with macro indicators included |

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

- **Single-step propagation only.** The stress test propagates shocks one hop: only direct neighbours of the shocked asset are affected. Multi-step cascading (shock to neighbour to neighbour's neighbour) is not modelled.
- **Linear threshold model.** The transmission equation $x_j = w \cdot \text{shock} + \text{noise}$ assumes a linear relationship between edge weight and shock transmission. Real contagion is often nonlinear: correlations spike during crises (the "correlation breakdown" problem).
- **Static network.** The network is built from a fixed historical window. It does not update in real time or adapt to changing market conditions.
- **No transaction costs or market microstructure.** The stress test is a theoretical model. It does not account for liquidity, bid-ask spreads, or position limits.
- **yfinance rate limits.** The data source (Yahoo Finance via yfinance) can throttle or block requests if you hit it too hard. Cached responses are reused for 24 hours.
- **Granger causality requires long time series.** With short periods (e.g. 5 days), the F-tests in Granger causality are unreliable. Use longer windows (6mo+) for this method.
- **Graphical Lasso assumes Gaussianity.** The L1-regularized estimator fits a Gaussian graphical model. Non-Gaussian tails are not captured.
- **RMT filtering is approximate.** The Marchenko-Pastur bound is exact only in the limit $N, T \to \infty$ with $N/T$ fixed. For small sample sizes, the noise/signal separation is approximate.
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
│   │   │   ├── macro.py         # GET /api/macro/tickers, POST /api/macro/fetch, POST /api/macro/network
│   │   │   └── assets.py        # GET /api/assets
│   │   └── services/
│   │       ├── data_fetcher.py     # yfinance data fetching + parquet cache
│   │       ├── network_builder.py  # 6 network construction methods
│   │       ├── rmt_filter.py       # Random Matrix Theory filtering
│   │       ├── simulation.py       # Monte Carlo stress test engine
│   │       ├── analysis.py         # Centrality, communities, systemic importance
│   │       ├── tail_dependence.py  # Copula-based tail dependence
│   │       ├── crisis_replay.py    # Historical crisis analysis
│   │       ├── fragility.py        # Rolling fragility index
│   │       └── macro_data.py       # VIX, Treasury yields, Dollar index
│   ├── tests/                   # 60 tests (unit + integration)
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
│   │       ├── MiniNetworkGraph.tsx  # Lightweight graph for crisis phases
│   │       ├── ExportPanel.tsx       # JSON/CSV export
│   │       └── ThemeToggle.tsx       # Dark/light mode toggle
│   └── package.json
├── docs/
│   └── design/
│       ├── contagionlab-spec.md   # Design specification
│       └── implementation-plan.md # Implementation plan
├── LICENSE                    # MIT License
└── README.md
```

## References

- Laloux, L., Cizeau, P., Bouchaud, J.-P., & Potters, M. (1999). "Noise Dressing of Financial Correlation Matrices." *Physical Review Letters*, 83(7), 1467-1470.
- Marcenko, V. A., & Pastur, L. A. (1967). "Distribution of Eigenvalues for Some Sets of Random Matrices." *Mathematics of the USSR-Sbornik*, 1(4), 457-483.
- Mantegna, R. N. (2000). "Hierarchical Structure in Financial Markets." *The European Physical Journal B*, 11(1), 193-197.
- Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models and Cross-spectral Methods." *Econometrica*, 37(3), 424-438.
- Friedman, J., Hastie, T., & Tibshirani, R. (2008). "Sparse Inverse Covariance Estimation with the Graphical Lasso." *Biostatistics*, 9(3), 432-441.
- Lauritzen, S. L. (1996). *Graphical Models*. Oxford University Press.
- Joe, H. (1997). *Multivariate Models and Dependence Concepts*. Chapman & Hall.
- Patton, A. J. (2006). "Modelling Asymmetric Exchange Rate Dependence." *International Economic Review*, 47(2), 527-556.
- Billio, M., Getmansky, M., Lo, A. W., & Pelizzon, L. (2012). "Measuring Systemic Risk in the Finance and Insurance Sectors." *Journal of Financial Economics*, 103(3), 535-559.
- Battiston, S., Puliga, M., Kaushik, R., Tacchella, P., & Caldarelli, G. (2012). "DebtRank: Too Central to Fail? Financial Networks, the FED and Systemic Risk." *Scientific Reports*, 2, 541.

## License

MIT License. See [LICENSE](LICENSE) for details.
