"""Roda a extração via LLM nas 15 contratações do gabarito e salva o resultado."""
import json
import time

from extracao import extrair_campos_textuais
from scripts.listar_editais_gabarito import CONTRATACOES_GABARITO

resultados = []

for numero_controle, cnpj, ano, sequencial in CONTRATACOES_GABARITO:
    print(f"Processando {numero_controle}...")
    inicio = time.time()
    try:
        campos = extrair_campos_textuais(cnpj, ano, sequencial)
        campos["numeroControlePNCP"] = numero_controle
        campos["erro"] = None
    except Exception as e:
        campos = {"numeroControlePNCP": numero_controle, "erro": str(e)}
    campos["tempo_total_segundos"] = time.time() - inicio
    resultados.append(campos)
    print(f"  -> modelo: {campos.get('modelo_usado')}, tempo: {campos['tempo_total_segundos']:.1f}s")

with open("dados/processados/extracao_gabarito.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"\nConcluído. {len(resultados)} contratações processadas.")
print("Salvo em dados/processados/extracao_gabarito.json")