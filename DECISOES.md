# DECISOES.md

## As 5 decisões técnicas principais

### 1. LLM só nos 3 campos que a API não fornece
5 dos 8 campos pedidos (objeto, modalidade, valor, data de abertura, município/UF)
vêm prontos e estruturados da API do PNCP — descoberto lendo a especificação OpenAPI
no Dia 1. Decidimos que o LLM só é chamado para os outros 3 (prazo de execução,
atestado técnico, exigências de habilitação), que só existem no texto livre do PDF.
**Alternativa descartada:** re-extrair todos os 8 campos via LLM, por uniformidade de
código. Descartada porque aumentaria custo, latência e superfície de erro/alucinação
em campos que já eram 100% confiáveis via API — contrário à regra 3.3 do desafio.

### 2. Separação física entre extração (com LLM) e validação (sem LLM)
`validacao.py` nunca importa `extracao.py` nem chama qualquer API de LLM — os dois
módulos só se conectam dentro de `pipeline.py`. Decisão tomada antes de escrever
qualquer código, especificamente para tornar estruturalmente impossível que um atalho
de última hora (ex: um `except: return valor_nao_validado`) deixe uma alucinação do
LLM passar direto pra API sem checagem.
**Alternativa descartada:** funções de extração e validação no mesmo arquivo,
chamadas em sequência por uma função orquestradora. Mais simples de escrever, mas um
`try/except` de distância de furar a regra "o LLM não pode ser juiz final de nada".

### 3. Score normalizado só sobre os critérios que puderam ser avaliados
Quando um campo necessário pra um critério do score (ex: valor sigiloso, atestado
técnico ausente) não é confiável, aquele critério some do cálculo — o score final é
`pontos_obtidos / pontos_possiveis_AVALIADOS`, não sobre o total. Mas
`criterios_avaliados`/`criterios_totais` sempre aparecem junto, pra não esconder
quando o score foi calculado sobre poucos critérios.
**Alternativa descartada:** contar critério não avaliado como pontuação neutra
(zero). Rejeitada porque isso trata "não sei" e "não se aplica bem" da mesma forma,
o que é enganoso — decisão amarrada ao exemplo do Anexo A ("como o score se comporta
quando falta um campo relevante?").

### 4. Validação de citação por trechos/frases, não por igualdade exata de string
A regra 3.3 exige que "valor extraído tem que existir literalmente no texto de
origem". Implementamos isso comparando se as frases da citação do LLM aparecem
(normalizadas) no texto original do PDF — com tolerância a diferenças de formatação
comuns (ligaduras tipográficas do PDF, sintaxe de link Markdown que o LLM às vezes
introduz).
**Alternativa descartada:** exigir igualdade exata de string inteira. Testamos essa
versão primeiro; ela rejeitava citações genuínas e corretas só por diferenças
triviais de formatação, produzindo falsos negativos em excesso — mais espinhoso que
útil pro sócio.

### 5. Fallback entre 5 modelos gratuitos fixos, em vez de roteador automático
`extracao.py` tenta uma lista fixa de modelos gratuitos do OpenRouter em ordem, até
um responder com sucesso. Descartamos o roteador `openrouter/free` (que sorteia
modelo a cada chamada) depois de ver, na prática, timeouts em modelos grandes,
respostas vazias em modelos de raciocínio longo, e variação inaceitável de latência.
**Alternativa descartada:** confiar no roteador automático por simplicidade.
Descartada porque comprometia tanto a qualidade (modelo sorteado podia ser fraco
demais) quanto a possibilidade de medir latência/custo de forma consistente,
exigida pelo `RESULTADOS.md`.

## O que mudaríamos se tivéssemos mais tempo

**Abrir arquivos `.zip`/`.rar`.** Descoberto tarde (Dia 3, ao rodar em 50 contratações
reais) que ~34% dos documentos reais vêm compactados, não como PDF direto — bem mais
que os 4 casos isolados da Caixa que identificamos no Dia 1. Isso afeta uma fatia
real e não-trivial do sistema em produção. Não implementamos extração de zip por
tempo, mas é a limitação de maior impacto que ficou de fora do MVP.

---

## Log cronológico de decisões por dia
(mantido como histórico do processo — ver acima para as 5 decisões curadas)

Dia 1) Arquitetura da ingestão: API do PNCP tem 5 dos 8 campos estruturados; os outros 3 exigem baixar o PDF do edital via endpoint /arquivos. Bug corrigido e medido: deduplicação por orgaoEntidade.cnpj descartava ~30% dos registros legítimos; trocado para numeroControlePNCP. Tratamento de dado ausente: quando o Projeto Básico não está anexado, os campos correspondentes viram null explícito com motivo, não erro nem invenção. Tratamento de valor sigiloso: identificado como problema de validação determinística (cruzar número suspeito + texto do objeto), não de extração — resolver depois. Separação extração/validação: módulos física e estruturalmente separados, seguindo uma "linha de montagem" onde cada módulo só importa dos que vêm antes dele — decisão pensada especificamente pra impedir que um atalho de última hora deixe o LLM "vazar" pra validação. Score normalizado sobre critérios avaliados (não sobre o total), com criterios_avaliados/criterios_totais sempre visíveis pra não mascarar quando o score foi calculado sobre poucos dados.

