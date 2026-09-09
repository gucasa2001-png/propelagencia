"""
PROPEL CRM — SERVIDOR WEB LOCAL (FastAPI)
Plataforma Comercial com Login, Kanban Interativo, Alertas de Follow-up e Scripts da Franquia.
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import re

from database import get_db, init_db

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
        "user": user
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

    return templates.TemplateResponse(request=request, name="portal_cliente.html", context={
        "cliente": cliente,
        "metricas": metricas,
        "criativos": criativos,
        "atividades": atividades
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
        "extrato_xp": extrato_xp
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


if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
