# Radar de Editais — Engevia

Sistema que ingere editais de licitação pública do PNCP, extrai 8 campos
estruturados, valida o que extraiu por regras determinísticas (sem IA) e
calcula um score de aderência ao perfil da Engevia Consultoria e Projetos.

## Como rodar:

### 1. Pré-requisitos

- Python 3.11+ instalado
- Uma chave de API do [OpenRouter](https://openrouter.ai) (gratuita)

### 2. Clonar e instalar dependências

```bash
git clone https://github.com/jopesmp/Radar-Editais.git
cd Radar-Editais
pip install -r requirements.txt
```

### 3. Configurar a chave da API

Copia o arquivo de exemplo e cola sua chave:

```bash
cp .env.example .env
```

Abre o `.env` recém-criado e preenche:

OPENROUTER_API_KEY=sua_chave_aqui

### 4. Rodar a avaliação (opcional, mas recomendado primeiro)

Confirma que tudo está funcionando comparando contra o gabarito de 15 documentos
anotados à mão:

```bash
python eval.py
```

Isso imprime a acurácia por campo. Ver `RESULTADOS.md` para os números de
referência e o contexto de cada um.

### 5. Rodar o pipeline completo (ingestão + extração + validação + score)

```bash
python -m scripts.rodar_pipeline_completo
```

Isso coleta contratações reais do PNCP (DF/GO/MG, últimos 7 dias), processa
até 50 delas, e salva o resultado em `dados/processados/oportunidades.json`.
Demora alguns minutos — cada documento passa por uma chamada real a um LLM
gratuito (latência típica: 8-25s por documento; ver `RESULTADOS.md`).

**Nota:** o script já usa dados brutos previamente coletados em
`dados/brutos/`. Para coletar dados novos da API do PNCP, use `ingestao.py`
diretamente (ver seção "Coletando novos dados" abaixo).

### 6. Subir a API

```bash
python -m uvicorn api:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Endpoint principal:

GET /oportunidades?min_score=70


Retorna as contratações processadas com score de aderência maior ou igual ao
valor informado, ordenadas da maior pra menor pontuação.

## Estrutura do projeto

.
├── schema.py              # formato dos dados (dataclasses) — sem lógica de decisão
├── ingestao.py             # coleta de dados da API do PNCP (corrige bug herdado de dedup)
├── extracao.py             # extração via LLM (só os 3 campos que exigem ler o PDF)
├── validacao.py            # validação determinística — NUNCA importa extracao.py nem chama LLM
├── score.py                # cálculo do score de aderência ao perfil da Engevia
├── pipeline.py              # orquestrador: liga extracao.py e validacao.py
├── storage.py               # persistência em JSON (sem banco relacional, fora de escopo)
├── api.py                   # FastAPI, endpoint GET /oportunidades
├── eval.py                  # harness de avaliação contra o gabarito
├── gabarito/                # 15 contratações anotadas manualmente
├── dados/
│   ├── brutos/               # JSON cru coletado da API do PNCP
│   └── processados/          # saída do pipeline
└── scripts/                 # utilitários de apoio (não fazem parte do pipeline formal)


## Coletando novos dados

```bash
python ingestao.py --uf DF --dias 7 --modalidade 6 --limite 50 --saida meus_dados.json -v
```

Parâmetros: `--uf` (uma UF por vez), `--dias` (janela retroativa), `--modalidade`
(código PNCP: 6 = pregão eletrônico, 4 = concorrência eletrônica), `--limite`.

## Limitações conhecidas

Ver `RESULTADOS.md`, seção "O que não funcionou", para a lista completa.
Resumo rápido: ~34% dos documentos reais vêm em `.zip`/`.rar` (não processados
pelo MVP); documentos escaneados sem camada de texto não são lidos; o tier
gratuito do OpenRouter tem limite de requisições que pode degradar a
performance sob uso intenso.

## Decisões técnicas

Ver `DECISOES.md` para as decisões de arquitetura tomadas, alternativas
descartadas, e o que seria feito diferente com mais tempo.

## Uso de IA no desenvolvimento

Ver `AI_LOG.md` para onde Claude foi usado como par de programação, erros
cometidos (por Claude e pelo modelo gratuito no pipeline), e como foram
percebidos e corrigidos.
