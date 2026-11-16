# Revisão técnica do E3 e do E4, com testes

## Introdução

Esta revisão examinou o notebook e o pacote de modelos (E3) e o painel (E4) em 09/11/2026, dois dias antes da entrega. O objetivo foi verificar se os controles que sustentam a reprodutibilidade e a leitura do lote resistem a falhas reais, e não apenas ao caminho feliz. O ponto de partida foi a revisão técnica externa da mesma data, cujas afirmações foram conferidas uma a uma no repositório antes de qualquer correção.

O método foi o mesmo para cada defeito, em três passos:

1. escrever primeiro o teste que reproduz a falha e vê-lo falhar;
2. corrigir o código;
3. rodar de novo a suíte inteira e o verificador da sprint.

A ordem importa. Um teste que nunca falhou não prova que detecta o defeito, e uma correção sem teste pode voltar sem aviso.

A tese desta revisão é que os dois defeitos de integridade encontrados eram reais, mas localizados. Ambos foram corrigidos sem alterar modelo, dado, protocolo ou métrica, como comprovam os seis SHA-256 do pacote, iguais antes e depois.

## Desenvolvimento

### 1. Linha de base

A linha de base foi medida antes de qualquer mudança, porque só ela permite afirmar o que não mudou. No commit `25bd525`, o verificador da Sprint 4 aprovou os dez controles:

- 882 testes sem MySQL e cobertura de 94,6%;
- 157 testes da Sprint 4;
- os 11 contratos de dependência e nenhum erro de tipo;
- complexidade máxima de 10 por função, no limite permitido.

Os seis SHA-256 do pacote `models/sprint4/v1` e o hash do manifesto do lote ativo foram guardados para a comparação final.

### 2. R06: o verificador aprovava um modelo adulterado

O controle de reprodutibilidade comparava apenas os valores escritos nos dois arquivos `checksums.sha256`, e por isso não percebia um arquivo alterado com o checksum mantido. O controle deveria provar que o pacote versionado e o pacote refeito pelo notebook contêm os mesmos modelos. Mas, se alguém acrescentasse bytes a `inadimplencia.joblib` sem mexer no checksum, os dois arquivos de checksums continuariam iguais, e o controle continuaria aprovando.

O teste novo fez exatamente isso numa cópia do pacote, e o controle antigo devolveu `aprovado`.

A correção fez cada pacote provar a própria integridade antes da comparação:

- **Integridade:** a função `_integridade` recalcula o SHA-256 de cada arquivo listado, pela mesma `artefatos.conferir` que o carregamento dos modelos já usava.
- **Entradas obrigatórias:** a função exige os dois modelos na lista e transforma checksums malformado em erro claro.
- **Comparação:** só depois os dois modelos são comparados entre os pacotes.

Os metadados não precisam ser iguais entre rodadas, porque registram a execução e o código de cada uma.

Nove testes cobrem os casos:

- pacote íntegro;
- modelo alterado no pacote versionado e no do notebook;
- modelo ausente;
- modelo fora do checksums;
- hash errado de outra entrada;
- checksums malformado;
- modelos diferentes com checksums coerentes;
- ausência da rodada do notebook, que deixa a liberação pendente.

### 3. R03: duas publicações durante uma leitura quebravam o painel

A leitura do lote resolvia o ponteiro uma vez e lia os arquivos depois. Por isso, duas publicações nesse intervalo podavam a pasta que o leitor tinha resolvido. A publicação mantém a versão ativa e a anterior. Se B e C fossem publicados enquanto o painel lia A, a poda removia A no meio da leitura, e um `FileNotFoundError` cru escapava ao tratamento de erro e chegava à interface.

Os testes novos provocam a corrida de forma determinística, com funções substituídas e sem esperas nem threads:

- duas publicações logo depois da resolução;
- a poda entre a conferência dos hashes e a abertura das tabelas;
- o ponteiro mudando em toda tentativa;
- a corrupção com ponteiro estável;
- a falha de leitura com ponteiro estável.

Os dois primeiros reproduziram o erro original.

A correção separou a carga de uma versão da coordenação das tentativas:

- **Coordenador:** a função pública `carregar_lote` lê o ponteiro antes de cada tentativa e, se a carga falhar, verifica se ele mudou. Se mudou, recomeça a carga inteira, até três vezes.
- **Ponteiro estável:** nesse caso, a recusa original é mantida, e uma falha de leitura vira `ErroLote` com a causa preservada.
- **Assinatura:** a função `assinatura_lote`, que os painéis usam para invalidar o cache, deixou de lançar erro quando o ponteiro é trocado entre a verificação de existência e o hash.

