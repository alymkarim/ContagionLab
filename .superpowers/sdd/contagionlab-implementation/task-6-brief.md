# Task 6: Monte Carlo Stress Testing

**Files:**
- Create: `backend/app/services/simulation.py`
- Create: `backend/tests/test_simulation.py`

**Depends on:** Task 4

## Steps

1. Write failing tests in `backend/tests/test_simulation.py`:
   - `_make_test_network()` — 3 nodes: NVDA-AMD (0.8), NVDA-QQQ (0.5), AMD-QQQ (0.4)
   - `test_stress_test_returns_results` — assert results has NVDA, AMD, QQQ with median, ci_95, prob_negative
   - `test_stress_test_shock_propagates_proportionally` — AMD median < QQQ median (stronger connection)
   - `test_stress_test_confidence_intervals` — ci_95[0] <= median <= ci_95[1] for all assets

2. Run tests to verify they fail

3. Implement `backend/app/services/simulation.py`:
   - `run_stress_test(G, shock_asset, shock_magnitude, n_sims, noise_std)` — for each neighbor, response = weight * shock + N(0, noise_std), returns {asset: {median, ci_95, prob_negative}}
   - Working comments explaining: linear threshold model, Monte Carlo, physics analogy (perturbation of coupled system)

4. Run tests to verify they pass

5. Commit: `git add backend/app/services/simulation.py backend/tests/test_simulation.py && git commit -m "Monte Carlo stress testing — linear threshold propagation with noise"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
