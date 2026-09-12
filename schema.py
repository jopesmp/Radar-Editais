from dataclasses import dataclass
from typing import Any


@dataclass
class CampoExtraido:
    """Representa um único campo extraído (ex: valor_estimado, objeto, etc).

    Segue o padrão que desenhamos: guarda o valor (se houver), se é
    confiável, o motivo (quando não confiável ou ausente) e de onde veio.
    """
    valor: Any
    confiavel: bool
    motivo: str | None = None
    fonte: str | None = None

@dataclass
class ContratacaoExtraida:
    """Os 8 campos extraídos de uma contratação, mais o identificador dela."""
    numero_controle_pncp: str
    objeto: CampoExtraido
    modalidade: CampoExtraido
    valor_estimado: CampoExtraido
    prazo_execucao: CampoExtraido
    data_abertura_propostas: CampoExtraido
    exigencia_atestado_capacidade_tecnica: CampoExtraido
    exigencias_habilitacao: CampoExtraido
    municipio_uf: CampoExtraido

@dataclass
class CriterioScore:
    """Um critério individual do score de aderência (ex: localização, modalidade).

    'pontos' e 'fonte' são None quando o critério não pôde ser avaliado —
    nesse caso ele fica de fora do cálculo do score final, em vez de contar
    como zero (decisão registrada no DECISOES.md: falta de dado != critério ruim).
    """
    criterio: str
    peso_maximo: float
    pontos: float | None
    avaliado: bool
    justificativa: str
    fonte: str | None = None


@dataclass
class ScoreAderencia:
    """Score de aderência de uma contratação ao perfil da Engevia.

    valor_final é normalizado: pontos_obtidos / pontos_possiveis_avaliados,
    não sobre pontos_possiveis_totais — por isso os dois campos ficam
    visíveis junto com criterios_avaliados/criterios_totais, pra não
    esconder quando o score foi calculado sobre poucos critérios.
    """
    valor_final: float
    pontos_obtidos: float
    pontos_possiveis_avaliados: float
    pontos_possiveis_totais: float
    criterios_avaliados: int
    criterios_totais: int
    detalhamento: list[CriterioScore]