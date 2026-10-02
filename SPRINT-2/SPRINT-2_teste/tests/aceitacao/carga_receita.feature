# language: pt
@integracao @rnf06 @rnf09 @parte2
Funcionalidade: Carga da receita observada
  Para ter dados reais confiáveis no banco
  Como equipe de dados da Sprint 2
  Quero carregar o CSV do portal sem duplicar, sem somar contas sobrepostas e com linhagem

  Contexto:
    Dado um banco de teste recém-criado

  Cenário: Carga da amostra publica componentes e totais separados
    Quando carrego a amostra de 10 linhas reais
    Então o banco tem 8 valores de componentes e 2 totais de conferência
    E cada valor aponta para a linha de origem no CSV

  Cenário: Reimportar o mesmo arquivo não duplica a receita
    Dado que a amostra de 10 linhas reais já foi carregada
    Quando carrego a amostra de 10 linhas reais
    Então a carga informa que o arquivo já existia
    E o banco continua com 1 snapshot e 8 valores de componentes

  Cenário: A arrecadação por tributo soma somente os componentes
    Quando carrego a amostra de 10 linhas reais
    Então a arrecadação de "IPTU" em jan/2025 é "2885620.64"
    E a arrecadação de "ISSQN" em jan/2025 é "21802997.01"
    E nenhuma conta-pai diverge da soma dos seus componentes

  Cenário: Valor com fração de centavo interrompe a publicação
    Quando carrego um arquivo com o valor "1.005" na conta "11125001"
    Então nada é publicado além do staging
    E a validação registra um erro de "CONTRATO_ENTRADA"
    E o arquivo fica registrado como "REJEITADO"

  Cenário: Reimportar um arquivo reprovado repete o diagnóstico, sem gravar de novo
    Dado que um arquivo com o valor "1.005" na conta "11125001" já foi carregado
    Quando carrego o mesmo arquivo de novo
    Então a carga informa que o arquivo já existia
    E o resumo é igual ao da primeira carga
    E o arquivo continua registrado uma única vez

  Cenário: Arquivo sem uma coluna do layout da fonte é reprovado sem interromper a carga
    Quando carrego um arquivo sem a coluna "valor_orcado"
    Então nada é publicado além do staging
    E a validação registra um erro de "CONTRATO_ENTRADA"
    E o arquivo fica registrado como "REJEITADO"

  Cenário: O orçamento anual não é multiplicado pelos meses
    Quando carrego a amostra de 10 linhas reais
    Então o orçamento da conta "1112500" é "112219000.00" gravado uma única vez
