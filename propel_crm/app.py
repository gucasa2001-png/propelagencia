"""
PROPEL CRM — SERVIDOR WEB LOCAL (FastAPI)
Plataforma Comercial com Login, Kanban Interativo, Alertas de Follow-up e Scripts da Franquia.
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3
import json
import re

from database import get_db, init_db, cadastrar_novo_cliente_completo
from relatorio_pdf import gerar_pdf_relatorio_mensal

def formatar_midia_url(url: str) -> dict:
    url = (url or "").strip()
    # 1. Google Drive (extrai ID do arquivo de qualquer formato de link)
    drive_match = re.search(r'(?:file/d/|id=)([-_\w]{20,})', url)
    if drive_match or "drive.google.com" in url:
        file_id = drive_match.group(1) if drive_match else ""
        return {
            "tipo": "drive",
            "embed_url": f"https://drive.google.com/file/d/{file_id}/preview" if file_id else url,
            "original_url": url,
            "file_id": file_id
        }
    # 2. YouTube
    yt_match = re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/))([\w-]{10,})', url)
    if yt_match:
        return {
            "tipo": "youtube",
            "embed_url": f"https://www.youtube.com/embed/{yt_match.group(1)}",
            "original_url": url
        }
    # 3. Loom
    loom_match = re.search(r'loom\.com/share/([\w-]+)', url)
    if loom_match:
        return {
            "tipo": "loom",
            "embed_url": f"https://www.loom.com/embed/{loom_match.group(1)}",
            "original_url": url
        }
    # 4. Vídeo direto MP4 / WebM
    if any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.ogg']):
        return {
            "tipo": "video_direto",
            "embed_url": url,
            "original_url": url
        }
    # 5. Padrão: Imagem
    return {
        "tipo": "imagem",
        "embed_url": url,
        "original_url": url
    }


def obter_clientes_sidebar() -> list:
    """Retorna lista de clientes ativos para o menu lateral em todas as páginas."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome_empresa, magic_token, logo_url, segmento FROM clientes_trafego WHERE status = 'ativo' ORDER BY nome_empresa ASC")
            return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []

app = FastAPI(title="Propel CRM — Sistema Comercial de Turismo")

# ── CAMADA DE OBSERVABILIDADE (OpenTelemetry + Sentry) ──────────────────────
try:
    from observability import setup_observability
    observability_status = setup_observability(app)
except Exception as e:
    observability_status = {"error": str(e), "sentry_active": False, "opentelemetry_active": False}

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/api/health")
def health_check():
    """Endpoint industrial de Health Check e Observabilidade."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "observability": observability_status,
        "database": "sqlite3_connected"
    }


@app.get("/api/sentry-debug")
def sentry_debug_trigger():
    """Endpoint de teste para verificar captura de erro no Sentry."""
    raise ZeroDivisionError("[Sentry Test] Verificação intencional de captura de exceção pela esteira de observabilidade.")


# ── ROTAS DE AUTENTICAÇÃO ──────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"erro": None})


@app.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(key="session_user", value=username, max_age=86400 * 30)
            return response
    return templates.TemplateResponse(request=request, name="login.html", context={"erro": "Usuário ou senha incorretos!"})


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_user")
    return response


# ── ROTAS PRINCIPAIS DO KANBAN ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def kanban_dashboard(request: Request):
    user = request.cookies.get("session_user")
    if not user:
        return RedirectResponse(url="/login")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads ORDER BY score DESC, id DESC")
        rows = cursor.fetchall()
        leads = [dict(r) for r in rows]

    # Organizar por estágios do Kanban
    colunas = {
        "novo_lead": [],
        "contato_feito": [],
        "reuniao_agendada": [],
        "proposta_enviada": [],
        "cliente_ativo": [],
        "descartado": []
    }

    agora = datetime.now()
    alertas_followup = 0

    for lead in leads:
        st = lead.get("status", "novo_lead")
        if st not in colunas:
            st = "novo_lead"

        # Cálculo de dias parado para alerta de follow-up (se > 3 dias em contato_feito)
        data_contato_str = lead.get("data_ultimo_contato") or lead.get("data_criacao")
        try:
            dt_contato = datetime.strptime(data_contato_str[:10], "%Y-%m-%d")
            dias_parado = (agora - dt_contato).days
        except Exception:
            dias_parado = 0

        lead["dias_parado"] = dias_parado
        lead["alerta_followup"] = (st == "contato_feito" and dias_parado >= 3)
        if lead["alerta_followup"]:
            alertas_followup += 1

        colunas[st].append(lead)

    # Estatísticas
    total_leads = len(leads)
    clientes_ativos = len(colunas["cliente_ativo"])
    em_negociacao = len(colunas["reuniao_agendada"]) + len(colunas["proposta_enviada"])

    return templates.TemplateResponse(request=request, name="kanban.html", context={
        "colunas": colunas,
        "total_leads": total_leads,
        "clientes_ativos": clientes_ativos,
        "em_negociacao": em_negociacao,
        "alertas_followup": alertas_followup,
        "user": user,
        "clientes_sidebar": obter_clientes_sidebar(),
        "active_menu": "kanban"
    })


# ── API ENDPOINTS (Mover card, salvar notas, atualizar marco) ──────────────

@app.post("/api/mover-lead")
def mover_lead(lead_id: int = Form(...), novo_status: str = Form(...)):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE leads 
        SET status = ?, data_ultimo_contato = ? 
        WHERE id = ?
        """, (novo_status, agora, lead_id))
        conn.commit()
    return {"status": "ok", "lead_id": lead_id, "novo_status": novo_status}


