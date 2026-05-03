import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.database import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_hearthstone.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override DB dependency for testing
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Create tables before tests, drop them after
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

client = TestClient(app)

def test_full_workflow():
    """Test user creation and authorization"""
    resp = client.post("/auth/register", json={"username": "testplayer", "password": "strongpass123"})
    assert resp.status_code == 201
    
    resp = client.post("/auth/login", data={"username": "testplayer", "password": "strongpass123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    """Test card creation"""
    for i in range(15):
        client.post("/cards/me", json={"name": f"TestCard_{i}", "mana_cost": i % 8, "rarity": "common"}, headers=headers)
        client.post("/cards/me", json={"name": f"TestCard_{i}", "mana_cost": i % 8, "rarity": "common"}, headers=headers)

    resp = client.get("/cards/me", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 15

    """Test card deletion"""
    resp = client.delete("/cards/me/1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["new_quantity"] == 1

    resp = client.delete("/cards/me/1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["new_quantity"] == 0

    """Delete existing card"""
    resp = client.delete("/cards/me/1", headers=headers)
    assert resp.status_code == 404

    """Recreate card, as it will be used further in tests"""
    client.post("/cards/me", json={"name": "TestCard_0", "mana_cost": 0, "rarity": "common"}, headers=headers)
    client.post("/cards/me", json={"name": "TestCard_0", "mana_cost": 0, "rarity": "common"}, headers=headers)
