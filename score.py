"""Score de aderência ao perfil da Engevia — 5 critérios, normalizado só sobre
os critérios que puderam ser avaliados (ver DECISOES.md, Dia 1, Opção B).
"""
import re

from schema import ContratacaoExtraida, CriterioScore, ScoreAderencia

UFS_AREA_ATUACAO = {"DF", "GO", "MG"}

ESPECIALIDADES_POSITIVAS = [
    "drenagem", "pavimenta", "pavimento", "projeto executivo",
    "projeto básico", "fiscalização de obra", "gerenciamento de obra",
    "infraestrutura viária", "sistema viário",
]
NAO_FAZ = [
    "edificação vertical", "edifício residencial", "elétrica de alta tensão",
    "alta tensão", "saneamento", " ete ", " eta ", "estação de tratamento",
]

TETO_OPERACIONAL = 5_000_000
PISO_INTERESSE = 150_000


def _criterio_localizacao(c: ContratacaoExtraida) -> CriterioScore:
    campo = c.municipio_uf
    if not campo.confiavel:
        return CriterioScore("localizacao", 15, None, False, "município/UF não confiável para avaliar", None)

    uf = campo.valor.strip().split("/")[-1].strip().upper()
    if uf in UFS_AREA_ATUACAO:
        return CriterioScore("localizacao", 15, 15, True, f"{campo.valor} está na área de atuação padrão (DF/GO/MG)", "municipio_uf")
    return CriterioScore(
        "localizacao", 15, 0, True,
        f"{campo.valor} fora da área de atuação padrão (DF/GO/MG). Perfil permite exceção 'com margem alta', "
        "mas não há dado de margem disponível no pipeline para avaliar essa exceção — pontuação conservadora.",
        "municipio_uf",
    )


def _criterio_aderencia_objeto(c: ContratacaoExtraida) -> CriterioScore:
    campo = c.objeto
    if not campo.confiavel:
        return CriterioScore("aderencia_objeto", 30, None, False, "objeto não confiável para avaliar", None)

    texto = campo.valor.lower()
    tem_positivo = any(termo in texto for termo in ESPECIALIDADES_POSITIVAS)
    tem_negativo = any(termo in texto for termo in NAO_FAZ)

    if tem_negativo and not tem_positivo:
        return CriterioScore("aderencia_objeto", 30, 0, True, "objeto menciona atividade que a Engevia não faz", "objeto")
    if tem_positivo and tem_negativo:
        return CriterioScore("aderencia_objeto", 30, 15, True, "objeto misto: mistura especialidade da Engevia com algo que ela não faz", "objeto")
    if tem_positivo:
        return CriterioScore("aderencia_objeto", 30, 30, True, "objeto menciona diretamente especialidade da Engevia", "objeto")
    return CriterioScore("aderencia_objeto", 30, 10, True, "objeto não menciona claramente nenhuma especialidade nem contraria — neutro/baixo", "objeto")


def _criterio_valor(c: ContratacaoExtraida) -> CriterioScore:
    campo = c.valor_estimado
    if not campo.confiavel:
        return CriterioScore("valor_na_faixa_operacional", 20, None, False, "valor não confiável para avaliar", None)

    valor = campo.valor
    if PISO_INTERESSE <= valor <= TETO_OPERACIONAL:
        return CriterioScore("valor_na_faixa_operacional", 20, 20, True, f"R$ {valor:,.2f} dentro da faixa operacional (R$150mil–R$5mi)", "valor_estimado")
    if valor > TETO_OPERACIONAL:
        return CriterioScore("valor_na_faixa_operacional", 20, 3, True, f"R$ {valor:,.2f} acima do teto operacional de R$5 milhões", "valor_estimado")
    return CriterioScore("valor_na_faixa_operacional", 20, 5, True, f"R$ {valor:,.2f} abaixo do piso de interesse de R$150 mil", "valor_estimado")


def _criterio_modalidade(c: ContratacaoExtraida) -> CriterioScore:
    campo = c.modalidade
    if not campo.confiavel:
        return CriterioScore("modalidade_preferida", 15, None, False, "modalidade não confiável para avaliar", None)

    texto = campo.valor.lower()
    if "dispensa" in texto or "inexigibilidade" in texto:
        return CriterioScore("modalidade_preferida", 15, 0, True, "modalidade evitada pela Engevia (dispensa/inexigibilidade)", "modalidade")
    if "pregão" in texto or "concorrência" in texto:
        return CriterioScore("modalidade_preferida", 15, 15, True, f"{campo.valor} está entre as modalidades preferidas", "modalidade")
    return CriterioScore("modalidade_preferida", 15, 7, True, f"{campo.valor} não é preferida nem evitada explicitamente — neutro", "modalidade")


def _criterio_atestado(c: ContratacaoExtraida) -> CriterioScore:
    campo = c.exigencia_atestado_capacidade_tecnica
    if not campo.confiavel:
        return CriterioScore("atestado_tecnico", 20, None, False, "exigência de atestado não confiável/indisponível para avaliar", None)

    # Simplificação de MVP: não comparamos quantidades numéricas da exigência
    # contra os atestados reais da Engevia (12km pavimentação, R$4mi drenagem)
    # de forma automática — sinaliza como compatível por padrão quando a
    # exigência está confiável, com nota explícita da limitação.
    return CriterioScore(
        "atestado_tecnico", 20, 15, True,
        "exigência de atestado presente e confiável; comparação quantitativa automática contra os "
        "atestados da Engevia não implementada no MVP (simplificação documentada)",
        "exigencia_atestado_capacidade_tecnica",
    )


def calcular_score(c: ContratacaoExtraida) -> ScoreAderencia:
    criterios = [
        _criterio_localizacao(c),
        _criterio_aderencia_objeto(c),
        _criterio_valor(c),
        _criterio_modalidade(c),
        _criterio_atestado(c),
    ]

    avaliados = [cr for cr in criterios if cr.avaliado]
    pontos_obtidos = sum(cr.pontos for cr in avaliados)
    pontos_possiveis_avaliados = sum(cr.peso_maximo for cr in avaliados)
    pontos_possiveis_totais = sum(cr.peso_maximo for cr in criterios)

    valor_final = (pontos_obtidos / pontos_possiveis_avaliados * 100) if pontos_possiveis_avaliados > 0 else 0.0

    return ScoreAderencia(
        valor_final=round(valor_final, 1),
        pontos_obtidos=pontos_obtidos,
        pontos_possiveis_avaliados=pontos_possiveis_avaliados,
        pontos_possiveis_totais=pontos_possiveis_totais,
        criterios_avaliados=len(avaliados),
        criterios_totais=len(criterios),
        detalhamento=criterios,
    )