@app.post("/api/salvar-detalhes")
def salvar_detalhes(
    lead_id: int = Form(...),
    notas: str = Form(""),
    tipo_reuniao: str = Form(""),
    data_reuniao: str = Form("")
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE leads 
        SET notas = ?, tipo_reuniao = ?, data_reuniao = ?
        WHERE id = ?
        """, (notas, tipo_reuniao, data_reuniao, lead_id))
        conn.commit()
    return {"status": "ok"}


@app.post("/api/toggle-marco")
def toggle_marco(lead_id: int = Form(...), marco: str = Form(...), valor: int = Form(...)):
    marcos_validos = [
        "marco1_boas_vindas", "marco2_briefing_samuel",
        "marco3_script_whatsapp", "marco4_aprovacao_landing",
        "marco5_campanhas_no_ar"
    ]
    if marco not in marcos_validos:
        raise HTTPException(status_code=400, detail="Marco inválido")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE leads SET {marco} = ? WHERE id = ?", (valor, lead_id))
        conn.commit()
    return {"status": "ok"}


# ── SUÍTE DE TRÁFEGO PAGO, PORTAL DO CLIENTE & GAMIFICAÇÃO ─────────────────

@app.get("/portal/{token}", response_class=HTMLResponse)
def portal_cliente(request: Request, token: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE magic_token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Link do portal inválido ou expirado.")
        cliente = dict(row)

        cursor.execute("SELECT * FROM metricas_trafego WHERE cliente_id = ? ORDER BY id DESC LIMIT 1", (cliente["id"],))
        metricas_row = cursor.fetchone()
        metricas = dict(metricas_row) if metricas_row else {
            "mes_referencia": "Mês Atual",
            "investimento_total": 0.0,
            "conversas_whatsapp": 0,
            "vendas_tintim": 0,
            "faturamento_rastreado": 0.0,
            "ultima_atualizacao": "Hoje"
        }

        cursor.execute("SELECT * FROM criativos_aprovacao WHERE cliente_id = ? ORDER BY id DESC", (cliente["id"],))
        criativos = [dict(r) for r in cursor.fetchall()]
        for cr in criativos:
            cr["midia_info"] = formatar_midia_url(cr.get("midia_url", ""))

        cursor.execute("SELECT * FROM atividades_agencia WHERE cliente_id = ? ORDER BY id DESC LIMIT 6", (cliente["id"],))
        atividades = [dict(r) for r in cursor.fetchall()]

        # Roadmap de Entregas do Cliente (Semanas 1 a 4)
        cursor.execute("SELECT * FROM roadmap_entregas WHERE cliente_id = ? ORDER BY semana ASC, id ASC", (cliente["id"],))
        roadmap_rows = [dict(r) for r in cursor.fetchall()]
        roadmap_semanas = {1: [], 2: [], 3: [], 4: []}
        for item in roadmap_rows:
            s = item.get("semana", 1)
            if s in roadmap_semanas:
                roadmap_semanas[s].append(item)
        concluidos = sum(1 for item in roadmap_rows if item.get("status") == "concluido")
        progresso_roadmap = int(concluidos / len(roadmap_rows) * 100) if roadmap_rows else 0

    return templates.TemplateResponse(request=request, name="portal_cliente.html", context={
        "cliente": cliente,
        "metricas": metricas,
        "criativos": criativos,
        "atividades": atividades,
        "roadmap_semanas": roadmap_semanas,
        "progresso_roadmap": progresso_roadmap
    })


@app.post("/portal/{token}/aprovar/{criativo_id}")
def aprovar_criativo(token: str, criativo_id: int):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE magic_token = ?", (token,))
        cliente = cursor.fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        cursor.execute("SELECT * FROM criativos_aprovacao WHERE id = ? AND cliente_id = ?", (criativo_id, cliente["id"]))
        criativo = cursor.fetchone()
        if not criativo:
            raise HTTPException(status_code=404, detail="Criativo não encontrado")

        cursor.execute("""
        UPDATE criativos_aprovacao 
        SET status = 'aprovado', data_aprovacao = ?
        WHERE id = ?
        """, (agora, criativo_id))

        # Recompensa de Gamificação (+50 XP para a equipe)
        cursor.execute("""
        INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
        VALUES (?, ?, ?, ?, ?)
        """, ('Samuel Tráfego', f"Anúncio '{criativo['titulo']}' aprovado pelo cliente!", 50, 'aprovacao', agora))

        # Registrar na Linha do Tempo do Cliente
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES (?, ?, ?, ?)
        """, (cliente["id"], f"Anúncio '{criativo['titulo']}' aprovado e agendado para veiculação", 'campanha', agora))

        conn.commit()

    return RedirectResponse(url=f"/portal/{token}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/portal/{token}/ajuste/{criativo_id}")
