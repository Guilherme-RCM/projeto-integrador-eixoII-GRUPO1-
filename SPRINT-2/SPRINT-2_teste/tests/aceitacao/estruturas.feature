# language: pt
@parte1
Funcionalidade: Estruturas de dados da fila de cobrança
  Para priorizar ações e localizar registros com eficiência
  Como sistema de inteligência tributária
  Quero heap, tabela hash e grafo com o comportamento descrito na literatura

  Cenário: A ação mais urgente sai primeiro e o pagamento retira a ação da fila
    Dado a fila com as ações
      | acao   | classe | prazo      | score |
      | acao-1 | 2      | 2026-10-15 | 0.40  |
      | acao-2 | 1      | 2026-10-05 | 0.10  |
      | acao-3 | 1      | 2026-10-05 | 0.90  |
    Quando o crédito da "acao-3" é pago
    Então a próxima ação é "acao-2"
    E depois a próxima ação é "acao-1"

  Cenário: Colisões são resolvidas por encadeamento (Gersting, Exemplo 50)
    Dado uma tabela hash com 10 posições
    Quando insiro as chaves 7, 23, 59, 158 e 48
    Então as chaves 158 e 48 ficam na mesma posição 8
    E a chave 48 é encontrada
    E a chave 68 não é encontrada

  Cenário: Os componentes de um tributo são recuperados pela conta-pai
    Dado o grafo contábil da amostra real
    Quando percorro a partir da conta "1112500"
    Então alcanço exatamente 4 componentes
    E a soma dos componentes é igual ao valor da conta-pai
