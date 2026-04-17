from holdout_003 import baseline_status


def test_baseline_status():
    assert baseline_status()['implemented'] is False
