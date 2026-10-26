# language: pt
@integracao @parte2
Funcionalidade: Créditos, pagamentos e negociação
  Para que a dívida seja acompanhada sem inconsistência
  Como servidor da Sefin
  Quero saldos derivados dos movimentos e uma única negociação ativa por crédito

  Contexto:
    Dado um banco de teste recém-criado com a semente sintética

  @rf17
  Cenário: Saldo é derivado de principal, acréscimos, cancelamentos e pagamentos
    Então o saldo do crédito 1 é "0.00"
    E o saldo do crédito 4 é "540.00"
    E nenhum crédito tem saldo negativo

  @rf18 @rnf10
  Cenário: Segunda negociação ativa para o mesmo crédito é rejeitada
    Dado que o crédito 3 já tem uma negociação ativa
    Quando uma nova negociação ativa é aberta para o crédito 3
    Então o banco rejeita a operação com o erro 1062
    E o crédito 3 continua com uma única negociação

  @rf17
  Cenário: Pagamento repartido não excede o valor pago
    Então nenhum pagamento tem apropriações acima do seu valor
