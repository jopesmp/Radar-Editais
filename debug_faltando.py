import json
import traceback

from pipeline import processar_contratacao

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

for registro in brutos:
    if registro["numeroControlePNCP"] in nc_faltando:
        print(f"\n=== {registro['numeroControlePNCP']} ===")
        try:
            resultado = processar_contratacao(registro)
            print("OK:", resultado.numero_controle_pncp)
        except Exception:
            traceback.print_exc()