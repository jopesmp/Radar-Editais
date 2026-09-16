# DECISOES.md

## As 5 decisões técnicas principais

### 1. LLM só nos 3 campos que a API não fornece
5 dos 8 campos pedidos (objeto, modalidade, valor, data de abertura, município/UF)
vêm prontos e estruturados da API do PNCP — descobri isso lendo a especificação
OpenAPI no Dia 1. Decidi que o LLM só é chamado para os outros 3 (prazo de execução,
atestado técnico, exigências de habilitação), que só existem no texto livre do PDF.
**Alternativa descartada:** re-extrair todos os 8 campos via LLM, por uniformidade de
código. Descartei essa opção porque aumentaria custo, latência e superfície de erro/
alucinação em campos que já eram 100% confiáveis via API — contrário à regra 3.3 do
desafio.

### 2. Separação física entre extração (com LLM) e validação (sem LLM)
`validacao.py` nunca importa `extracao.py` nem chama qualquer API de LLM — os dois
módulos só se conectam dentro de `pipeline.py`. Tomei essa decisão antes de escrever
qualquer código, especificamente para tornar estruturalmente impossível que um atalho
de última hora (ex: um `except: return valor_nao_validado`) deixasse uma alucinação
do LLM passar direto para a API sem checagem.
**Alternativa descartada:** funções de extração e validação no mesmo arquivo,
chamadas em sequência por uma função orquestradora. Mais simples de escrever, mas um
`try/except` de distância de furar a regra "o LLM não pode ser juiz final de nada".

