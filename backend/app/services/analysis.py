"""
Network analysis module for financial contagion graphs.

Computes centrality metrics, detects communities, and scores each
node's systemic importance using a composite measure.

All metrics use standard networkx routines.  The composite score
blends eigenvector, betweenness, degree, and community-size
contributions — analogous to an order parameter that measures how
close a system is to a phase transition.
"""

import networkx as nx
import numpy as np


def compute_centrality(G: nx.Graph) -> dict:
    """Compute four centrality metrics for every node in the graph.

    Metrics returned per node:
      - **degree** — fraction of nodes this node is connected to.
        Simple but ignores indirect influence.
      - **betweenness** — how often a node lies on shortest paths
        between other pairs.  High betweenness means the node is a
        *bridge* whose removal would disconnect the network.
      - **eigenvector** — proportional to the sum of neighbours'
        eigenvector scores.  Mathematically, it is the leading
        eigenvector of the adjacency matrix:  Ax = lambda_1 x.
        Nodes connected to other well-connected nodes score high.
      - **PageRank** — a random-walk measure: probability that a
        walker who follows edges at random (with teleportation)
        lands on this node.  A damped version of eigenvector
        centrality.

    Parameters
    ----------
    G : nx.Graph
        Undirected weighted graph (e.g. from build_pearson_network).

    Returns
    -------
    dict
        {node: {degree, betweenness, eigenvector, pagerank}}
    """
    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="weight")

    # Eigenvector centrality is the principal eigenvector of the adjacency
    # matrix.  We use the power-iteration solver with weight="weight" so
    # edge weights (correlation strengths) amplify the score.
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000, weight="weight")
    except nx.PowerIterationFailedConvergence:
        # Fallback: use unweighted eigenvector centrality if the weighted
        # version does not converge (can happen with noisy weights).
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000)

    # PageRank treats edge weights as transition probabilities.
    # The damping factor alpha=0.85 means 15 % of the time the walker
    # teleports to a random node — prevents getting trapped in cliques.
    pagerank = nx.pagerank(G, alpha=0.85, weight="weight")

    result = {}
    for node in G.nodes():
        result[node] = {
            "degree": degree[node],
            "betweenness": betweenness[node],
            "eigenvector": eigenvector[node],
            "pagerank": pagerank[node],
        }
    return result


def detect_communities(G: nx.Graph) -> dict:
    """Detect communities using the Louvain modularity optimisation.

    The Louvain algorithm greedily maximises the modularity Q:

        Q = (1/2m) * sum_ij [ A_ij - (k_i * k_j)/(2m) ] * delta(c_i, c_j)

    where A_ij is the adjacency matrix, k_i is the degree of node i,
    m is total edge weight, and delta(c_i, c_j) = 1 if nodes i, j
    belong to the same community.  Higher Q means denser within-group
    connections and sparser between-group connections.

    In statistical-physics language, the Louvain algorithm finds
    communities by optimising an *order parameter* Q — similar to
    minimising free energy in a spin system.  Each pass sweeps over
    nodes and moves them to the neighbouring community that gives the
    largest gain in Q, then aggregates communities into super-nodes
    and repeats until convergence.

    Parameters
    ----------
    G : nx.Graph
        Undirected graph.

    Returns
    -------
    dict
        {num_communities, assignment, sizes}
        - num_communities : int
        - assignment : {node: community_index}
        - sizes : {community_index: member_count}
    """
    # louvain_communities returns a list of sets, each set is one community.
    communities = nx.community.louvain_communities(G, seed=42)

    assignment = {}
    sizes = {}
    for idx, community in enumerate(communities):
        sizes[idx] = len(community)
        for node in community:
            assignment[node] = idx

    return {
        "num_communities": len(communities),
        "assignment": assignment,
        "sizes": sizes,
    }


def compute_systemic_importance(G: nx.Graph) -> dict:
    """Compute a composite systemic-importance score for each node.

    The score blends four normalised centrality measures:

        score_i = 0.30 * eigenvector_i
                 + 0.30 * betweenness_i
                 + 0.25 * degree_i
                 + 0.15 * community_fraction_i

    where community_fraction_i = size_of_i's_community / total_nodes.
    This captures both local connectivity (degree), global bridge
    role (betweenness), influence propagation (eigenvector), and
    community membership (larger communities add a baseline risk).

    All raw values are min-max normalised to [0, 1] before blending
    so that no single metric dominates simply due to scale.

    The percentile rank gives each node's position relative to all
    others — useful for alerting: nodes above the 90th percentile
    are flagged as systemically important.

    Parameters
    ----------
    G : nx.Graph
        Undirected weighted graph.

    Returns
    -------
    dict
        {node: {score, percentile}}
        - score : float in [0, 1]
        - percentile : float in [0, 100]
    """
    centrality = compute_centrality(G)
    communities = detect_communities(G)

    n = G.number_of_nodes()

    # Gather raw component values per node
    raw = {}
    for node in G.nodes():
        c = centrality[node]
        comm_size = communities["sizes"][communities["assignment"][node]]
        raw[node] = {
            "eigenvector": c["eigenvector"],
            "betweenness": c["betweenness"],
            "degree": c["degree"],
            "community_fraction": comm_size / n,
        }

    # Min-max normalise each component to [0, 1]
    def _normalise(values: dict) -> dict:
        vals = list(values.values())
        vmin, vmax = min(vals), max(vals)
        span = vmax - vmin
        if span == 0:
            return {k: 0.0 for k in values}
        return {k: (v - vmin) / span for k, v in values.items()}

    norm = {}
    for component in ["eigenvector", "betweenness", "degree", "community_fraction"]:
        comp_vals = {node: raw[node][component] for node in G.nodes()}
        norm[component] = _normalise(comp_vals)

    # Weighted blend
    scores = {}
    for node in G.nodes():
        scores[node] = (
            0.30 * norm["eigenvector"][node]
            + 0.30 * norm["betweenness"][node]
            + 0.25 * norm["degree"][node]
            + 0.15 * norm["community_fraction"][node]
        )

    # Percentile rank: fraction of nodes with score <= this node's score
    all_scores = sorted(scores.values())
    result = {}
    for node, s in scores.items():
        # Count how many nodes have score <= s, then divide by total
        count_le = sum(1 for v in all_scores if v <= s)
        result[node] = {
            "score": s,
            "percentile": (count_le / len(all_scores)) * 100.0,
        }

    return result
