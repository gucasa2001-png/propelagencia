import sys
sys.path.insert(0, ".")
import scraper

print("Buscando: passeio de lancha em Ilhabela...")
resultados = scraper.buscar_leads("passeio de lancha Ilhabela contato whatsapp", num_resultados=5)
print(f"Resultados encontrados: {len(resultados)}")
for r in resultados:
    titulo = r["titulo"][:65]
    url = r["url"][:70]
    snippet = r["snippet"][:100]
    print(f"  Nome: {titulo}")
    print(f"  URL:  {url}")
    print(f"  Info: {snippet}")
    print()
