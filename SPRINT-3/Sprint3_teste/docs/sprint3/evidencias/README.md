# Evidências da Sprint 3

| Arquivo | O que comprova |
|---|---|
| [etl.log](etl.log) | execução real completa de referência, de 21/10/2026 (`20261021T065740-9b9054`, código `ea64aa6`): coleta das sete fontes (com as requisições, o robots.txt de cada host e a recusa do NUCLEOGOV), cada validação com a evidência, a carga no MySQL e a geração da EDA; todas as linhas com o identificador da execução |
| [etl_26-10-2026.log](etl_26-10-2026.log) | execução sem rede de 26/10/2026 (`20261026T155511-c3ba7c`, código `8dee5ba`), com o código final da entrega: o mesmo bruto de 21/10 reprocessado, 33 de 33 validações impeditivas, a carga no MySQL e a geração da [EDA](../EDA.md) |
| [qualidade.md](qualidade.md) | quality gates G1–G14 de 21/10/2026, rodados logo depois da execução de referência, sobre o código de então; o relatório atual fica em [docs/qualidade.md](../../qualidade.md) |
| [manifesto_resumo.md](manifesto_resumo.md) | os arquivos do bruto da execução de referência, com tamanho e SHA-256 (o bruto em si fica fora do Git) |

A coleta registrada é a de 21/10/2026, e a execução de 26/10/2026 reprocessou o mesmo bruto com o código final, porque as mudanças de 26/10 (a API do portal NUCLEOGOV como alternativa, a mensagem de erro sem caminho local e as referências conferidas) não exigiam coletar de novo, e o manual de coleta da coordenação pede que um dado já baixado seja guardado e reaproveitado. Os arquivos de `data/` não são versionados, porque o próprio pipeline os reconstrói e porque o bruto completo passa de 40 MB. A ligação entre estas evidências e o banco é o identificador da execução, que aparece em todas as linhas do log, no registro `execucao_pipeline` e no relatório `data/pronto/qualidade_dados.json`.
