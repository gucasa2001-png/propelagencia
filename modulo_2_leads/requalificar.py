import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import qualificador, exportador

config = qualificador.carregar_config()
leads_brutos = qualificador.ler_csv_bruto(config)
print(f"Leads brutos carregados: {len(leads_brutos)}")

qualificados, descartados = qualificador.qualificar_leads(leads_brutos, config)

alta = [l for l in qualificados if "ALTA" in l.get("prioridade", "")]
media = [l for l in qualificados if "MEDIA" in l.get("prioridade", "") or "MÉDIA" in l.get("prioridade", "")]

print(f"[ALTA PRIORIDADE]: {len(alta)}")
print(f"[MEDIA PRIORIDADE]: {len(media)}")
print(f"[DESCARTADOS]: {len(descartados)}")

exportador.gerar_markdown(qualificados, descartados, config)
exportador.salvar_descartados_csv(descartados, config)

print()
print("=" * 60)
print("DOSSIÊ DOS LEADS PRIORITÁRIOS (ICP: FROTA + COMPARTILHADO):")
print("=" * 60)
for i, l in enumerate(qualificados[:5], 1):
    score = l.get("score", 0)
    nome = l.get("nome", "")[:50]
    cidade = l.get("cidade", "")
    wpp = l.get("whatsapp", "") or l.get("telefone", "Sem tel")
    cnpj = l.get("cnpj", "Não localizado")
    socios = ", ".join(l.get("socios", [])) or "Não localizados"
    pixel = "ATIVO" if l.get("tem_pixel_meta") else "AUSENTE"
    print(f"\n#{i} [{score}/100] {nome} ({cidade})")
    print(f"   Contato: {wpp}")
    print(f"   CNPJ:    {cnpj}")
    print(f"   Sócios:  {socios}")
    print(f"   Pixel Meta no Site: {pixel}")
    if l.get("instagram"):
        print(f"   Instagram: {l.get('instagram')}")
    if l.get("sinais_frota"):
        print(f"   Frota:     {', '.join(l.get('sinais_frota'))}")

