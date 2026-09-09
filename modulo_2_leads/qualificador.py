"""
MÓDULO 2 — PROPEL AGENTES
Qualificador de Leads — ICP Real

ICP Propel:
  Agências de passeios náuticos locais (lancha/barco) com frota própria,
  R$30k-150k/mês, que já tentaram tráfego pago sem resultado.
  Ticket Propel: R$1.500 a R$4.000/mês.

Score 0-100:
  - É agência de passeios náuticos (não pousada/hotel/surf): 35 pts
  - Sem anúncios na Meta (oportunidade):                     25 pts
  - Tem Instagram:                                           15 pts
  - Tem site próprio:                                        10 pts
  - Avaliação Google 4.0+:                                   10 pts
  - Tem WhatsApp visível:                                     5 pts
"""

import json
import csv
import re
import logging
import requests
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("qualificador")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "outputs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def carregar_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def e_nicho_alvo(lead: dict, config: dict) -> bool:
    """
    Verifica se o lead é uma agência de passeios náuticos (ICP alvo).
    Exclui pousadas, hotéis, escolas de surf, transfers, órgãos públicos.
    """
    texto = (
        lead.get("nome", "") + " " +
        lead.get("snippet", "") + " " +
        lead.get("nicho", "") + " " +
        lead.get("url", "")
    ).lower()

    # Palavras que CONFIRMAM o nicho alvo
    palavras_alvo = config.get("palavras_chave_nicho_alvo", [])
    tem_alvo = any(p.lower() in texto for p in palavras_alvo)

    # Palavras que EXCLUEM o lead (não é o ICP)
    palavras_excluir = config.get("palavras_chave_excluir", [])
    tem_exclusao = any(p.lower() in texto for p in palavras_excluir)

    return tem_alvo and not tem_exclusao


def verificar_anuncios_meta(instagram_handle: str) -> bool:
    """
    Verifica na Meta Ad Library se o perfil tem anúncios ativos.
    Retorna True se NÃO tem anúncios (oportunidade = lead mais quente).
    """
    if not instagram_handle:
        return True  # sem Instagram = sem anúncios por definição

    handle = instagram_handle.lstrip("@")
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=BR"
        f"&q={handle}&search_type=keyword_unordered"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        sem_anuncios = (
            "No results" in resp.text
            or "Nenhum resultado" in resp.text
            or "não encontrou" in resp.text.lower()
        )
        return sem_anuncios
    except Exception:
        return True  # conservador: assume sem anúncios


def detectar_frota_e_compartilhado(lead: dict, config: dict) -> tuple[bool, bool, list[str], list[str]]:
    """
    Detecta sinais de frota (Jeep, 4x4, barcos) e venda de passeios compartilhados.
    """
    texto = (
        lead.get("nome", "") + " " +
        lead.get("snippet", "") + " " +
        lead.get("nicho", "") + " " +
        lead.get("url", "")
    ).lower()

    termos_frota = config.get("palavras_chave_frota", ["jeep", "4x4", "lancha", "barco", "escuna", "frota"])
    termos_comp = config.get("palavras_chave_compartilhado", ["compartilhado", "coletivo", "por pessoa", "vaga"])

    achados_frota = [t for t in termos_frota if t in texto]
    achados_comp = [c for c in termos_comp if c in texto]

    tem_frota = len(achados_frota) > 0
    tem_comp = len(achados_comp) > 0

    return tem_frota, tem_comp, achados_frota, achados_comp


