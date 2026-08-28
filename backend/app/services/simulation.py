"""
Monte Carlo stress testing via linear threshold propagation.

Simulates how a price shock on one asset ripples through a financial
network to its neighbours.

Physics analogy
---------------
Think of the correlation network as a set of masses connected by
springs (the edge weights).  Giving one mass a push (the shock) causes
the connected masses to move proportionally to the spring stiffness.
Each Monte Carlo draw adds independent thermal noise N(0, noise_std),
modelling the fact that real markets are stochastic — the same shock
never produces exactly the same outcome twice.

Linear threshold model
----------------------
For a shocked asset *S* with magnitude *m*, each neighbour *j* receives:

    x_j = w_{Sj} * m + epsilon_j,    epsilon_j ~ N(0, noise_std)

where w_{Sj} is the edge weight (correlation strength) between S and j.
The weight acts as a **transmission coefficient**: a higher correlation
means more of the shock passes through.

Monte Carlo
-----------
We repeat the above experiment *n_sims* times, drawing fresh noise each
run, then summarise the distribution of x_j with:
  - median  (robust central estimate)
  - ci_95   (2.5 % and 97.5 % percentiles — the 95 % confidence interval)
  - prob_negative  (fraction of simulations where x_j < 0)

The shocked asset itself is assigned a deterministic response equal to
the shock magnitude (it is the source, not a receiver).
"""

import networkx as nx
import numpy as np


def run_stress_test(
    G: nx.Graph,
    shock_asset: str,
    shock_magnitude: float,
    n_sims: int = 1000,
    noise_std: float = 0.01,
) -> dict[str, dict]:
    """Run a Monte Carlo stress test on a correlation network.

    Parameters
    ----------
    G : nx.Graph
        Undirected weighted graph.  ``edge['weight']`` is the
        correlation-strength coupling between two assets.
    shock_asset : str
        Node label of the asset receiving the initial shock.
    shock_magnitude : float
        Size of the shock (negative = crash scenario).
    n_sims : int
        Number of Monte Carlo draws (default 1 000).
    noise_std : float
        Standard deviation of the per-neighbour Gaussian noise
        (default 0.01 — small relative to typical shock sizes).

    Returns
    -------
    dict[str, dict]
        ``{ticker: {"median": float, "ci_95": [lo, hi], "prob_negative": float}}``
        for every node in the graph.
    """
    if shock_asset not in G:
        raise ValueError(f"Shock asset '{shock_asset}' not in graph")

    # Deterministic seed so results are reproducible across runs.
    rng = np.random.default_rng(42)

    results: dict[str, dict] = {}

    # --- The shocked asset itself is the source of the perturbation.
    # Its response is the shock magnitude (no noise — it is the input).
    results[shock_asset] = {
        "median": shock_magnitude,
        "ci_95": [shock_magnitude, shock_magnitude],
        "prob_negative": float(shock_magnitude < 0),
    }

    # --- Propagate the shock to each neighbour via Monte Carlo draws.
    # For every neighbour j of the shock asset:
    #   x_j = w_{Sj} * shock_magnitude + N(0, noise_std)
    # The edge weight w_{Sj} acts as a linear transmission coefficient.
    neighbours = dict(G[shock_asset])

    for neighbour, edge_data in neighbours.items():
        w = edge_data["weight"]
        # Expected response (signal) from the linear threshold model.
        signal = w * shock_magnitude
        # Draw n_sims independent noise samples: each sim gets its own
        # realisation of the stochastic component.
        noise = rng.standard_normal(n_sims) * noise_std
        samples = signal + noise

        # Summarise the simulated distribution.
        median = float(np.median(samples))
        lo = float(np.percentile(samples, 2.5))
        hi = float(np.percentile(samples, 97.5))
        prob_neg = float(np.mean(samples < 0))

        results[neighbour] = {
            "median": median,
            "ci_95": [lo, hi],
            "prob_negative": prob_neg,
        }

    # --- Assets that are NOT direct neighbours of the shock asset
    # receive no transmission (response = 0).  This is the "threshold"
    # part of the linear threshold model: only direct neighbours are
    # affected in a single-step propagation.
    for node in G.nodes:
        if node not in results:
            results[node] = {
                "median": 0.0,
                "ci_95": [0.0, 0.0],
                "prob_negative": 0.0,
            }

    return results
