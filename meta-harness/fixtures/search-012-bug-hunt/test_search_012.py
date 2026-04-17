from search_012 import solve


def test_roundtrip():
    assert solve([3, 2, 1]) == [1, 2, 3]


def test_duplicates_are_preserved():
    assert solve([3, 2, 1, 2]) == [1, 2, 2, 3]
