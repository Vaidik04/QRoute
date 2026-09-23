"""
tests/test_encoding.py
======================
Unit tests for random-key encoding/decoding.
"""

import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.encoding import (
    random_keys_to_permutation,
    permutation_to_random_keys,
    clip_keys,
    validate_permutation,
)


class TestRandomKeyEncoding:
    def test_basic_permutation(self):
        keys = np.array([0.71, 0.12, 0.89, 0.34])
        perm = random_keys_to_permutation(keys)
        assert sorted(perm) == [0, 1, 2, 3]
        assert perm == [1, 3, 0, 2]  # argsort of [0.71, 0.12, 0.89, 0.34]

    def test_permutation_covers_all_customers(self):
        n = 20
        keys = np.random.default_rng(42).uniform(0, 1, n)
        perm = random_keys_to_permutation(keys)
        assert sorted(perm) == list(range(n))
        assert len(perm) == n

    def test_deterministic_with_same_keys(self):
        keys = np.array([0.5, 0.1, 0.9, 0.3, 0.7])
        p1 = random_keys_to_permutation(keys)
        p2 = random_keys_to_permutation(keys)
        assert p1 == p2

    def test_roundtrip_permutation_to_keys_and_back(self):
        """Encoding a permutation as keys then decoding should give same permutation."""
        perm = [3, 0, 2, 1, 4]
        keys = permutation_to_random_keys(perm)
        recovered = random_keys_to_permutation(keys)
        assert recovered == perm

    def test_single_customer(self):
        keys = np.array([0.42])
        perm = random_keys_to_permutation(keys)
        assert perm == [0]

    def test_500_customers(self):
        n = 500
        keys = np.random.default_rng(0).uniform(0, 1, n)
        perm = random_keys_to_permutation(keys)
        assert len(perm) == n
        assert sorted(perm) == list(range(n))

    def test_clip_keys_in_range(self):
        keys = np.array([-0.5, 0.5, 1.5, 0.0, 1.0])
        clipped = clip_keys(keys)
        assert (clipped >= 0.0).all()
        assert (clipped <= 1.0).all()

    def test_validate_permutation_valid(self):
        assert validate_permutation([2, 0, 1, 3], 4) is True

    def test_validate_permutation_invalid_duplicate(self):
        assert validate_permutation([0, 0, 1, 2], 4) is False

    def test_validate_permutation_wrong_length(self):
        assert validate_permutation([0, 1, 2], 4) is False

    def test_tied_keys_still_valid_permutation(self):
        """Ties broken by numpy argsort — must still be valid permutation."""
        keys = np.array([0.5, 0.5, 0.5, 0.5])
        perm = random_keys_to_permutation(keys)
        assert sorted(perm) == [0, 1, 2, 3]
