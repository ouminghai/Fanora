from app.core.config import Settings


def test_railway_postgres_urls_use_psycopg_driver() -> None:
    postgres = Settings(database_url="postgres://user:pass@host:5432/fanora")
    postgresql = Settings(database_url="postgresql://user:pass@host:5432/fanora")

    assert postgres.database_url == "postgresql+psycopg://user:pass@host:5432/fanora"
    assert postgresql.database_url == "postgresql+psycopg://user:pass@host:5432/fanora"
