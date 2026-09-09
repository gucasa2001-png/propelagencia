"""
MÓDULO 2 — PROPEL AGENTES
Script Principal (Orquestrador)

Executa o pipeline completo:
  1. Scraper → coleta leads brutos
  2. Qualificador → pontua cada lead
  3. Exportador → gera relatório final

Uso: python main.py
"""

import logging
import sys
import io
from datetime import datetime
from pathlib import Path

# Força UTF-8 no terminal Windows para suportar emoji nos logs
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

import scraper
import qualificador
import exportador

# ── Configuração de log ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent / "outputs" / "log_execucao.txt",
            encoding="utf-8"
        )
    ]
)
log = logging.getLogger("main")


def main():
    inicio = datetime.now()

    log.info("=" * 60)
    log.info("🚀 PROPEL AGENTES — MÓDULO 2: INTELIGÊNCIA COMERCIAL")
    log.info(f"   Iniciado em: {inicio.strftime('%d/%m/%Y %H:%M')}")
    log.info("=" * 60)

    # ── Passo 1: Carregar configuração ───────────────────────────────────────
    config = scraper.carregar_config()
    log.info(f"\n📍 Cidades-alvo: {', '.join(config['cidades'])}")
    log.info(f"🎯 Nichos: {len(config['nichos'])} categorias configuradas\n")

    # ── Passo 2: Scraping ────────────────────────────────────────────────────
    log.info("─" * 40)
    log.info("ETAPA 1/3 — SCRAPING")
    log.info("─" * 40)
    leads_brutos = scraper.scrape_leads(config)
    scraper.salvar_csv(leads_brutos, config)
    log.info(f"✅ {len(leads_brutos)} leads coletados.\n")

    if not leads_brutos:
        log.error("Nenhum lead coletado. Encerrando.")
        return

    # ── Passo 3: Qualificação ────────────────────────────────────────────────
    log.info("─" * 40)
    log.info("ETAPA 2/3 — QUALIFICAÇÃO")
    log.info("─" * 40)
    leads_qualificados, leads_descartados = qualificador.qualificar_leads(leads_brutos, config)
    log.info(f"✅ {len(leads_qualificados)} qualificados | ❌ {len(leads_descartados)} descartados\n")

    # ── Passo 4: Exportação ──────────────────────────────────────────────────
    log.info("─" * 40)
    log.info("ETAPA 3/3 — EXPORTAÇÃO")
    log.info("─" * 40)
    caminho_relatorio = exportador.gerar_markdown(leads_qualificados, leads_descartados, config)
    exportador.salvar_descartados_csv(leads_descartados, config)

    # ── Resumo final ─────────────────────────────────────────────────────────
    duracao = (datetime.now() - inicio).seconds
    alta_prioridade = [l for l in leads_qualificados if "ALTA" in l.get("prioridade", "")]

    log.info("\n" + "=" * 60)
    log.info("🏁 EXECUÇÃO CONCLUÍDA")
    log.info(f"   Duração total: {duracao // 60}m {duracao % 60}s")
    log.info(f"   🔥 Leads Alta Prioridade: {len(alta_prioridade)}")
    log.info(f"   🟡 Leads Média Prioridade: {len(leads_qualificados) - len(alta_prioridade)}")
    log.info(f"   📄 Relatório: {caminho_relatorio}")
    log.info("=" * 60)
    log.info("\n✅ Abra o arquivo LEADS_QUALIFICADOS.md e comece a prospectar!")


if __name__ == "__main__":
    main()