### 3. Score normalizado só sobre os critérios que puderam ser avaliados
Quando um campo necessário para um critério do score (ex: valor sigiloso, atestado
técnico ausente) não é confiável, aquele critério some do cálculo — o score final é
`pontos_obtidos / pontos_possiveis_AVALIADOS`, não sobre o total. Mas
`criterios_avaliados`/`criterios_totais` sempre aparecem junto, para não esconder
quando o score foi calculado sobre poucos critérios.
**Alternativa descartada:** contar critério não avaliado como pontuação neutra
(zero). Rejeitei essa opção porque trata "não sei" e "não se aplica" da mesma forma,
o que é enganoso — decisão amarrada ao exemplo do Anexo A ("como o score se comporta
quando falta um campo relevante?").

### 4. Validação de citação por trechos/frases, não por igualdade exata de string
A regra 3.3 exige que "valor extraído tem que existir literalmente no texto de
origem". Implementei isso comparando se as frases da citação do LLM aparecem
(normalizadas) no texto original do PDF — com tolerância a diferenças de formatação
comuns (ligaduras tipográficas do PDF, sintaxe de link Markdown que o LLM às vezes
introduz).
**Alternativa descartada:** exigir igualdade exata de string inteira. Testei essa
versão primeiro; ela rejeitava citações genuínas e corretas só por diferenças
triviais de formatação, produzindo falsos negativos em excesso — mais atrapalho que
ajuda para o sócio.

### 5. Fallback entre 5 modelos gratuitos fixos, em vez de roteador automático
`extracao.py` tenta uma lista fixa de modelos gratuitos do OpenRouter em ordem, até
um responder com sucesso. Descartei o roteador `openrouter/free` (que sorteia modelo
a cada chamada) depois de ver, na prática, timeouts em modelos grandes, respostas
vazias em modelos de raciocínio longo, e variação inaceitável de latência.
**Alternativa descartada:** confiar no roteador automático por simplicidade.
Descartei essa opção porque comprometia tanto a qualidade (o modelo sorteado podia
ser fraco demais) quanto a possibilidade de medir latência/custo de forma
consistente, exigida pelo `RESULTADOS.md`.

## O que eu mudaria se tivesse mais tempo

**Abrir arquivos `.zip`/`.rar`.** Descobri tarde (Dia 3, ao rodar em 50 contratações
reais) que ~34% dos documentos reais vêm compactados, não como PDF direto — bem mais
que os 4 casos isolados da Caixa que eu tinha identificado no Dia 1. Isso afeta uma
fatia real e não-trivial do sistema em produção. Não implementei extração de zip por
falta de tempo, mas é a limitação de maior impacto que ficou de fora do MVP.

**Rastreabilidade do resultado da validação de CNPJ.** O CNPJ do órgão é validado
(`cnpj_valido`) em `validacao.py`, mas hoje o resultado não está anexado a nenhum
campo do schema de forma clara — removi o acoplamento que ele tinha originalmente
com o campo `objeto` por inconsistência (não fazia sentido o CNPJ "contaminar" a
confiabilidade de um campo que não depende dele), e não cheguei a colocá-lo em um
lugar melhor. Resultado: hoje, se o CNPJ do órgão for inválido, essa informação é
computada mas fica efetivamente invisível para o sócio. Se tivesse mais tempo,
adicionaria um campo dedicado no schema (ex: `orgao_cnpj_valido`) em vez de tentar
reacoplar a um campo de negócio que não tem relação direta.

## Como o front-end (dia extra) se encaixa

O front (`frontend/index.html`) não altera nenhuma das 5 decisões acima — ele só
consome a API já existente. As decisões técnicas específicas do front (menores, mas
documentadas para coerência do processo):

- **Filtro por score mínimo processado no cliente, não em nova chamada à API.**
  Dataset pequeno o suficiente para caber inteiro na memória do navegador, resposta
  ao filtro instantânea, e menos pontos de falha de rede durante a defesa ao vivo.
- **Isolamento em branch (`feature/frontend`), não fork.** Mantém histórico de
  commits único no mesmo repositório (relevante para a regra 3.6), com uma tag
  (`v1-api-estavel`) marcando o ponto de resgate antes de começar — permite abandonar
  o front sem impacto na `main` caso não ficasse pronto a tempo.

## Log cronológico de decisões por dia
(mantido como histórico do meu processo — ver acima para as 5 decisões curadas)

**Dia 1)** Arquitetura da ingestão: a API do PNCP tem 5 dos 8 campos estruturados; os
outros 3 exigem baixar o PDF do edital via endpoint `/arquivos`. Corrigi e medi um
bug herdado: a deduplicação por `orgaoEntidade.cnpj` descartava ~30% dos registros
legítimos; troquei para `numeroControlePNCP`. Tratamento de dado ausente: quando o
Projeto Básico não está anexado, os campos correspondentes viram `null` explícito com
motivo, não erro nem invenção. Tratamento de valor sigiloso: identifiquei como
problema de validação determinística (cruzar número suspeito + texto do objeto), não
de extração — resolveria depois. Separação extração/validação: módulos física e
estruturalmente separados, seguindo uma "linha de montagem" onde cada módulo só
importa dos que vêm antes dele — decisão pensada especificamente para impedir que um
atalho de última hora deixasse o LLM "vazar" para a validação. Score normalizado
sobre os critérios avaliados (não sobre o total), com `criterios_avaliados`/
`criterios_totais` sempre visíveis para não mascarar quando o score foi calculado
sobre poucos dados.

**Dia 2)** Composição do gabarito: escolhi os 15 documentos por categoria de
dificuldade de extração (documento limpo, valor sigiloso, anexo ausente, formatação/
plataforma diferente, objeto ambíguo, modalidade diferente) — não pelos mais fáceis
de ler, para não inflar artificialmente a acurácia medida depois pelo `eval.py`.

Formato do gabarito simplificado: `gabarito.json` guarda só o valor correto e literal
de cada campo (sem a estrutura confiavel/motivo/fonte do `schema.py`) — essa
rastreabilidade é responsabilidade do sistema em produção, não do gabarito, que
existe só para comparação.

Correção de uma suposição errada do Dia 1: eu tinha registrado a entrada da NOVACAP
com `prazo_execucao` e `exigencia_atestado_capacidade_tecnica` nulos, assumindo que
"Projeto Básico ausente" implicava ausência desses dados. Lendo o Edital na íntegra,
os dois campos estavam lá. Lição: ausência de anexo não implica ausência do dado — o
sistema real precisa ler o documento disponível antes de decidir que um campo está
indisponível, não inferir isso só pela lista de arquivos anexados.

