# RESULTADOS.md

## Resumo por dia

**Dia 1 — Ingestão e exploração.** Mapeada a API do PNCP (2 especificações OpenAPI
distintas). Descoberto que 5 dos 8 campos pedidos vêm prontos da API; os outros 3
exigem ler o PDF do edital. Corrigido um bug real no `pncp_client.py` herdado: a
deduplicação usava `orgaoEntidade.cnpj` como chave, descartando ~30% dos registros
legítimos sempre que o mesmo órgão publicava mais de uma contratação na mesma janela
(medido: 50 registros brutos → 35 após dedup incorreta → 50 após a correção, trocando
a chave para `numeroControlePNCP`).

**Dia 2 — Gabarito.** Anotados manualmente 15 documentos, escolhidos por categoria de
dificuldade de extração (não pelos mais fáceis), cobrindo: documento limpo, valor
sigiloso (3 variações diferentes — fictício, temporário e permanente), anexo ausente,
plataforma de publicação diferente, objeto ambíguo, e modalidade fora do pregão.

**Dia 3 — Extração e validação.** Implementado `extracao.py` (LLM só nos 3 campos
textuais, via OpenRouter, modelo gratuito) e `validacao.py` (determinística, sem IA:
dígito verificador de CNPJ, UF válida, coerência de data, sinal de valor sigiloso,
citação literal no texto de origem).

## Acurácia por campo (contra o gabarito de 15 documentos)

Medida com `eval.py`, em duas camadas — presença (o campo foi corretamente identificado
como existente ou ausente) e similaridade textual (aproximação, ver ressalva abaixo).

| Campo | Acurácia de presença (bruta, 15 docs) | Acurácia de presença (10 docs processáveis) |
|---|---|---|
| prazo_execucao | 73% (11/15) | ~90% |
| exigencia_atestado_capacidade_tecnica | 60% (9/15) | ~90% |
| exigencias_habilitacao | 60% (9/15) | ~90% |

A coluna "bruta" inclui 5 documentos que o pipeline não conseguiu processar por
limitação estrutural conhecida (ver seção abaixo), não por erro do modelo. Descontando
esses 5, a acurácia de presença nos 10 documentos restantes é de aproximadamente 90%
(27 de 30 verificações de campo corretas).

**Similaridade de texto** (SequenceMatcher, só nos casos em que ambos têm valor):
prazo_execucao 0.19 (n=7), atestado técnico 0.32 (n=2), habilitação 0.23 (n=9).
Esses números são consistentemente baixos mesmo quando o conteúdo está correto, porque
a métrica penaliza qualquer paráfrase — o modelo frequentemente resume/reescreve em vez
de copiar literalmente. É uma métrica fraca; serve como sinal aproximado, não como
medida de qualidade real. Não tivemos tempo hábil nos 4 dias para substituir por uma
comparação semântica mais adequada.

## Custo médio por documento

**R$ 0,00.** Todos os modelos usados no pipeline são de tier gratuito do OpenRouter,
por exigência da regra 3.1 do desafio.

## Latência média por documento

Medida na execução real contra os 15 documentos do gabarito:
- **~12,0 segundos** por documento, considerando só os 10 documentos em que o LLM foi
  de fato chamado (min: 7,2s, max: 25,6s — variação grande porque o modelo que responde
  muda dependendo de disponibilidade/fallback).
- **~8,3 segundos** em média incluindo os 5 documentos que falharam rápido por
  limitação estrutural (não chegaram a chamar o LLM).

## O que não funcionou (seção honesta)

1. **4 de 15 documentos vêm em `.zip` (Caixa Econômica Federal).** O `extracao.py`
   só lê PDF direto — não abre arquivos compactados. Decisão consciente de MVP: esses
   4 documentos ficam com os 3 campos textuais em `null`, motivo registrado.
2. **1 de 15 documentos é um PDF escaneado sem camada de texto** (Santa Terezinha de
   Goiás). Extração de texto direto não funciona; exigiria OCR, fora do escopo do MVP.
3. **O roteador automático `openrouter/free` provou-se instável demais** para uso em
   produção — timeouts em modelos grandes, erro 429 por fila compartilhada, e
   respostas vazias por consumo de tokens em "raciocínio" interno. Resolvido fixando
   uma lista de fallback de 5 modelos testados manualmente.
4. **A checagem de citação literal (regra 3.3) é rigorosa o suficiente para gerar
   falsos negativos** quando o modelo reformata levemente uma citação real (ex:
   convertendo uma URL solta em link Markdown). Isso reduz a métrica de "confiável"
   mesmo quando o conteúdo extraído está correto. Optamos por manter o rigor —
   preferimos rejeitar informação correta a aceitar uma alucinação sem aviso — mas é
   uma limitação real da métrica de acurácia reportada acima.
5. **Uma inconsistência de valor não foi resolvida** (edital do bloquete sextavado,
   Itambacuri): a API mostra R$ 0,00, o texto do edital declara R$ 461.300,00, e a
   soma da própria tabela de itens do edital dá R$ 218.400,00 — os três divergem entre
   si. Decisão: marcar como não confiável e documentar a divergência, sem escolher
   arbitrariamente qual dos três números é o correto.
6. **Uma decisão de score ainda está em aberto:** em 2 editais do DNIT, o órgão está
   sediado em Brasília/DF, mas a obra física ocorre em outros estados (SC/RS;
   RN/PB/PE/AL/SE). Ainda não decidimos se o critério de "localização" do score.py
   deve considerar a sede do órgão ou o local físico da obra — a ser resolvido ao
   implementar `score.py`.

## O que mudaríamos com mais tempo

Ver `DECISOES.md` para a lista completa — mas o item mais relevante aqui é substituir
a métrica de similaridade textual (SequenceMatcher) por uma comparação semântica
(ex: embeddings), já que a atual subestima a qualidade real da extração ao penalizar
paráfrases corretas.