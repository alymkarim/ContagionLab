import numpy as np
import pytest

from app.services.rmt_filter import compute_mp_upper_bound, filter_correlation_matrix


def test_mp_upper_bound():
    """Marchenko-Pastur upper bound for N=50, T=250, sigma2=1 should be ≈ 2.094."""
    lambda_plus = compute_mp_upper_bound(n=50, t=250, sigma2=1.0)
    np.testing.assert_almost_equal(lambda_plus, 2.094, decimal=3)


def test_filter_removes_noise_eigenvalues():
    """After filtering, all eigenvalues of the correlation matrix must be <= lambda_plus."""
    rng = np.random.default_rng(42)
    n, t = 50, 250
    # Generate random returns: n assets, t observations
    returns = rng.standard_normal((n, t))
    # Compute sample correlation matrix
    corr = np.corrcoef(returns)
    lambda_plus = compute_mp_upper_bound(n, t, sigma2=1.0)
    filtered = filter_correlation_matrix(corr, t, sigma2=1.0)
    eigvals = np.linalg.eigvalsh(filtered)
    assert np.all(eigvals <= lambda_plus + 1e-10), (
        f"Eigenvalues {eigvals[eigvals > lambda_plus]} exceed lambda_plus={lambda_plus}"
    )


def test_filter_preserves_trace():
    """Trace of filtered correlation matrix must approximately equal n (number of assets)."""
    rng = np.random.default_rng(123)
    n, t = 50, 250
    returns = rng.standard_normal((n, t))
    corr = np.corrcoef(returns)
    filtered = filter_correlation_matrix(corr, t, sigma2=1.0)
    np.testing.assert_almost_equal(np.trace(filtered), n, decimal=10)
