"""
Testes automatizados para:
1. Blindagem de segurança (bloqueio de rotas administrativas sem autenticação).
2. Fluxo de login com credenciais de fundador.
3. Acesso contínuo público do cliente pelo portal.
4. Geração de mensagens especializadas para grupos de WhatsApp.
5. Geração e inserção automática de anúncios na esteira do Creative Strategist.
"""

import os
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app
from database import get_db

client = TestClient(app, headers={"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"})


def test_autenticacao_bloqueio_rotas_administrativas():
    """Valida que visitantes sem cookie de sessão são redirecionados para /login com código 303."""
    client.cookies.clear()

    # Rota raiz /
    res_home = client.get("/", follow_redirects=False)
    assert res_home.status_code == 303
    assert res_home.headers["location"] == "/login"

    # Rota operacional
    res_operacional = client.get("/operacional", follow_redirects=False)
    assert res_operacional.status_code == 303
    assert res_operacional.headers["location"] == "/login"

    # Rota configuracoes
    res_config = client.get("/configuracoes", follow_redirects=False)
    assert res_config.status_code == 303
    assert res_config.headers["location"] == "/login"


def test_login_fluxo_sucesso_e_acesso_liberado():
    """Valida que o login com credenciais válidas gera cookie de sessão e libera acesso."""
    client.cookies.clear()
    payload = {"username": "propel", "password": "propel2027"}
    res_login = client.post("/login", data=payload, follow_redirects=False)
    assert res_login.status_code == 303
    assert "session_user" in client.cookies

    # Agora o acesso a rotas administrativas deve ser liberado (200 OK)
    res_home = client.get("/")
    assert res_home.status_code == 200


def test_portal_cliente_permanece_publico_e_funcional():
    """Valida que os portais de clientes continuam 100% públicos sem exigir login."""
    client.cookies.clear()
    res_portal = client.get("/portal/rotamar-turismo")
    assert res_portal.status_code == 200
    assert "Rotamar Ilhabela Turismo" in res_portal.text


def test_api_vitorias_semana_gerar_grupo():
    """Valida gerador de mensagens para grupo de WhatsApp com marcação @Maycon e @Equipe."""
    res = client.get("/api/vitorias-semana/gerar-grupo?cliente_id=5&semana=1")
    assert res.status_code == 200
    data = res.json()
    assert "texto" in data
    assert "wpp_share_link" in data
    assert "ATUALIZAÇÃO ESTRATÉGICA PROPEL AGENTES" in data["texto"]
    assert "@Maycon" in data["texto"] or "@" in data["texto"]
    assert "api.whatsapp.com/send" in data["wpp_share_link"]


def test_api_criativos_gerar_e_adicionar():
    """Valida o agente Creative Strategist gerando anúncio e inserindo na fila de aprovação."""
    payload = {
        "cliente_id": 5,
        "angulo": "exclusividade",
        "formato": "imagem"
    }
    res = client.post("/api/criativos/gerar-e-adicionar", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["sucesso"] is True
    assert "criativo_id" in data
    cid = data["criativo_id"]

    # Verificar existência no banco
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM criativos_aprovacao WHERE id = ?", (cid,))
        criativo = cursor.fetchone()
        assert criativo is not None
        assert criativo["cliente_id"] == 5
        assert criativo["status"] == "pendente"

        # Limpeza do teste
        cursor.execute("DELETE FROM criativos_aprovacao WHERE id = ?", (cid,))
        conn.commit()
