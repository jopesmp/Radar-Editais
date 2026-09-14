"""Script exploratório: lista os PDFs de Edital das 15 contratações do gabarito.

Não faz parte do pipeline formal — é só apoio pra anotação manual do Dia 2.
"""
import time
import requests

# Cada tupla: (numeroControlePNCP, cnpj, ano, sequencial) — os 15 escolhidos
CONTRATACOES_GABARITO = [
    ("18404855000143-1-000051/2026", "18404855000143", 2026, 51),
    ("18404855000143-1-000052/2026", "18404855000143", 2026, 52),
    ("18404855000143-1-000053/2026", "18404855000143", 2026, 53),
    ("00037457000170-1-000019/2026", "00037457000170", 2026, 19),
    ("01138122000101-1-000086/2026", "01138122000101", 2026, 86),
    ("00508903000188-1-001714/2026", "00508903000188", 2026, 1714),
    ("00360305000104-1-000705/2026", "00360305000104", 2026, 705),
    ("00360305000104-1-000720/2026", "00360305000104", 2026, 720),
    ("00360305000104-1-000721/2026", "00360305000104", 2026, 721),
    ("00360305000104-1-000723/2026", "00360305000104", 2026, 723),
    ("04892707000100-1-000125/2026", "04892707000100", 2026, 125),
    ("04892707000100-1-000128/2026", "04892707000100", 2026, 128),
    ("01137116000130-1-000038/2026", "01137116000130", 2026, 38),
    ("01409580000138-1-001406/2026", "01409580000138", 2026, 1406),
    ("45271342000184-1-000044/2026", "45271342000184", 2026, 44),
]

BASE_URL = "https://pncp.gov.br/api/pncp/v1"


def listar_documentos(cnpj: str, ano: int, sequencial: int) -> list[dict]:
    url = f"{BASE_URL}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def main() -> None:
    for numero_controle, cnpj, ano, sequencial in CONTRATACOES_GABARITO:
        print(f"\n=== {numero_controle} ===")
        try:
            documentos = listar_documentos(cnpj, ano, sequencial)
        except requests.RequestException as exc:
            print(f"  ERRO ao consultar: {exc}")
            continue

        if not documentos:
            print("  Nenhum documento encontrado.")
            continue

        for doc in documentos:
            print(f"  [{doc['tipoDocumentoNome']}] {doc['titulo']}")
            print(f"    {doc['url']}")

        time.sleep(0.5)  # não martelar a API


if __name__ == "__main__":
    main()