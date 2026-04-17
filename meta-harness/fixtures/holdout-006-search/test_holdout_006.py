from holdout_006 import current_state


def test_fixture_loads():
    assert current_state()['status'] == 'baseline'
