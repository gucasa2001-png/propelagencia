"""
MÓDULO 2 — PROPEL AGENTES
Enriquecedor e Investigador de Leads (Dossiê Comercial)

Para os leads com alto potencial (ICP Alto: Jeeps/Barcos + Compartilhado):
  - Localiza o CNPJ da empresa
  - Consulta os nomes dos Sócios / Donos na Receita Federal via BrasilAPI
  - Audita o Site: Pixel do Facebook/Meta, Google Analytics, Botão WhatsApp
  - Identifica links do Instagram e TikTok
"""

import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from ddgs import DDGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("enriquecedor")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def buscar_cnpj_empresa(nome_empresa: str, cidade: str) -> str:
    """
    Tenta encontrar o CNPJ da empresa através de busca pública.
    """
    queries = [
        f'"{nome_empresa}" {cidade} cnpj',
        f'cnpj "{nome_empresa}"',
        f'{nome_empresa} {cidade} "cnpj"'
    ]

    for q in queries:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, region="br-pt", max_results=3):
                    texto = r.get("title", "") + " " + r.get("body", "")
                    # Regex para CNPJ com ou sem pontuação
                    cnpjs = re.findall(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", texto)
                    if cnpjs:
                        cnpj_limpo = re.sub(r"\D", "", cnpjs[0])
                        if len(cnpj_limpo) == 14:
                            return cnpj_limpo
        except Exception as e:
            log.debug(f"Erro ao buscar CNPJ de {nome_empresa}: {e}")
            continue

    return ""


def consultar_socios_cnpj(cnpj: str) -> dict:
    """
    Consulta os dados da empresa e sócios (QSA) na Receita Federal via BrasilAPI.
    """
    if not cnpj:
        return {"razao_social": "", "socios": [], "capital_social": ""}

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            dados = resp.json()
            razao = dados.get("razao_social", "")
            socios = []
            for s in dados.get("qsa", []):
                nome = s.get("nome_socio", "")
                qualificacao = s.get("qualificacao_socio", "")
                if nome:
                    socios.append(f"{nome.title()} ({qualificacao})")

            return {
                "cnpj_formatado": dados.get("cnpj", cnpj),
                "razao_social": razao,
                "nome_fantasia": dados.get("nome_fantasia", ""),
                "capital_social": dados.get("capital_social", 0),
                "socios": socios,
                "situacao": dados.get("descricao_situacao_cadastral", "ATIVA"),
                "cidade": dados.get("municipio", ""),
                "inicio_atividade": dados.get("data_inicio_atividade", "")
            }
    except Exception as e:
        log.debug(f"Erro ao consultar BrasilAPI para CNPJ {cnpj}: {e}")

    return {"razao_social": "", "socios": [], "capital_social": ""}


def auditar_site(url: str) -> dict:
    """
    Acessa o site e verifica a infraestrutura de marketing:
      - Tem Pixel do Meta/Facebook?
      - Tem Google Analytics / Tag Manager?
      - Tem botão de WhatsApp integrado?
      - Tem link de Instagram e TikTok?
    """
    auditoria = {
        "tem_pixel_meta": False,
        "tem_google_analytics": False,
        "tem_botao_whatsapp": False,
        "instagram": "",
        "tiktok": "",
        "menciona_frota": False,
        "detalhes_frota": [],
        "menciona_compartilhado": False,
        "detalhes_compartilhado": []
    }

    if not url or not url.startswith("http"):
        return auditoria

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        html = resp.text
        html_lower = html.lower()

        # 1. Pixel do Meta / Facebook
        if any(p in html_lower for p in ["fbevents.js", "fbq('init'", "connect.facebook.net", "facebook-jssdk"]):
            auditoria["tem_pixel_meta"] = True

        # 2. Google Analytics / GTM
        if any(g in html_lower for g in ["googletagmanager.com", "gtag(", "analytics.js", "ga('create'"]):
            auditoria["tem_google_analytics"] = True

        # 3. WhatsApp no site
        if any(w in html_lower for w in ["wa.me/", "api.whatsapp.com", "whatsapp.com/send", "joinchat"]):
            auditoria["tem_botao_whatsapp"] = True

        # 4. Instagram
        ig_matches = re.findall(r"instagram\.com/([a-zA-Z0-9_\.]+)", html, re.IGNORECASE)
        ignorar_ig = ["p", "reel", "stories", "explore", "tv", "share"]
        for ig in ig_matches:
            ig_clean = ig.rstrip("/")
            if ig_clean.lower() not in ignorar_ig:
                auditoria["instagram"] = f"https://instagram.com/{ig_clean}"
                break

        # 5. TikTok
        tt_matches = re.findall(r"tiktok\.com/@?([a-zA-Z0-9_\.]+)", html, re.IGNORECASE)
        for tt in tt_matches:
            tt_clean = tt.rstrip("/")
            if tt_clean:
                auditoria["tiktok"] = f"https://tiktok.com/@{tt_clean}"
                break

        # 6. Sinais de Frota (Jeep, 4x4, Barcos, Lanchas)
        termos_frota = ["jeep", "4x4", "defender", "troller", "lancha", "barco", "escuna", "nossa frota", "embarcação"]
        for t in termos_frota:
            if t in html_lower:
                auditoria["menciona_frota"] = True
                auditoria["detalhes_frota"].append(t)

        # 7. Sinais de Passeios Compartilhados
        termos_comp = ["compartilhado", "coletivo", "por pessoa", "vaga", "vagas", "diário", "saída diária"]
        for c in termos_comp:
            if c in html_lower:
                auditoria["menciona_compartilhado"] = True
                auditoria["detalhes_compartilhado"].append(c)

    except Exception as e:
        log.debug(f"Erro ao auditar {url}: {e}")

    return auditoria


def enriquecer_lead(lead: dict) -> dict:
    """
    Gera o dossiê completo de um lead prioritário.
    """
    nome = lead.get("nome", "")
    cidade = lead.get("cidade", "")
    url = lead.get("url", "")

    log.info(f"🔎 Auditando infraestrutura web de: {nome}...")
    auditoria = auditar_site(url)

    lead["tem_pixel_meta"] = auditoria["tem_pixel_meta"]
    lead["tem_google_analytics"] = auditoria["tem_google_analytics"]
    lead["tem_botao_whatsapp"] = auditoria["tem_botao_whatsapp"]
    if auditoria["instagram"] and not lead.get("instagram"):
        lead["instagram"] = auditoria["instagram"]
    lead["tiktok"] = auditoria["tiktok"]
    lead["sinais_frota"] = list(set(auditoria["detalhes_frota"]))
    lead["sinais_compartilhado"] = list(set(auditoria["detalhes_compartilhado"]))

    # Busca CNPJ e Sócios
    log.info(f"🏛️ Investigando CNPJ e Quadro Societário de: {nome}...")
    cnpj = buscar_cnpj_empresa(nome, cidade)
    if not cnpj and lead.get("telefone"):
        # Tenta buscar por telefone
        tel_limpo = re.sub(r"\D", "", lead.get("telefone", ""))
        cnpj = buscar_cnpj_empresa(tel_limpo, cidade)

    if cnpj:
        dados_receita = consultar_socios_cnpj(cnpj)
        lead["cnpj"] = cnpj
        lead["razao_social"] = dados_receita.get("razao_social", "")
        lead["socios"] = dados_receita.get("socios", [])
        lead["capital_social"] = dados_receita.get("capital_social", "")
        lead["data_abertura"] = dados_receita.get("inicio_atividade", "")
    else:
        lead["cnpj"] = ""
        lead["razao_social"] = ""
        lead["socios"] = []

    return lead
