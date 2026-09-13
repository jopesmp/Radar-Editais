Dia 1)
Arquitetura da ingestão: API do PNCP tem 5 dos 8 campos estruturados; os outros 3 exigem baixar o PDF do edital via endpoint /arquivos.
Bug corrigido e medido: deduplicação por orgaoEntidade.cnpj descartava ~30% dos registros legítimos; trocado para numeroControlePNCP.
Tratamento de dado ausente: quando o Projeto Básico não está anexado, os campos correspondentes viram null explícito com motivo, não erro nem invenção.
Tratamento de valor sigiloso: identificado como problema de validação determinística (cruzar número suspeito + texto do objeto), não de extração — resolver depois.
Separação extração/validação: módulos física e estruturalmente separados, seguindo uma "linha de montagem" onde cada módulo só importa dos que vêm antes dele — decisão pensada especificamente pra impedir que um atalho de última hora deixe o LLM "vazar" pra validação.
Score normalizado sobre critérios avaliados (não sobre o total), com criterios_avaliados/criterios_totais sempre visíveis pra não mascarar quando o score foi calculado sobre poucos dados.