Dia 2) Composição do gabarito: 15 documentos escolhidos por categoria de dificuldade de extração (documento limpo, valor sigiloso, anexo ausente, formatação/plataforma diferente, objeto ambíguo, modalidade diferente) — não pelos mais fáceis de ler, pra não inflar artificialmente a acurácia medida depois pelo eval.py.

Formato do gabarito simplificado: gabarito.json guarda só o valor correto e literal de cada campo (sem a estrutura confiavel/motivo/fonte do schema.py) — essa rastreabilidade é responsabilidade do sistema em produção, não do gabarito, que existe só pra comparação.

Correção de uma suposição errada do Dia 1: a entrada da NOVACAP havia sido registrada com prazo_execucao e exigencia_atestado_capacidade_tecnica nulos, assumindo que "Projeto Básico ausente" implicava ausência desses dados. Lendo o Edital na íntegra, os dois campos estavam lá. Lição: ausência de anexo não implica ausência do dado — o sistema real precisa ler o documento disponível antes de decidir que um campo está indisponível, não inferir isso só pela lista de arquivos anexados.

Catalogadas 6 categorias distintas de "por que um campo é null", encontradas em casos reais do gabarito (não hipotéticas): (1) sigilo permanente, nunca revelado (TERRACAP); (2) valor fictício 0.0/0.01, às vezes inconsistente com o próprio texto (Correios, bloquete sextavado); (3) sigilo temporário, revelado só após a fase de lances (4 editais da Caixa — Lei 13.303/2016, Art. 34); (4) documento/anexo ausente no PNCP (Justiça Federal GO, DNIT); (5) prazo definido pelo próprio licitante na proposta, não fixado pelo órgão (Caixa retrofit); (6) dado existente no documento mas não localizado na leitura manual, por limitação de tempo/processo de anotação (Estado de Goiás, Santa Terezinha). O validacao.py e o score.py vão precisar tratar essas categorias de forma diferenciada, não só como "null genérico".

Inconsistência de valor não resolvida por decisão consciente (caso do bloquete sextavado): API mostra 0.0, texto do edital declara R$ 461.300,00, soma da própria tabela de itens dá R$ 218.400,00 — os três divergem entre si. Decisão: não investigar a causa raiz (custo-benefício ruim pra um MVP de 4 dias), marcar valor_estimado como null e documentar a divergência como está, em vez de escolher arbitrariamente um dos três números.

Pegadinha de localização identificada (DNIT, 2 editais): unidadeOrgao aponta Brasília/DF (sede administrativa), mas a obra física ocorre em outros estados (SC/RS; RN/PB/PE/AL/SE). Decisão em aberto pro score.py: o critério de "localização" deve considerar a sede do órgão ou o local físico da obra (que só existe no texto do objeto)? Ainda não decidido — registrado como ponto a resolver antes de implementar score.py.

Limitações de escopo do MVP registradas explicitamente: (1) pipeline não processa anexos em .zip (4 editais da Caixa vinham assim) — extração manual necessária pro gabarito, mas o extracao.py em produção precisará decidir se abre zips ou ignora; (2) PDFs escaneados sem camada de texto (1 edital, Santa Terezinha) exigem OCR, não extração direta — mais lento e menos confiável; o extracao.py real vai precisar de um caminho de fallback pra esse caso ou aceitar que esses documentos ficam com campos null por padrão.

Exigência de habilitação pode ser geograficamente restritiva: edital de Santa Terezinha de Goiás exige que o licitante já possua posto de combustível instalado no próprio município. Relevante pro score.py — esse tipo de exigência pode ser um desqualificador direto (a Engevia não tem presença física em todo município do DF/GO/MG), diferente de exigências "genéricas" de habilitação que qualquer empresa cumpre.

Organização de branches por tarefa: feat/ingestao-pncp (Dia 1) e feat/gabarito (Dia 2), cada uma com commits granulares ao longo do trabalho — decisão tomada depois de perceber, a meio do Dia 2, que commits tinham ido parar na main por engano; corrigido criando a branch a partir do ponto atual, sem necessidade de reescrever histórico.

**Lacuna conhecida:** o CNPJ do órgão é validado (`cnpj_valido`), mas o resultado
não está anexado a nenhum campo do schema de forma clara desde a simplificação do
Dia 4 (removemos o acoplamento que ele tinha com o campo `objeto`, por
inconsistência). Seria bom adicionar um campo dedicado ou anexar ao motivo de
todos os 8 campos quando o CNPJ do órgão é inválido.
...