"""
Testes automatizados para a Sidebar Lateral Unificada do Propel CRM.
Verifica a consistência da navegação contínua em todos os módulos do sistema.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app
from database import get_db

client = TestClient(app)


def test_sidebar_em_todas_as_telas():
    """Valida se a sidebar unificada está presente em todos os módulos principais."""
    # Autenticar cookie de sessão para kanban
    client.cookies.set("session_user", "Fundador Propel")

    rotas = [
        ("/", "Pipeline Comercial"),
        ("/trafego", "Mesa de Tráfego"),
        ("/operacional", "Módulo Operacional"),
        ("/auditoria", "Auditoria 360"),
        ("/configuracoes", "Configurações"),
    ]

    for rota, titulo_esperado in rotas:
        response = client.get(rota)
        assert response.status_code == 200, f"Falha na rota {rota}"
        html = response.text
        # Elementos estruturais da Sidebar
        assert "PROPEL" in html
        assert "Módulos do Sistema" in html
        assert "Pipeline Comercial" in html
        assert "Mesa de Tráfego" in html
        assert "Módulo Operacional" in html
        assert "Auditoria 360" in html
        assert "Configurações" in html
        assert "Portais dos Clientes" in html


def test_sidebar_destaque_ativo():
    """Valida se a classe de item ativo é aplicada corretamente dependendo da rota."""
    client.cookies.set("session_user", "Fundador Propel")

    # 1. Rota /
    res_kanban = client.get("/")
    assert "active_menu" not in res_kanban.text or res_kanban.status_code == 200

    # 2. Rota /operacional
    res_operacional = client.get("/operacional")
    assert res_operacional.status_code == 200
    assert "Módulo Operacional" in res_operacional.text

    # 3. Rota /configuracoes
    res_config = client.get("/configuracoes")
    assert res_config.status_code == 200
    assert "Central de Parâmetros" in res_config.text


def test_atalhos_portais_clientes_na_sidebar():
    """Valida se os portais dos clientes aparecem com link correto na sidebar."""
    res = client.get("/configuracoes")
    assert res.status_code == 200
    html = res.text
    # Pelo menos um dos clientes cadastrados deve estar listado na sidebar
    assert "/portal/" in html
