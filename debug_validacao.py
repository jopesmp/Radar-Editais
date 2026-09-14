import json

from extracao import extrair_texto_edital
from validacao import validar_contratacao

with open("dados/brutos/bruto_df.json", encoding="utf-8") as f:
    registros = json.load(f)

registro_novacap = next(r for r in registros if r["numeroControlePNCP"].startswith("00037457000170"))

with open("dados/processados/extracao_gabarito.json", encoding="utf-8") as f:
    extracoes = json.load(f)

extracao_novacap = next(e for e in extracoes if e["numeroControlePNCP"] == registro_novacap["numeroControlePNCP"])

texto = extrair_texto_edital("00037457000170", 2026, 19)

resultado = validar_contratacao(registro_novacap, extracao_novacap, texto)

for campo in ["objeto", "modalidade", "valor_estimado", "prazo_execucao", "data_abertura_propostas",
              "exigencia_atestado_capacidade_tecnica", "exigencias_habilitacao", "municipio_uf"]:
    c = getattr(resultado, campo)
    print(f"{campo:45} confiavel={c.confiavel!s:6} valor={str(c.valor)[:60]!r}")

print("\n--- Diagnóstico dos 2 campos rejeitados ---")
for campo in ["exigencia_atestado_capacidade_tecnica", "exigencias_habilitacao"]:
    bruto = extracao_novacap.get(campo) or {}
    print(f"\n{campo}:")
    print(f"  valor extraído: {bruto.get('valor')!r}")
    print(f"  trecho citado:  {bruto.get('trecho_citado')!r}")
    if bruto.get("trecho_citado"):
        from validacao import _normalizar
        trecho_norm = _normalizar(bruto["trecho_citado"])
        print(f"  trecho está no texto? {trecho_norm in _normalizar(texto)}")