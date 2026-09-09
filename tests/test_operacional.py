"""
TESTES DO MÓDULO OPERACIONAL — PROPEL CRM
Cobre Roadmap Semanal (Semana 1 a 4), Checklist do Gestor e Gerador de Vitórias da Semana.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "propel_crm"))

from fastapi.testclient import TestClient
from app import app
from database import init_db, seed_operacional, get_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_operational_data():
    """Garante tabelas e dados operacionais populados."""
    init_db()
    seed_operacional()


def test_painel_operacional_renders():
    """Valida renderização da tela /operacional com dados do cliente e do roadmap."""
    response = client.get("/operacional")
    assert response.status_code == 200
    assert "Módulo Operacional" in response.text
    assert "Roadmap de 4 Semanas" in response.text
    assert "SEMANA 1" in response.text
    assert "SEMANA 2" in response.text
    assert "The AI Checklist" in response.text


def test_toggle_item_roadmap():
    """Valida alternância de status de um item do Roadmap via AJAX."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM roadmap_entregas LIMIT 1")
        item = cursor.fetchone()
        item_id = item["id"]

    # Marcar como concluído
    resp1 = client.post("/api/roadmap/toggle", data={"item_id": item_id, "novo_status": "concluido"})
    assert resp1.status_code == 200
    assert resp1.json()["novo_status"] == "concluido"

    # Reabrir
    resp2 = client.post("/api/roadmap/toggle", data={"item_id": item_id, "novo_status": "pendente"})
    assert resp2.status_code == 200
    assert resp2.json()["novo_status"] == "pendente"


def test_toggle_checklist_gestor():
    """Valida alternância de status do checklist operacional do gestor."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM checklist_operacional LIMIT 1")
        chk = cursor.fetchone()
        chk_id = chk["id"]

    resp = client.post("/api/checklist/toggle", data={"item_id": chk_id, "status_hoje": 1})
    assert resp.status_code == 200
    assert resp.json()["status_hoje"] == 1


def test_gerador_vitorias_semana():
    """Valida geração do texto formatado e link WhatsApp para envio das vitórias semanais."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes_trafego LIMIT 1")
        cid = cursor.fetchone()["id"]

    resp = client.get(f"/api/vitorias-semana/gerar?cliente_id={cid}&semana=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "Vitórias da Semana 1" in data["texto"]
    assert "wa.me" in data["wpp_link"]


def test_portal_cliente_exibe_roadmap():
    """Valida que o cliente visualiza o roadmap do mês no portal dele."""
    resp = client.get("/portal/odonto-camila")
    assert resp.status_code == 200
    assert "Cronograma do seu Mês de Tráfego" in resp.text
    assert "Semana 1" in resp.text
