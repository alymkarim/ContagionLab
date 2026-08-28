# Task 5: Network Analysis

**Files:**
- Create: `backend/app/services/analysis.py`
- Create: `backend/tests/test_analysis.py`

**Depends on:** Task 4

## Steps

1. Write failing tests in `backend/tests/test_analysis.py`:
   - `_make_test_graph()` — helper creating graph with HUB node connected to A, B, C, D and edge A-B
   - `test_centrality_returns_dict` — assert result has HUB with degree, betweenness, eigenvector, pagerank
   - `test_hub_has_highest_centrality` — HUB degree > A degree
   - `test_communities_returns_list` — assert has num_communities and assignment
   - `test_systemic_importance_returns_dict` — assert HUB has score and percentile

2. Run tests to verify they fail

3. Implement `backend/app/services/analysis.py`:
   - `compute_centrality(G)` — returns {node: {degree, betweenness, eigenvector, pagerank}} using networkx
   - `detect_communities(G)` — Louvain method, returns {num_communities, assignment, sizes}
   - `compute_systemic_importance(G)` — composite score: 0.3*eigenvector + 0.3*betweenness + 0.25*degree + 0.15*community_size, normalized, percentile ranked
   - Working comments explaining eigenvector centrality = principal eigenvector, Louvain modularity Q, order parameter analogy

4. Run tests to verify they pass

5. Commit: `git add backend/app/services/analysis.py backend/tests/test_analysis.py && git commit -m "network analysis — centrality metrics, Louvain communities, systemic importance score"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
