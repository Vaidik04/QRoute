"""
quantum/qaoa.py
===============
Quantum Approximate Optimization Algorithm (QAOA) Engine.

Demonstrates quantum circuit optimization on small VRP QUBO instances (4–6 customers).

Features:
1. Exact Statevector Quantum Simulator (Pure NumPy):
   - Implements unitary circuit evolution:
     |ψ(γ, β)⟩ = ∏_{l=1}^p e^{-i β_l H_B} e^{-i γ_l H_C} |+⟩^{⊗n}
   - Evaluates exact Hamiltonian expectation value ⟨ψ|H_C|ψ⟩ in 2^N Hilbert space.
   - Computes quantum approximation ratio and ground-state fidelity.
   - Zero external quantum framework dependencies required.
2. Classical Parameter Optimization (COBYLA / Nelder-Mead).
3. Optional Qiskit Aer backend when Qiskit is present in the environment.
4. Classical Simulated Annealing baseline fallback for N > 16.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import minimize


@dataclass
class QAOAResult:
    """Result of a QAOA run on a QUBO instance."""
    algorithm: str
    best_bitstring: np.ndarray
    best_energy: float
    permutation: list[int]
    feasible: bool
    n_qubits: int
    n_layers: int
    runtime_ms: float
    circuit_depth: Optional[int] = None
    expectation_value: Optional[float] = None
    approximation_ratio: Optional[float] = None
    ground_state_fidelity: Optional[float] = None
    optimal_gammas: list[float] = field(default_factory=list)
    optimal_betas: list[float] = field(default_factory=list)


def run_qaoa(
    Q: np.ndarray,
    n_cust: int,
    n_pos: int,
    n_layers: int = 2,
    seed: int = 42,
    max_iterations: int = 60,
    backend: str = "auto",
) -> QAOAResult:
    """Run QAOA on the given QUBO matrix.

    Parameters
    ----------
    Q : np.ndarray
        QUBO matrix from qubo.build_qubo_matrix().
    n_cust, n_pos : int
        Problem dimensions (n_qubits = n_cust * n_pos).
    n_layers : int
        QAOA circuit depth p.
    seed : int
    max_iterations : int
        Classical optimizer iterations.
    backend : str
        "auto" (default: statevector if n_qubits <= 16), "statevector", "qiskit", or "annealing".

    Returns
    -------
    QAOAResult
    """
    t_start = time.perf_counter()
    n_vars = n_cust * n_pos

    # 1. Statevector simulator (Pure NumPy, exact circuit dynamics for n_vars <= 16)
    if backend in ("auto", "statevector") and n_vars <= 16:
        return _run_qaoa_statevector(Q, n_cust, n_pos, n_vars, n_layers, seed, max_iterations, t_start)

    # 2. Try Qiskit if explicitly requested
    if backend in ("auto", "qiskit"):
        try:
            return _run_qaoa_qiskit(Q, n_cust, n_pos, n_vars, n_layers, seed, max_iterations, t_start)
        except ImportError:
            pass

    # 3. Fallback for larger instances (N > 16)
    return _run_simulated_annealing(Q, n_cust, n_pos, n_vars, seed, t_start)


# ---------------------------------------------------------------------------
# Pure NumPy Exact Quantum Statevector QAOA Simulator
# ---------------------------------------------------------------------------

def _run_qaoa_statevector(
    Q: np.ndarray,
    n_cust: int,
    n_pos: int,
    n_vars: int,
    n_layers: int,
    seed: int,
    max_iterations: int,
    t_start: float,
) -> QAOAResult:
    """Exact statevector evolution in 2^n_vars Hilbert space using pure NumPy."""
    from .qubo import build_basis_energies, decode_qubo_solution

    bit_matrix, energies = build_basis_energies(Q, n_vars)
    min_energy = float(np.min(energies))
    max_energy = float(np.max(energies))

    n_states = 2 ** n_vars
    rng = np.random.default_rng(seed)

    # Statevector evolution function: |ψ(γ, β)⟩
    def simulate_circuit(gammas: np.ndarray, betas: np.ndarray) -> np.ndarray:
        # Equal superposition: |+⟩^{⊗n}
        state = np.full(n_states, 1.0 / np.sqrt(n_states), dtype=complex)

        for l in range(n_layers):
            gamma_l = gammas[l]
            beta_l = betas[l]

            # 1. Cost unitary: e^{-i γ_l H_C}
            state = state * np.exp(-1j * gamma_l * energies)

            # 2. Mixer unitary: e^{-i β_l H_B} = ∏_k e^{-i β_l X_k}
            cos_b = np.cos(beta_l)
            sin_b = -1j * np.sin(beta_l)
            u_x = np.array([[cos_b, sin_b], [sin_b, cos_b]], dtype=complex)

            for k in range(n_vars):
                # Apply 2x2 gate to qubit k
                state = state.reshape(2 ** (n_vars - k - 1), 2, 2 ** k)
                state = np.einsum("ij,ajb->aib", u_x, state)

            state = state.reshape(-1)

        return state

    # Objective function for classical optimizer: expectation value ⟨ψ|H_C|ψ⟩
    def cost_func(params: np.ndarray) -> float:
        gammas = params[:n_layers]
        betas = params[n_layers:]
        state = simulate_circuit(gammas, betas)
        probs = np.abs(state) ** 2
        return float(np.sum(probs * energies))

    # Initial variational parameters [γ_1..γ_p, β_1..β_p]
    init_params = np.concatenate([
        rng.uniform(0.1, np.pi, size=n_layers),
        rng.uniform(0.1, np.pi / 2.0, size=n_layers),
    ])

    opt_res = minimize(
        cost_func,
        init_params,
        method="COBYLA",
        options={"maxiter": max_iterations, "tol": 1e-4},
    )

    opt_gammas = opt_res.x[:n_layers]
    opt_betas = opt_res.x[n_layers:]

    # Final optimal statevector
    final_state = simulate_circuit(opt_gammas, opt_betas)
    probabilities = np.abs(final_state) ** 2

    # Find candidate bitstrings sorted by measurement probability
    top_indices = np.argsort(probabilities)[::-1]

    # Select the lowest energy bitstring among high-probability measurements
    best_idx = int(top_indices[0])
    for idx in top_indices[:10]:
        if energies[idx] < energies[best_idx]:
            best_idx = int(idx)

    best_bitstring = bit_matrix[best_idx].copy()
    best_energy = float(energies[best_idx])
    permutation = decode_qubo_solution(best_bitstring, n_cust, n_pos)

    # Compute Quantum Metrics
    exp_val = float(np.sum(probabilities * energies))
    energy_span = max(1e-9, max_energy - min_energy)
    approx_ratio = float((max_energy - exp_val) / energy_span)

    # Ground-state fidelity: probability mass on true minimum energy states
    ground_mask = np.isclose(energies, min_energy, atol=1e-6)
    fidelity = float(np.sum(probabilities[ground_mask]))

    runtime_ms = (time.perf_counter() - t_start) * 1000

    return QAOAResult(
        algorithm="qaoa_statevector",
        best_bitstring=best_bitstring,
        best_energy=best_energy,
        permutation=permutation,
        feasible=len(permutation) == n_cust,
        n_qubits=n_vars,
        n_layers=n_layers,
        runtime_ms=runtime_ms,
        circuit_depth=n_layers * 2,
        expectation_value=round(exp_val, 4),
        approximation_ratio=round(approx_ratio, 4),
        ground_state_fidelity=round(fidelity, 4),
        optimal_gammas=[round(float(g), 4) for g in opt_gammas],
        optimal_betas=[round(float(b), 4) for b in opt_betas],
    )


# ---------------------------------------------------------------------------
# Qiskit Aer Simulator (Optional)
# ---------------------------------------------------------------------------

def _run_qaoa_qiskit(Q, n_cust, n_pos, n_vars, n_layers, seed, max_iterations, t_start):
    """QAOA implementation using Qiskit Aer simulator."""
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit.algorithms.minimum_eigensolvers import QAOA
    from qiskit.algorithms.optimizers import COBYLA
    from qiskit_aer.primitives import Sampler

    qp = QuadraticProgram()
    for i in range(n_vars):
        qp.binary_var(name=f"x{i}")

    linear = {f"x{i}": float(Q[i, i]) for i in range(n_vars)}
    quadratic = {}
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            if abs(Q[i, j]) > 1e-10:
                quadratic[(f"x{i}", f"x{j}")] = float(Q[i, j])
    qp.minimize(linear=linear, quadratic=quadratic)

    sampler = Sampler(run_options={"seed": seed, "shots": 1024})
    optimizer = COBYLA(maxiter=max_iterations)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=n_layers)
    solver = MinimumEigenOptimizer(qaoa)

    result = solver.solve(qp)
    x = np.array([result.x[i] for i in range(n_vars)])

    from .qubo import decode_qubo_solution, qubo_energy
    permutation = decode_qubo_solution(x, n_cust, n_pos)
    energy = qubo_energy(Q, x)

    return QAOAResult(
        algorithm="qaoa_qiskit_simulator",
        best_bitstring=x,
        best_energy=energy,
        permutation=permutation,
        feasible=len(permutation) == n_cust,
        n_qubits=n_vars,
        n_layers=n_layers,
        runtime_ms=(time.perf_counter() - t_start) * 1000,
        circuit_depth=n_layers * 2,
        expectation_value=float(result.fval) if hasattr(result, "fval") else None,
    )


# ---------------------------------------------------------------------------
# Classical Simulated Annealing Fallback
# ---------------------------------------------------------------------------

def _run_simulated_annealing(Q, n_cust, n_pos, n_vars, seed, t_start):
    """Simulated annealing fallback when n_vars > 16."""
    from .qubo import decode_qubo_solution, qubo_energy

    rng = np.random.default_rng(seed)
    x = rng.integers(0, 2, size=n_vars).astype(float)
    energy = qubo_energy(Q, x)
    best_x = x.copy()
    best_energy = energy

    T = 10.0
    T_min = 0.01
    cooling = 0.95

    while T > T_min:
        for _ in range(n_vars):
            flip_idx = int(rng.integers(0, n_vars))
            x_new = x.copy()
            x_new[flip_idx] = 1.0 - x_new[flip_idx]
            e_new = qubo_energy(Q, x_new)
            delta = e_new - energy
            if delta < 0 or rng.random() < np.exp(-delta / T):
                x = x_new
                energy = e_new
            if energy < best_energy:
                best_energy = energy
                best_x = x.copy()
        T *= cooling

    permutation = decode_qubo_solution(best_x, n_cust, n_pos)

    return QAOAResult(
        algorithm="simulated_annealing_fallback",
        best_bitstring=best_x,
        best_energy=best_energy,
        permutation=permutation,
        feasible=len(permutation) == n_cust,
        n_qubits=n_vars,
        n_layers=0,
        runtime_ms=(time.perf_counter() - t_start) * 1000,
    )
