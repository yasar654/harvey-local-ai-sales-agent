from fastapi.testclient import TestClient
from app.main import app


def test_core_crud_and_no_cloud_fallback(tmp_path, monkeypatch):
    from app import db, local_ai
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    # Force the remote-host guard so this test is deterministic even when
    # the developer happens to have Ollama running locally.
    monkeypatch.setattr(local_ai, "OLLAMA_URL", "https://invalid.example")
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        b = client.post('/api/businesses', json={"name":"TestCo","industry":"SaaS"})
        assert b.status_code == 200, b.text
        product = client.post('/api/products', json={"business_id":b.json()['id'],"name":"TestCRM","description":"A simple CRM"})
        assert product.status_code == 200, product.text
        prospect = client.post('/api/prospects', json={"product_id":product.json()['id'],"company":"Example Dental","source_text":"A clinic accepts bookings by phone."})
        assert prospect.status_code == 200, prospect.text
        # Ollama is intentionally absent in CI; the app must return explicit 503.
        result = client.post(f"/api/ai/icp/{product.json()['id']}")
        assert result.status_code == 503
        assert "no cloud fallback" in result.json()['detail'].lower()
        assert client.get('/api/logs').status_code == 200


def test_local_endpoint_policy(monkeypatch):
    from app import local_ai
    monkeypatch.setattr(local_ai, "OLLAMA_URL", "https://api.example.com")
    assert local_ai._local_base_url() is False
    monkeypatch.setattr(local_ai, "OLLAMA_URL", "http://127.0.0.1:11434")
    assert local_ai._local_base_url() is True


def test_research_reuses_stored_evidence_offline(tmp_path, monkeypatch):
    from app import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        b = client.post('/api/businesses', json={"name":"TestCo"}).json()
        product = client.post('/api/products', json={"business_id":b['id'],"name":"TestCRM","description":"CRM"}).json()
        prospect = client.post('/api/prospects', json={"product_id":product['id'],"company":"Stored Prospect","website":"https://invalid.example","source_text":"Downloaded public text: hiring a sales manager."}).json()
        with db.connect() as conn:
            conn.execute("UPDATE prospects SET research=? WHERE id=?",("Previously downloaded local evidence",prospect['id']))
        # Stored research must be returned without attempting any external request.
        result=client.post(f"/api/research/{prospect['id']}")
        assert result.status_code == 200
        assert result.json()['source'] == 'stored_offline'
        assert result.json()['research'] == 'Previously downloaded local evidence'


def test_research_blocks_local_hosts(tmp_path, monkeypatch):
    from app import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "private-host.db")
    with TestClient(app) as client:
        business = client.post('/api/businesses', json={"name": "TestCo"}).json()
        product = client.post('/api/products', json={"business_id": business['id'], "name": "TestProduct", "description": "Demo"}).json()
        prospect = client.post('/api/prospects', json={"product_id": product['id'], "company": "Local Host", "website": "http://127.0.0.1:9000/admin"}).json()
        response = client.post(f"/api/research/{prospect['id']}")
        assert response.status_code == 400
        assert "public http" in response.json()["detail"].lower()
