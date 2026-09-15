# RESULTADOS.md

## Resumo por dia

**Dia 1 — Ingestão e exploração.** Mapeada a API do PNCP (duas especificações OpenAPI
distintas: consulta pública e a API de manutenção com GETs públicos escondidos).
Descoberto que 5 dos 8 campos pedidos vêm prontos da API; os outros 3 exigem ler o PDF
do edital. Corrigido um bug real no `pncp_client.py` herdado: a deduplicação usava
`orgaoEntidade.cnpj` como chave, descartando ~30% dos registros legítimos sempre que o
mesmo órgão publicava mais de uma contratação na mesma janela (medido: 50 registros
brutos → 35 após a dedup incorreta → 50 após a correção, trocando a chave para
`numeroControlePNCP`).

**Dia 2 — Gabarito.** Anotados manualmente 15 documentos, escolhidos por categoria de
dificuldade de extração (não pelos mais fáceis), cobrindo: documento limpo, valor
sigiloso (3 variações — fictício, temporário e permanente), anexo ausente, plataforma
de publicação diferente, objeto ambíguo, e modalidade fora do pregão.

**Dia 3 — Extração, validação, score, API.** Pipeline completo implementado e testado
ponta a ponta em 50 contratações reais (ingestão → extração LLM → validação
determinística → score → API FastAPI). 46-50 processadas com sucesso a cada rodada
(variação por instabilidade momentânea do provedor gratuito, nunca por falha
estrutural do pipeline).

**Dia 4 — Evals e ajuste da métrica.** Reescrito `eval.py` para medir o pipeline
completo (pós-validação), não só a extração isolada. Corrigidos dois problemas na
métrica de comparação (ligaduras tipográficas do PDF e checagem de citação por
igualdade exata demais para textos longos) — ambos aumentaram a acurácia medida sem
mudar uma linha do sistema, só corrigindo como medíamos.

## Acurácia por campo (pipeline completo, contra os 15 documentos do gabarito)

Última medição, com a métrica de citação já corrigida:

| Campo | Acurácia de presença | Similaridade de texto (quando ambos têm valor) |
|---|---|---|
| objeto | 100% (15/15) | 0.80 |
| modalidade | 100% (15/15) | 0.77 |
| valor_estimado | 67% (10/15) | 1.00 (n=10) |
| data_abertura_propostas | 100% (15/15) | 0.79 |
| municipio_uf | 100% (15/15) | 0.72 |
| prazo_execucao | 67% (10/15) | 0.27 (n=7) |
| exigencia_atestado_capacidade_tecnica | 47% (7/15) | sem casos comparáveis nessa rodada |
| exigencias_habilitacao | 47% (7/15) | 0.22 (n=7) |

**Leitura dos números:** os 5 campos que vêm direto da API (sem LLM) têm acurácia de
presença de 100% — esperado, já que não dependem de extração, só de validação
determinística (CNPJ, UF, data, sigilo). Os 3 campos que dependem do LLM (prazo,
atestado, habilitação) ficam entre 47-67%, refletindo tanto a capacidade real do
modelo gratuito quanto — de forma importante — o esgotamento de cota gratuita
observado ao longo do dia (ver seção de latência/limitações abaixo). Em execuções
anteriores no mesmo dia, sob cota mais disponível, esses mesmos campos chegaram a
90% de acurácia de presença nos documentos que o pipeline conseguiu processar
(ver rodada do Dia 3).

**Sobre a similaridade de texto:** valores baixos em prazo/habilitação **não** indicam
conteúdo errado — indicam paráfrase. Conferimos manualmente vários casos (ex: o
atestado técnico da NOVACAP) onde o conteúdo extraído estava correto, mas reescrito
com palavras diferentes do gabarito. SequenceMatcher penaliza isso pesadamente; é uma
métrica fraca para texto livre, mantida por simplicidade (sem dependência nova) mas
documentada como limitação.

## Custo médio por documento

**R$ 0,00.** Todos os modelos usados no pipeline são de tier gratuito do OpenRouter,
por exigência da regra 3.1 do desafio.

