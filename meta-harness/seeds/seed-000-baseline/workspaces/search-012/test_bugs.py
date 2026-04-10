import threading
import pytest
from array_utils import sliding_window_max, chunk, running_sum
from counter import ThreadSafeCounter
from parser import parse_config, parse_int, parse_bool


# --- array_utils tests ---

def test_sliding_window_max_basic():
    # FAILS due to off-by-one: window is too large
    assert sliding_window_max([1, 3, 2, 5, 4], 3) == [3, 5, 5]

def test_chunk_basic():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

def test_running_sum():
    assert running_sum([1, 2, 3, 4]) == [1, 3, 6, 10]


# --- counter tests ---

def test_counter_single_thread():
    c = ThreadSafeCounter()
    for _ in range(100):
        c.increment()
    assert c.get() == 100

def test_counter_threaded():
    # FAILS due to race condition: final count != 1000
    c = ThreadSafeCounter()
    threads = [threading.Thread(target=lambda: [c.increment() for _ in range(100)])
               for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert c.get() == 1000

def test_counter_reset():
    c = ThreadSafeCounter()
    c.increment()
    c.reset()
    assert c.get() == 0


# --- parser tests ---

def test_parse_config_zero_value():
    # FAILS due to type coercion: integer 0 is falsy → uses default 30 instead of 0
    result = parse_config({"timeout": 0})
    assert result["timeout"] == 0

def test_parse_config_defaults():
    result = parse_config({})
    assert result == {"timeout": 30, "retries": 3, "prefix": "default"}

def test_parse_int():
    assert parse_int("42") == 42
    assert parse_int("bad") is None

def test_parse_bool():
    assert parse_bool("true") is True
    assert parse_bool("false") is False