def calcular_score(lead: dict, config: dict) -> tuple[int, list[str], list[str]]:
    """
    Calcula o score de qualificação (0–100) com base no ICP real da Propel.
    Retorna: (score, pontos_positivos, alertas)
    """
    criterios = config["criterios_qualificacao"]
    score = 0
    positivos = []
    alertas = []

    # Não aceitar lixo óbvio (órgão público, pousadas se não tiver passeio)
    if not e_nicho_alvo(lead, config):
        alertas.append("❌ Fora do nicho alvo (hospedagem/surf/órgão público)")
        return 0, positivos, alertas

    # ── Critério 1 (30 pts): Tem Jeep 4x4 ou Barco/Lancha próprio ────────────
    tem_frota, tem_comp, frota_achados, comp_achados = detectar_frota_e_compartilhado(lead, config)
    if tem_frota:
        score += criterios["tem_jeep_ou_barco_proprio"]["peso"]
        positivos.append(f"🚙⚓ Frota identificada ({', '.join(frota_achados[:3])})")
    else:
        alertas.append("❓ Frota própria não confirmada no snippet")

    # ── Critério 2 (25 pts): Vende Passeio Compartilhado ────────────────────
    if tem_comp:
        score += criterios["vende_passeio_compartilhado"]["peso"]
        positivos.append(f"👥 Vende compartilhado/por pessoa ({', '.join(comp_achados[:2])}) - ALTA demanda de tráfego!")
    else:
        # Se é passeio de escuna ou castelhanos, tipicamente é compartilhado
        if any(w in lead.get("nome", "").lower() for w in ["escuna", "castelhanos", "coletivo"]):
            score += 20
            positivos.append("👥 Rota típica de passeio compartilhado (alta demanda)")
        else:
            alertas.append("❓ Modelo compartilhado não explícito no snippet")

    # ── Critério 3 (20 pts): Sem anúncios na Meta ────────────────────────────
    sem_anuncios = verificar_anuncios_meta(lead.get("instagram", ""))
    if sem_anuncios:
        score += criterios["sem_anuncios_meta"]["peso"]
        positivos.append("✅ Sem anúncios ativos na Meta — oportunidade de entrada!")
    else:
        alertas.append("⚠️ Já possui anúncios ativos na Meta")

    # ── Critério 4 (10 pts): Tem site próprio ────────────────────────────────
    tem_site = str(lead.get("tem_site_proprio", "False")).lower() == "true"
    if tem_site:
        score += criterios["tem_site_proprio"]["peso"]
        positivos.append("🌐 Possui site próprio estruturado")
    else:
        alertas.append("⚠️ Sem site próprio detectado")

    # ── Critério 5 (10 pts): Tem Instagram ──────────────────────────────────
    if lead.get("instagram"):
        score += criterios["tem_instagram"]["peso"]
        positivos.append(f"📸 Instagram: {lead['instagram']}")
    else:
        alertas.append("❌ Sem Instagram detectado")

    # ── Critério 6 (5 pts): Tem WhatsApp ─────────────────────────────────────
    tem_wpp = bool(lead.get("whatsapp")) or ("wa.me" in lead.get("url", ""))
    if tem_wpp:
        score += criterios["tem_whatsapp"]["peso"]
        positivos.append(f"📱 WhatsApp comercial identificado")
    elif lead.get("telefone"):
        positivos.append(f"📞 Telefone: {lead['telefone']}")
    else:
        alertas.append("❌ Sem contato direto detectado")

    return score, positivos, alertas


def qualificar_leads(leads_brutos: list[dict], config: dict) -> tuple[list, list]:
    """Pipeline de qualificação com enriquecimento automático nos leads prioritários."""
    import enriquecedor

    qualificados = []
    descartados = []
    score_min = config["score_minimo_qualificado"]
    score_pri = config["score_minimo_prioritario"]

    for lead in leads_brutos:
        nome = lead.get("nome", "")[:55]
        score, positivos, alertas = calcular_score(lead, config)

        lead["score"] = score
        lead["pontos_positivos"] = positivos + alertas
        lead["prioridade"] = (
            "🔥 ALTA"   if score >= score_pri else
            "🟡 MÉDIA"  if score >= score_min else
            "⬇️ BAIXA"
        )

        if score >= score_min:
            # Enriquecimento dos líderes do ranking (CNPJ, Sócios, Auditoria do Site)
            if score >= 60:
                log.info(f"⚡ Enriquecendo lead de alto potencial: {nome}...")
                try:
                    lead = enriquecedor.enriquecer_lead(lead)
                except Exception as e:
                    log.warning(f"Erro ao enriquecer {nome}: {e}")
            qualificados.append(lead)
        else:
            descartados.append(lead)

    qualificados.sort(key=lambda x: x["score"], reverse=True)
    return qualificados, descartados


def ler_csv_bruto(config: dict) -> list[dict]:
    caminho = OUTPUT_DIR / config["output"]["arquivo_csv"]
    if not caminho.exists():
        log.error(f"Arquivo CSV não encontrado: {caminho}")
        log.error("Execute scraper.py primeiro!")
        return []
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("PROPEL AGENTES — QUALIFICADOR (ICP: Agências Náuticas)")
    log.info(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log.info("=" * 60)

    config = carregar_config()
    leads_brutos = ler_csv_bruto(config)

    if not leads_brutos:
        exit(1)

    log.info(f"📥 {len(leads_brutos)} leads brutos carregados.")
    qualificados, descartados = qualificar_leads(leads_brutos, config)

    log.info(f"\n✅ Leads qualificados: {len(qualificados)}")
    log.info(f"❌ Leads descartados: {len(descartados)}")
    log.info("Próximo passo: rode exportador.py para gerar o relatório final.")
