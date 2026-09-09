"""
Testes automatizados para a Central de Configurações, Gestão de Clientes,
Logotipos, Vitórias da Semana e Geração de Relatório Executivo Mensal em PDF.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import sqlite3

# Adicionar pasta do app ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "propel_crm"))

from app import app
from database import get_db

client = TestClient(app)


def test_configuracoes_page_render():
    """Valida se a página /configuracoes renderiza com código 200 e elementos visuais."""
    response = client.get("/configuracoes")
    assert response.status_code == 200
    html = response.text
    assert "Central de Configurações" in html or "Central de Parâmetros" in html
    assert "Gestão de Clientes" in html
    assert "Identidade Visual & Logos" in html
    assert "Vitórias da Semana" in html
    assert "Relatórios Mensais" in html


def test_cadastrar_novo_cliente_com_roadmap_automatico():
    """Valida criação de cliente e geração automática das 17 entregas do Roadmap."""
    payload = {
        "nome_empresa": "Pousada Ilha Bela Teste",
        "segmento": "Hospedagem & Charme",
        "responsavel_nome": "Marcos Pousadeiro",
        "whatsapp": "5512999990000",
        "magic_token": "pousada-ilha-bela-teste",
        "verba_mensal": "3000.0",
        "meta_cpa": "30.0",
        "logo_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=160",
        "cor_primaria": "#1E3A8A",
        "status": "ativo"
    }
    response = client.post("/api/configuracoes/cliente/salvar", data=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sucesso"] is True
    assert data["modo"] == "criacao"
    novo_id = data["cliente_id"]

    # Verificar no banco se criou as 17 entregas do roadmap
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as total FROM roadmap_entregas WHERE cliente_id = ?", (novo_id,))
        total_entregas = cursor.fetchone()["total"]
        assert total_entregas == 17

        # Verificar se inseriu métricas iniciais
        cursor.execute("SELECT count(*) as total FROM metricas_trafego WHERE cliente_id = ?", (novo_id,))
        assert cursor.fetchone()["total"] >= 1


def test_atualizar_logo_cliente():
    """Valida a troca e persistência de logotipo do cliente."""
    nova_logo = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=160"
    payload = {
        "cliente_id": 1,
        "logo_url": nova_logo,
        "cor_primaria": "#0D9488"
    }
    response = client.post("/api/configuracoes/cliente/logo", data=payload)
    assert response.status_code == 200
    assert response.json()["sucesso"] is True

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT logo_url FROM clientes_trafego WHERE id = 1")
        row = cursor.fetchone()
        assert row["logo_url"] == nova_logo


def test_customizar_vitorias_semana():
    """Valida salvar configuração customizada das vitórias da semana."""
    payload = {
        "cliente_id": 1,
        "semana": 2,
        "saudacao": "Olá, equipe Odonto Camila!",
        "destaques_custom": "Tivemos 15 novos agendamentos diretos no WhatsApp!",
        "proximos_passos": "Lançamento da nova campanha de clareamento."
    }
    response = client.post("/api/configuracoes/vitorias/salvar", data=payload)
    assert response.status_code == 200
    assert response.json()["sucesso"] is True

    # Verificar se o endpoint de geração reflete a customização
    res_wpp = client.get("/api/vitorias-semana/gerar?cliente_id=1&semana=2")
    assert res_wpp.status_code == 200
    txt = res_wpp.json()["texto"]
    assert "Olá, equipe Odonto Camila!" in txt
    assert "15 novos agendamentos diretos" in txt


def test_gerar_relatorio_pdf_download_binario():
    """Valida geração e download de PDF oficial com mime-type e header de anexo."""
    response = client.get("/api/cliente/1/relatorio/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]
    # Todo PDF válido começa com %PDF-
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_portal_cliente_pdf_download():
    """Valida download de PDF pela rota pública do portal via magic token."""
    response = client.get("/portal/odonto-camila/relatorio/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_portal_cliente_exibe_logo_e_botao_pdf():
    """Valida se o portal do cliente renderiza a logo e o botão de download de PDF."""
    response = client.get("/portal/odonto-camila")
    assert response.status_code == 200
    html = response.text
    assert "Baixar Relatório PDF" in html
    assert "/portal/odonto-camila/relatorio/pdf" in html
