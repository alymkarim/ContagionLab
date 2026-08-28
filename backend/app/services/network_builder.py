"""
Network construction methods for financial contagion analysis.

Provides multiple approaches to build a network graph from asset return
data, each capturing different aspects of co-movement:

1. **Pearson correlation** — linear dependence between raw returns.
2. **Spearman rank correlation** — monotonic dependence, robust to outliers.
3. **Partial correlation** — direct pairwise dependence after removing
   the effect of all other assets (precision-matrix approach).
4. **Graphical Lasso** — sparse precision matrix via L1 penalty, good
   for high-dimensional settings.
5. **Granger causality** — temporal (directed) dependence: does asset A
   help predict asset B beyond B's own past?

References:
  - Pearson: standard product-moment correlation.
  - Spearman: rank-based, see Siegel & Castellan (1988).
  - Partial: see Lauritzen (1996) "Graphical Models".
  - Granger: Granger (1969) "Investigating Causal Relations by
    Econometric Models and Cross-spectral Methods", Econometrica 37.
"""

import networkx as nx
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.covariance import GraphicalLassoCV
from statsmodels.tsa.stattools import grangercausalitytests


def correlation_to_network(
    corr: np.ndarray,
    tickers: list[str],
    mode: str = "top_k",
    k: int = 3,
    threshold: float = 0.3,
) -> nx.Graph:
    """Convert a correlation matrix into a weighted network graph.

    Each asset becomes a node.  Edges connect assets whose
    correlation exceeds a cutoff, with edge weight = |correlation|.

    Parameters
    ----------
    corr : np.ndarray
        N×N symmetric correlation matrix.
    tickers : list[str]
        Asset labels (length N).
    mode : str
        "top_k" — for each node, keep at most the k strongest edges.
        "threshold" — keep all edges with |corr| > threshold.
    k : int
        Maximum degree per node when mode="top_k" (default 3).
    threshold : float
        Minimum |correlation| to form an edge when mode="threshold".

    Returns
    -------
    nx.Graph
        Undirected weighted graph.
    """
    n = corr.shape[0]
    G = nx.Graph()
    G.add_nodes_from(tickers)

    if mode == "top_k":
        # Greedy degree-constrained construction: sort ALL possible edges
        # by |correlation| descending, then add each edge only if both
        # endpoints currently have degree < k.  This guarantees that no
        # node ever exceeds degree k, while keeping the strongest edges.
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                edges.append((abs(corr[i, j]), i, j))
        edges.sort(key=lambda x: x[0], reverse=True)
        for w, i, j in edges:
            if w == 0:
                break
            if G.degree(tickers[i]) < k and G.degree(tickers[j]) < k:
                G.add_edge(tickers[i], tickers[j], weight=w)
    elif mode == "threshold":
        # Add every edge whose absolute correlation exceeds the threshold.
        for i in range(n):
            for j in range(i + 1, n):
                if abs(corr[i, j]) > threshold:
                    G.add_edge(tickers[i], tickers[j], weight=abs(corr[i, j]))
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Use 'top_k' or 'threshold'.")

    return G


def build_pearson_network(
    returns: pd.DataFrame,
    mode: str = "top_k",
    k: int = 3,
    threshold: float = 0.3,
) -> nx.Graph:
    """Build a network from Pearson (linear) correlation.

    Pearson correlation measures linear co-movement:

        r_ij = cov(R_i, R_j) / (std(R_i) * std(R_j))

    Limitations:
      - Only captures *linear* relationships.
      - Sensitive to outliers (a single extreme day dominates).
      - Does not distinguish direct from indirect relationships:
        A and B may be correlated only because both correlate with C.

    Parameters
    ----------
    returns : pd.DataFrame
        (T, N) matrix of asset returns.
    mode, k, threshold : forwarded to correlation_to_network.

    Returns
    -------
    nx.Graph
    """
    corr = np.corrcoef(returns.values, rowvar=False)
    return correlation_to_network(corr, list(returns.columns), mode=mode, k=k, threshold=threshold)


