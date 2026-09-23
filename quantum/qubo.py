"""
quantum/qubo.py
==============
QUBO (Quadratic Unconstrained Binary Optimization) formulation and Ising mapping
for small VRP instances (4–6 customers).

This is the Quantum Lab module — a rigorous demonstration of the quantum
optimization concept, NOT the city-scale routing engine.

Formulations:
1. QUBO:
       min  x^T Q x,  x ∈ {0, 1}^N
   x_{i,j} = 1 if customer i is visited at position j.

2. Ising Hamiltonian:
       H = ∑_{i<j} J_{i,j} Z_i Z_j + ∑_i h_i Z_i + C_offset,  Z_i ∈ {-1, +1}
   Mapped via x_i = (1 - Z_i) / 2.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from optimization.problem import VRPProblem


def build_qubo_matrix(
    problem: "VRPProblem",
    n_customers: Optional[int] = None,
    penalty_capacity: float = 10.0,
    penalty_assignment: float = 20.0,
) -> tuple[np.ndarray, int, int]:
    """Build the QUBO matrix Q for a small VRP instance.

    Binary variables: x_{i,j} = 1 if customer i visits position j.
    Variable ordering: flatten (i, j) → row-major, idx = i * n_pos + j.

    Parameters
    ----------
    problem : VRPProblem   (max 6 customers recommended)
    n_customers : int | None    Limit to first n_customers (default: all).
    penalty_capacity : float    Penalty coefficient for capacity violation.
    penalty_assignment : float  Penalty coefficient for assignment violations.

    Returns
    -------
    (Q, n_cust, n_pos)
        Q : np.ndarray, shape (n_cust*n_pos, n_cust*n_pos)
        n_cust : int    Number of customers in the QUBO.
        n_pos : int     Number of positions (= n_cust).
    """
    if n_customers is None:
        n_customers = min(problem.n_customers, 6)
    n_cust = n_customers
    n_pos = n_cust  # one position per customer (single-vehicle TSP-like)
    n_vars = n_cust * n_pos

    Q = np.zeros((n_vars, n_vars))

    def var(i: int, j: int) -> int:
        """Map (customer i, position j) to variable index."""
        return i * n_pos + j

    # ---------------------------------------------------------------
    # Objective: minimize total distance
    # ---------------------------------------------------------------
    for pos in range(n_pos - 1):
        for ci in range(n_cust):
            for cj in range(n_cust):
                if ci == cj:
                    continue
                dist = problem.distance(ci + 1, cj + 1)
                v1 = var(ci, pos)
                v2 = var(cj, pos + 1)
                Q[v1, v2] += dist

    # Depot → first and last → depot
    for ci in range(n_cust):
        v_first = var(ci, 0)
        v_last = var(ci, n_pos - 1)
        Q[v_first, v_first] += problem.distance(0, ci + 1)
        Q[v_last, v_last] += problem.distance(ci + 1, 0)

    # ---------------------------------------------------------------
    # Constraint 1: Each customer assigned to exactly one position
    # ---------------------------------------------------------------
    A = penalty_assignment
    for ci in range(n_cust):
        for j in range(n_pos):
            v = var(ci, j)
            Q[v, v] += A * (1.0 - 2.0)
        for j in range(n_pos):
            for k in range(j + 1, n_pos):
                v1, v2 = var(ci, j), var(ci, k)
                Q[v1, v2] += 2.0 * A

    # ---------------------------------------------------------------
    # Constraint 2: Each position occupied by at most one customer
    # ---------------------------------------------------------------
    for pos in range(n_pos):
        for ci in range(n_cust):
            for ck in range(ci + 1, n_cust):
                v1, v2 = var(ci, pos), var(ck, pos)
                Q[v1, v2] += 2.0 * A

    # Symmetrise
    Q = (Q + Q.T) / 2.0

    return Q, n_cust, n_pos


def qubo_to_ising(Q: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Convert a QUBO matrix into an Ising Hamiltonian (J, h, offset).

    Mapping: x_i = (1 - s_i) / 2 where s_i ∈ {-1, +1} (eigenvalues of Pauli Z).
    Energy: E = s^T J s + h^T s + offset.

    Returns
    -------
    (J, h, offset)
        J : np.ndarray, shape (N, N), symmetric zero-diagonal coupling matrix.
        h : np.ndarray, shape (N,), local longitudinal magnetic field.
        offset : float, scalar energy shift.
    """
    n = Q.shape[0]
    Q_sym = (Q + Q.T) / 2.0

    J = np.zeros((n, n), dtype=float)
    h = np.zeros(n, dtype=float)
    offset = 0.0

    for i in range(n):
        h[i] -= Q_sym[i, i] / 2.0
        offset += Q_sym[i, i] / 2.0
        for j in range(i + 1, n):
            w = 2.0 * Q_sym[i, j]
            J[i, j] = w / 8.0
            J[j, i] = w / 8.0
            h[i] -= w / 4.0
            h[j] -= w / 4.0
            offset += w / 4.0

    return J, h, float(offset)


def build_basis_energies(Q: np.ndarray, n_vars: int) -> tuple[np.ndarray, np.ndarray]:
    """Precompute QUBO energies for all 2^n_vars computational basis states.

    Returns (bit_matrix, energies).
    """
    n_states = 2 ** n_vars
    bit_matrix = ((np.arange(n_states)[:, None] >> np.arange(n_vars)) & 1).astype(float)
    # Energy: E_z = x_z^T Q x_z
    energies = np.einsum("bi,ij,bj->b", bit_matrix, Q, bit_matrix)
    return bit_matrix, energies


def qubo_energy(Q: np.ndarray, x: np.ndarray) -> float:
    """Compute QUBO energy x^T Q x for a binary vector x."""
    return float(x @ Q @ x)


def decode_qubo_solution(
    x: np.ndarray,
    n_cust: int,
    n_pos: int,
) -> list[int]:
    """Decode a binary QUBO solution to a customer visit permutation."""
    assignment = x.reshape(n_cust, n_pos)
    permutation = []
    for pos in range(n_pos):
        col = assignment[:, pos]
        assigned = np.where(col > 0.5)[0]
        if len(assigned) == 1:
            permutation.append(int(assigned[0]))
        else:
            return []
    if sorted(permutation) != list(range(n_cust)):
        return []
    return permutation


def brute_force_qubo(Q: np.ndarray, n_vars: int) -> tuple[np.ndarray, float]:
    """Brute-force enumeration of all 2^n_vars bitstrings (for n_vars ≤ 20)."""
    if n_vars > 20:
        raise ValueError(f"n_vars={n_vars} too large for brute force (max 20).")

    bit_matrix, energies = build_basis_energies(Q, n_vars)
    best_idx = int(np.argmin(energies))
    return bit_matrix[best_idx].copy(), float(energies[best_idx])
