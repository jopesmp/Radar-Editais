# AI_LOG.md

Registro de onde usei IA (como par de programação) durante o desenvolvimento, onde ela errou,
como percebi o erro, e o que fiz a respeito. Separo o registro em três partes:
erros da IA me ajudando a construir o sistema (desenvolvimento geral e front-end), e erros
do modelo fraco que roda dentro do pipeline de extração (OpenRouter).

---

## Parte 1 — Erros da IA (assistente de desenvolvimento)

### 1.1 Suposição incorreta sobre "anexo ausente" (Dia 1 → corrigido no Dia 2)
No Dia 1, ao ver que o endpoint `/arquivos` da NOVACAP só listava o Edital (sem o
Projeto Básico anexado separadamente), a IA concluiu que os campos `prazo_execucao`
e `exigencia_atestado_capacidade_tecnica` deveriam ficar `null`, já que o Edital
"remetia" ao Projeto Básico ausente. **Isso estava errado.** No Dia 2, ao ler eu mesmo
o texto completo do Edital para montar o gabarito, ficou claro que esses dois campos
estavam detalhados dentro do próprio Edital (item 11 e Tabela 2), e não dependiam do
Projeto Básico. Como percebi: lendo o documento inteiro, não só a lista de anexos.
O que fiz: corrigi a entrada no `gabarito.json` e documentei a lição em `DECISOES.md`
— "ausência de anexo não implica ausência do dado; o sistema real precisa ler o
documento disponível antes de decidir que um campo está indisponível."

### 1.2 Atribuição errada de conteúdo a um documento (Dia 2)
Durante a leitura do edital da TERRACAP, a IA referenciou de memória uma "Tabela 2
com 540 TR em sistema chiller" como se pertencesse a esse edital — na verdade essa
tabela era da NOVACAP, outro documento. Como percebi: Desconfiei da inconsistência
ao comparar com o texto real extraído pouco depois, e eu corrigi antes de seguir.
O que fiz: não deixei a informação errada entrar no gabarito; reconferi a partir do
texto real de cada documento.

### 1.3 Slug de modelo gratuito desatualizado (Dia 3)
Pedi à IA uma recomendação de modelo gratuito no OpenRouter com bom contexto; ela
buscou na web e sugeriu `deepseek/deepseek-v4-flash:free`. Ao chamar a API de verdade,
veio erro 404: "This model is unavailable for free. The paid version is available now."
Como percebi: rodando a chamada real e lendo o corpo do erro (em vez de assumir que
funcionaria). O que fiz: implementei uma consulta ao vivo em `GET /api/v1/models` para
listar os modelos gratuitos vigentes no momento da execução, em vez de confiar em texto
de documentação/busca que pode ficar desatualizado de um dia para o outro.

---

## Parte 2 — Erros do modelo fraco no pipeline (extração via OpenRouter)

Por regra do desafio (3.1), o pipeline só pode usar modelos gratuitos/locais — não a
IA que usei como assistente de desenvolvimento. Os erros abaixo são do modelo que roda
dentro do `extracao.py`, e não da IA de apoio citada na Parte 1.

### 2.1 Roteador automático `openrouter/free` instável
Usar o roteador automático (que sorteia entre modelos gratuitos a cada chamada) causou
três tipos de falha: (a) modelos de raciocínio longo (ex: Cohere North Mini) consumiam
todo o limite de tokens "pensando" e devolviam `content: null`; (b) modelos grandes
(ex: Nemotron 550B) estouravam timeout de 90-120s; (c) erro 429 por rate-limit
compartilhado entre todos os usuários do tier gratuito de um provedor específico.
Como percebi: inspecionando a resposta bruta da API (campo `model`, `reasoning`,
`finish_reason`) em vez de só capturar a exceção genericamente.
O que fiz: abandonei o roteador automático, fixei uma lista de fallback com 5 modelos
testados manualmente, com try/except que pula para o próximo modelo em qualquer falha.