def solicitar_ajuste(token: str, criativo_id: int, feedback: str = Form(...)):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE magic_token = ?", (token,))
        cliente = cursor.fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        cursor.execute("""
        UPDATE criativos_aprovacao 
        SET status = 'ajuste', feedback_cliente = ?
        WHERE id = ? AND cliente_id = ?
        """, (feedback, criativo_id, cliente["id"]))

        # Registrar na Linha do Tempo
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES (?, ?, ?, ?)
        """, (cliente["id"], f"Ajuste solicitado no anúncio: {feedback[:40]}...", 'criativo', agora))

        conn.commit()

    return RedirectResponse(url=f"/portal/{token}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/trafego", response_class=HTMLResponse)
def painel_trafego(request: Request):
    with get_db() as conn:
        cursor = conn.cursor()

        # Clientes
        cursor.execute("SELECT * FROM clientes_trafego ORDER BY id ASC")
        clientes = [dict(r) for r in cursor.fetchall()]

        # Criativos com dados do cliente
        cursor.execute("""
        SELECT c.*, cl.nome_empresa as empresa_nome, cl.magic_token
        FROM criativos_aprovacao c
        JOIN clientes_trafego cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
        """)
        todos_criativos = [dict(r) for r in cursor.fetchall()]

        criativos_pendentes = [c for c in todos_criativos if c["status"] == "pendente"]
        criativos_ajuste = [c for c in todos_criativos if c["status"] == "ajuste"]
        criativos_aprovados = [c for c in todos_criativos if c["status"] == "aprovado"]

        for cr in todos_criativos:
            cr["midia_info"] = formatar_midia_url(cr.get("midia_url", ""))

        # Gamificação Total XP
        cursor.execute("SELECT COALESCE(SUM(pontos), 0) as total FROM gamificacao_equipe WHERE gestor_nome LIKE 'Samuel%'")
        total_xp = cursor.fetchone()["total"]

        # Histórico recente de pontos
        cursor.execute("SELECT * FROM gamificacao_equipe ORDER BY id DESC LIMIT 5")
        extrato_xp = [dict(r) for r in cursor.fetchall()]

    return templates.TemplateResponse(request=request, name="painel_trafego.html", context={
        "clientes": clientes,
        "criativos_pendentes": criativos_pendentes,
        "criativos_ajuste": criativos_ajuste,
        "criativos_aprovados": criativos_aprovados,
        "total_xp": total_xp,
        "extrato_xp": extrato_xp,
        "clientes_sidebar": obter_clientes_sidebar(),
        "active_menu": "trafego"
    })


@app.post("/trafego/novo-criativo")
def criar_novo_criativo(
    cliente_id: int = Form(...),
    titulo: str = Form(...),
    formato: str = Form("video"),
    midia_url: str = Form(...),
    texto_copy: str = Form(...),
    publico_alvo: str = Form("Público Local")
):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO criativos_aprovacao (cliente_id, titulo, midia_url, formato, texto_copy, publico_alvo, status, data_envio)
        VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
        """, (cliente_id, titulo.strip(), midia_url.strip(), formato, texto_copy.strip(), publico_alvo.strip(), agora))

        # Adicionar à Linha do Tempo do Cliente
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES (?, ?, 'criativo', ?)
        """, (cliente_id, f"Novo anúncio '{titulo}' preparado para sua aprovação", agora))

        # Recompensa de Gamificação: +30 XP por cadastrar criativo
        cursor.execute("""
        INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
        VALUES ('Samuel Tráfego', ?, 30, 'producao', ?)
        """, (f"Novo criativo '{titulo}' cadastrado", agora))

        conn.commit()

    return RedirectResponse(url="/trafego", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/trafego/checklist")
def registrar_checklist(item: str = Form(...), pontos: int = Form(20)):
    agora = datetime.now().strftime("%d/%m às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
        VALUES ('Samuel Tráfego', ?, ?, 'checklist_diario', ?)
        """, (f"Checklist cumprido: {item}", pontos, agora))
        conn.commit()
    return RedirectResponse(url="/trafego", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/webhook/tintim")
def webhook_tintim(request: Request, payload: dict = None):
    """
    Endpoint real para receber Webhooks do Tintim ou n8n.
    Espera JSON com: {'cliente_id': 1, 'evento': 'venda_confirmada', 'valor': 450.0}
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cliente_id = payload.get("cliente_id", 1) if payload else 1
        valor = float(payload.get("valor", 0.0)) if payload else 0.0

        cursor.execute("""
        UPDATE metricas_trafego
        SET vendas_tintim = vendas_tintim + 1,
            faturamento_rastreado = faturamento_rastreado + ?
        WHERE cliente_id = ?
        """, (valor, cliente_id))

        agora = datetime.now().strftime("%d/%m às %H:%M")
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES (?, ?, 'relatorio', ?)
        """, (cliente_id, f"Nova venda de R$ {valor:.2f} rastreada via Tintim no WhatsApp!", agora))

        conn.commit()
    return {"status": "sucesso", "mensagem": "Venda do Tintim computada com sucesso"}


