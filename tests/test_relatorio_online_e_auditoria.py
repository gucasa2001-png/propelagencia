import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app
from database import get_db

client = TestClient(app)


def test_relatorio_online_portal_rotamar():
    """Valida renderização do Relatório Executivo Online para Rotamar Turismo via magic token."""
    response = client.get("/portal/rotamar-turismo/relatorio")
    assert response.status_code == 200
    html = response.text
    assert "Rotamar Ilhabela Turismo" in html
    assert "Relatório de Performance & Entregas de Tráfego" in html
    assert "Termômetro de Performance do Mês" in html
    assert "Cronograma do Mês de Tráfego" in html
    assert "Auditoria de Presença Digital do Cliente" in html
    # Validar zeramento correto de métricas no relatório
    assert "R$ 0,00" in html
    assert "Novas Conversas" in html
    assert "leads</span>" in html
    assert "Aguardando primeiros leads" in html


def test_relatorio_online_cliente_id():
    """Valida acesso ao relatório executivo online via ID interno do cliente."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM clientes_trafego WHERE magic_token = 'rotamar-turismo'").fetchone()
        assert row is not None
        cid = row["id"]

    response = client.get(f"/cliente/{cid}/relatorio")
    assert response.status_code == 200
    assert "Rotamar Ilhabela Turismo" in response.text
    assert "Relatório Executivo Online" in response.text


def test_laudo_auditoria_portal_rotamar():
    """Valida laudo de Auditoria 360 no celular para Rotamar Turismo."""
    response = client.get("/portal/rotamar-turismo/auditoria")
    assert response.status_code == 200
    html = response.text
    assert "Rotamar Ilhabela Turismo" in html
    assert "Laudo Executivo de Presença & Conversão 360°" in html
    assert "4.1" in html  # Score real cadastrado para Rotamar
    assert "Instagram" in html
    assert "Google Meu Negócio" in html
    assert "Site & Landing Page" in html
    assert "Plano de Ação Recomendado" in html


def test_laudo_auditoria_cliente_id():
    """Valida acesso ao laudo de auditoria via ID do cliente."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM clientes_trafego WHERE magic_token = 'rotamar-turismo'").fetchone()
        cid = row["id"]

    response = client.get(f"/cliente/{cid}/auditoria")
    assert response.status_code == 200
    assert "Rotamar Ilhabela Turismo" in response.text
    assert "Índice Geral de Saúde" in response.text


def test_portal_cliente_has_relatorio_and_auditoria_links_and_zeroed_metrics():
    """Valida que o Portal do Cliente possui os botões online e exibe métricas limpas zeradas."""
    response = client.get("/portal/rotamar-turismo")
    assert response.status_code == 200
    html = response.text
    # Links dos novos módulos
    assert "/portal/rotamar-turismo/relatorio" in html
    assert "/portal/rotamar-turismo/auditoria" in html
    # Métricas zeradas
    assert "R$ 0,00" in html
    assert "Novas Conversas" in html
    assert "leads</span>" in html
    assert "Aguardando leads" in html
    assert "0 vendas fechadas" in html


def test_portal_invalid_tokens_return_404():
    """Valida que rotas com token inexistente retornam 404 adequadamente."""
    res_rel = client.get("/portal/token-inexistente-12345/relatorio")
    assert res_rel.status_code == 404

    res_aud = client.get("/portal/token-inexistente-12345/auditoria")
    assert res_aud.status_code == 404