As tabelas devolvidas vêm sempre de uma única versão, o que o teste confere registrando a pasta de cada leitura.

### 4. E3: notebook, pacote e reprodução

O notebook e o pacote não precisaram de correção de código, e a revisão confirmou isso por medida:

- **Notebook:** continua com as 16 células executadas, sem erro e sem caminho local nas saídas.
- **Pacote:** os seis SHA-256 de `models/sprint4/v1` ficaram idênticos aos da linha de base.
- **Reprodução:** o controle de reprodutibilidade, agora conferindo os bytes reais, aprova a igualdade entre o pacote versionado e o refeito pelo notebook.

A única mudança no notebook foi de texto. Numa célula de texto, "taxa anual constante de 0,12" passou a "probabilidade anual de recuperação de 12%", convertida numa taxa diária constante. A correção foi feita também no gerador do notebook e no gerador do relatório final, para que uma nova geração não traga a imprecisão de volta.

### 5. E4: o painel Qt e o que os testes encontraram

O painel Qt, interface principal desde a ADR-ML-09, ganhou 22 testes, e eles encontraram quatro problemas que a inspeção visual não teria revelado com segurança.

1. **Desempenho.** A tabela do ranking chamava a função de dados 17.953 vezes na primeira exibição, porque o ajuste automático das colunas recalculava a tabela inteira a cada relayout, e cada chamada criava uma linha do pandas. As colunas passaram a ser guardadas como listas e ajustadas uma vez a cada troca de dados. A primeira exibição caiu de 1,16 s para 0,27 s.
2. **Folha de estilo.** Reaplicar a folha de estilo a cada janela repolia todas as janelas abertas, e nos testes o custo crescia até parecer uma trava. A aplicação do tema tornou-se idempotente, e a janela é destruída ao fechar.
3. **Contraste.** Dois tokens do padrão ficavam abaixo da WCAG 2.2 [wcag22]: a borda dos campos, com 1,6:1, e o texto do selo "alta", com 4,0:1. Ambos foram trocados por variantes do próprio padrão, no Qt e no Figma.
4. **Teclado.** Nos grupos exclusivos (navegação e ordenação), o Qt deixa só o botão marcado na ordem do Tab. Os testes confirmaram que as setas percorrem os demais botões, como numa lista de abas, e que os atalhos Ctrl+1 a Ctrl+5 levam a cada tela.

O painel Streamlit, mantido como reserva, recebeu a mesma correção do R03, porque usa a mesma `carregar_lote`, e passou a compartilhar com o Qt a função do aviso do M2.

### 6. Pendências que continuam abertas

Três pendências não cabem numa correção de código e continuam declaradas:

- **Integração contínua:** o workflow `qualidade.yml` ainda roda só o `quality_gate.py` e não chama o verificador da Sprint 4, que depende da base da Sprint 3 em `data/pronto`.
- **LGPD:** a verificação de coincidência entre registros simulados e imóveis reais, por setor, prevista na seção 8 do E1, não foi executada.
- **Usabilidade:** o questionário SUS com analistas reais da Sefin depende de dados reais e de autorização.

## Conclusão

A revisão encontrou dois defeitos de integridade reais e quatro problemas de qualidade na interface nova, e todos foram corrigidos sem tocar o que foi avaliado:

- os seis SHA-256 do pacote e o manifesto do lote ativo continuam iguais aos da linha de base;
- as métricas do E2 não mudaram.

O padrão comum aos achados é que todos dependiam de uma condição que o caminho feliz não exercita: um arquivo adulterado com o checksum mantido, duas publicações durante uma leitura, uma tabela redesenhada muitas vezes, uma cor que parece legível mas não passa na medida. Por isso, cada correção veio acompanhada do teste que a reproduz, e o resultado esperado é que esses defeitos não voltem sem que a suíte acuse.

A verificação final, no código `d14a33b`, aprovou os dez controles: 930 testes sem MySQL, cobertura de 94,7%, 205 testes da Sprint 4, 11 contratos de dependência, nenhum erro de tipo, estrutura dentro dos limites, os 26 DOIs da Sprint 4 conferidos e a reprodutibilidade conferida pelos bytes reais. O registro completo está em [`reports/sprint4/verificacoes.json`](../../reports/sprint4/verificacoes.json).

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `wcag22`.