Cataloguei 6 categorias distintas de "por que um campo é null", encontradas em casos
reais do gabarito (não hipotéticas): (1) sigilo permanente, nunca revelado
(TERRACAP); (2) valor fictício 0.0/0.01, às vezes inconsistente com o próprio texto
(Correios, bloquete sextavado); (3) sigilo temporário, revelado só após a fase de
lances (4 editais da Caixa — Lei 13.303/2016, Art. 34); (4) documento/anexo ausente
no PNCP (Justiça Federal GO, DNIT); (5) prazo definido pelo próprio licitante na
proposta, não fixado pelo órgão (Caixa retrofit); (6) dado existente no documento mas
não localizado na minha leitura manual, por limitação de tempo/processo de anotação
(Estado de Goiás, Santa Terezinha). O `validacao.py` e o `score.py` vão precisar
tratar essas categorias de forma diferenciada, não só como "null genérico".

Inconsistência de valor não resolvida, por decisão consciente (caso do bloquete
sextavado): a API mostra 0.0, o texto do edital declara R$ 461.300,00, a soma da
própria tabela de itens dá R$ 218.400,00 — os três divergem entre si. Decisão: não
investigar a causa raiz (custo-benefício ruim para um MVP de 4 dias), marcar
`valor_estimado` como `null` e documentar a divergência como está, em vez de escolher
arbitrariamente um dos três números.

Pegadinha de localização identificada (DNIT, 2 editais): `unidadeOrgao` aponta
Brasília/DF (sede administrativa), mas a obra física ocorre em outros estados (SC/RS;
RN/PB/PE/AL/SE). **Decisão: o critério de "localização" do `score.py` considera a
sede do órgão (`unidadeOrgao`), não o local físico da obra.** Optei pela sede por
simplificação: é o único dado estruturado e confiável vindo direto da API em todos os
casos, enquanto o local físico da obra só existe (quando existe) como texto livre
dentro do objeto, exigindo extração adicional sujeita às mesmas limitações do modelo
fraco. Trade-off consciente: nos casos tipo DNIT, o critério de localização pode
pontuar "dentro da área de atuação" mesmo quando a obra real é fora do DF/GO/MG —
limitação documentada, não escondida.

**Dia 3)** Limitações de escopo do MVP registradas explicitamente: (1) o pipeline
não processa anexos em `.zip` (4 editais da Caixa vinham assim) — fiz a extração
manual para o gabarito, mas o `extracao.py` em produção vai precisar decidir se abre
zips ou ignora, ficando de fora do MVP por ora (ver "O que eu mudaria se tivesse mais
tempo"); (2) **PDFs escaneados sem camada de texto (1 edital, Santa Terezinha):
decidi não implementar OCR para esse tipo de documento, para economizar recursos**
(tempo de processamento e, potencialmente, custo, já que OCR de qualidade
frequentemente depende de mais uma chamada de API ou de processamento local mais
pesado do que vale a pena para um caso isolado no dataset). Esses documentos ficam
com os campos correspondentes `null`, com motivo explícito ("documento sem camada de
texto extraível, OCR fora do escopo"), em vez de tentar uma extração que eu não
validei como confiável.

Exigência de habilitação pode ser geograficamente restritiva: o edital de Santa
Terezinha de Goiás exige que o licitante já possua posto de combustível instalado no
próprio município. Relevante para o `score.py` — esse tipo de exigência pode ser um
desqualificador direto (a Engevia não tem presença física em todo município do
DF/GO/MG), diferente de exigências "genéricas" de habilitação que qualquer empresa
cumpre.

Organização de branches por tarefa: `feat/ingestao-pncp` (Dia 1) e `feat/gabarito`
(Dia 2), cada uma com commits granulares ao longo do trabalho — decisão tomada depois
de perceber, no meio do Dia 2, que alguns commits tinham ido parar na `main` por
engano; corrigi criando a branch a partir do ponto atual, sem necessidade de
reescrever histórico.

**Dia 4)** Validação de CNPJ (`cnpj_valido`) implementada em `validacao.py`, mas
resultado hoje não anexado a nenhum campo do schema de forma clara — removi o
acoplamento que tinha com o campo `objeto`, por inconsistência. Ver seção "O que eu
mudaria se tivesse mais tempo".

**Dia extra)** Front-end construído em camadas pequenas e testadas isoladamente
(fetch simples → filtro → detalhamento do score → alerta de campos não confiáveis →
organização visual → tratamento de erro de conexão/lista vazia), em branch separada
(`feature/frontend`) com merge para `main` só depois de confirmado funcionando. Ver
seção "Como o front-end se encaixa" para as decisões técnicas específicas.
