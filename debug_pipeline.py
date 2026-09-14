import json
from dataclasses import asdict

from pipeline import processar_lote
from score import calcular_score

with open("dados/brutos/bruto_df.json", encoding="utf-8") as f:
    registros = json.load(f)

amostra = registros[:3]
resultados = processar_lote(amostra)

for r in resultados:
    print(f"\n=== {r.numero_controle_pncp} ===")
    for campo, valor in asdict(r).items():
        if campo == "numero_controle_pncp":
            continue
        print(f"  {campo:45} confiavel={valor['confiavel']!s:6} valor={str(valor['valor'])[:50]!r}")

print("\n\n=== SCORES ===")
for r in resultados:
    s = calcular_score(r)
    print(f"\n{r.numero_controle_pncp}: {s.valor_final}/100 ({s.criterios_avaliados}/{s.criterios_totais} critérios avaliados)")
    for crit in s.detalhamento:
        status = f"{crit.pontos}/{crit.peso_maximo}" if crit.avaliado else "não avaliado"
        print(f"  {crit.criterio:30} {status:15} {crit.justificativa[:70]}")