def build_spearman_network(
    returns: pd.DataFrame,
    mode: str = "top_k",
    k: int = 3,
    threshold: float = 0.3,
) -> nx.Graph:
    """Build a network from Spearman rank correlation.

    Spearman correlation is the Pearson correlation of the *ranks* of
    the observations.  It captures monotonic (but not necessarily
    linear) dependence and is more robust to outliers and heavy tails.

    Properties:
      - Bounded in [-1, 1].
      - Equals +1 if the two assets are perfectly monotonically
        related.
      - Robust: a single extreme observation only changes one rank,
        so its influence is bounded.

    Parameters
    ----------
    returns : pd.DataFrame
        (T, N) matrix of asset returns.
    mode, k, threshold : forwarded to correlation_to_network.

    Returns
    -------
    nx.Graph
    """
    corr, _ = stats.spearmanr(returns.values)
    # spearmanr returns (corr_matrix, pvalue) when given a matrix
    return correlation_to_network(corr, list(returns.columns), mode=mode, k=k, threshold=threshold)


def build_partial_correlation_network(
    returns: pd.DataFrame,
    mode: str = "top_k",
    k: int = 3,
    threshold: float = 0.3,
) -> nx.Graph:
    """Build a network from partial correlations via the precision matrix.

    Partial correlation measures the *direct* relationship between two
    assets after controlling for (removing the influence of) all other
    assets.  It is computed from the inverse of the covariance matrix
    (the precision matrix):

        partial_corr(i,j) = -Theta_ij / sqrt(Theta_ii * Theta_jj)

    where Theta = Sigma^{-1}.  If the partial correlation is near zero,
    assets i and j are conditionally independent given all others.

    This approach is powerful because it strips out *spurious*
    correlations caused by a common factor, giving a cleaner picture
    of which assets are truly directly connected.

    Limitations:
      - Requires the covariance matrix to be invertible (T > N).
      - Sensitive to estimation noise when N is large relative to T.
      - Does not handle sparse systems well without regularization.

    Parameters
    ----------
    returns : pd.DataFrame
        (T, N) matrix of asset returns.  T must exceed N.
    mode, k, threshold : forwarded to correlation_to_network.

    Returns
    -------
    nx.Graph
    """
    cov = np.cov(returns.values, rowvar=False)
    # Invert the covariance matrix to get the precision matrix.
    # This is numerically expensive (O(N^3)) but exact.
    precision = np.linalg.inv(cov)
    n = precision.shape[0]
    # Convert precision matrix entries to partial correlations using:
    #   rho_partial(i,j) = -Theta_ij / sqrt(Theta_ii * Theta_jj)
    diag = np.sqrt(np.diag(precision))
    # Avoid division by zero — diagonal of a valid covariance inverse
    # should always be positive, but guard anyway.
    diag = np.maximum(diag, 1e-12)
    partial_corr = -precision / np.outer(diag, diag)
    np.fill_diagonal(partial_corr, 1.0)
    # Clamp to valid correlation range (numerical noise can push values
    # slightly outside [-1, 1]).
    partial_corr = np.clip(partial_corr, -1.0, 1.0)
    return correlation_to_network(partial_corr, list(returns.columns), mode=mode, k=k, threshold=threshold)


