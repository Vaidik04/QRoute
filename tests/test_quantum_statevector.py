"""
tests/test_quantum_statevector.py
=================================
Unit tests for the Quantum Lab:
- QUBO to Ising Hamiltonian transformation
- Pure NumPy Statevector QAOA simulation
- Approximation ratio & fidelity calculations
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from optimization.problem import VRPProblem
from quantum.qubo import build_qubo_matrix, qubo_to_ising, brute_force_qubo, qubo_energy
from quantum.qaoa import run_qaoa, QAOAResult


@pytest.fixture
def small_problem():
    return VRPProblem.random_cvrp(n_customers=3, n_vehicles=1, capacity=50.0, seed=42)


class TestQuantumStatevector:
    def test_qubo_to_ising_equivalence(self, small_problem):
        """Verify that QUBO energy matches Ising energy for random bitstrings."""
        Q, n_cust, n_pos = build_qubo_matrix(small_problem, n_customers=3)
        n_vars = n_cust * n_pos
        J, h, offset = qubo_to_ising(Q)

        rng = np.random.default_rng(123)
        for _ in range(10):
            x = rng.integers(0, 2, size=n_vars).astype(float)
            # Map x in {0, 1} to spin s in {-1, +1}
            s = 1.0 - 2.0 * x

            e_qubo = float(x @ Q @ x)
            e_ising = float(s @ J @ s + h @ s + offset)
            assert np.isclose(e_qubo, e_ising, atol=1e-6), f"Mismatch: QUBO {e_qubo} vs Ising {e_ising}"

    def test_statevector_qaoa_execution(self, small_problem):
        """Verify pure NumPy statevector QAOA runs and returns valid quantum metrics."""
        Q, n_cust, n_pos = build_qubo_matrix(small_problem, n_customers=3)
        n_vars = n_cust * n_pos
        assert n_vars == 9

        res = run_qaoa(Q, n_cust, n_pos, n_layers=2, seed=42, max_iterations=30, backend="statevector")
        assert isinstance(res, QAOAResult)
        assert res.algorithm == "qaoa_statevector"
        assert res.n_qubits == 9
        assert res.n_layers == 2
        assert res.runtime_ms > 0
        assert res.expectation_value is not None
        assert res.approximation_ratio is not None
        assert 0.0 <= res.approximation_ratio <= 1.0
        assert res.ground_state_fidelity is not None
        assert 0.0 <= res.ground_state_fidelity <= 1.0
        assert len(res.optimal_gammas) == 2
        assert len(res.optimal_betas) == 2
