"""Adiciona ao storage os 4 registros que faltaram na rodada anterior,
sem precisar reprocessar os 50 de novo (economiza tempo/chamadas de API)."""
import json
from dataclasses import asdict

from pipeline import processar_contratacao
from score import calcular_score
from storage import carregar_resultados, salvar_resultados

nc_faltando = {
    "00394684000153-1-000136/2026",
    "34028316000103-1-000067/2026",
    "00037457000170-1-000021/2026",
    "00348003000110-1-000935/2026",
}

brutos = []
for arq in [
    "dados/brutos/bruto_df.json", "dados/brutos/bruto_go.json",
    "dados/brutos/bruto_mg.json", "dados/brutos/bruto_concorrencia.json",
]:
    brutos.extend(json.load(open(arq, encoding="utf-8")))

resultados_existentes = carregar_resultados()
ja_salvos = {r["numero_controle_pncp"] for r in resultados_existentes}

for registro in brutos:
    nc = registro["numeroControlePNCP"]
    if nc in nc_faltando and nc not in ja_salvos:
        print(f"Processando {nc}...")
        resultado = processar_contratacao(registro)
        item = asdict(resultado)
        item["score"] = asdict(calcular_score(resultado))
        resultados_existentes.append(item)

salvar_resultados(resultados_existentes)
print(f"\nTotal salvo agora: {len(resultados_existentes)}")