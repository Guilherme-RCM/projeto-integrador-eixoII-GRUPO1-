# language: pt
@integracao @rf03 @rnf03
Funcionalidade: Registro de auditoria coerente
  Para rastrear quem fez cada ação
  Como auditor
  Quero que todo registro identifique corretamente o tipo de ator

  Contexto:
    Dado um banco de teste recém-criado com a semente sintética

  Cenário: Ação de usuário sem identificação do usuário é rejeitada
    Quando registro uma ação do tipo "USUARIO" sem informar o usuário
    Então o banco rejeita a operação com o erro 3819

  Cenário: Tarefa automática é registrada com o identificador do sistema
    Quando registro uma ação do tipo "TAREFA" feita por "etl.carregar_receita"
    Então o registro é aceito
