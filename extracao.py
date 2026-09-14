"""Extração via LLM dos 3 campos que só existem no texto do edital.

Os outros 5 campos (objeto, modalidade, valor, data de abertura, município/UF)
vêm direto da API do PNCP via ingestao.py e NÃO passam por aqui — só os campos
textuais (prazo de execução, atestado técnico, exigências de habilitação)
exigem ler o PDF, porque a API não os fornece (ver DECISOES.md, Dia 1).
"""
import io

import requests
from pypdf import PdfReader

BASE_URL_ARQUIVOS = "https://pncp.gov.br/api/pncp/v1"


def listar_documentos(cnpj: str, ano: int, sequencial: int) -> list[dict]:
    """Lista os documentos (PDFs) anexados a uma contratação."""
    url = f"{BASE_URL_ARQUIVOS}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def extrair_texto_edital(cnpj: str, ano: int, sequencial: int) -> str | None:
    """Baixa o primeiro documento do tipo 'Edital' e extrai o texto dele.

    Retorna None se: não houver documento, o download falhar, ou o PDF não
    tiver camada de texto (documento escaneado) — esses casos ficam para o
    extracao.py decidir o que fazer (campos viram null com motivo).
    """
    documentos = listar_documentos(cnpj, ano, sequencial)

    edital = next(
        (doc for doc in documentos if doc.get("tipoDocumentoNome") == "Edital"),
        None,
    )
    if edital is None:
        return None

    resposta = requests.get(edital["url"], timeout=60)
    resposta.raise_for_status()

    leitor = PdfReader(io.BytesIO(resposta.content))
    texto = "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)

    texto = texto.strip()
    return texto if texto else None

import json
import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO = "google/gemma-4-26b-a4b-it:free"
LIMITE_CARACTERES = 60_000  


def montar_prompt(texto_edital: str) -> str:
    texto_recortado = texto_edital[:LIMITE_CARACTERES]
    return f"""Você vai ler um trecho de um edital de licitação pública brasileira e extrair 3 informações específicas.

REGRAS IMPORTANTES:
- Só extraia informação que está EXPLICITAMENTE escrita no texto. Nunca deduza, infira ou complete com conhecimento geral.
- Para cada campo, cite o TRECHO EXATO do texto (copiado literalmente, palavra por palavra) que comprova sua resposta.
- - Se a informação não aparecer no texto, retorne valor null e trecho_citado null para aquele campo. Não invente.
- O texto pode ter cabeçalhos de capítulo quebrados por PDF mal formatado (ex: "HABILIT\nAÇÃO"). Procure os conceitos mesmo que o cabeçalho esteja com espaçamento ou quebra de linha estranha.
- Leia o texto INTEIRO antes de responder, não só o início — as informações podem estar em qualquer parte do documento.

Responda APENAS com um JSON válido, neste formato exato:
{{
  "prazo_execucao": {{"valor": "string ou null", "trecho_citado": "string ou null"}},
  "exigencia_atestado_capacidade_tecnica": {{"valor": "string ou null", "trecho_citado": "string ou null"}},
  "exigencias_habilitacao": {{"valor": "string ou null", "trecho_citado": "string ou null"}}
}}

Campos a extrair:
1. prazo_execucao: prazo de entrega, execução ou vigência do contrato/serviço.
2. exigencia_atestado_capacidade_tecnica: exigência específica de atestado de capacidade técnica (quantidades, tipos de serviço comprovado, etc). Se o edital só remeter a outro documento (Termo de Referência/Projeto Básico) sem detalhar aqui, retorne null.
3. exigencias_habilitacao: lista resumida das exigências de habilitação (jurídica, fiscal, econômico-financeira, técnica).

TEXTO DO EDITAL:
{texto_recortado}
"""


def _limpar_bloco_markdown(texto: str) -> str:
    """Remove cercas de markdown (```json ... ```) que alguns modelos usam
    mesmo quando response_format=json_object foi pedido."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1] if "\n" in texto else texto
        if texto.endswith("```"):
            texto = texto.rsplit("```", 1)[0]
    return texto.strip()


MODELOS_FALLBACK = [
    "nex-agi/nex-n2.5-mini:free",
    "inclusionai/ling-3.0-flash-vl:free",
    "google/gemma-4-26b-a4b-it:free",
    "poolside/laguna-xs-2.1:free",
    "nvidia/nemotron-3.5-lightning:free",
]


def chamar_llm(prompt: str, tentativas_por_modelo: int = 1) -> tuple[dict, str, float]:
    """Tenta os modelos da lista de fallback em ordem, usando o primeiro que responder.

    Retorna (json_extraido, nome_do_modelo_usado, latencia_em_segundos).
    """
    import time

    ultimo_erro = None

    for modelo in MODELOS_FALLBACK:
        for _ in range(tentativas_por_modelo):
            inicio = time.time()
            try:
                resposta = requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": modelo,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 3000,
                        "reasoning": {"enabled": False},
                    },
                    timeout=45,
                )
                latencia = time.time() - inicio

                if resposta.status_code != 200:
                    print(f"[aviso] {modelo}: HTTP {resposta.status_code}, tentando próximo modelo...")
                    ultimo_erro = resposta.text
                    break  # não insiste no mesmo modelo, pula pro próximo

                dados = resposta.json()
                conteudo = dados["choices"][0]["message"].get("content")
                if not conteudo or not conteudo.strip():
                    print(f"[aviso] {modelo}: content vazio, tentando próximo modelo...")
                    break

                conteudo_limpo = _limpar_bloco_markdown(conteudo)
                try:
                    return json.loads(conteudo_limpo), modelo, latencia
                except json.JSONDecodeError:
                    print(f"[aviso] {modelo}: JSON inválido, tentando próximo modelo...")
                    break

            except requests.exceptions.RequestException as e:
                print(f"[aviso] {modelo}: {type(e).__name__}, tentando próximo modelo...")
                ultimo_erro = str(e)
                break

    raise RuntimeError(f"Todos os modelos de fallback falharam. Último erro: {ultimo_erro}")


def extrair_campos_textuais(cnpj: str, ano: int, sequencial: int) -> dict:
    """Retorna os 3 campos textuais extraídos via LLM, mais metadados de execução."""
    texto = extrair_texto_edital(cnpj, ano, sequencial)

    if texto is None:
        motivo = "documento não encontrado ou sem camada de texto extraível (PDF escaneado)"
        campo_vazio = {"valor": None, "trecho_citado": None, "motivo": motivo}
        return {
            "prazo_execucao": campo_vazio,
            "exigencia_atestado_capacidade_tecnica": campo_vazio,
            "exigencias_habilitacao": campo_vazio,
            "modelo_usado": None,
            "latencia_segundos": None,
        }

    prompt = montar_prompt(texto)
    resultado, modelo, latencia = chamar_llm(prompt)
    resultado["modelo_usado"] = modelo
    resultado["latencia_segundos"] = latencia
    return resultado