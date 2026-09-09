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

        # 6. Roadmap Semanal de Entregas (Semana 1 a 4)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            semana INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            frequencia TEXT NOT NULL,
            frequencia_cor TEXT NOT NULL,
            status TEXT DEFAULT 'pendente', -- 'pendente', 'em_andamento', 'concluido'
            data_conclusao TEXT DEFAULT '',
            FOREIGN KEY (cliente_id) REFERENCES clientes_trafego(id)
        )
        """)

        # 7. Checklist Operacional do Gestor de Tráfego (The AI Checklist)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_operacional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            acao TEXT NOT NULL,
            frequencia TEXT NOT NULL, -- 'Diária', 'Semanal', 'Mensal'
            ferramenta TEXT NOT NULL,
            metrica_sucesso TEXT NOT NULL,
            prompt_ia TEXT DEFAULT '',
            status_hoje INTEGER DEFAULT 0,
            data_execucao TEXT DEFAULT ''
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


def seed_operacional():
    """Alimenta o banco com os clientes reais e o ciclo do Roadmap de 4 semanas."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Clientes Oficiais da Agência
        clientes_iniciais = [
            ("Vivaventura Ecoturismo", "Passeios de Jipe e Barco em Ilhabela", "Gabriel Vivaventura", "5512982934171", "vivaventura-eco", 1800.0, 18.0),
            ("Land Point Turismo", "Lanchas e Flexboat em Ilhabela", "Rodrigo França", "5512991354250", "landpoint-ilhabela", 2500.0, 20.0),
            ("Rotamar Ilhabela Turismo", "Avistamento de Baleias e Lanchas", "Maycon Rotamar", "5512997123456", "rotamar-turismo", 1500.0, 15.0),
            ("Clínica Odonto Camila", "Odontologia Estética & Implantes", "Dra. Camila", "5511987654321", "odonto-camila", 1500.0, 25.0)
        ]

        for nome, seg, resp, wpp, token, verba, cpa in clientes_iniciais:
            cursor.execute("SELECT id FROM clientes_trafego WHERE magic_token = ?", (token,))
            if not cursor.fetchone():
                agora = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("""
                INSERT INTO clientes_trafego (nome_empresa, segmento, responsavel_nome, whatsapp, magic_token, verba_mensal, meta_cpa, status, data_inicio)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ativo', ?)
                """, (nome, seg, resp, wpp, token, verba, cpa, agora))

        # Obter IDs de clientes
        cursor.execute("SELECT id, nome_empresa FROM clientes_trafego")
        clientes_db = cursor.fetchall()

        # 2. Template de Entregas do Roadmap (Fiel à imagem oficial)
        entregas_template = [
            # SEMANA 1
            (1, "Contrato", "renovacao_automatica", "verde_escuro"),
            (1, "Pagamento Serviço", "todo_mes", "verde_limao"),
            (1, "Onboarding", "uma_unica_vez", "azul_claro"),
            (1, "Acessos e Configurações", "uma_unica_vez", "azul_claro"),
            (1, "Planejamento Estratégico", "trimestral", "azul_escuro"),
            (1, "Vitórias da Semana", "toda_semana", "amarelo"),
            # SEMANA 2
            (2, "Envio dos Criativos", "todo_mes", "verde_limao"),
            (2, "Pagamento Anúncios", "todo_mes", "verde_limao"),
            (2, "Campanhas de Anúncio", "todo_mes", "verde_limao"),
            (2, "Vitórias da Semana", "toda_semana", "amarelo"),
            # SEMANA 3
            (3, "Campanhas de Anúncio", "todo_mes", "verde_limao"),
            (3, "Testes e Validações de Públicos e Criativos", "todo_mes", "verde_limao"),
            (3, "Otimização", "todo_mes", "verde_limao"),
            (3, "Vitórias da Semana", "toda_semana", "amarelo"),
            # SEMANA 4
            (4, "Feedback e Relatórios", "todo_mes", "verde_limao"),
            (4, "Relatório Mensal", "todo_mes", "verde_limao"),
            (4, "Vitórias da Semana", "toda_semana", "amarelo"),
        ]

        for c in clientes_db:
            cid = c["id"]
            cursor.execute("SELECT id FROM roadmap_entregas WHERE cliente_id = ?", (cid,))
            if not cursor.fetchone():
                for semana, titulo, freq, cor in entregas_template:
                    cursor.execute("""
                    INSERT INTO roadmap_entregas (cliente_id, semana, titulo, frequencia, frequencia_cor, status)
                    VALUES (?, ?, ?, ?, ?, 'pendente')
                    """, (cid, semana, titulo, freq, cor))

        # 3. Itens do Checklist Operacional do Gestor com Prompts de IA (The AI Checklist)
        cursor.execute("SELECT count(*) as total FROM checklist_operacional")
        if cursor.fetchone()["total"] == 0:
            prompt_ctr = """Atue como um analista de performance de anúncios especializado em métricas de Facebook Ads/Google Ads.
Receba como entrada uma planilha exportada do gerenciador de anúncios contendo pelo menos as colunas: [Nome do Anúncio], [Data], [Frequência] e [CTR (%)], cobrindo duas semanas distintas.
Sua tarefa é:
1. Calcular a média de Frequência e média de CTR separadamente para cada uma das duas semanas.
2. Comparar a variação da CTR entre as semanas e identificar se ela está estável, crescente ou em queda.
3. Destacar anúncios que apresentaram alta Frequência (acima de [X]) e queda de CTR na comparação semanal.
4. Sugerir ações práticas para otimizar os anúncios com alta frequência e queda de CTR (fadiga de criativo, saturação).
Apresente o resultado em formato de tabela comparativa e traga um resumo em bullet points com recomendações."""

            prompt_criativos = """Atue como um estrategista de marketing e criativos para anúncios especializado em Facebook Ads, Instagram Ads e Google Ads.
Receba como entrada a transcrição de 5 anúncios em vídeo que já provaram ser de alta performance (CTR alto e conversão consistente).
Sua tarefa é:
1. Analisar os textos fornecidos, identificando os principais gatilhos mentais, propostas de valor e CTAs.
2. Criar novas variações de roteiros de anúncios, explorando diferentes ângulos criativos (storytelling, benefícios diretos, prova social, urgência, autoridade).
3. Garantir formato de vídeo curto (até 30 segundos), com abertura forte nos primeiros 3 segundos, corpo com diferenciais e CTA persuasivo.
Apresente em tabela com: Roteiro, Gatilho Mental Usado e Sugestão Visual."""

            prompt_publicos = """Atue como um analista de públicos e performance de campanhas de tráfego pago.
Receba como entrada uma planilha exportada do gerenciador de anúncios contendo: [Nome do Público], [Semana], [CPA] e [CTR (%)], cobrindo as duas últimas semanas.
Sua tarefa é:
1. Calcular a média de CPA e de CTR separadamente para cada público nas duas semanas.
2. Identificar e listar públicos com aumento no CPA e queda no CTR (indicando saturação).
3. Sugerir plano de ação: testar novos criativos, expandir segmentação, pausar ou criar Lookalike.
Apresente a análise organizada em tabela comparativa."""

            prompt_orcamento = """Atue como um analista de mídia paga especializado em otimização de orçamento de campanhas.
Receba como entrada uma planilha exportada com: [Nome da Campanha], [Semana], [Investimento] e [ROAS].
Sua tarefa é:
1. Calcular o ROAS de cada campanha nas duas semanas.
2. Classificar as campanhas em: Alta performance (aumentar verba), Média performance (ajustar) e Baixa performance (reduzir/pausar).
3. Indicar exatamente de quais campanhas retirar orçamento e para quais direcionar visando maximizar o retorno total.
Apresente a redistribuição em tabela acompanhada de justificativa estratégica."""

            prompt_benchmark = """Atue como um especialista em copywriting e modelagem de criativos para anúncios.
Receba a transcrição de anúncios de concorrentes que apresentaram alto engajamento.
Sua tarefa é:
1. Mapear padrões de comunicação, gatilhos mentais e tom de voz.
2. Criar novas versões adaptadas para o meu serviço de turismo/passeios, preservando a estrutura persuasiva.
3. Estruturar variações em storytelling, quebra de objeções e urgência.
Apresente em tabela com Nova Copy, Gatilho Mental e Sugestão de Formato."""

            prompt_tendencias = """Atue como um especialista em marketing digital e análise de tendências focado em conversões no turismo regional.
Segmento: [Turismo / Passeios de Barco / Pousadas / Ecoturismo].
Sua tarefa é:
1. Descrever 3 estratégias atuais com alto potencial de conversão para o segmento.
2. Para cada estratégia sugerir: formato recomendado (vídeo curto, carrossel, reels), tom e gatilhos mentais indicados, e ideia inicial de copy.
Apresente em tabela com Estratégia, Justificativa, Aplicação na Campanha e Exemplo Prático."""

            checklist_itens = [
                ("Monitoramento de Contas", "Conferir saldo das contas de anúncio", "Diária", "Escalai", "Todas contas ativas e com saldo", ""),
                ("Monitoramento de Contas", "Identificar ADS reprovados", "Diária", "Escalai", "0 campanhas reprovadas", ""),
                ("Monitoramento de Contas", "Detectar variações anormais de gasto", "Diária", "Escalai", "Gasto limite diário controlado", ""),
                ("Análise de Performance", "Analisar métricas-chave (CPA)", "Diária", "Escalai", "CPA dentro da meta", ""),
                ("Análise de Performance", "Detectar anúncios com alta frequência e queda de CTR", "Semanal", "ChatGPT", "CTR estável ou crescente", prompt_ctr),
                ("Gestão de Criativos", "Gerar novas ideias de criativos", "Semanal", "ChatGPT", "Novos criativos prontos", prompt_criativos),
                ("Gestão de Públicos", "Conferir públicos com saturação", "Semanal", "ChatGPT", "Audiências renovadas", prompt_publicos),
                ("Otimização de Orçamento", "Redistribuir verba entre campanhas", "Semanal", "ChatGPT", "ROAS mantido ou melhorado", prompt_orcamento),
                ("Relatórios e Comunicação", "Criar resumo diário de performance", "Diária", "Escalai", "Relatório entregue no dia", ""),
                ("Relatórios e Comunicação", "Relatório de Fechamento Mensal", "Mensal", "Escalai", "Relatório de Fechamento Entregue", ""),
                ("Pesquisa e Benchmark", "Monitorar criativos de concorrentes", "Mensal", "ChatGPT", "Insights aplicados", prompt_benchmark),
                ("Pesquisa e Benchmark", "Sugerir tendências para aplicar nas campanhas", "Mensal", "ChatGPT", "Tendências aplicadas", prompt_tendencias),
                ("Organizar tarefas no Kanban", "Gerir tarefas para nada cair no limbo", "Diária", "Propel CRM", "Nenhuma tarefa fora do kanban", "")
            ]

            for cat, acao, freq, fer, met, pr in checklist_itens:
                cursor.execute("""
                INSERT INTO checklist_operacional (categoria, acao, frequencia, ferramenta, metrica_sucesso, prompt_ia, status_hoje)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (cat, acao, freq, fer, met, pr))

        conn.commit()


if __name__ == "__main__":
    init_db()
    seed_operacional()
    print("Banco de dados SQLite inicializado e populado com o Módulo Operacional!")

