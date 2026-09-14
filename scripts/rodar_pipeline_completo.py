"""Roda o pipeline completo (extração + validação + score) e salva em storage."""
import json
from dataclasses import asdict

from pipeline import processar_lote
from score import calcular_score
from storage import salvar_resultados

ARQUIVOS_BRUTOS = [
    "dados/brutos/bruto_df.json",
    "dados/brutos/bruto_go.json",
    "dados/brutos/bruto_mg.json",
    "dados/brutos/bruto_concorrencia.json",
]

registros = []
vistos = set()
for caminho in ARQUIVOS_BRUTOS:
    with open(caminho, encoding="utf-8") as f:
        for r in json.load(f):
            if r["numeroControlePNCP"] not in vistos:
                vistos.add(r["numeroControlePNCP"])
                registros.append(r)

# Limita a ~50 pra ficar dentro do escopo mínimo pedido e não estourar o
# limite diário de requisições gratuitas do OpenRouter
amostra = registros[:50]
print(f"Processando {len(amostra)} contratações (de {len(registros)} coletadas)...")

resultados_extraidos = processar_lote(amostra)

resultados_finais = []
for r in resultados_extraidos:
    s = calcular_score(r)
    item = asdict(r)
    item["score"] = asdict(s)
    resultados_finais.append(item)

salvar_resultados(resultados_finais)
print(f"\nConcluído. {len(resultados_finais)} oportunidades salvas em dados/processados/oportunidades.json")