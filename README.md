# Radar de Editais — Engevia

Sistema que ingere editais de licitação pública do PNCP, extrai 8 campos
estruturados, valida o que extraiu por regras determinísticas e
calcula um score de aderência ao perfil da Engevia Consultoria e Projetos.

## Duas formas de rodar

Este README tem dois caminhos, dependendo do que você quer ver:

- **Demo rápida**: usa dados já processados, commitados no repositório como
  exemplo. Mostra a API e o front funcionando sem esperar nenhuma chamada de
  LLM.
- **Execução completa**: roda o pipeline do zero — coleta, extração via LLM,
  validação e score — sobre dados novos, coletados na hora da API do PNCP.

Os passos 1-3 (pré-requisitos, instalação, chave de API) são comuns aos dois
caminhos. A partir do passo 4, escolha um dos dois.

## Pré-requisitos comuns

### 1. Pré-requisitos

- Python 3.11+ instalado
- Uma chave de API do [OpenRouter](https://openrouter.ai) (gratuita) —
  necessária mesmo para a Demo rápida, pois a API de importação
  (`import fastapi` etc.) e o restante do projeto compartilham o mesmo
  `.env`; só a chamada real ao LLM é evitada nesse caminho.

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

```
OPENROUTER_API_KEY=sua_chave_aqui
```

---

## Caminho A — Demo rápida

Usa o `dados/processados/oportunidades.json` já commitado no repositório —
resultado de uma execução anterior do pipeline completo, mantido como
exemplo. Pule direto para o passo 6.

### 4. (pulado neste caminho — não é preciso rodar o pipeline)

### 5. (pulado neste caminho)

Não é preciso rodar `eval.py` para ver a demo, mas se quiser conferir a
acurácia medida contra o gabarito, veja o Caminho B, passo 4, ou direto
`RESULTADOS.md`.

### 6. Subir a API

```bash
python -m uvicorn api:app --reload
```

A API sobe em `http://127.0.0.1:8000` e já serve o conteúdo de
`dados/processados/oportunidades.json`.

Testa rápido que está no ar:

```bash
curl "http://127.0.0.1:8000/oportunidades?min_score=70"
```

Deve retornar um JSON com `total` e uma lista de `oportunidades`. Se vier
vazio, tenta `min_score=0` para conferir se há dados carregados.

### 7. Abrir o front-end

Em um **segundo terminal** (deixe o `uvicorn` do passo 6 rodando no
primeiro), a partir da raiz do projeto:

```bash
python -m http.server 5500
```

Depois, abra no navegador:

```
http://localhost:5500/frontend/index.html
```

A página busca os dados da API automaticamente. Use o slider para filtrar
por score mínimo; cada oportunidade mostra os 8 campos extraídos (com aviso
visual nos marcados como não confiáveis) e o detalhamento do cálculo do
score. Se a API não estiver no ar, a página mostra um aviso de erro de
conexão em vez de travar carregando.

---

## Caminho B — Execução completa (pipeline do zero)

Roda a coleta, extração, validação e score sobre dados novos, coletados na
hora direto da API do PNCP. Use este caminho se quiser ver o pipeline
processando editais reais, não só os já commitados como exemplo.

### 4. Rodar a avaliação (opcional, mas recomendado primeiro)

Confirma que tudo está funcionando comparando contra o gabarito de 15
documentos anotados à mão:

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
até 50 delas, e **sobrescreve** `dados/processados/oportunidades.json` com o
resultado novo. Demora alguns minutos — cada documento passa por uma chamada
real a um LLM gratuito (latência típica: 8-25s por documento; ver
`RESULTADOS.md`).

> **Nota:** este script usa dados brutos já coletados em `dados/brutos/`.
> Para coletar dados novos da API do PNCP antes de processar, use
> `ingestao.py` diretamente (ver seção "Coletando novos dados" abaixo).

### 6. Subir a API

```bash
python -m uvicorn api:app --reload
```

A API sobe em `http://127.0.0.1:8000` e agora serve o resultado que você
acabou de gerar no passo 5.

Testa rápido que está no ar:

```bash
curl "http://127.0.0.1:8000/oportunidades?min_score=70"
```

### 7. Abrir o front-end (opcional)

Mesmos passos do Caminho A, item 7 — o front consome a API independente de
qual caminho gerou os dados.

---

## Estrutura do projeto

```
.
├── schema.py              # formato dos dados (dataclasses) — sem lógica de decisão
├── ingestao.py            # coleta de dados da API do PNCP (corrige bug herdado de dedup)
├── extracao.py            # extração via LLM (só os 3 campos que exigem ler o PDF)
├── validacao.py           # validação determinística — NUNCA importa extracao.py nem chama LLM
├── score.py                # cálculo do score de aderência ao perfil da Engevia
├── pipeline.py             # orquestrador: liga extracao.py e validacao.py
├── storage.py               # persistência em JSON (sem banco relacional, fora de escopo)
├── api.py                    # FastAPI, endpoint GET /oportunidades
├── eval.py                    # harness de avaliação contra o gabarito
├── frontend/
│   └── index.html             # front simples que consome a própria API (opcional, bônus)
├── gabarito/                   # 15 contratações anotadas manualmente
├── dados/
│   ├── brutos/                  # JSON cru coletado da API do PNCP
│   └── processados/              # saída do pipeline — já vem com um exemplo commitado
└── scripts/                       # utilitários de apoio (não fazem parte do pipeline formal)
```

## Coletando novos dados

```bash
python ingestao.py --uf DF --dias 7 --modalidade 6 --limite 50 --saida meus_dados.json -v
```

Parâmetros: `--uf` (uma UF por vez), `--dias` (janela retroativa),
`--modalidade` (código PNCP: 6 = pregão eletrônico, 4 = concorrência
eletrônica), `--limite`.

## Limitações conhecidas

Ver `RESULTADOS.md`, seção "O que não funcionou", para a lista completa.
Resumo rápido: ~34% dos documentos reais vêm em `.zip`/`.rar` (não
processados pelo MVP); documentos escaneados sem camada de texto não passam
por OCR (fora do MVP, por decisão consciente de custo — ver `DECISOES.md`);
o tier gratuito do OpenRouter tem limite de requisições que pode degradar a
performance sob uso intenso.

## Decisões técnicas

Ver `DECISOES.md` para as decisões de arquitetura tomadas, alternativas
descartadas, e o que seria feito diferente com mais tempo.

## Uso de IA no desenvolvimento

Ver `AI_LOG.md` para onde Claude foi usado como par de programação, erros
cometidos (por Claude e pelo modelo gratuito no pipeline), e como foram
percebidos e corrigidos.
