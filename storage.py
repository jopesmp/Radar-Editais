"""Persistência simples em JSON — sem banco relacional (fora de escopo, ver enunciado)."""
import json
from dataclasses import asdict
from pathlib import Path

CAMINHO_RESULTADOS = Path("dados/processados/oportunidades.json")


def salvar_resultados(resultados: list[dict]) -> None:
    CAMINHO_RESULTADOS.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_RESULTADOS, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


def carregar_resultados() -> list[dict]:
    if not CAMINHO_RESULTADOS.exists():
        return []
    with open(CAMINHO_RESULTADOS, encoding="utf-8") as f:
        return json.load(f)