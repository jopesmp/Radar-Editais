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