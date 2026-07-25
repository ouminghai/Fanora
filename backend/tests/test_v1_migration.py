from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_v1_is_the_single_active_alembic_head() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    script = ScriptDirectory.from_config(Config(str(backend_dir / "alembic.ini")))

    assert script.get_heads() == ["20260723_v1"]
    assert len(list((backend_dir / "alembic" / "versions").glob("*.py"))) == 1
    assert len(list((backend_dir / "alembic" / "legacy_versions").glob("*.py"))) == 30