@app.post("/api/criativo/mover-status")
def mover_status_criativo(criativo_id: int = Form(...), novo_status: str = Form(...)):
    """
    Endpoint assíncrono Pipedrive: atualiza o status do criativo via Drag & Drop sem recarregar tela.
    """
    if novo_status not in ["pendente", "ajuste", "aprovado"]:
        raise HTTPException(status_code=400, detail="Status inválido")

    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT c.*, cl.nome_empresa FROM criativos_aprovacao c JOIN clientes_trafego cl ON c.cliente_id = cl.id WHERE c.id = ?", (criativo_id,))
        criativo = cursor.fetchone()
        if not criativo:
            raise HTTPException(status_code=404, detail="Criativo não encontrado")

        if novo_status == "aprovado":
            cursor.execute("""
            UPDATE criativos_aprovacao 
            SET status = ?, data_aprovacao = ?
            WHERE id = ?
            """, (novo_status, agora, criativo_id))

            cursor.execute("""
            INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
            VALUES ('Samuel Tráfego', ?, 50, 'aprovacao', ?)
            """, (f"Anúncio '{criativo['titulo']}' aprovado via Drag & Drop!", agora))
            
            cursor.execute("""
            INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
            VALUES (?, ?, 'campanha', ?)
            """, (criativo["cliente_id"], f"Anúncio '{criativo['titulo']}' aprovado e agendado para subida", agora))
        else:
            cursor.execute("""
            UPDATE criativos_aprovacao 
            SET status = ?
            WHERE id = ?
            """, (novo_status, criativo_id))

        conn.commit()

        # Recalcular XP atual
        cursor.execute("SELECT COALESCE(SUM(pontos), 0) as total FROM gamificacao_equipe WHERE gestor_nome LIKE 'Samuel%'")
        novo_total_xp = cursor.fetchone()["total"]

    return {"status": "ok", "novo_status": novo_status, "total_xp": novo_total_xp}


@app.post("/api/webhook/tintim/simular")
def simular_webhook_tintim(cliente_id: int = Form(1), valor: float = Form(450.0)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE metricas_trafego
        SET vendas_tintim = vendas_tintim + 1,
            faturamento_rastreado = faturamento_rastreado + ?
        WHERE cliente_id = ?
        """, (valor, cliente_id))

        agora = datetime.now().strftime("%d/%m às %H:%M")
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES (?, ?, 'relatorio', ?)
        """, (cliente_id, f"Nova venda de R$ {valor:.2f} confirmada no WhatsApp (Tintim)!", agora))

        cursor.execute("""
        INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
        VALUES ('Samuel Tráfego', 'Nova venda no cliente gerada pelo tráfego (+ Tintim)', 30, 'conversao', ?)
        """, (agora,))

        conn.commit()

    return RedirectResponse(url="/trafego", status_code=status.HTTP_303_SEE_OTHER)


