"""Tests for sort utility."""
import pytest
from sort_utils import sort_numbers


def test_basic_sort():
    assert sort_numbers([3, 1, 2]) == [1, 2, 3]


def test_empty_input():
    assert sort_numbers([]) == []


def test_duplicates():
    assert sort_numbers([3, 1, 2, 1, 3]) == [1, 1, 2, 3, 3]


def test_negative_numbers():
    assert sort_numbers([-3, -1, -2, 0, 1]) == [-3, -2, -1, 0, 1]


def test_single_element():
    assert sort_numbers([42]) == [42]


def test_already_sorted():
    assert sort_numbers([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]
