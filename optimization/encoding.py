"""
optimization/encoding.py
========================
Random-key representation: the bridge between continuous QPSO positions
and discrete customer permutations.

Reference: Bean, J.C. (1994). "Genetic algorithms and random keys for
sequencing and optimization." ORSA Journal on Computing, 6(2), 154–160.

How it works
------------
Each customer is assigned a continuous key in [0, 1].  Sorting the keys
from smallest to largest produces a permutation of customers.  The QPSO
particle position IS the key vector — QPSO arithmetic is done on keys,
not on the permutation directly.

Example (n=8 customers):
    keys   = [0.71, 0.12, 0.89, 0.34, 0.53, 0.07, 0.65, 0.27]
    sorted → indices 5 1 7 3 4 6 0 2  (argsort)
    permutation of customer ids = [6, 2, 8, 4, 5, 7, 1, 3]  (1-indexed)

The decoder then walks this permutation left-to-right and assigns customers
to vehicles greedily while respecting capacity/time constraints.
"""

from __future__ import annotations

import numpy as np


def random_keys_to_permutation(keys: np.ndarray) -> list[int]:
    """Convert a real-valued key vector to a customer-visit permutation.

    Parameters
    ----------
    keys : np.ndarray, shape (n_customers,)
        Continuous values in [0, 1].  Each position i corresponds to
        customer i (0-indexed).

    Returns
    -------
    permutation : list[int]
        0-indexed customer ids sorted by ascending key value.
        Length == n_customers.  Each id appears exactly once.

    Example
    -------
    >>> keys = np.array([0.71, 0.12, 0.89, 0.34])
    >>> random_keys_to_permutation(keys)
    [1, 3, 0, 2]
    """
    return list(np.argsort(keys))


def permutation_to_random_keys(
    permutation: list[int],
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Convert a customer permutation back to a representative key vector.

    The inverse of ``random_keys_to_permutation`` is not unique (many key
    vectors map to the same permutation).  We produce one valid representative
    by spacing keys evenly in [0, 1] according to rank.

    Parameters
    ----------
    permutation : list[int]
        0-indexed customer ids specifying visit order.
    rng : optional Generator
        If provided, adds small jitter to avoid repeated ties.

    Returns
    -------
    keys : np.ndarray, shape (n_customers,)

    Example
    -------
    >>> perm = [1, 3, 0, 2]
    >>> permutation_to_random_keys(perm)
    array([0.5  , 0.125, 0.875, 0.375])
    """
    n = len(permutation)
    keys = np.empty(n, dtype=np.float64)
    # rank[i] = position at which customer i appears in the permutation
    rank = np.empty(n, dtype=int)
    for position, customer_id in enumerate(permutation):
        rank[customer_id] = position
    # Map rank 0..n-1 to evenly spaced keys in (0, 1)
    keys = (rank + 0.5) / n
    if rng is not None:
        noise = rng.uniform(-0.5 / n * 0.9, 0.5 / n * 0.9, size=n)
        keys = np.clip(keys + noise, 1e-9, 1.0 - 1e-9)
    return keys


def clip_keys(keys: np.ndarray) -> np.ndarray:
    """Clip key values to [0, 1] after QPSO arithmetic."""
    return np.clip(keys, 0.0, 1.0)


def validate_permutation(permutation: list[int], n_customers: int) -> bool:
    """Return True if permutation is a valid ordering of 0..n_customers-1."""
    if len(permutation) != n_customers:
        return False
    return sorted(permutation) == list(range(n_customers))


# Allow Optional type hint without importing typing explicitly
from typing import Optional  # noqa: E402 (intentional placement)