# ── ROTAS DO MÓDULO OPERACIONAL & ROADMAP ──────────────────────────────────

@app.get("/operacional", response_class=HTMLResponse)
def painel_operacional(request: Request, cliente_id: Optional[int] = None):
    with get_db() as conn:
        cursor = conn.cursor()

        # Lista de clientes ativos
        cursor.execute("SELECT * FROM clientes_trafego WHERE status = 'ativo' ORDER BY id ASC")
        clientes = [dict(r) for r in cursor.fetchall()]

        if not clientes:
            return HTMLResponse("Nenhum cliente cadastrado no momento.")

        # Cliente selecionado (padrão é o primeiro)
        if cliente_id is None:
            cliente_atual = clientes[0]
        else:
            cliente_atual = next((c for c in clientes if c["id"] == cliente_id), clientes[0])

        cid = cliente_atual["id"]

        # Roadmap de 4 Semanas do Cliente
        cursor.execute("SELECT * FROM roadmap_entregas WHERE cliente_id = ? ORDER BY semana ASC, id ASC", (cid,))
        roadmap_rows = [dict(r) for r in cursor.fetchall()]

        roadmap_semanas = {1: [], 2: [], 3: [], 4: []}
        for item in roadmap_rows:
            sem = item.get("semana", 1)
            if sem in roadmap_semanas:
                roadmap_semanas[sem].append(item)

        # Estatísticas de Conclusão do Roadmap
        total_itens = len(roadmap_rows)
        concluidos = sum(1 for r in roadmap_rows if r.get("status") == "concluido")
        progresso_mensal = int(concluidos / total_itens * 100) if total_itens > 0 else 0

        progresso_por_semana = {}
        for s in [1, 2, 3, 4]:
            itens_sem = roadmap_semanas[s]
            total_s = len(itens_sem)
            conc_s = sum(1 for i in itens_sem if i.get("status") == "concluido")
            progresso_por_semana[s] = int(conc_s / total_s * 100) if total_s > 0 else 0

        # Checklist Operacional do Gestor (The AI Checklist)
        cursor.execute("SELECT * FROM checklist_operacional ORDER BY id ASC")
        checklist_rows = [dict(r) for r in cursor.fetchall()]

        checklist_diario = [i for i in checklist_rows if i["frequencia"] == "Diária"]
        checklist_semanal = [i for i in checklist_rows if i["frequencia"] == "Semanal"]
        checklist_mensal = [i for i in checklist_rows if i["frequencia"] == "Mensal"]

    return templates.TemplateResponse(request=request, name="painel_operacional.html", context={
        "clientes": clientes,
        "cliente_atual": cliente_atual,
        "roadmap_semanas": roadmap_semanas,
        "progresso_mensal": progresso_mensal,
        "progresso_por_semana": progresso_por_semana,
        "checklist_diario": checklist_diario,
        "checklist_semanal": checklist_semanal,
        "checklist_mensal": checklist_mensal,
        "clientes_sidebar": obter_clientes_sidebar(),
        "active_menu": "operacional"
    })


