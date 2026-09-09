"""
Testes automatizados para a Home Hub Executiva (Cockpit Central de Comando).
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app

client = TestClient(app)


def test_home_page_renders_cockpit():
    """Valida se a rota / renderiza o Cockpit Executivo com status 200 e métricas."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Cockpit Executivo" in html
    assert "Meta Espanha" in html
    assert "Clientes de Tráfego" in html
    assert "Pipeline Comercial" in html
    assert "Módulos da Assessoria" in html
    assert "Clientes Ativos na Assessoria" in html
    assert "Linha do Tempo da Agência" in html


def test_crm_and_kanban_routes():
    """Valida se as rotas /crm e /kanban mantêm o pipeline comercial ativo."""
    client.cookies.set("session_user", "Fundador Propel")

    res_crm = client.get("/crm")
    assert res_crm.status_code == 200
    assert "PROPEL AGENTES" in res_crm.text
    assert "kanban-col" in res_crm.text

    res_kanban = client.get("/kanban")
    assert res_kanban.status_code == 200
    assert "kanban-col" in res_kanban.text


def test_sidebar_includes_home_and_crm():
    """Valida se a sidebar tem o atalho Início (Cockpit) e o link para /crm."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert 'Início (Cockpit)' in html
    assert 'href="/crm"' in html
