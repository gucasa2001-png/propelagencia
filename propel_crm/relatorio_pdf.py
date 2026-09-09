"""
PROPEL CRM — GERADOR DE RELATÓRIO EXECUTIVO MENSAL EM PDF
Utiliza ReportLab para gerar relatórios de tráfego, vendas e entregas com padrão industrial.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)

def hex_to_color(hex_str: str, default=colors.HexColor("#1E40AF")):
    try:
        if hex_str and hex_str.startswith("#"):
            return colors.HexColor(hex_str)
        return default
    except Exception:
        return default

def gerar_pdf_relatorio_mensal(cliente: dict, metricas: dict, roadmap_itens: list, vitorias_texto: str = "") -> bytes:
    """
    Gera o PDF executivo do relatório mensal do cliente e retorna os bytes do arquivo.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    story = []
    styles = getSampleStyleSheet()

    # Cores Oficiais Propel
    primary_color = colors.HexColor("#1E3A8A")   # Azul Marinho Nobre
    secondary_color = colors.HexColor("#0D9488") # Teal / Esmeralda
    text_dark = colors.HexColor("#0F172A")       # Slate 900
    text_muted = colors.HexColor("#64748B")      # Slate 500
    bg_card = colors.HexColor("#F8FAFC")         # Slate 50
    border_color = colors.HexColor("#E2E8F0")    # Slate 200

    # Estilos de Tipografia
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=secondary_color
    )
    heading2_style = ParagraphStyle(
        "ReportHeading2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4
    )
    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=text_dark
    )
    muted_style = ParagraphStyle(
        "ReportMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=text_muted
    )
    kpi_number_style = ParagraphStyle(
        "KPINumber",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        alignment=1, # Centralizado
        textColor=primary_color
    )
    kpi_label_style = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        alignment=1,
        textColor=text_muted
    )

    # ── 1. CABEÇALHO EXECUTIVO ─────────────────────────────────────────────
    header_table_data = [
        [
            Paragraph("<b>PROPEL AGENTES INTELIGENTES</b><br/><font color='#64748B' size='8'>Alta Performance em Tráfego & Automação Comercial</font>", normal_style),
            Paragraph(f"<font color='#1E3A8A' size='13'><b>RELATÓRIO MENSAL</b></font><br/><font color='#64748B' size='8'>Ciclo: {metricas.get('mes_referencia', 'Mês Atual')}</font>", ParagraphStyle('RAlign', parent=normal_style, alignment=2))
        ]
    ]
    header_table = Table(header_table_data, colWidths=[100 * mm, 74 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=4, spaceAfter=12))

    # ── 2. CARD DE IDENTIFICAÇÃO DO CLIENTE ─────────────────────────────────
    nome_empresa = cliente.get("nome_empresa", "Cliente")
    responsavel = cliente.get("responsavel_nome", "-")
    segmento = cliente.get("segmento", "-")
    whatsapp = cliente.get("whatsapp", "-")
    verba = float(cliente.get("verba_mensal", 0.0))
    meta_cpa = float(cliente.get("meta_cpa", 0.0))
    emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    info_data = [
        [
            Paragraph(f"<b>Empresa:</b> {nome_empresa}", normal_style),
            Paragraph(f"<b>Responsável:</b> {responsavel}", normal_style),
            Paragraph(f"<b>Emissão:</b> {emissao}", normal_style),
        ],
        [
            Paragraph(f"<b>Segmento:</b> {segmento}", normal_style),
            Paragraph(f"<b>WhatsApp:</b> {whatsapp}", normal_style),
            Paragraph(f"<b>Verba Contratada:</b> R$ {verba:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), normal_style),
        ]
    ]
    info_table = Table(info_data, colWidths=[64 * mm, 55 * mm, 55 * mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_card),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # ── 3. GRADE DE INDICADORES DE PERFORMANCE (KPIs) ───────────────────────
    story.append(Paragraph("📊 Indicadores Comerciais & Tráfego Pago", heading2_style))

    investimento = float(metricas.get("investimento_total", 0.0))
    conversas = int(metricas.get("conversas_whatsapp", 0))
    vendas = int(metricas.get("vendas_tintim", 0))
    faturamento = float(metricas.get("faturamento_rastreado", 0.0))

    cpa_real = (investimento / conversas) if conversas > 0 else 0.0
    roas = (faturamento / investimento) if investimento > 0 else 0.0

    kpi_card_data = [
        [
            Paragraph(f"R$ {investimento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), kpi_number_style),
            Paragraph(f"{conversas}", kpi_number_style),
            Paragraph(f"{vendas}", kpi_number_style),
            Paragraph(f"R$ {faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), kpi_number_style),
            Paragraph(f"R$ {cpa_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), kpi_number_style),
            Paragraph(f"{roas:.1f}x", kpi_number_style),
        ],
        [
            Paragraph("INVESTIMENTO TOTAL", kpi_label_style),
            Paragraph("LEADS NO WHATSAPP", kpi_label_style),
            Paragraph("VENDAS CONFIRMADAS", kpi_label_style),
            Paragraph("FATURAMENTO RASTREADO", kpi_label_style),
            Paragraph(f"CPA MÉDIO (META R$ {meta_cpa:.0f})", kpi_label_style),
            Paragraph("ROAS ESTIMADO", kpi_label_style),
        ]
    ]
    col_w = 174 * mm / 6
    kpi_table = Table(kpi_card_data, colWidths=[col_w] * 6)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # ── 4. ROADMAP DE 4 SEMANAS (ENTREGAS DA AGÊNCIA) ──────────────────────
    story.append(Paragraph("🗺️ Roadmap de Entregas Operacionais do Ciclo", heading2_style))

    roadmap_table_data = [
        [
            Paragraph("<b>Semana</b>", ParagraphStyle('TH', parent=normal_style, fontName='Helvetica-Bold', textColor=colors.white)),
            Paragraph("<b>Entrega / Módulo</b>", ParagraphStyle('TH', parent=normal_style, fontName='Helvetica-Bold', textColor=colors.white)),
            Paragraph("<b>Frequência</b>", ParagraphStyle('TH', parent=normal_style, fontName='Helvetica-Bold', textColor=colors.white)),
            Paragraph("<b>Status Operacional</b>", ParagraphStyle('TH', parent=normal_style, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        ]
    ]

    total_entregas = len(roadmap_itens)
    concluidas_count = 0

    for item in roadmap_itens:
        sem = item.get("semana", 1)
        titulo = item.get("titulo", "")
        freq = item.get("frequencia", "").replace("_", " ").title()
        status_item = item.get("status", "pendente")
        
        if status_item == "concluido":
            concluidas_count += 1
            status_html = "<font color='#16A34A'><b>[✓] Concluído</b></font>"
        else:
            status_html = "<font color='#D97706'>[ ] Em Andamento</font>"

        roadmap_table_data.append([
            Paragraph(f"Semana {sem}", normal_style),
            Paragraph(titulo, normal_style),
            Paragraph(freq, muted_style),
            Paragraph(status_html, ParagraphStyle('ST', parent=normal_style, alignment=1)),
        ])

    roadmap_table = Table(roadmap_table_data, colWidths=[24 * mm, 80 * mm, 38 * mm, 32 * mm])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_card]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(roadmap_table)

    pct_concluido = int((concluidas_count / total_entregas * 100)) if total_entregas > 0 else 0
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Resumo de Execução:</b> {concluidas_count} de {total_entregas} entregas finalizadas ({pct_concluido}% do ciclo concluído).",
        ParagraphStyle('ExecSum', parent=normal_style, textColor=secondary_color, fontName='Helvetica-Bold')
    ))
    story.append(Spacer(1, 10))

    # ── 5. VITÓRIAS DA SEMANA & DIRETRIZES ESTRATÉGICAS ───────────────────
    story.append(Paragraph("🎯 Destaques de Performance & Próximos Passos", heading2_style))
    
    if not vitorias_texto:
        vitorias_texto = (
            f"1. As campanhas de Meta Ads e Google Ads foram monitoradas e otimizadas rigorosamente no período.<br/>"
            f"2. Os criativos de maior retenção geraram conversas diretas de alta intenção de compra no WhatsApp.<br/>"
            f"3. Otimização contínua de lances para manter o CPA dentro da meta de R$ {meta_cpa:.2f}."
        )

    vitorias_box = Table(
        [[Paragraph(vitorias_texto, normal_style)]],
        colWidths=[174 * mm]
    )
    vitorias_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_card),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vitorias_box)
    story.append(Spacer(1, 14))

    # ── 6. ASSINATURA & CHANCELA DA AGÊNCIA ───────────────────────────────
    footer_data = [
        [
            Paragraph("<b>Samuel Tráfego & Equipe de Performance</b><br/><font color='#64748B' size='8'>Gestão de Tráfego Pago • Propel Agentes</font>", normal_style),
            Paragraph("<b>Aprovado por:</b><br/><font color='#64748B' size='8'>Diretoria de Operações Propel CRM</font>", normal_style)
        ]
    ]
    footer_table = Table(footer_data, colWidths=[90 * mm, 84 * mm])
    footer_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(footer_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
