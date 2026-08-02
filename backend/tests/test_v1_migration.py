from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_latest_schema_is_the_single_active_alembic_head() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    script = ScriptDirectory.from_config(Config(str(backend_dir / "alembic.ini")))

    assert script.get_heads() == ["20260801_0001"]
    assert script.get_revision("20260723_v1") is not None
    assert script.get_revision("20260801_0001") is not None
    assert len(list((backend_dir / "alembic" / "legacy_versions").glob("*.py"))) == 30
