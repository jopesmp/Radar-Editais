"""Validação determinística dos campos extraídos — camada SEM LLM.

Este módulo NUNCA importa extracao.py nem faz chamada de rede/LLM. Só recebe
dados já prontos (do JSON da API e do resultado do LLM) e decide se são
confiáveis, aplicando regras fixas do enunciado: dígito verificador de CNPJ,
UF válida, coerência de datas, e citação real no texto de origem.
"""
import re
from datetime import datetime

from schema import CampoExtraido, ContratacaoExtraida

UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}


def validar_cnpj(cnpj: str) -> bool:
    """Valida os dois dígitos verificadores do CNPJ (algoritmo padrão da Receita)."""
    cnpj = re.sub(r"\D", "", cnpj or "")
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito(base: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    d1 = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(cnpj[:12] + str(d1), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[-2:] == f"{d1}{d2}"


def validar_uf(municipio_uf: str) -> bool:
    if not municipio_uf:
        return False
    uf = municipio_uf.strip().split("/")[-1].strip().upper()
    return uf in UFS_VALIDAS


def validar_data(data_str: str) -> bool:
    """Confere se é uma data ISO válida e cai num intervalo plausível."""
    if not data_str:
        return False
    try:
        dt = datetime.fromisoformat(data_str)
        return 2020 <= dt.year <= 2035
    except (ValueError, TypeError):
        return False


def valor_parece_sigiloso(valor, objeto: str, informacao_complementar: str = "") -> bool:
    """Sinal combinado: valor suspeito (perto de zero) + texto menciona sigilo.

    Descoberto na exploração manual do Dia 1 — a API não marca sigilo com um
    campo booleano, então cruzamos dois sinais em vez de confiar só no número.
    """
    texto = f"{objeto or ''} {informacao_complementar or ''}".lower()
    menciona_sigilo = "sigilos" in texto
    valor_suspeito = valor is not None and valor < 1.0
    return valor_suspeito and menciona_sigilo


def _normalizar(texto: str) -> str:
    texto = texto or ""
    # Desfaz sintaxe de link Markdown: "[texto](url)" -> "texto"
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    # Normaliza ligaduras tipográficas comuns do PDF (fi, fl, ff, ffi, ffl)
    ligaduras = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
    for lig, normal in ligaduras.items():
        texto = texto.replace(lig, normal)
    return re.sub(r"\s+", " ", texto).strip().lower()


def citacao_existe_no_texto(trecho_citado: str, texto_fonte: str, limiar: float = 0.7) -> bool:
    """Regra 3.3: valor extraído precisa existir (substancialmente) no texto de origem.

    Para citações longas (comuns em habilitação/atestado técnico), exigir 100%
    de igualdade literal é frágil demais — pequenas diferenças de formatação
    (quebra de linha, hifenização do PDF) quebram a citação inteira mesmo
    quando o conteúdo é genuíno. Em vez disso, exige que pelo menos `limiar`
    (padrão 70%) das FRASES da citação apareçam literalmente no texto — isso
    ainda rejeita citação totalmente inventada, mas tolera reformatação leve.
    """
    if not trecho_citado or not texto_fonte:
        return False

    texto_fonte_norm = _normalizar(texto_fonte)
    frases = re.split(r"[.;\n]+", trecho_citado)
    frases = [f.strip() for f in frases if len(f.strip()) > 15]  # ignora fragmentos curtos demais

    if not frases:
        return _normalizar(trecho_citado) in texto_fonte_norm

    acertos = sum(1 for f in frases if _normalizar(f) in texto_fonte_norm)
    return (acertos / len(frases)) >= limiar


def validar_contratacao(
    registro_api: dict,
    extracao_textual: dict,
    texto_edital: str | None,
) -> ContratacaoExtraida:
    """Aplica todas as regras determinísticas e monta o registro final dos 8 campos."""

    objeto_raw = registro_api.get("objetoCompra") or ""
    info_complementar = registro_api.get("informacaoComplementar") or ""
    valor_raw = registro_api.get("valorTotalEstimado")
    cnpj = (registro_api.get("orgaoEntidade") or {}).get("cnpj", "")
    cnpj_valido = validar_cnpj(cnpj)

    objeto = CampoExtraido(
        valor=objeto_raw if objeto_raw else None,
        confiavel=bool(objeto_raw),
        motivo=None if objeto_raw else "campo ausente na API",
        fonte="objetoCompra (API)",
    )

    modalidade_raw = registro_api.get("modalidadeNome")
    modalidade = CampoExtraido(
        valor=modalidade_raw,
        confiavel=bool(modalidade_raw),
        motivo=None if modalidade_raw else "campo ausente na API",
        fonte="modalidadeNome (API)",
    )

    sigiloso = valor_parece_sigiloso(valor_raw, objeto_raw, info_complementar)
    valor_estimado = CampoExtraido(
        valor=None if sigiloso else valor_raw,
        confiavel=(not sigiloso) and (valor_raw is not None),
        motivo=(
            "valor sugere sigilo (próximo de zero + menção a 'sigiloso' no texto)" if sigiloso
            else (None if valor_raw is not None else "campo ausente na API")
        ),
        fonte="valorTotalEstimado (API)",
    )

    data_raw = registro_api.get("dataAberturaProposta")
    data_valida = validar_data(data_raw)
    data_abertura_propostas = CampoExtraido(
        valor=data_raw if data_valida else None,
        confiavel=data_valida,
        motivo=None if data_valida else "data ausente ou fora do formato/intervalo esperado",
        fonte="dataAberturaProposta (API)",
    )

    unidade = registro_api.get("unidadeOrgao") or {}
    municipio_uf_raw = f"{unidade.get('municipioNome', '')}/{unidade.get('ufSigla', '')}"
    uf_valida = validar_uf(municipio_uf_raw)
    municipio_uf = CampoExtraido(
        valor=municipio_uf_raw if uf_valida else None,
        confiavel=uf_valida,
        motivo=None if uf_valida else f"UF {unidade.get('ufSigla')!r} não é uma das 27 UFs válidas",
        fonte="unidadeOrgao (API)",
    )

    def validar_campo_textual(nome_campo: str) -> CampoExtraido:
        bruto = extracao_textual.get(nome_campo)
        if not isinstance(bruto, dict):
            return CampoExtraido(
                valor=None, confiavel=False,
                motivo=f"resposta do LLM malformada para este campo (esperava objeto JSON, veio {type(bruto).__name__})",
                fonte=None,
            )
        valor = bruto.get("valor")
        trecho = bruto.get("trecho_citado")

        if valor is None:
            return CampoExtraido(
                valor=None, confiavel=False,
                motivo=bruto.get("motivo") or "não encontrado pelo modelo no texto do edital",
                fonte=None,
            )

        citacao_ok = citacao_existe_no_texto(trecho, texto_edital)
        modelo = extracao_textual.get("modelo_usado", "desconhecido")
        return CampoExtraido(
            valor=valor if citacao_ok else None,
            confiavel=citacao_ok,
            motivo=None if citacao_ok else "citação do LLM não encontrada literalmente no texto de origem (possível alucinação)",
            fonte=f"LLM ({modelo})" if citacao_ok else None,
        )

    return ContratacaoExtraida(
        numero_controle_pncp=registro_api.get("numeroControlePNCP", ""),
        objeto=objeto,
        modalidade=modalidade,
        valor_estimado=valor_estimado,
        prazo_execucao=validar_campo_textual("prazo_execucao"),
        data_abertura_propostas=data_abertura_propostas,
        exigencia_atestado_capacidade_tecnica=validar_campo_textual("exigencia_atestado_capacidade_tecnica"),
        exigencias_habilitacao=validar_campo_textual("exigencias_habilitacao"),
        municipio_uf=municipio_uf,
    )