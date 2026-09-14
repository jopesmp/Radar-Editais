import json
from dataclasses import asdict

from pipeline import processar_lote

with open("dados/brutos/bruto_df.json", encoding="utf-8") as f:
    registros = json.load(f)

# Pega só 3 pra teste rápido
amostra = registros[:3]
resultados = processar_lote(amostra)

for r in resultados:
    print(f"\n=== {r.numero_controle_pncp} ===")
    for campo, valor in asdict(r).items():
        if campo == "numero_controle_pncp":
            continue
        print(f"  {campo:45} confiavel={valor['confiavel']!s:6} valor={str(valor['valor'])[:50]!r}")