### 2.2 Campo presente no texto, mas não encontrado pelo modelo
Em pelo menos 3 dos 15 documentos do gabarito, o modelo retornou `null` para um campo
que estava claramente presente no texto (confirmado via busca manual de posição da
seção no texto extraído). Não foi truncamento — a seção estava dentro do limite de
caracteres enviado. É limitação real de capacidade do modelo gratuito escolhido.
Como percebi: rodando `eval.py` contra o gabarito e depois um script de diagnóstico
que localiza a posição exata de cada seção no texto bruto.
O que fiz: aceitei como limitação documentada (ver `RESULTADOS.md`); não tentei
mascarar o número, reportei a acurácia de presença tal como medida.

### 2.3 Citação real, porém reformatada (falso negativo na validação)
O modelo citou um trecho genuíno e correto do edital da NOVACAP, mas reescreveu uma
URL do texto original em sintaxe de link Markdown (`[texto](url)`) — isso quebrou a
checagem determinística de "a citação existe literalmente no texto de origem" (regra
3.3), mesmo o conteúdo estando substancialmente certo.
Como percebi: script de diagnóstico comparando o trecho citado lado a lado com o
texto de origem, `trecho in texto`.
O que fiz: mantive a validação rigorosa como está — prefiro um falso negativo (campo
correto marcado como não confiável) a um falso positivo (alucinação aceita como
verdadeira). Documentei como trade-off consciente, não como bug a corrigir.

---

## Parte 3 — Front-end (dia extra)

O front (`frontend/index.html`) foi construído com apoio de IA como par de programação,
em camadas pequenas e testadas uma a uma antes de avançar (fetch simples sem estilo →
filtro → detalhamento do score → alerta de campos não confiáveis → CSS → tratamento
de erro). Dois pontos valem registro:

### 3.1 Estratégia de teste de CORS não funcionou de primeira
A primeira sugestão da IA para verificar se o CORS estava liberado foi abrir um HTML
de teste direto do disco (`file:///...`) e rodar um `fetch` pelo console do navegador.
Isso gerou ruído que não era o erro de CORS de verdade: o Chrome bloqueou o paste no
console por padrão (proteção contra self-XSS) e ainda apareceram mensagens confusas de
"Unsafe attempt to load URL... 'file:' URLs are treated as unique security origins",
que pareciam erro mas eram sobre a própria natureza da origem `file://`, não sobre CORS.
Como percebi: depois de duas tentativas sem sucesso pelo console, ficou claro que o
problema era a abordagem de teste, não a configuração de CORS em si — o `CORSMiddleware`
já tinha sido corrigido e o erro relatado nunca mencionava "CORS policy" de fato.
O que fiz (com a IA): abandonamos o teste via console/`file://` e passamos a servir a
pasta por HTTP local (`python -m http.server`) com o teste embutido em um `<script>` no
próprio HTML, escrevendo o resultado na tela em vez de depender do console. Resolveu de
primeira e passou a ser o método usado no resto do desenvolvimento do front.

### 3.2 Falha silenciosa não prevista na primeira versão
A primeira versão do `carregarOportunidades()`, sugerida pela IA, não tinha tratamento
de erro no `fetch`. Ao testar manualmente o cenário "API fora do ar" (proposto pela IA
como teste de estresse, não algo que eu pedi), a página ficava presa em "Carregando..."
para sempre, sem nenhum aviso — uma falha silenciosa, o oposto do que a regra 3.4 do
desafio pede para o pipeline como um todo.
Como percebi: reproduzindo o cenário manualmente (derrubando a API e recarregando a
página) a pedido da própria IA, que sugeriu o teste antes de considerar o front pronto.
O que fiz: adicionamos `try/catch` em volta do `fetch`, exibindo uma mensagem explícita
de erro de conexão na tela, e também tratamos o caso de lista vazia (`oportunidades: []`)
separadamente, para não confundir "sem resultados para o filtro" com "erro de conexão".
