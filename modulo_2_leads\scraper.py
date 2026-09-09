"""
MÓDULO 2 — PROPEL AGENTES
Scraper de Leads de Turismo Local
Ilhabela | Ubatuba | São Sebastião

Busca empresas de turismo via DuckDuckGo (sem API paga, sem bloqueio).
"""

import json
import time
import re
import csv
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# ── Configuração de log ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("scraper")

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Headers para simular navegador ───────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def carregar_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def buscar_leads(query: str, num_resultados: int = 8) -> list[dict]:
    """
    Busca via DuckDuckGo — confiável, sem bloqueio, sem API paga.
    """
    resultados = []
    dominios_ignorar = [
        "youtube.com", "wikipedia.org", "tripadvisor.com",
        "booking.com", "airbnb.com", "guia", "yelp.com"
    ]

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="br-pt", max_results=num_resultados):
                url = r.get("href", "")
                if not url or not url.startswith("http"):
                    continue
                if any(d in url for d in dominios_ignorar):
                    continue

                resultados.append({
                    "titulo": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", "")
                })

    except Exception as e:
        log.warning(f"Erro na busca '{query}': {e}")

    return resultados


def extrair_dados_do_snippet(titulo: str, snippet: str, url: str) -> dict:
    """
    Extrai dados básicos do título e snippet do resultado de busca.
    """
    dados = {
        "nome": titulo,
        "url": url,
        "snippet": snippet,
        "telefone": "",
        "whatsapp": "",
        "instagram": "",
        "email": "",
    }

    # Regex para telefone brasileiro
    telefones = re.findall(r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?\d{4}|\d{4})-?\d{4}", snippet)
    if telefones:
        dados["telefone"] = telefones[0].strip()

    # Busca por Instagram no snippet
    instagram = re.findall(r"@([A-Za-z0-9_.]+)|instagram\.com/([A-Za-z0-9_.]+)", snippet, re.IGNORECASE)
    if instagram:
        handle = instagram[0][0] or instagram[0][1]
        dados["instagram"] = f"@{handle}"

    # Busca por email
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", snippet)
    if emails:
        dados["email"] = emails[0]

    return dados


def enriquecer_pagina(dados: dict) -> dict:
    """
    Acessa a página do negócio e extrai mais informações.
    (Telefone, Instagram, WhatsApp, e-mail)
    """
    url = dados.get("url", "")
    if not url:
        return dados

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        texto = resp.text
        soup = BeautifulSoup(texto, "html.parser")

        # Texto completo visível da página
        texto_visivel = soup.get_text(separator=" ", strip=True)

        # Telefone
        if not dados["telefone"]:
            tels = re.findall(r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?\d{4}|\d{4})-?\d{4}", texto_visivel)
            if tels:
                dados["telefone"] = tels[0].strip()

        # WhatsApp (links wa.me)
        wpp_links = re.findall(r"wa\.me/(\d+)", texto)
        if wpp_links:
            dados["whatsapp"] = f"https://wa.me/{wpp_links[0]}"

        # Instagram
        if not dados["instagram"]:
            ig = re.findall(r"instagram\.com/([A-Za-z0-9_.]+)", texto, re.IGNORECASE)
            if ig and ig[0] not in ["p", "reel", "stories", "explore"]:
                dados["instagram"] = f"@{ig[0]}"

        # Email
        if not dados["email"]:
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto_visivel)
            if emails:
                dados["email"] = emails[0]

        # Verificar se tem site próprio (não apenas plataforma de terceiros)
        plataformas_terceiros = ["booking.com", "tripadvisor", "airbnb", "guia", "yelp"]
        dados["tem_site_proprio"] = not any(p in url for p in plataformas_terceiros)

    except Exception as e:
        log.debug(f"Erro ao enriquecer {url}: {e}")

    return dados


def scrape_leads(config: dict) -> list[dict]:
    """
    Função principal: gera queries de busca e coleta leads.
    """
    leads_brutos = []
    vistos = set()  # evitar duplicatas

    for cidade in config["cidades"]:
        for nicho in config["nichos"]:
            query = f"{nicho} {cidade} contato whatsapp"
            log.info(f"🔍 Buscando: {query}")

            resultados = buscar_leads(query, num_resultados=8)

            for r in resultados:
                url = r["url"]
                if url in vistos:
                    continue
                vistos.add(url)

                lead = extrair_dados_do_snippet(r["titulo"], r["snippet"], url)
                lead["cidade"] = cidade
                lead["nicho"] = nicho
                lead["query_origem"] = query
                lead["tem_site_proprio"] = False  # será atualizado no enriquecimento

                # Enriquecer acessando a página (com delay para não ser bloqueado)
                log.info(f"   ↳ Enriquecendo: {lead['nome'][:50]}...")
                lead = enriquecer_pagina(lead)
                leads_brutos.append(lead)

                time.sleep(2)  # intervalo respeitoso entre requisições

            time.sleep(3)  # intervalo entre queries

    return leads_brutos


def salvar_csv(leads: list[dict], config: dict):
    """Salva todos os leads brutos em CSV para referência."""
    caminho = OUTPUT_DIR / config["output"]["arquivo_csv"]
    campos = ["nome", "url", "cidade", "nicho", "telefone", "whatsapp",
              "instagram", "email", "tem_site_proprio", "snippet"]

    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    log.info(f"✅ CSV bruto salvo em: {caminho}")


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("PROPEL AGENTES — MÓDULO 2: SCRAPER DE LEADS")
    log.info(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log.info("=" * 60)

    config = carregar_config()
    leads = scrape_leads(config)
    salvar_csv(leads, config)

    log.info(f"\n📊 Total de leads coletados: {len(leads)}")
    log.info("Próximo passo: rode qualificador.py para gerar a lista priorizada.")
