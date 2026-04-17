from app.service import healthcheck


def test_healthcheck():
    assert healthcheck() == {'ok': True}