@app.post("/api/roadmap/toggle")
def toggle_item_roadmap(item_id: int = Form(...), novo_status: str = Form(...)):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        data_concl = agora if novo_status == "concluido" else ""
        cursor.execute("""
        UPDATE roadmap_entregas
        SET status = ?, data_conclusao = ?
        WHERE id = ?
        """, (novo_status, data_concl, item_id))

        # Obter cliente e título para registrar atividade
        cursor.execute("SELECT cliente_id, titulo FROM roadmap_entregas WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if item and novo_status == "concluido":
            cursor.execute("""
            INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
            VALUES (?, ?, 'campanha', ?)
            """, (item["cliente_id"], f"Entrega '{item['titulo']}' marcada como concluída no Roadmap", agora))

        conn.commit()

    return {"sucesso": True, "novo_status": novo_status}


@app.post("/api/checklist/toggle")
def toggle_item_checklist(item_id: int = Form(...), status_hoje: int = Form(...)):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE checklist_operacional
        SET status_hoje = ?, data_execucao = ?
        WHERE id = ?
        """, (status_hoje, agora if status_hoje == 1 else "", item_id))
        conn.commit()

    return {"sucesso": True, "status_hoje": status_hoje}


@app.get("/api/vitorias-semana/gerar")
def gerar_vitorias_semana(cliente_id: int, semana: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        cursor.execute("SELECT * FROM roadmap_entregas WHERE cliente_id = ? AND semana = ?", (cliente_id, semana))
        itens_semana = [dict(r) for r in cursor.fetchall()]

        # Buscar configuração customizada de vitórias
        cursor.execute("SELECT * FROM vitorias_semana_config WHERE cliente_id = ? AND semana = ?", (cliente_id, semana))
        cfg_row = cursor.fetchone()
        cfg = dict(cfg_row) if cfg_row else {}

    concluidos = [i["titulo"] for i in itens_semana if i["status"] == "concluido"]
    pendentes = [i["titulo"] for i in itens_semana if i["status"] != "concluido"]

    itens_formatados = "\n".join([f"✅ {t}" for t in concluidos]) if concluidos else "✅ Todas as campanhas ativas e otimizadas!"
    
    # Destaques customizados se houver
    destaques_custom = cfg.get("destaques_custom", "").strip()
    if destaques_custom:
        itens_formatados += f"\n🌟 *Destaque Estratégico:* {destaques_custom}"

    proximos_texto = cfg.get("proximos_passos", "").strip()
    if not proximos_texto and pendentes:
        proximos_texto = "\n".join([f"🔜 {t}" for t in pendentes])

    proximos = f"\n\n🎯 *Próximos passos para a Semana {semana + 1 if semana < 4 else 1}:*\n{proximos_texto}" if proximos_texto else ""

    saudacao = cfg.get("saudacao", "").strip()
    if not saudacao:
        saudacao = f"Fala, {cliente['responsavel_nome']}! Passando com o resumo oficial das nossas *Vitórias da Semana {semana}* na {cliente['nome_empresa']}:"

    texto = (
        f"{saudacao}\n\n"
        f"{itens_formatados}"
        f"{proximos}\n\n"
        f"Qualquer dúvida estou à disposição por aqui. Seguimos firmes na meta! 🚀"
    )

    import urllib.parse
    texto_encoded = urllib.parse.quote(texto)
    tel = cliente["whatsapp"].replace("+", "").replace("-", "").replace(" ", "")
    wpp_link = f"https://wa.me/{tel}?text={texto_encoded}"

    return {"texto": texto, "wpp_link": wpp_link}


# ── ROTA E APIS DA CENTRAL DE AUDITORIA DIGITAL 360 ─────────────────────────

@app.get("/auditoria", response_class=HTMLResponse)
def auditoria_view(request: Request, lead_id: Optional[int] = None, cliente_id: Optional[int] = None):
    user = request.cookies.get("session_user") or "Especialista Propel"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cidade, nicho, instagram, url, whatsapp FROM leads ORDER BY score DESC, nome ASC")
        leads = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, nome_empresa, segmento, responsavel_nome, whatsapp FROM clientes_trafego WHERE status = 'ativo' ORDER BY nome_empresa ASC")
        clientes_trafego = [dict(r) for r in cursor.fetchall()]

        auditoria_previa = None
        if lead_id:
            cursor.execute("SELECT * FROM auditorias_digitais WHERE lead_id = ? ORDER BY id DESC LIMIT 1", (lead_id,))
            row = cursor.fetchone()
            if row:
                auditoria_previa = dict(row)
        elif cliente_id:
            cursor.execute("SELECT * FROM auditorias_digitais WHERE cliente_trafego_id = ? ORDER BY id DESC LIMIT 1", (cliente_id,))
            row = cursor.fetchone()
            if row:
                auditoria_previa = dict(row)

    return templates.TemplateResponse(request=request, name="auditoria.html", context={
        "user": user,
        "leads": leads,
        "clientes_trafego": clientes_trafego,
        "lead_id_selecionado": lead_id,
        "cliente_id_selecionado": cliente_id,
        "auditoria_previa": auditoria_previa,
        "clientes_sidebar": obter_clientes_sidebar(),
        "active_menu": "auditoria"
    })


@app.post("/api/auditoria/salvar")
async def salvar_auditoria_api(request: Request):
    dados = await request.json()
    lead_id = dados.get("lead_id")
    cliente_trafego_id = dados.get("cliente_trafego_id")
    nome_empresa = dados.get("nome_empresa", "Empresa Auditada")
    auditor = dados.get("auditor", "Especialista Propel")
    score_geral = float(dados.get("score_geral", 0.0))
    score_instagram = float(dados.get("score_instagram", 0.0))
    score_google = float(dados.get("score_google", 0.0))
    score_site = float(dados.get("score_site", 0.0))
    dados_json = json.dumps(dados.get("dados", {}), ensure_ascii=False)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        cursor = conn.cursor()

        auditoria_existente = None
        if lead_id:
            cursor.execute("SELECT id FROM auditorias_digitais WHERE lead_id = ?", (lead_id,))
            auditoria_existente = cursor.fetchone()
        elif cliente_trafego_id:
            cursor.execute("SELECT id FROM auditorias_digitais WHERE cliente_trafego_id = ?", (cliente_trafego_id,))
            auditoria_existente = cursor.fetchone()

        if auditoria_existente:
            aud_id = auditoria_existente["id"]
            cursor.execute("""
            UPDATE auditorias_digitais
            SET nome_empresa = ?, auditor = ?, score_geral = ?, score_instagram = ?, score_google = ?, score_site = ?, dados_json = ?, data_atualizacao = ?
            WHERE id = ?
            """, (nome_empresa, auditor, score_geral, score_instagram, score_google, score_site, dados_json, agora, aud_id))
        else:
            cursor.execute("""
            INSERT INTO auditorias_digitais (lead_id, cliente_trafego_id, nome_empresa, auditor, score_geral, score_instagram, score_google, score_site, dados_json, data_criacao, data_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (lead_id, cliente_trafego_id, nome_empresa, auditor, score_geral, score_instagram, score_google, score_site, dados_json, agora, agora))
            aud_id = cursor.lastrowid

        if cliente_trafego_id:
            cursor.execute("""
            INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
            VALUES (?, ?, 'relatorio', ?)
            """, (cliente_trafego_id, f"Auditoria Digital 360 realizada (Nota de Saúde: {score_geral:.1f}/10)", agora))

        conn.commit()

    return {"sucesso": True, "id": aud_id, "score_geral": score_geral, "data_atualizacao": agora}


@app.get("/api/auditoria/obter")
def obter_auditoria_api(lead_id: Optional[int] = None, cliente_id: Optional[int] = None, id: Optional[int] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        row = None
        if id:
            cursor.execute("SELECT * FROM auditorias_digitais WHERE id = ?", (id,))
            row = cursor.fetchone()
        elif lead_id:
            cursor.execute("SELECT * FROM auditorias_digitais WHERE lead_id = ? ORDER BY id DESC LIMIT 1", (lead_id,))
            row = cursor.fetchone()
        elif cliente_id:
            cursor.execute("SELECT * FROM auditorias_digitais WHERE cliente_trafego_id = ? ORDER BY id DESC LIMIT 1", (cliente_id,))
            row = cursor.fetchone()

        if not row:
            return {"encontrado": False}

        d = dict(row)
        try:
            d["dados"] = json.loads(d["dados_json"])
        except Exception:
            d["dados"] = {}
        del d["dados_json"]
        return {"encontrado": True, "auditoria": d}


@app.get("/api/auditoria/listar")
def listar_auditorias_api():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, lead_id, cliente_trafego_id, nome_empresa, auditor, score_geral, data_atualizacao FROM auditorias_digitais ORDER BY id DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        return {"total": len(rows), "auditorias": rows}


# ── ROTAS DA CENTRAL DE CONFIGURAÇÕES & RELATÓRIOS EM PDF ──────────────────

@app.get("/configuracoes", response_class=HTMLResponse)
def central_configuracoes(request: Request, cliente_id: Optional[int] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego ORDER BY id ASC")
        clientes = [dict(r) for r in cursor.fetchall()]

        if not clientes:
            cliente_atual = None
            vitorias_configs = []
        else:
            if cliente_id is None:
                cliente_atual = clientes[0]
            else:
                cliente_atual = next((c for c in clientes if c["id"] == cliente_id), clientes[0])

            cursor.execute("SELECT * FROM vitorias_semana_config WHERE cliente_id = ? ORDER BY semana ASC", (cliente_atual["id"],))
            vitorias_configs = [dict(r) for r in cursor.fetchall()]

    return templates.TemplateResponse(request=request, name="configuracoes.html", context={
        "clientes": clientes,
        "cliente_atual": cliente_atual,
        "vitorias_configs": vitorias_configs,
        "clientes_sidebar": obter_clientes_sidebar(),
        "active_menu": "configuracoes"
    })


@app.post("/api/configuracoes/cliente/salvar")
def salvar_cliente_config(
    cliente_id: Optional[int] = Form(None),
    nome_empresa: str = Form(...),
    segmento: str = Form(...),
    responsavel_nome: str = Form(...),
    whatsapp: str = Form(...),
    magic_token: str = Form(...),
    verba_mensal: float = Form(1500.0),
    meta_cpa: float = Form(15.0),
    logo_url: str = Form(""),
    cor_primaria: str = Form("#1E40AF"),
    status: str = Form("ativo")
):
    token_sanitizado = re.sub(r'[^a-zA-Z0-9_-]', '-', magic_token.strip().lower()).strip('-')
    
    with get_db() as conn:
        cursor = conn.cursor()
        if cliente_id:
            cursor.execute("""
            UPDATE clientes_trafego
            SET nome_empresa = ?, segmento = ?, responsavel_nome = ?, whatsapp = ?,
                magic_token = ?, verba_mensal = ?, meta_cpa = ?, logo_url = ?,
                cor_primaria = ?, status = ?
            WHERE id = ?
            """, (
                nome_empresa.strip(), segmento.strip(), responsavel_nome.strip(), whatsapp.strip(),
                token_sanitizado, verba_mensal, meta_cpa, logo_url.strip(),
                cor_primaria.strip(), status, cliente_id
            ))
            conn.commit()
            return {"sucesso": True, "cliente_id": cliente_id, "modo": "atualizacao"}
        else:
            cid = cadastrar_novo_cliente_completo({
                "nome_empresa": nome_empresa,
                "segmento": segmento,
                "responsavel_nome": responsavel_nome,
                "whatsapp": whatsapp,
                "magic_token": token_sanitizado,
                "verba_mensal": verba_mensal,
                "meta_cpa": meta_cpa,
                "logo_url": logo_url,
                "cor_primaria": cor_primaria
            })
            return {"sucesso": True, "cliente_id": cid, "modo": "criacao"}


@app.post("/api/configuracoes/cliente/logo")
def atualizar_logo_cliente(
    cliente_id: int = Form(...),
    logo_url: str = Form(...),
    cor_primaria: str = Form("#1E40AF")
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE clientes_trafego
        SET logo_url = ?, cor_primaria = ?
        WHERE id = ?
        """, (logo_url.strip(), cor_primaria.strip(), cliente_id))
        conn.commit()
    return {"sucesso": True, "cliente_id": cliente_id, "logo_url": logo_url}


@app.post("/api/configuracoes/vitorias/salvar")
def salvar_vitorias_config(
    cliente_id: int = Form(...),
    semana: int = Form(...),
    saudacao: str = Form(""),
    destaques_custom: str = Form(""),
    proximos_passos: str = Form("")
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO vitorias_semana_config (cliente_id, semana, saudacao, destaques_custom, proximos_passos)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cliente_id, semana) DO UPDATE SET
            saudacao = excluded.saudacao,
            destaques_custom = excluded.destaques_custom,
            proximos_passos = excluded.proximos_passos
        """, (cliente_id, semana, saudacao.strip(), destaques_custom.strip(), proximos_passos.strip()))
        conn.commit()
    return {"sucesso": True, "cliente_id": cliente_id, "semana": semana}


@app.get("/api/cliente/{cliente_id}/relatorio/pdf")
def baixar_relatorio_pdf(cliente_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes_trafego WHERE id = ?", (cliente_id,))
        cli_row = cursor.fetchone()
        if not cli_row:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        cliente = dict(cli_row)

        cursor.execute("SELECT * FROM metricas_trafego WHERE cliente_id = ? ORDER BY id DESC LIMIT 1", (cliente_id,))
        met_row = cursor.fetchone()
        metricas = dict(met_row) if met_row else {
            "mes_referencia": "Mês Vigente",
            "investimento_total": cliente.get("verba_mensal", 0.0),
            "conversas_whatsapp": 0,
            "vendas_tintim": 0,
            "faturamento_rastreado": 0.0
        }

        cursor.execute("SELECT * FROM roadmap_entregas WHERE cliente_id = ? ORDER BY semana ASC, id ASC", (cliente_id,))
        roadmap_itens = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT destaques_custom FROM vitorias_semana_config WHERE cliente_id = ? ORDER BY semana DESC LIMIT 1", (cliente_id,))
        vit_row = cursor.fetchone()
        vitorias_texto = vit_row["destaques_custom"] if vit_row and vit_row["destaques_custom"] else ""

    pdf_bytes = gerar_pdf_relatorio_mensal(cliente, metricas, roadmap_itens, vitorias_texto)
    nome_arquivo = f"Relatorio_Mensal_{cliente['magic_token']}_{datetime.now().strftime('%Y_%m')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"'
        }
    )


@app.get("/portal/{token}/relatorio/pdf")
def baixar_relatorio_pdf_portal(token: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes_trafego WHERE magic_token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Portal do cliente não encontrado")
        cid = row["id"]

    return baixar_relatorio_pdf(cliente_id=cid)


if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

