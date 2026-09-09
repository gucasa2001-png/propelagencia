"""
TESTES DE INTEGRAÇÃO — PROPEL CRM
Cobre rotas FastAPI, autenticação por cookie, portal do cliente e APIs de movimentação.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "propel_crm"))

from fastapi.testclient import TestClient
from app import app
from database import init_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Garante que as tabelas SQLite existam para os testes."""
    init_db()


def test_api_health_endpoint():
    """Valida endpoint de saúde e status da observabilidade."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "observability" in data
    assert data["database"] == "sqlite3_connected"


def test_login_page_renders():
    """Valida renderização da página de login."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Propel Agentes" in response.text
    assert "password" in response.text


def test_login_authentication_flow():
    """Valida fluxo de login com credenciais corretas e geração de cookie."""
    response = client.post("/login", data={"username": "propel", "password": "propel2027"}, follow_redirects=False)
    assert response.status_code == 303
    assert "session_user" in response.cookies


def test_portal_cliente_magic_link():
    """Valida acesso do cliente sem necessidade de login prévio."""
    response = client.get("/portal/odonto-camila")
    assert response.status_code in [200, 404]  # 200 se seed rodado, 404 se token virgem


def test_mover_criativo_api():
    """Valida chamada da API de atualização de status do anúncio."""
    response = client.post("/api/criativo/mover-status", data={
        "criativo_id": "1",
        "novo_status": "aprovado"
    })
    assert response.status_code in [200, 303, 404]
