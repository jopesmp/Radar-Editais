"""Harness de avaliação: compara a saída do PIPELINE COMPLETO (extração + validação)
contra o gabarito anotado à mão. Roda com: python eval.py
"""
import json
from difflib import SequenceMatcher

from pipeline import processar_contratacao

CAMPOS_TEXTUAIS = [
    "prazo_execucao",
    "exigencia_atestado_capacidade_tecnica",
    "exigencias_habilitacao",
]

# Mapeia nome do campo no gabarito (snake_case simples) pro atributo do dataclass
CAMPO_PARA_ATRIBUTO = {
    "objeto": "objeto",
    "modalidade": "modalidade",
    "valor_estimado": "valor_estimado",
    "prazo_execucao": "prazo_execucao",
    "data_abertura_propostas": "data_abertura_propostas",
    "exigencia_atestado_capacidade_tecnica": "exigencia_atestado_capacidade_tecnica",
    "exigencias_habilitacao": "exigencias_habilitacao",
    "municipio_uf": "municipio_uf",
}


def similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def main():
    with open("gabarito/gabarito.json", encoding="utf-8") as f:
        gabarito = {item["numeroControlePNCP"]: item for item in json.load(f)}

    brutos = []
    for arq in [
        "dados/brutos/bruto_df.json", "dados/brutos/bruto_go.json",
        "dados/brutos/bruto_mg.json", "dados/brutos/bruto_concorrencia.json",
    ]:
        brutos.extend(json.load(open(arq, encoding="utf-8")))
    brutos_por_nc = {r["numeroControlePNCP"]: r for r in brutos}

    acertos_presenca = {campo: 0 for campo in CAMPO_PARA_ATRIBUTO}
    similaridades = {campo: [] for campo in CAMPO_PARA_ATRIBUTO}
    total = 0

    for numero_controle, item_gabarito in gabarito.items():
        registro_api = brutos_por_nc.get(numero_controle)
        if registro_api is None:
            print(f"[aviso] {numero_controle}: não encontrado nos dados brutos, pulando")
            continue

        print(f"Avaliando {numero_controle}...")
        resultado = processar_contratacao(registro_api)
        total += 1

        for campo_gabarito, atributo in CAMPO_PARA_ATRIBUTO.items():
            campo_extraido = getattr(resultado, atributo)
            valor_extraido = campo_extraido.valor if campo_extraido.confiavel else None
            valor_gabarito = item_gabarito.get(campo_gabarito)

            presenca_bate = (valor_extraido is not None) == (valor_gabarito is not None)
            if presenca_bate:
                acertos_presenca[campo_gabarito] += 1

            if valor_extraido is not None and valor_gabarito is not None:
                similaridades[campo_gabarito].append(similaridade(valor_extraido, valor_gabarito))

    print(f"\n=== Acurácia de presença (pipeline completo, pós-validação) — base: {total} documentos ===")
    for campo in CAMPO_PARA_ATRIBUTO:
        pct = acertos_presenca[campo] / total * 100 if total else 0
        print(f"  {campo:45} {acertos_presenca[campo]}/{total} ({pct:.0f}%)")

    print(f"\n=== Similaridade de texto (só quando ambos têm valor confiável) ===")
    for campo in CAMPO_PARA_ATRIBUTO:
        valores = similaridades[campo]
        if valores:
            print(f"  {campo:45} média {sum(valores)/len(valores):.2f} (n={len(valores)})")
        else:
            print(f"  {campo:45} sem casos comparáveis")


if __name__ == "__main__":
    main()