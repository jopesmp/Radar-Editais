"""Harness de avaliação: compara a extração do pipeline contra o gabarito anotado à mão."""
import json
from difflib import SequenceMatcher

CAMPOS_TEXTUAIS = [
    "prazo_execucao",
    "exigencia_atestado_capacidade_tecnica",
    "exigencias_habilitacao",
]


def carregar_json(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def avaliar_campo(valor_extraido, valor_gabarito) -> dict:
    """Compara um campo. Retorna se acertou a PRESENÇA e, se aplicável, a similaridade de texto."""
    presenca_extraida = valor_extraido is not None
    presenca_gabarito = valor_gabarito is not None
    acertou_presenca = presenca_extraida == presenca_gabarito

    sim = None
    if presenca_extraida and presenca_gabarito:
        sim = similaridade(str(valor_extraido), str(valor_gabarito))

    return {"acertou_presenca": acertou_presenca, "similaridade": sim}


def main():
    gabarito = {item["numeroControlePNCP"]: item for item in carregar_json("gabarito/gabarito.json")}
    extraidos = {item["numeroControlePNCP"]: item for item in carregar_json("dados/processados/extracao_gabarito.json")}

    print(f"Gabarito: {len(gabarito)} documentos | Extraídos: {len(extraidos)} documentos\n")

    acertos_presenca = {campo: 0 for campo in CAMPOS_TEXTUAIS}
    similaridades = {campo: [] for campo in CAMPOS_TEXTUAIS}
    total = 0

    for numero_controle, item_gabarito in gabarito.items():
        item_extraido = extraidos.get(numero_controle)
        if item_extraido is None:
            print(f"[aviso] {numero_controle} não foi processado pela extração")
            continue

        total += 1
        for campo in CAMPOS_TEXTUAIS:
            valor_extraido = (item_extraido.get(campo) or {}).get("valor")
            valor_gabarito = item_gabarito.get(campo)

            resultado = avaliar_campo(valor_extraido, valor_gabarito)
            if resultado["acertou_presenca"]:
                acertos_presenca[campo] += 1
            if resultado["similaridade"] is not None:
                similaridades[campo].append(resultado["similaridade"])

    print(f"=== Acurácia de presença (acertar se o campo existe ou não) — base: {total} documentos ===")
    for campo in CAMPOS_TEXTUAIS:
        pct = acertos_presenca[campo] / total * 100 if total else 0
        print(f"  {campo:45} {acertos_presenca[campo]}/{total} ({pct:.0f}%)")

    print(f"\n=== Similaridade de texto (só quando ambos têm valor) ===")
    for campo in CAMPOS_TEXTUAIS:
        valores = similaridades[campo]
        if valores:
            media = sum(valores) / len(valores)
            print(f"  {campo:45} média {media:.2f} (n={len(valores)})")
        else:
            print(f"  {campo:45} sem casos comparáveis")


if __name__ == "__main__":
    main()