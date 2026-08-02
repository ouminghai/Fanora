from pathlib import Path

from sqlalchemy import text

from scripts.export_demo_data_sql import create_engine, export_sql
from scripts.import_demo_data_sql import import_sql


async def test_export_and_import_all_tables_except_alembic_version(tmp_path: Path):
    database_path = tmp_path / "demo.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    export_path = tmp_path / "demo.sql"
    engine = create_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE TABLE alembic_version (version_num TEXT PRIMARY KEY)"))
            await connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY, name TEXT NOT NULL, payload TEXT)"))
            await connection.execute(
                text("CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id), note TEXT)")
            )
            await connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('head-version')"))
            await connection.exec_driver_sql(
                "INSERT INTO parents (id, name, payload) VALUES (1, 'Fanora', '{\"score\":3,\"enabled\":true}')"
            )
            await connection.execute(text("INSERT INTO children (id, parent_id, note) VALUES (1, 1, 'story; memory')"))
    finally:
        await engine.dispose()

    await export_sql(database_url, export_path)
    exported_sql = export_path.read_text(encoding="utf-8")
    assert 'INSERT INTO "parents"' in exported_sql
    assert 'INSERT INTO "children"' in exported_sql
    assert 'INSERT INTO "alembic_version"' not in exported_sql

    engine = create_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("UPDATE alembic_version SET version_num = 'keep-this-version'"))
            await connection.execute(text("UPDATE parents SET name = 'changed' WHERE id = 1"))
            await connection.execute(text("INSERT INTO parents (id, name, payload) VALUES (2, 'stale row', NULL)"))
    finally:
        await engine.dispose()

    await import_sql(database_url, export_path)

    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            versions = (await connection.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
            parents = (await connection.execute(text("SELECT id, name, payload FROM parents ORDER BY id"))).all()
            children = (await connection.execute(text("SELECT id, parent_id, note FROM children"))).all()
    finally:
        await engine.dispose()

    assert versions == ["keep-this-version"]
    assert parents == [(1, "Fanora", '{"score":3,"enabled":true}')]
    assert children == [(1, 1, "story; memory")]
