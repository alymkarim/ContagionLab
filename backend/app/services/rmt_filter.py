"""
Random Matrix Theory (RMT) filtering of correlation matrices.

Implements the method of Laloux et al. (1999) — "Random Matrix Theory
of Financial Correlations" — which separates the eigenvalues of a
sample correlation matrix into a "noise" bulk (consistent with random
noise) and a "signal" set (genuine cross-correlations).

Key ideas:

1. **Marchenko-Pastur (MP) law** — For an N×N correlation matrix built
   from T observations of N assets, random (noise) eigenvalues are
   bounded above by

       lambda_plus = sigma² * (1 + sqrt(N/T))²

   where sigma² is the variance of the underlying returns (set to 1
   for standardised returns, so the correlation matrix has unit diagonal).

2. **Noise eigenvalue clipping** — Eigenvalues below lambda_plus are
   replaced by their average (the mean of the noise eigenvalues).  This
   preserves the trace of the matrix: the sum of eigenvalues equals N,
   the dimension, which is required for a valid correlation matrix.

3. **Signal extraction** — Eigenvalues above lambda_plus are kept
   unchanged.  These carry genuine information about asset co-movements.

References:
  - Laloux, L., Cizeau, P., Bouchaud, J.-P. & Potters, M. (1999).
    "Random Matrix Theory of Financial Correlations."
    Int. J. Theor. Appl. Finance, 2, 391-397.
  - Marcenko, V. A. & Pastur, L. A. (1967).
    "Distribution of Eigenvalues for Some Sets of Random Matrices."
    Math. USSR-Sbornik, 1, 457-483.
"""

import numpy as np


def compute_mp_upper_bound(n: int, t: int, sigma2: float = 1.0) -> float:
    """Marchenko-Pastur upper bound for the eigenvalue spectrum.

    The MP law says that for a random N×T matrix X with iid entries of
    variance sigma², the eigenvalues of (1/T) X Xᵀ are bounded in the
    limit N, T → ∞ with q = N/T fixed by:

        lambda_minus = sigma² * (1 - sqrt(N/T))²
        lambda_plus  = sigma² * (1 + sqrt(N/T))²

    We return lambda_plus, the noise ceiling — any eigenvalue larger
    than this is unlikely to be pure noise and therefore carries
    genuine signal.

    Parameters
    ----------
    n : int
        Number of assets (rows of the returns matrix).
    t : int
        Number of observations (columns of the returns matrix).
    sigma2 : float
        Variance of the entries.  For standardised returns this is 1.

    Returns
    -------
    float
        The MP upper bound lambda_plus.
    """
    return sigma2 * (1.0 + np.sqrt(n / t)) ** 2


def filter_correlation_matrix(
    corr: np.ndarray,
    t: int,
    sigma2: float = 1.0,
) -> np.ndarray:
    """Filter a correlation matrix by clipping noise eigenvalues.

    Steps:
      1. Eigendecompose the sample correlation matrix C = V Λ Vᵀ.
      2. Identify eigenvalues below the MP bound lambda_plus.
      3. Replace (clip) those noise eigenvalues by their mean.  Because
         the mean of the noise eigenvalues equals (sum_of_noise_eigenvalues)
         / (count_of_noise_eigenvalues), and we do not touch signal
         eigenvalues, the total trace is preserved: trace(C_filtered) = N.
      4. Reconstruct the matrix: C_filtered = V Λ_filtered Vᵀ.
      5. Symmetrise (force exact symmetry to kill floating-point drift).
      6. Clip diagonal to exactly 1.
      7. Clip off-diagonal elements to [-1, 1].

    Parameters
    ----------
    corr : np.ndarray
        N×N symmetric correlation matrix (sample).
    t : int
        Number of observations used to build corr.
    sigma2 : float
        Variance of the underlying returns (default 1).

    Returns
    -------
    np.ndarray
        The filtered N×N correlation matrix.
    """
    n = corr.shape[0]
    lambda_plus = compute_mp_upper_bound(n, t, sigma2)

    # --- Eigendecomposition ------------------------------------------------
    # corr is real symmetric, so we use eigh (guaranteed real eigenvalues
    # and orthonormal eigenvectors).
    eigvals, eigvecs = np.linalg.eigh(corr)

    # --- Noise eigenvalue clipping -----------------------------------------
    # Eigenvalues below lambda_plus are consistent with random noise.
    # Replace them by their average so the trace is preserved:
    #   sum(filtered_eigvals) = sum(signal_eigvals) + mean(noise) * n_noise
    #                          = sum(signal_eigvals) + sum(noise_eigvals)
    #                          = sum(all_eigvals) = N
    noise_mask = eigvals < lambda_plus
    if np.any(noise_mask):
        mean_noise = eigvals[noise_mask].mean()
        eigvals[noise_mask] = mean_noise

    # --- Reconstruct the matrix --------------------------------------------
    # C_filtered = V Λ_filtered Vᵀ
    filtered = eigvecs @ np.diag(eigvals) @ eigvecs.T

    # --- Symmetrise (kill floating-point asymmetry) -------------------------
    filtered = (filtered + filtered.T) / 2.0

    # --- Clip diagonal to exactly 1 ----------------------------------------
    np.fill_diagonal(filtered, 1.0)

    # --- Clip off-diagonals to valid correlation range [-1, 1] -------------
    off_diag_mask = ~np.eye(n, dtype=bool)
    filtered[off_diag_mask] = np.clip(filtered[off_diag_mask], -1.0, 1.0)

    return filtered