def build_graphical_lasso_network(
    returns: pd.DataFrame,
    mode: str = "top_k",
    k: int = 3,
    threshold: float = 0.3,
) -> nx.Graph:
    """Build a network from a sparse precision matrix (Graphical Lasso).

    Graphical Lasso fits a Gaussian Graphical Model by maximizing the
    penalized log-likelihood:

        l(Omega) = log det(Omega) - Tr(S * Omega) - alpha * ||Omega||_1

    where Omega = Sigma^{-1} is the precision matrix, S is the sample
    covariance, and alpha controls the L1 penalty strength.  The L1
    penalty drives many precision-matrix entries to exactly zero,
    producing a *sparse* graph where only the strongest direct
    dependencies remain.

    sklearn's GraphicalLassoCV selects alpha automatically via
    cross-validation.

    Advantages over plain partial correlations:
      - Regularization reduces estimation error in high dimensions.
      - Produces a sparse, interpretable graph.
      - Handles the case N ~ T better than raw matrix inversion.

    Limitations:
      - Assumes Gaussian data.
      - The L1 penalty can over-shrink weak but real edges.

    Parameters
    ----------
    returns : pd.DataFrame
        (T, N) matrix of asset returns.
    mode, k, threshold : forwarded to correlation_to_network.

    Returns
    -------
    nx.Graph
    """
    model = GraphicalLassoCV(cv=5).fit(returns.values)
    # The precision matrix from the fitted model
    precision = model.precision_
    n = precision.shape[0]
    # Convert to partial correlations using the same formula as above:
    #   rho_partial(i,j) = -Theta_ij / sqrt(Theta_ii * Theta_jj)
    diag = np.sqrt(np.diag(precision))
    diag = np.maximum(diag, 1e-12)
    partial_corr = -precision / np.outer(diag, diag)
    np.fill_diagonal(partial_corr, 1.0)
    partial_corr = np.clip(partial_corr, -1.0, 1.0)
    return correlation_to_network(partial_corr, list(returns.columns), mode=mode, k=k, threshold=threshold)


def build_granger_causality_network(
    returns: pd.DataFrame,
    max_lag: int = 2,
    significance: float = 0.05,
) -> nx.DiGraph:
    """Build a directed network from pairwise Granger causality tests.

    Granger causality asks: does the past of asset A help predict the
    future of asset B, beyond what B's own past already predicts?

    Formally, we fit two autoregressive models for B:
      - Restricted:   B_t = sum_j phi_j * B_{t-j} + epsilon_t
      - Unrestricted: B_t = sum_j phi_j * B_{t-j} + sum_j psi_j * A_{t-j} + epsilon_t

    If the unrestricted model has significantly lower variance (F-test),
    we say A "Granger-causes" B, and add a directed edge A → B.

    Properties:
      - Produces a *directed* graph (DiGraph) because causality is
        asymmetric: A may Granger-cause B without B Granger-causing A.
      - Sensitive to the choice of max_lag.
      - Does NOT imply true causation — it detects *predictive*
        relationships, which may be driven by a common hidden driver.

    Parameters
    ----------
    returns : pd.DataFrame
        (T, N) matrix of asset returns.  T should be much larger than
        max_lag for reliable F-tests.
    max_lag : int
        Number of lags to include in the autoregressive models.
    significance : float
        P-value threshold for the F-test (default 0.05).

    Returns
    -------
    nx.DiGraph
        Directed graph where edge A → B means A Granger-causes B.
    """
    tickers = list(returns.columns)
    n = len(tickers)
    G = nx.DiGraph()
    G.add_nodes_from(tickers)

    data = returns.values

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Pair (cause=i, effect=j): test if column i Granger-causes column j.
            # statsmodels expects shape (T, 2) with effect column first.
            pair = np.column_stack([data[:, j], data[:, i]])
            try:
                result = grangercausalitytests(pair, maxlag=max_lag, verbose=False)
                # result is a dict keyed by lag number (1-indexed).
                # We check if *any* lag is significant at the given level.
                min_p = min(
                    result[lag][0]["ssr_ftest"][1]
                    for lag in range(1, max_lag + 1)
                    if lag in result
                )
                if min_p < significance:
                    G.add_edge(tickers[i], tickers[j], p_value=min_p)
            except Exception:
                # If the test fails (e.g. degenerate series), skip this pair.
                pass

    return G
