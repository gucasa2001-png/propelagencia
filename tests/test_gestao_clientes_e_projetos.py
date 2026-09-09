"""
Testes automatizados para:
1. Adição de novos clientes com seleção do plano de projeto (Lite, Soft, Gold).
2. Divisão das entregas nos 3 projetos oficiais da proposta Rotamar.
3. Exibição das abas e badges no Painel Operacional (/operacional) e Configurações (/configuracoes).
4. Exclusão segura de clientes e cascata no banco de dados SQLite.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app
from database import get_db

client = TestClient(app)


def test_configuracoes_render_botoes_e_projetos():
    """Valida se /configuracoes renderiza botão de cadastro, tabela, modal e abas de projetos."""
    response = client.get("/configuracoes")
    assert response.status_code == 200
    html = response.text

    assert "Cadastrar Novo Cliente" in html
    assert "modal-cliente" in html
    assert "modal-excluir" in html
    assert "Projeto Lite Propel" in html
    assert "Projeto Soft Propel" in html
    assert "Projeto Gold Propel" in html
    assert "Projetos da Proposta" in html


def test_cadastrar_cliente_com_plano_soft():
    """Valida cadastro de cliente com plano_projeto='soft' e associação correta das entregas."""
    token = f"teste-soft-{uuid.uuid4().hex[:8]}"
    payload = {
        "nome_empresa": "Turismo Soft Teste Ltda",
        "segmento": "Turismo e Receptivo",
        "responsavel_nome": "Juliana Viagens",
        "whatsapp": "5511988887777",
        "magic_token": token,
        "verba_mensal": "2500.0",
        "meta_cpa": "40.0",
        "logo_url": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=160",
        "cor_primaria": "#10B981",
        "status": "ativo",
        "plano_projeto": "soft"
    }

    res = client.post("/api/configuracoes/cliente/salvar", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["sucesso"] is True
    novo_id = data["cliente_id"]

    # Verificar no banco de dados
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE id = ?", (novo_id,))
        cliente = cursor.fetchone()
        assert cliente is not None
        assert cliente["plano_projeto"] == "soft"
        assert cliente["nome_empresa"] == "Turismo Soft Teste Ltda"

        # Verificar se as entregas do roadmap foram criadas e possuem projeto_tipo
        cursor.execute("SELECT count(*) as total FROM roadmap_entregas WHERE cliente_id = ?", (novo_id,))
        total = cursor.fetchone()["total"]
        assert total > 0

        # Pelo menos uma entrega deve ter projeto_tipo definido
        cursor.execute("SELECT count(*) as com_projeto FROM roadmap_entregas WHERE cliente_id = ? AND projeto_tipo IS NOT NULL", (novo_id,))
        com_projeto = cursor.fetchone()["com_projeto"]
        assert com_projeto > 0

    # Limpeza
    client.post(f"/api/configuracoes/cliente/excluir/{novo_id}")


def test_painel_operacional_exibe_badge_e_projetos():
    """Valida se o painel operacional exibe o badge do projeto contratado e a 4ª aba de projetos."""
    token = f"teste-operacional-{uuid.uuid4().hex[:8]}"
    payload = {
        "nome_empresa": "Passeios Gold Teste Ltda",
        "segmento": "Turismo e Passeios Náuticos",
        "responsavel_nome": "Rodrigo Gold",
        "whatsapp": "5511999998888",
        "magic_token": token,
        "verba_mensal": "4000.0",
        "meta_cpa": "35.0",
        "logo_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=160",
        "cor_primaria": "#D97706",
        "status": "ativo",
        "plano_projeto": "gold"
    }

    res_cad = client.post("/api/configuracoes/cliente/salvar", data=payload)
    assert res_cad.status_code == 200
    novo_id = res_cad.json()["cliente_id"]

    res = client.get(f"/operacional?cliente_id={novo_id}")
    assert res.status_code == 200
    html = res.text

    assert "Projeto Gold Propel" in html
    assert "Os 3 Projetos da Proposta" in html
    assert "aba-conteudo-projetos" in html
    assert "Fase I" in html
    assert "Fase II" in html
    assert "Fase III" in html
    assert "Fase IV" in html

    # Excluir cliente de teste
    res_del = client.post(f"/api/configuracoes/cliente/excluir/{novo_id}")
    assert res_del.status_code == 200
    assert res_del.json()["sucesso"] is True


def test_excluir_cliente_seguro():
    """Valida endpoint de exclusão segura removendo cliente e dados vinculados."""
    token = f"para-excluir-{uuid.uuid4().hex[:8]}"
    payload = {
        "nome_empresa": "Cliente Descartável Teste",
        "segmento": "Geral",
        "responsavel_nome": "Carlos Temporário",
        "whatsapp": "5511911112222",
        "magic_token": token,
        "verba_mensal": "1500.0",
        "meta_cpa": "50.0",
        "logo_url": "",
        "cor_primaria": "#3B82F6",
        "status": "ativo",
        "plano_projeto": "lite"
    }

    # Cadastrar
    res = client.post("/api/configuracoes/cliente/salvar", data=payload)
    cid = res.json()["cliente_id"]

    # Conferir existência
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes_trafego WHERE id = ?", (cid,))
        assert cursor.fetchone() is not None

        cursor.execute("SELECT count(*) as c FROM roadmap_entregas WHERE cliente_id = ?", (cid,))
        assert cursor.fetchone()["c"] > 0

    # Excluir via endpoint
    res_del = client.post(f"/api/configuracoes/cliente/excluir/{cid}")
    assert res_del.status_code == 200
    dados_del = res_del.json()
    assert dados_del["sucesso"] is True

    # Verificar que sumiu do banco e não sobrou resíduo no roadmap
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes_trafego WHERE id = ?", (cid,))
        assert cursor.fetchone() is None

        cursor.execute("SELECT count(*) as c FROM roadmap_entregas WHERE cliente_id = ?", (cid,))
        assert cursor.fetchone()["c"] == 0


def test_excluir_cliente_inexistente_retorna_404():
    """Valida se tentar excluir cliente inexistente retorna erro 404 amigável."""
    res = client.post("/api/configuracoes/cliente/excluir/999999")
    assert res.status_code == 404
    assert "detail" in res.json()
