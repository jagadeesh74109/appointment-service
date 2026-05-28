from fastapi.testclient import TestClient

from src.appointment_service.main import app
from src.common.security import create_access_token, decode_access_token


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "appointment"}


def test_jwt_claims_match_patient_contract():
    token = create_access_token("7", "Patient", "patient@example.com")
    payload = decode_access_token(token)

    assert payload["sub"] == "7"
    assert payload["role"] == "Patient"
    assert payload["email"] == "patient@example.com"
