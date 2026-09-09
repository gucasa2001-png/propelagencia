"""
MÓDULO 2 — PROPEL AGENTES
Exportador de Leads Qualificados

Gera o arquivo LEADS_QUALIFICADOS.md pronto para usar
no bloco de prospecção da tarde.
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("exportador")
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "outputs"


def carregar_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def gerar_markdown(qualificados: list[dict], descartados: list[dict], config: dict):
    """Gera o arquivo LEADS_QUALIFICADOS.md formatado para leitura rápida."""
    caminho = OUTPUT_DIR / config["output"]["arquivo_leads_qualificados"]
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    alta_prioridade = [l for l in qualificados if "ALTA" in l.get("prioridade", "")]
    media_prioridade = [l for l in qualificados if "MÉDIA" in l.get("prioridade", "")]

    linhas = [
        f"# 🎯 Leads Qualificados — Propel Agentes",
        f"",
        f"> Gerado automaticamente em **{agora}**",
        f"> Total qualificados: **{len(qualificados)}** | Alta prioridade: **{len(alta_prioridade)}**",
        f"",
        f"---",
        f"",
    ]

    # ── Seção Alta Prioridade ─────────────────────────────────────────────
    if alta_prioridade:
        linhas += [
            f"## 🔥 Alta Prioridade ({len(alta_prioridade)} leads)",
            f"*Aborde esses primeiro — maior potencial de conversão*",
            f"",
        ]
        for i, lead in enumerate(alta_prioridade, 1):
            linhas += _formatar_lead(i, lead)

    # ── Seção Média Prioridade ────────────────────────────────────────────
    if media_prioridade:
        linhas += [
            f"",
            f"---",
            f"",
            f"## 🟡 Média Prioridade ({len(media_prioridade)} leads)",
            f"",
        ]
        for i, lead in enumerate(media_prioridade, 1):
            linhas += _formatar_lead(i, lead)

    # ── Rodapé ────────────────────────────────────────────────────────────
    linhas += [
        f"",
        f"---",
        f"",
        f"## 📊 Resumo da Rodada",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total coletado | {len(qualificados) + len(descartados)} |",
        f"| Qualificados | {len(qualificados)} |",
        f"| Alta prioridade | {len(alta_prioridade)} |",
        f"| Média prioridade | {len(media_prioridade)} |",
        f"| Descartados | {len(descartados)} |",
        f"",
        f"*Próxima atualização: rode `run.bat` novamente*",
    ]

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    log.info(f"✅ Relatório salvo em: {caminho}")
    return caminho


def _formatar_lead(numero: int, lead: dict) -> list[str]:
    """Formata um único lead com seu Dossiê Comercial completo em Markdown."""
    score = lead.get("score", 0)
    nome = lead.get("nome", "Sem nome")
    cidade = lead.get("cidade", "")
    nicho = lead.get("nicho", "")
    url = lead.get("url", "")
    telefone = lead.get("telefone", "—")
    whatsapp = lead.get("whatsapp", "")
    instagram = lead.get("instagram", "—")
    tiktok = lead.get("tiktok", "—")
    cnpj = lead.get("cnpj", "")
    razao = lead.get("razao_social", "")
    socios = lead.get("socios", [])
    tem_pixel = lead.get("tem_pixel_meta", False)
    tem_ga = lead.get("tem_google_analytics", False)
    tem_wpp_btn = lead.get("tem_botao_whatsapp", False)
    sinais_frota = lead.get("sinais_frota", [])
    sinais_comp = lead.get("sinais_compartilhado", [])
    pontos = lead.get("pontos_positivos", [])

    contato = f"[WhatsApp Direto]({whatsapp})" if (whatsapp and "wa.me" in whatsapp) else (whatsapp or telefone)
    ig_link = f"[{instagram}]({instagram})" if (instagram and instagram.startswith("http")) else instagram
    tt_link = f"[{tiktok}]({tiktok})" if (tiktok and tiktok.startswith("http")) else (tiktok or "Não detectado")

    linhas = [
        f"### {numero}. {nome}",
        f"**Score de ICP:** `{score}/100` | **Cidade:** {cidade} | **Foco:** {nicho}",
        f"",
        f"#### 💼 Dossiê Corporativo & Contato",
        f"| Dado | Informação |",
        f"|------|------------|",
        f"| 🌐 Site Oficial | [{url[:60]}...]({url}) |" if len(url) > 60 else f"| 🌐 Site Oficial | [{url}]({url}) |",
        f"| 📱 WhatsApp / Contato | **{contato}** |",
        f"| 📸 Instagram | {ig_link} |",
        f"| 🎵 TikTok | {tt_link} |",
    ]

    if cnpj:
        linhas.append(f"| 🏛️ CNPJ / Razão Social | `{cnpj}` — {razao} |")
    if socios:
        socios_str = ", ".join(socios)
        linhas.append(f"| 👥 **Sócios / Donos (QSA)** | **{socios_str}** |")

    linhas += [
        f"",
        f"#### 🛠️ Auditoria Técnica do Site",
        f"- **Pixel Meta (Facebook Ads):** {'🟢 ATIVO' if tem_pixel else '🔴 AUSENTE (Não rastreia tráfego pago!)'}",
        f"- **Google Analytics:** {'🟢 ATIVO' if tem_ga else '🟡 AUSENTE'}",
        f"- **Botão WhatsApp Flutuante:** {'🟢 ATIVO no site' if tem_wpp_btn else '🟡 Sem botão direto visível'}",
    ]

    if sinais_frota:
        linhas.append(f"- **Sinais de Frota:** {', '.join(sinais_frota)}")
    if sinais_comp:
        linhas.append(f"- **Passeios Compartilhados:** {', '.join(sinais_comp)}")

    linhas += [
        f"",
        f"**Pontos de Qualificação:**",
    ]
    for ponto in pontos:
        linhas.append(f"- {ponto}")

    linhas += ["", "---", ""]
    return linhas


def salvar_descartados_csv(descartados: list[dict], config: dict):
    """Salva leads descartados para revisão futura."""
    caminho = OUTPUT_DIR / config["output"]["arquivo_descartados"]
    campos = ["nome", "url", "cidade", "nicho", "score", "telefone", "instagram"]

    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(descartados)

    log.info(f"📁 Descartados salvos em: {caminho}")
