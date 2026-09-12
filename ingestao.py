"""
Cliente para a API pública de consulta do PNCP (Portal Nacional de Contratações Públicas).

Código de apoio fornecido junto com o desafio técnico. A ideia é te poupar algumas
horas na etapa de ingestão para você gastar esse tempo no que interessa.

Uso rápido:

    python pncp_client.py --uf DF --dias 7 --modalidade 6 --limite 50 --saida editais.json

Documentação oficial da API de consulta:
    https://pncp.gov.br/api/consulta/swagger-ui/index.html

Sem dependências além de `requests`:

    pip install requests
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

import requests

logger = logging.getLogger("pncp")

BASE_URL = "https://pncp.gov.br/api/consulta/v1"

# Tamanho máximo de página aceito pela API. Valores maiores são rejeitados.
TAMANHO_PAGINA_MAX = 50

MODALIDADES = {
    1: "Leilão eletrônico",
    2: "Diálogo competitivo",
    3: "Concurso",
    4: "Concorrência eletrônica",
    5: "Concorrência presencial",
    6: "Pregão eletrônico",
    7: "Pregão presencial",
    8: "Dispensa de licitação",
    9: "Inexigibilidade",
    10: "Manifestação de interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão presencial",
}


class PNCPError(RuntimeError):
    """Falha ao conversar com a API do PNCP."""


@dataclass
class PaginaPNCP:
    """Uma página de resultados devolvida pela API."""

    data: list[dict[str, Any]] = field(default_factory=list)
    total_registros: int = 0
    total_paginas: int = 0
    numero_pagina: int = 0
    paginas_restantes: int = 0
    empty: bool = True

    @classmethod
    def from_response(cls, payload: dict[str, Any]) -> "PaginaPNCP":
        return cls(
            data=payload.get("data") or [],
            total_registros=payload.get("totalRegistros", 0),
            total_paginas=payload.get("totalPaginas", 0),
            numero_pagina=payload.get("numeroPagina", 0),
            paginas_restantes=payload.get("paginasRestantes", 0),
            empty=payload.get("empty", True),
        )


class PNCPClient:
    """Cliente HTTP com retry, backoff e rate limiting básico.

    A API de consulta do PNCP é aberta e não exige credencial, mas é instável em
    horário comercial: 429 e 5xx acontecem com frequência.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_tentativas: int = 3,
        intervalo_entre_chamadas: float = 0.5,
    ) -> None:
        self.timeout = timeout
        self.max_tentativas = max_tentativas
        self.intervalo = intervalo_entre_chamadas
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "radar-editais/0.1",
            }
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        ultima_excecao: Exception | None = None

        for tentativa in range(1, self.max_tentativas + 1):
            try:
                resposta = self.session.get(url, params=params, timeout=self.timeout)

                if resposta.status_code == 204:
                    # A API usa 204 quando o filtro não retorna nada.
                    return {"data": [], "totalRegistros": 0, "empty": True}

                if resposta.status_code == 429 or resposta.status_code >= 500:
                    espera = 2**tentativa
                    logger.warning(
                        "HTTP %s em %s — nova tentativa em %ss (%d/%d)",
                        resposta.status_code,
                        path,
                        espera,
                        tentativa,
                        self.max_tentativas,
                    )
                    time.sleep(espera)
                    continue

                resposta.raise_for_status()
                return resposta.json()

            except (requests.RequestException, ValueError) as exc:
                ultima_excecao = exc
                logger.warning("Falha em %s: %s", path, exc)
                time.sleep(2**tentativa)

        raise PNCPError(
            f"Não foi possível obter {path} após {self.max_tentativas} tentativas"
        ) from ultima_excecao

    def consultar_contratacoes(
        self,
        data_inicial: date,
        data_final: date,
        modalidade: int,
        uf: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = TAMANHO_PAGINA_MAX,
    ) -> PaginaPNCP:
        """Consulta uma única página de contratações por data de publicação."""
        params: dict[str, Any] = {
            "dataInicial": data_inicial.strftime("%Y%m%d"),
            "dataFinal": data_final.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
            "tamanhoPagina": min(tamanho_pagina, TAMANHO_PAGINA_MAX),
        }
        if uf:
            params["uf"] = uf.upper()

        payload = self._get("/contratacoes/publicacao", params)
        time.sleep(self.intervalo)
        return PaginaPNCP.from_response(payload)

    def coletar(
        self,
        data_inicial: date,
        data_final: date,
        modalidade: int,
        uf: str | None = None,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """Percorre as páginas e devolve os registros coletados, sem duplicatas."""
        registros: list[dict[str, Any]] = []
        pagina = 1

        while len(registros) < limite:
            resultado = self.consultar_contratacoes(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidade=modalidade,
                uf=uf,
                pagina=pagina,
            )

            if not resultado.data:
                break

            registros.extend(resultado.data)
            pagina += 1

        registros = _remover_duplicados(registros)
        logger.info("Coletados %d registros em %d página(s)", len(registros), pagina - 1)
        return registros[:limite]


def _remover_duplicados(registros: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove registros repetidos.

    Usa numeroControlePNCP como chave (identifica a contratação), não o CNPJ
    do órgão. A versão original usava CNPJ, o que descartava contratações
    legítimas sempre que o mesmo órgão publicava mais de uma na mesma janela
    de tempo — bug encontrado por auditoria manual comparando totalRegistros
    da API bruta com a saída do cliente.
    """
    vistos: set[str] = set()
    unicos: list[dict[str, Any]] = []

    for registro in registros:
        chave = registro.get("numeroControlePNCP")
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(registro)

    return unicos

def resumir(registro: dict[str, Any]) -> str:
    """Linha curta de resumo, útil para inspecionar os dados no terminal."""
    orgao = (registro.get("orgaoEntidade") or {}).get("razaoSocial", "?")
    unidade = registro.get("unidadeOrgao") or {}
    local = f"{unidade.get('municipioNome', '?')}/{unidade.get('ufSigla', '?')}"
    valor = registro.get("valorTotalEstimado")
    valor_fmt = f"R$ {valor:,.2f}" if isinstance(valor, (int, float)) else "sigiloso"
    objeto = (registro.get("objetoCompra") or "").strip().replace("\n", " ")

    return (
        f"[{registro.get('numeroControlePNCP', '?')}] {local} · {valor_fmt}\n"
        f"    {orgao}\n"
        f"    {objeto[:140]}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta contratações públicas do PNCP")
    parser.add_argument("--uf", default=None, help="Sigla da UF, ex: DF")
    parser.add_argument("--dias", type=int, default=7, help="Janela retroativa em dias")
    parser.add_argument(
        "--modalidade",
        type=int,
        default=6,
        help=f"Código da modalidade. Opções: {MODALIDADES}",
    )
    parser.add_argument("--limite", type=int, default=50, help="Máximo de registros")
    parser.add_argument("--saida", default=None, help="Arquivo JSON de saída")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    hoje = date.today()
    inicio = hoje - timedelta(days=args.dias)

    cliente = PNCPClient()
    registros = cliente.coletar(
        data_inicial=inicio,
        data_final=hoje,
        modalidade=args.modalidade,
        uf=args.uf,
        limite=args.limite,
    )

    for registro in registros:
        print(resumir(registro))
        print()

    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as arquivo:
            json.dump(registros, arquivo, ensure_ascii=False, indent=2)
        logger.info("Salvo em %s", args.saida)


if __name__ == "__main__":
    main()
