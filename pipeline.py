"""Orquestrador: ingestão (já feita) -> extração (LLM) -> validação (determinística).

Este é o único módulo que conhece tanto extracao.py quanto validacao.py — eles
nunca se importam diretamente entre si (ver DECISOES.md, Dia 1).
"""
import re
from typing import Any

from extracao import extrair_texto_edital, extrair_campos_textuais_de_texto
from validacao import validar_contratacao
from schema import ContratacaoExtraida


def parse_numero_controle(numero: str) -> tuple[str, int, int]:
    """Extrai (cnpj, ano, sequencial) de um numeroControlePNCP, ex: '00037457000170-1-000019/2026'."""
    m = re.match(r"(\d{14})-\d+-(\d+)/(\d{4})", numero or "")
    if not m:
        raise ValueError(f"numeroControlePNCP em formato inesperado: {numero!r}")
    cnpj, sequencial, ano = m.groups()
    return cnpj, int(ano), int(sequencial)


def processar_contratacao(registro_api: dict[str, Any]) -> ContratacaoExtraida:
    """Roda o pipeline completo pra UM registro vindo da API do PNCP."""
    numero_controle = registro_api.get("numeroControlePNCP", "")

    try:
        cnpj, ano, sequencial = parse_numero_controle(numero_controle)
        texto_edital = extrair_texto_edital(cnpj, ano, sequencial)
    except Exception as e:
        print(f"[aviso] {numero_controle}: falha ao buscar/ler PDF ({e})")
        texto_edital = None

    try:
        extracao_textual = extrair_campos_textuais_de_texto(texto_edital)
    except Exception as e:
        print(f"[aviso] {numero_controle}: falha na extração via LLM ({e})")
        campo_vazio = {"valor": None, "trecho_citado": None, "motivo": f"falha na extração: {e}"}
        extracao_textual = {
            "prazo_execucao": campo_vazio,
            "exigencia_atestado_capacidade_tecnica": campo_vazio,
            "exigencias_habilitacao": campo_vazio,
        }

    return validar_contratacao(registro_api, extracao_textual, texto_edital)


def processar_lote(registros: list[dict]) -> list[ContratacaoExtraida]:
    """Roda o pipeline pra uma lista de registros, sem derrubar tudo se um falhar."""
    resultados = []
    for i, registro in enumerate(registros, 1):
        numero = registro.get("numeroControlePNCP", "?")
        print(f"[{i}/{len(registros)}] {numero}")
        try:
            resultados.append(processar_contratacao(registro))
        except Exception:
            import traceback
            print(f"[erro] {numero}: pipeline falhou completamente")
            traceback.print_exc()
    return resultados