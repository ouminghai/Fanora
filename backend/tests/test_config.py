from app.core.config import Settings


def test_railway_postgres_urls_use_psycopg_driver() -> None:
    postgres = Settings(database_url="postgres://user:pass@host:5432/fanora")
    postgresql = Settings(database_url="postgresql://user:pass@host:5432/fanora")

    assert postgres.database_url == "postgresql+psycopg://user:pass@host:5432/fanora"
    assert postgresql.database_url == "postgresql+psycopg://user:pass@host:5432/fanora"


def test_frontend_origin_regex_is_optional() -> None:
    assert Settings(frontend_origin_regex="").cors_origin_regex is None
    assert Settings(frontend_origin_regex=r"https://fanora-git-.*\.vercel\.app").cors_origin_regex == (
        r"https://fanora-git-.*\.vercel\.app"
    )
