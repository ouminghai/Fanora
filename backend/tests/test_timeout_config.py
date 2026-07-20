from app.core.config import settings


def test_database_connection_waits_up_to_one_minute():
    assert settings.database_pool_timeout_seconds == 60
    assert settings.database_connect_timeout_seconds == 60
