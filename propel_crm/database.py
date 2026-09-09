"""
PROPEL CRM — BANCO DE DADOS LOCAL (SQLite)
Gerencia leads, estágios de Kanban, alertas de follow-up e marcos de onboarding.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "propel_crm.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Tabela de Usuários para Login
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nome TEXT NOT NULL
        )
        """)

        # Tabela de Leads no Kanban
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cidade TEXT,
            nicho TEXT,
            url TEXT,
            telefone TEXT,
            whatsapp TEXT,
            instagram TEXT,
            tiktok TEXT,
            cnpj TEXT,
            razao_social TEXT,
            socios TEXT,
            frota TEXT,
            score INTEGER DEFAULT 0,
            prioridade TEXT DEFAULT 'MEDIA',
            tem_pixel_meta INTEGER DEFAULT 0,
            
            -- Kanban & Pipeline
            status TEXT DEFAULT 'novo_lead', 
            -- 'novo_lead', 'contato_feito', 'reuniao_agendada', 'proposta_enviada', 'cliente_ativo', 'descartado'
            
            tipo_reuniao TEXT DEFAULT '', -- 'presencial' ou 'online'
            data_reuniao TEXT DEFAULT '',
            
            -- Datas para controle de follow-up
            data_criacao TEXT NOT NULL,
            data_ultimo_contato TEXT,
            proximo_followup TEXT,
            dias_parado INTEGER DEFAULT 0,
            
            -- Notas e Observações Comerciais
            notas TEXT DEFAULT '',
            
            -- Marcos Onboarding McDonald's (0 ou 1)
            marco1_boas_vindas INTEGER DEFAULT 0,
            marco2_briefing_samuel INTEGER DEFAULT 0,
            marco3_script_whatsapp INTEGER DEFAULT 0,
            marco4_aprovacao_landing INTEGER DEFAULT 0,
            marco5_campanhas_no_ar INTEGER DEFAULT 0
        )
        """)

        # ── TABELAS DA SUÍTE DE TRÁFEGO PAGO LOCAL & PORTAL DO CLIENTE ──

        # 1. Clientes de Tráfego Pago
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes_trafego (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_empresa TEXT NOT NULL,
            segmento TEXT NOT NULL,
            responsavel_nome TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            magic_token TEXT UNIQUE NOT NULL,
            verba_mensal REAL DEFAULT 1500.0,
            meta_cpa REAL DEFAULT 15.0,
            status TEXT DEFAULT 'ativo',
            data_inicio TEXT NOT NULL
        )
        """)

        # 2. Métricas Diárias / Consolidadas de Tráfego
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_trafego (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            mes_referencia TEXT NOT NULL,
            investimento_total REAL DEFAULT 0.0,
            conversas_whatsapp INTEGER DEFAULT 0,
            vendas_tintim INTEGER DEFAULT 0,
            faturamento_rastreado REAL DEFAULT 0.0,
            ultima_atualizacao TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes_trafego(id)
        )
        """)

        # 3. Esteira de Criativos para Aprovação
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS criativos_aprovacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            midia_url TEXT NOT NULL,
            formato TEXT DEFAULT 'imagem', -- 'imagem' ou 'video'
            texto_copy TEXT NOT NULL,
            publico_alvo TEXT,
            status TEXT DEFAULT 'pendente', -- 'pendente', 'aprovado', 'ajuste'
            feedback_cliente TEXT DEFAULT '',
            data_envio TEXT NOT NULL,
            data_aprovacao TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes_trafego(id)
        )
        """)

        # 4. Linha do Tempo de Atividades da Agência (Gera Certeza ao Cliente)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS atividades_agencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            categoria TEXT DEFAULT 'otimizacao', -- 'otimizacao', 'criativo', 'campanha', 'relatorio'
            data_hora TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes_trafego(id)
        )
        """)

        # 5. Gamificação da Equipe / Gestores de Tráfego
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamificacao_equipe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gestor_nome TEXT NOT NULL,
            evento TEXT NOT NULL,
            pontos INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
        """)

        # Criar usuário padrão caso não exista
        cursor.execute("SELECT id FROM usuarios WHERE username = 'propel'")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO usuarios (username, password, nome)
            VALUES ('propel', 'propel2027', 'Fundador Propel')
            """)

        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Banco de dados SQLite inicializado com sucesso!")
