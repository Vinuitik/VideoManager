import pytest
from fastapi.testclient import TestClient

# TestClient wraps the FastAPI app and handles the async event loop for you.
# It behaves like requests — synchronous, no await needed.
@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c
