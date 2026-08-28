# Task 3: RMT Filtering

**Files:**
- Create: `backend/app/services/rmt_filter.py`
- Create: `backend/tests/test_rmt_filter.py`

**Depends on:** Task 2

## Steps

1. Write failing tests in `backend/tests/test_rmt_filter.py`:
   - `test_mp_upper_bound` — for N=50, T=250, sigma2=1: lambda_plus ≈ 2.094
   - `test_filter_removes_noise_eigenvalues` — generate random returns, filter correlation matrix, assert all eigenvalues <= lambda_plus
   - `test_filter_preserves_trace` — assert trace approximately preserved after filtering

2. Run tests to verify they fail (cannot import)

3. Implement `backend/app/services/rmt_filter.py`:
   - `compute_mp_upper_bound(n, t, sigma2)` — Marchenko-Pastur upper bound: lambda_plus = sigma2 * (1 + sqrt(n/t))^2
   - `filter_correlation_matrix(corr, t, sigma2)` — eigendecompose, clip noise eigenvalues to mean (trace-preserving), reconstruct, symmetrize, clip diagonal to 1, clip off-diagonals to [-1,1]
   - Working comments explaining: MP law, noise eigenvalue clipping, trace preservation, reference to Laloux et al. 1999

4. Run tests to verify they pass

5. Commit: `git add backend/app/services/rmt_filter.py backend/tests/test_rmt_filter.py && git commit -m "RMT filtering — Marchenko-Pastur eigenvalue clipping with trace preservation"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
