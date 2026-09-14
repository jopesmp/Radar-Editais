import json

gabarito = {i["numeroControlePNCP"]: i for i in json.load(open("gabarito/gabarito.json", encoding="utf-8"))}
extraidos = {i["numeroControlePNCP"]: i for i in json.load(open("dados/processados/extracao_gabarito.json", encoding="utf-8"))}

campos = ["prazo_execucao", "exigencia_atestado_capacidade_tecnica", "exigencias_habilitacao"]

for nc, g in gabarito.items():
    e = extraidos.get(nc, {})
    for campo in campos:
        vg = g.get(campo)
        ve = (e.get(campo) or {}).get("valor")
        if (vg is None) != (ve is None):
            situacao_gabarito = "tem" if vg else "null"
            situacao_extraido = "tem" if ve else "null"
            print(f"{nc} | {campo} | gabarito={situacao_gabarito} extraido={situacao_extraido}")