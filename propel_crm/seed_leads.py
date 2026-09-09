"""
PROPEL CRM — SEED LEADS
Importa os leads minerados e qualificados diretamente para o banco SQLite.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from database import get_db, init_db

OUTPUTS_DIR = Path(__file__).parent.parent / "modulo_2_leads" / "outputs"
CSV_PATH = OUTPUTS_DIR / "leads_brutos.csv"
CONFIG_PATH = Path(__file__).parent.parent / "modulo_2_leads" / "config.json"


def seed_data():
    init_db()

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)

    # Importa o qualificador para pegar scores e dossiês
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "modulo_2_leads"))
    import qualificador

    leads_brutos = qualificador.ler_csv_bruto(config)
    qualificados, _ = qualificador.qualificar_leads(leads_brutos, config)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        cursor = conn.cursor()
        # Limpar anteriores para evitar duplicatas no seed
        cursor.execute("DELETE FROM leads")

        for l in qualificados:
            cursor.execute("""
            INSERT INTO leads (
                nome, cidade, nicho, url, telefone, whatsapp, instagram, tiktok,
                cnpj, razao_social, socios, frota, score, prioridade, tem_pixel_meta,
                status, data_criacao, data_ultimo_contato, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                l.get("nome", ""),
                l.get("cidade", ""),
                l.get("nicho", ""),
                l.get("url", ""),
                l.get("telefone", ""),
                l.get("whatsapp", ""),
                l.get("instagram", ""),
                l.get("tiktok", ""),
                l.get("cnpj", ""),
                l.get("razao_social", ""),
                ", ".join(l.get("socios", [])),
                ", ".join(l.get("sinais_frota", [])),
                l.get("score", 0),
                l.get("prioridade", "MEDIA"),
                1 if l.get("tem_pixel_meta") else 0,
                "novo_lead",
                agora,
                agora,
                "Importado automaticamente pelo Agente de Inteligência Comercial."
            ))

        conn.commit()
    print(f"Seed concluído com sucesso! {len(qualificados)} leads importados para o Kanban.")


if __name__ == "__main__":
    seed_data()
