import os

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["CHECKPOINT_DATABASE_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_MODEL"] = ""

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