## Latência média por documento

- Rodada do Dia 3 (cota gratuita disponível): **~12 segundos** por documento com
  chamada ao LLM bem-sucedida (min 7,2s, max 25,6s).
- Rodada do Dia 4 (cota parcialmente esgotada): latência bem maior e mais instável,
  com múltiplas tentativas de fallback por documento (4-5 modelos testados em
  sequência antes de um responder, ou de todos falharem).

## O que não funcionou (seção honesta)

1. **Documentos em `.zip`/`.rar` são mais comuns do que imaginávamos.** No Dia 1
   identificamos isso só nos 4 editais da Caixa Econômica Federal. Rodando o pipeline
   em 50 contratações reais no Dia 3, descobrimos que **cerca de 17 de 50** (34%)
   vinham em formato compactado — vários órgãos diferentes, não só a Caixa. O
   `extracao.py` não abre esses arquivos; eles ficam com os 3 campos textuais em
   `null`, motivo registrado. Isso é a limitação estrutural mais impactante do MVP.

2. **1 de 15 documentos do gabarito é PDF escaneado sem camada de texto** (Santa
   Terezinha de Goiás). Exigiria OCR, fora do escopo do MVP.

3. **O tier gratuito do OpenRouter esgota rápido sob uso intenso.** Com cerca de 130+
   chamadas de LLM feitas ao longo dos 2 dias de extração/eval, o sistema começou a
   bater em rate-limit (429) na maioria dos modelos de fallback, sobrando só o último
   da lista — ou nenhum, em alguns casos. Isso é uma limitação real de qualquer
   pipeline dependente de tier gratuito compartilhado, e explica parte da variação de
   acurácia entre rodadas no mesmo dia. Mitigado com uma lista de 5 modelos de
   fallback, mas não eliminado.

4. **Um bug real foi encontrado e corrigido durante o eval do Dia 4:** um dos modelos
   de fallback (mais fraco) devolveu `exigencias_habilitacao` como uma string solta
   em vez do objeto JSON esperado (`{"valor": ..., "trecho_citado": ...}`). Isso
   derrubava a validação com `AttributeError`. Corrigido com uma checagem de tipo
   explícita antes de acessar o campo, tratando como "extração malformada" em vez de
   quebrar o pipeline — consistente com a regra 3.4.

5. **A checagem de citação literal (regra 3.3) começou rigorosa demais** e foi
   ajustada duas vezes no Dia 4: primeiro para tolerar reformatação de links Markdown
   e ligaduras tipográficas do PDF (ex: "eﬁciência" → "eficiência"), depois para
   comparar por frase (limiar de 70% das frases da citação presentes no texto) em vez
   de exigir igualdade exata do trecho inteiro — citações longas (habilitação,
   atestado técnico) raramente batem 100% mesmo quando genuínas, por causa de quebras
   de linha e hifenização do PDF original.

6. **Uma inconsistência de valor não foi resolvida** (edital do bloquete sextavado,
   Itambacuri): a API mostra R$ 0,00, o texto do edital declara R$ 461.300,00, e a
   soma da própria tabela de itens do edital dá R$ 218.400,00 — os três divergem.
   Decisão: marcar como não confiável e documentar a divergência, sem escolher
   arbitrariamente qual dos três números é o correto.

7. **Decisão de score ainda simplificada:** o critério de "localização" usa
   `municipio_uf` (sede administrativa do órgão), não o local físico da obra. Em
   editais do DNIT, isso mostra Brasília/DF mesmo quando a obra em si é em outro
   estado — uma simplificação conhecida, documentada em `DECISOES.md`, não corrigida
   por falta de tempo.

## O que mudaríamos com mais tempo

Ver `DECISOES.md` para a lista completa. Destaques: (a) substituir a métrica de
similaridade textual por comparação semântica; (b) implementar abertura de `.zip` na
extração, já que afeta ~34% dos documentos reais coletados; (c) usar uma chave paga
ou local (Ollama) para eliminar a instabilidade do tier gratuito compartilhado.