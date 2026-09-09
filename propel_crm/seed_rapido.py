"""
SEED RÁPIDO — Importa instantaneamente os leads qualificados para o banco SQLite.
"""

import re
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "propel_crm.db"
MD_PATH = Path(__file__).parent.parent / "modulo_2_leads" / "outputs" / "LEADS_QUALIFICADOS.md"


def seed_rapido():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not MD_PATH.exists():
        print("Arquivo de leads não encontrado!")
        return

    conteudo = MD_PATH.read_text(encoding="utf-8")
    blocos = conteudo.split("### ")

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM leads")

    inseridos = 0
    for b in blocos[1:]:
        linhas = b.strip().split("\n")
        titulo = linhas[0].split(". ", 1)[-1].strip() if ". " in linhas[0] else linhas[0].strip()
        
        # Extrair score, cidade, nicho
        score_match = re.search(r"Score.*?`(\d+)/100`", b)
        cidade_match = re.search(r"Cidade:\*\* ([^\|\n]+)", b)
        nicho_match = re.search(r"(?:Nicho|Foco):\*\* ([^\n]+)", b)
        
        score = int(score_match.group(1)) if score_match else 50
        cidade = cidade_match.group(1).strip() if cidade_match else "Ilhabela"
        nicho = nicho_match.group(1).strip() if nicho_match else "Passeio"

        # Extrair dados do Dossiê
        url_match = re.search(r"Site.*?\[(.*?)\]\((.*?)\)", b)
        url = url_match.group(2) if url_match else ""

        wpp_match = re.search(r"(?:Contato|WhatsApp).*?(\+?[\d\(\)\s\-]{8,})", b)
        wpp = wpp_match.group(1).strip() if wpp_match else ""

        ig_match = re.search(r"Instagram.*?(@[a-zA-Z0-9_\.]+|https://instagram\.com/[a-zA-Z0-9_\.]+)", b)
        ig = ig_match.group(1).strip() if ig_match else ""

        cnpj_match = re.search(r"CNPJ.*?`(\d{14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})`", b)
        cnpj = cnpj_match.group(1).strip() if cnpj_match else ""

        razao_match = re.search(r"Razão Social.*?—\s*([^\n\|]+)", b)
        razao = razao_match.group(1).strip() if razao_match else ""

        socios_match = re.search(r"Sócios / Donos.*?\|\s*\*\*([^\*]+)\*\*", b)
        socios = socios_match.group(1).strip() if socios_match else ""

        tem_pixel = 1 if "Pixel Meta (Facebook Ads):** 🟢 ATIVO" in b else 0
        prioridade = "ALTA" if score >= 75 else "MEDIA"

        # Frota
        frota_match = re.search(r"Sinais de Frota:\*\* ([^\n]+)", b)
        frota = frota_match.group(1).strip() if frota_match else "Lancha / Barco"

        cursor.execute("""
        INSERT INTO leads (
            nome, cidade, nicho, url, telefone, whatsapp, instagram,
            cnpj, razao_social, socios, frota, score, prioridade, tem_pixel_meta,
            status, data_criacao, data_ultimo_contato, notas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            titulo, cidade, nicho, url, wpp, wpp, ig,
            cnpj, razao, socios, frota, score, prioridade, tem_pixel,
            "novo_lead", agora, agora, "Mapeado pelo Agente Comercial Propel."
        ))
        inseridos += 1

    conn.commit()
    conn.close()
    print(f"Sucesso: {inseridos} leads inseridos no banco de dados!")


if __name__ == "__main__":
    seed_rapido()
