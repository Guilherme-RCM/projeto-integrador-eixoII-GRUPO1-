# E4 — MVP: painel de priorização da dívida ativa

## Introdução

O E4 pede um painel funcional, demonstrável ao vivo e ligado ao pipeline real, com três conteúdos:

- o ranking de devedores por score de recuperabilidade;
- o mapa de inadimplência por setor;
- a projeção de arrecadação potencial.

O enunciado aceita "Streamlit ou equivalente". Em 09/11/2026, o grupo decidiu oferecer ao analista da Sefin uma aplicação de mesa em Qt, simples e obrigatoriamente intuitiva, concebida por uma persona especialista em governança digital e desenhada antes no Figma. O painel Streamlit, já testado, ficou como reserva para a demonstração (ADR-ML-09). Em 15 e 16/11/2026, os dois painéis ganharam a paleta de identidade da equipe (ADR-ML-13) e reuniram, em telas separadas do lote, o experimento M2-Cenários, a base vetorial e o dashboard da Sprint 3 (ADR-ML-12 e ADR-ML-14).

Este documento mostra como o painel Qt cumpre cada parte do pedido, por que as duas interfaces dão sempre os mesmos números e como a usabilidade e a acessibilidade foram conferidas. A tese é que um painel de apoio à cobrança só é útil se o analista entende o que cada número significa e o que ele não promete. Por isso, a interface explica o número ao lado dele, mantém o aviso de dados sintéticos sempre visível e nunca mostra número de um lote que não passou na conferência.

## Desenvolvimento

### 1. A persona e os princípios do desenho

A persona é uma especialista em governança digital que avalia se a ferramenta pode apoiar uma decisão pública sem induzir erro. Dela decorrem cinco princípios, cada um com uma consequência visível na tela:

| Princípio | Consequência no painel |
|---|---|
| Linguagem simples | Rótulos como "principal em aberto" e "valor esperado em 365 dias", datas em dd/mm/aaaa, valores em reais e uma frase "em linguagem simples" para cada modelo |
| Transparência | Aviso fixo de dados sintéticos; texto que explica o score ao lado do ranking; quadro "o que a projeção não é"; tela "Sobre o modelo" com o que cada modelo sabe e não sabe |
| Decisão humana | Frase "o painel apoia a decisão do analista: ele não decide a cobrança"; créditos do devedor abertos a um clique, para que o critério de pontuação possa ser explicado (LGPD, art. 20) |
| Acessibilidade | Contraste de pelo menos 4,5:1 no texto e 3:1 nos controles, foco visível tracejado, nome acessível em todo controle, operação completa pelo teclado [wcag22] |
| Poucos cliques | Filtros comuns às quatro telas da carteira, ordenação de um clique e atalhos de teclado (seção 5) |

### 2. Do Figma ao Qt: a base visual

O desenho foi feito antes da implementação, para que as decisões de forma fossem tomadas uma vez e copiadas, e não improvisadas a cada tela. O arquivo "PI2 Sprint 4 — Painel Qt (Inteligência Tributária)" (<https://www.figma.com/design/w8EQCcPnrPW6b7JCq2KfNl>) tem duas páginas:

- **Componentes:** as variáveis de cor, espaçamento e raio e oito componentes com variantes (botão, item de navegação, cartão de indicador, aviso, campo de filtro, segmento, selo de faixa e linha do ranking).
- **Telas:** as cinco telas em 1366 × 768 px, montadas com instâncias desses componentes. As quatro telas acrescentadas depois (Cenários do M2, Base vetorial, Receita tributária e Renda e simulação, de 15 e 16/11/2026) reaproveitam os mesmos componentes no Qt e ainda não têm prancha no Figma.

A estrutura visual é a do Padrão Digital de Governo (gov.br DS), conferida no pacote oficial `@govbr-ds/core` 3.7.0 em 09/11/2026 [govbr_ds]: espaçamentos de 4, 8, 16, 24 e 32 px, raios, componentes e foco tracejado. As cores, desde 15/11/2026, são as da paleta de identidade que a equipe definiu para o painel (ADR-ML-13), e cada uma tem um papel fixo:

| Cor | Hex | Papel no painel |
|---|---|---|
| Azul-petróleo escuro | #293F49 | cor primária: navegação, botões, valores dos cartões, primeira série dos gráficos e extremo escuro do mapa |
| Vinho | #42313F | apoio escuro: cabeçalho, item ativo da navegação, botão sob o mouse e dica de ferramenta |
| Dourado envelhecido | #A38B55 | realce: foco do teclado, filete do cabeçalho, marca do item ativo, segunda série dos gráficos e aviso de dados sintéticos |
| Branco pérola acinzentado | #C9C9C4 | neutro: bordas, botão desabilitado e texto secundário sobre o petróleo e o vinho |

Os tons claros dos fundos (seleção, avisos e linhas alternadas das tabelas) são misturas dessas cores com o branco, e só o estado de erro mantém o vermelho do gov.br DS, porque a paleta não tem um tom de alerta. A verificação de contraste pela WCAG 2.2 [wcag22] decidiu o uso de duas cores:

- **Pérola:** tem 1,7:1 contra o branco e por isso não serve de texto nem de contorno de controle sobre fundo branco. Os contornos dos campos usam #6F7F86, um cinza derivado do petróleo, com 4,2:1; o pérola fica nas bordas decorativas e no texto sobre o petróleo e o vinho, onde passa de 6,6:1.
- **Dourado:** tem 3,3:1 contra o branco, o bastante para marcas gráficas e para o foco, que pedem 3:1, mas não para texto, que pede 4,5:1. Por isso o dourado nunca carrega texto: o rótulo de cada barra fica sempre na cor do texto.

Os 20 pares de cor usados em texto passam de 4,5:1, e o menor tem 6,3:1; os 8 pares de marcas gráficas passam de 3:1. O teste do painel confere as duas listas a cada execução. As duas séries dos gráficos, petróleo e dourado, têm 3,4:1 entre si e diferem na luminância, e não só no matiz, o que as mantém distintas para quem não distingue cores; nos gráficos de linha, cada tributo também tem marcador e traço próprios, de modo que a identidade nunca depende só da cor. O Streamlit usa a mesma paleta, pelo tema de `.streamlit/config.toml` e pelos mesmos gráficos, e a rampa do mapa vai do petróleo a 12% sobre o branco ao petróleo puro nas duas interfaces. O arquivo do Figma ainda guarda as cores do gov.br DS: atualizar as variáveis de cor e desenhar as quatro telas novas ficou como pendência.

A fonte é a Raleway, a alternativa à Rawline prevista no padrão, embutida na aplicação sob a licença SIL Open Font License 1.1. Ela não tem as letras gregas, e por isso a interface escreve "Spearman" e "beta" por extenso. A interface não usa brasão nem logotipo oficial e se identifica como "protótipo acadêmico UFT/BIINAR".

### 3. Ligação com o pipeline, sem treino na interação

O painel Qt só apresenta, e essa separação garante que ele e o Streamlit mostrem os mesmos números. Toda a regra de negócio está em `pipeline/ml/painel.py`, que as duas interfaces chamam:

- a leitura verificada do lote;
- os filtros, o ranking, o mapa e a projeção;
- o aviso do achado do M2.

A camada `app/qt/servico.py` apenas encadeia essas funções e não importa o Qt, de modo que é testada sem janela.

O painel não treina nem reajusta modelo, porque um modelo ajustado durante a interação não teria versão, avaliação nem rastro (ADR-ML-01). Ao abrir, `carregar_lote` confere, nesta ordem:

1. o ponteiro `ativo.json`;
2. o esquema do manifesto;
3. o SHA-256 dos sete arquivos;
4. a versão e o SHA-256 dos modelos, contra o pacote aprovado.

Lote ausente, incompleto, adulterado ou de outro pacote troca o painel inteiro por uma mensagem em linguagem simples, com o botão "Tentar novamente", e nenhum número aparece. Desde a revisão técnica de 09/11/2026, a carga também resiste a publicações concorrentes: se o ponteiro mudar durante a leitura, a carga recomeça do zero, até três vezes, e nunca mistura arquivos de versões diferentes ([Revisão técnica do E3 e do E4](Revisao_Tecnica_E3_E4.md)).

### 4. As nove telas

Qt e Streamlit têm o mesmo conteúdo nas nove telas (ADR-ML-15). As matrizes M1 e M2 ficam em Sobre o modelo; os detalhes dos créditos ficam no Ranking; e o mapa permite abrir o ranking do setor. Títulos, textos, métricas e formatos são compartilhados. As capturas do Qt estão abaixo; as da reserva estão em [capturas_streamlit](capturas_streamlit).

Cada opção de filtro mostra sua contagem na carteira inteira. Combinações sem devedores mostram um aviso e valores zerados. No Qt, tanto o texto quanto a caixa de seleção marcam a opção, e Enter marca o único resultado da busca. As escolhas permanecem ao trocar de tela; as telas complementares têm seus próprios controles. O ranking inicia por valor esperado e permite trocar para score. O CSV exporta todos os créditos filtrados, independentemente do top-k exibido.


As telas seguem a ordem de uso de um analista: entender a carteira, priorizar, localizar no território, estimar o retorno e conferir os limites do modelo. Os filtros de região, faixa e setor ficam acima das quatro primeiras telas e valem para todas, de modo que ranking, mapa, projeção e exportação sempre usam os mesmos devedores. As outras cinco telas não usam esses filtros, e a barra some quando uma delas abre. A navegação as reúne em três grupos, para que o analista saiba de onde vem cada número: "Carteira do lote" (as quatro primeiras), "Modelos" (Sobre o modelo, Cenários do M2 e Base vetorial) e "Dashboard da Sprint 3" (Receita tributária e Renda e simulação).

| Tela | Conteúdo | Captura |
|---|---|---|
| Resumo | quatro indicadores (devedores, créditos, principal, valor esperado), como usar o painel, devedores por faixa com o zero explícito e o aviso do achado do M2 | [01_resumo.png](capturas_qt/01_resumo.png) |
| Ranking de devedores | tabela ordenável pelo cabeçalho, ordenação por valor esperado ou por score, top-k de 10 a 500, exportação e créditos do devedor | [02_ranking_de_devedores.png](capturas_qt/02_ranking_de_devedores.png) |
| Mapa por setor | polígonos reais dos 635 setores, três medidas, setor suprimido em cinza hachurado, legenda da rampa, setor selecionado e os cinco maiores valores | [03_mapa_por_setor.png](capturas_qt/03_mapa_por_setor.png) |
| Projeção de arrecadação | quatro indicadores, barras de principal e de valor esperado por faixa e o quadro "o que a projeção não é", com a conciliação | [04_projecao_de_arrecadacao.png](capturas_qt/04_projecao_de_arrecadacao.png) |
| Sobre o modelo | M1 e M2 em linguagem simples, limites e direitos, e as métricas de todos os modelos no teste congelado | [05_sobre_o_modelo.png](capturas_qt/05_sobre_o_modelo.png) |
| Cenários do M2 | experimento em simulação, separado do lote: escolha do cenário (sem sinal, sinal fraco, sinal moderado e mudança de padrão) e da partição de teste, quatro indicadores (ROC-AUC, pagamento no topo de 10%, ganho sobre a previsão constante e inclinação de calibração), pagamento observado e previsto por faixa, pela regra de capacidade ou pelos cortes do lote, leitura em linguagem simples, critérios fixados antes do treino e métodos comparados | [06_cenarios_do_m2.png](capturas_qt/06_cenarios_do_m2.png) |
| Base vetorial | análise complementar, fora do lote: escolha da tarefa, a métrica do candidato escolhido e a da referência, o ganho com o intervalo de 95%, as dimensões do vetor, o aviso quando o espaço usa a renda do setor, a calibração por quintil de renda e os doze candidatos com a regra de um erro-padrão | [07_base_vetorial.png](capturas_qt/07_base_vetorial.png) |
| Receita tributária | dashboard da Sprint 3, dado real e agregado: período e tributo, arrecadação real, peso da dívida ativa, crescimento real ao ano, pico sazonal, evolução por tributo, composição em exercício e dívida ativa, sazonalidade e indicadores anuais | [08_receita_tributaria.png](capturas_qt/08_receita_tributaria.png) |
| Renda e simulação | dashboard da Sprint 3: renda real dos setores (Censo 2022) ao lado da inadimplência simulada, com mapa, setor selecionado, inadimplência por quintil de renda e distribuição da renda | [09_renda_e_simulacao.png](capturas_qt/09_renda_e_simulacao.png) |

No lote atual, a carteira de 31/07/2026 tem:

- 78.122 créditos elegíveis, de 52.510 devedores sintéticos;
- principal em aberto de R$ 60.118.722,19;
- valor esperado de recuperação em 365 dias de R$ 6.948.081,53 (11,6%).

Todos os devedores estão na faixa baixa, porque a simulação aplica a mesma probabilidade anual de 12% a toda dívida inscrita ([E2](../../E2/documentacao/E2_modelos.md), seção 3.3). O painel diz isso com o zero explícito nas faixas alta e média, em vez de renomear quantis como "alta recuperabilidade".

A tela Cenários do M2 mostra o que mudaria se houvesse sinal, sem misturar essa hipótese com o lote. Ela lê o experimento publicado em `reports/sprint4/m2_cenarios` por `pipeline/ml/cenarios.py`, que confere o manifesto e o SHA-256 de cada arquivo antes de devolver qualquer número; se a publicação faltar ou tiver sido alterada, a tela mostra só a mensagem, e as outras cinco continuam com o lote conferido. Três escolhas de desenho evitam a leitura errada:

- **Aviso próprio:** a faixa azul "Experimento complementar, fora do lote" fica acima dos números, e os filtros do painel somem, porque não se aplicam.
- **Unidade declarada:** as medidas são por crédito, e não por devedor, e são médias de 20 réplicas, com o intervalo de 95% da média ao lado do ROC-AUC.
- **Faixa com a taxa ao lado:** cada faixa mostra o pagamento observado e a probabilidade prevista. No cenário moderado, as faixas por capacidade pagam 27,0%, 18,0% e 3,3%; pelos cortes do lote, a faixa alta fica vazia e 99,99% dos créditos caem na baixa. No cenário sem sinal, a nota avisa que as três faixas pagam o mesmo.

O botão "Abrir o relatório completo" abre no navegador o relatório do experimento, com os gráficos e todas as comparações. A análise e as referências estão no [E2](../../E2/documentacao/E2_modelos.md), seção 3.9.

As telas do dashboard da Sprint 3 levam para o painel o que a equipe tinha montado à parte, com a mesma regra das demais: os números vêm de dados publicados com manifesto e são recalculados, e não escritos no código (ADR-ML-14). Os dados são os cinco arquivos da camada pronta da Sprint 3, publicados em `reports/sprint4/painel_sprint3` depois de conferida a procedência. Três decisões corrigem o dashboard original:

- **Crescimento real:** a média simples das variações anuais, que dava +12,9%, mistura tributos de tamanhos diferentes e dá o mesmo peso a anos de base pequena e grande. O painel mostra a taxa composta entre o primeiro e o último ano do período, que de 2010 a 2025 é de +7,8% ao ano e que reproduz os números que o próprio dashboard citava no texto: +9,5% ao ano no ISSQN e −2,9% no IPTU, de 2019 a 2025. Quando o período atravessa 2019, o cartão avisa que a série troca de fonte.
- **Valores calculados:** a mediana da renda, a correlação de Spearman (−0,83) e os totais saem dos dados a cada abertura; o dashboard original trazia alguns desses números escritos no código e a mediana marcada numa posição fixa do eixo.
- **Renda no mapa:** a cor segue a posição do setor na ordem de renda, porque a renda é assimétrica e uma escala linear deixaria quase todos os setores no tom mais claro. A inadimplência simulada usa a escala linear.

O aviso amarelo da tela Renda e simulação separa as naturezas do dado: a renda é real, do Censo 2022, e a inadimplência é simulada (ADR-003 da Sprint 3), com a relação entre as duas imposta pelo parâmetro beta = −0,5. A tela Base vetorial, por sua vez, lê os relatórios de `reports/sprint4/base_vetorial` só depois de conferir o pacote `models/sprint4/vetorial-v1` arquivo por arquivo e a coerência entre os relatórios: o candidato escolhido e a métrica do teste precisam ser os mesmos nas métricas, na seleção e na comparação. Publicação ausente ou adulterada vira mensagem só na tela que a lê.

### 5. Avaliação de usabilidade pela persona

A avaliação heurística confrontou o painel com as dez heurísticas de usabilidade de Nielsen, na forma revista em 1994 [nielsen1994]. Uma heurística é um princípio geral que serve de lista de conferência para encontrar problemas sem usuários na sala.

| Heurística | Como o painel atende | Evidência |
|---|---|---|
| 1. Visibilidade do estado do sistema | Cabeçalho com "Lote … conferido", mensagens na barra de estado e página de erro quando o lote é recusado | testes de lote recusado e de atualização |
| 2. Correspondência com o mundo real | Vocabulário do analista, reais no padrão brasileiro, datas por extenso e frases "em linguagem simples" | telas Resumo e Sobre |
| 3. Controle e liberdade do usuário | "Limpar filtros", "Mostrar todas" em cada filtro, clique duplo para reenquadrar o mapa e nenhuma ação destrutiva | componentes de filtro e mapa |
| 4. Consistência e padrões | Tokens do gov.br DS e os mesmos componentes no Figma e no Qt; filtros iguais em todas as telas | arquivo do Figma e `app/qt/tema.py` |
| 5. Prevenção de erros | Painel somente leitura; score e valor esperado nunca misturados na mesma ordenação; exportação pede o nome do arquivo | tela Ranking |
| 6. Reconhecer em vez de lembrar | Resumo da escolha em cada filtro, tela atual destacada, navegação em três grupos, título e subtítulo que explicam cada tela e dicas de ferramenta | todas as telas |
| 7. Flexibilidade e eficiência | Ctrl+1 a Ctrl+9, F5, Ctrl+E, setas na navegação e ordenação pelo cabeçalho | teste dos atalhos e das setas |
| 8. Estética e minimalismo | Um aviso fixo, nove telas em três grupos e cartões com o valor abreviado e o exato abaixo | capturas |
| 9. Reconhecer, diagnosticar e recuperar-se de erros | Mensagem com a causa ("nenhum lote publicado", "lote adulterado…") e o botão "Tentar novamente", nunca um traceback | testes de lote recusado |
| 10. Ajuda e documentação | Quadro "Como usar o painel", dica de atalhos, "o que a projeção não é" e este documento | tela Resumo |

O percurso de oito tarefas típicas mediu o caminho mínimo de cada uma a partir da tela inicial:

| Tarefa do analista | Caminho | Cliques |
|---|---|---|
| Ver os 10 devedores de maior valor esperado da região Norte | Região → Norte → fechar → Ranking → Mostrar → 10 | 6 |
| Saber quanto um setor pode render em 365 dias | Mapa → setor → "Ver ranking do setor" → Projeção | 4 |
| Explicar a posição de um devedor no ranking | Ranking → linha do devedor → "Ver créditos do devedor" | 3 |
| Exportar os créditos da faixa baixa da região Sul | Faixa → Baixa → fechar → Região → Sul → fechar → Exportar → salvar | 8 |
| Saber se o modelo de recuperabilidade é confiável | Sobre o modelo | 1 |
| Entender por que todos estão na faixa baixa e o que mudaria com sinal | Cenários do M2 | 1 |
| Ver quanto do IPTU veio da dívida ativa desde 2019 | Receita tributária → período inicial → 2019 → IPTU | 4 |
| Saber se a base vetorial supera a referência no M2 | Base vetorial → Recuperabilidade (M2) | 2 |

As duas avaliações foram feitas pelo próprio grupo, com a persona, e não substituem um teste com analistas reais. Por isso, a aplicação do questionário SUS com servidores da Sefin fica registrada como pendência, para quando houver dados reais e autorização.

### 6. Como executar

O painel Qt depende de duas bibliotecas que ficam fora do `requirements.lock` do pacote de modelos: o PySide6 e, para os testes, o pytest-qt. A instalação com a restrição do lock impede que o pip troque as versões fixadas do scikit-learn, do NumPy, do pandas, do SciPy e do joblib.

```bash
python -m pip install -c requirements.lock -r requirements-interface.txt
python -m app.qt                                   # interface principal (lote de reports/sprint4/lote)
python -m app.qt --capturas docs/sprint4/capturas_qt   # grava uma imagem de cada tela e sai
streamlit run app/painel_sprint4.py                # reserva: abre http://localhost:8501
python treinar_sprint4.py --so-lote                # opcional: publica um lote novo com o pacote v1
python treinar_sprint4.py --reverter-lote          # opcional: volta ao lote anterior
```

As pastas do lote e do pacote podem ser trocadas pelas variáveis `PI2_LOTE_SPRINT4` e `PI2_MODELOS_SPRINT4`, nas duas interfaces; a do experimento M2-Cenários, pela variável `PI2_CENARIOS_M2`. O comando `python scripts/publicar_m2_cenarios.py` publica de novo o experimento a partir da pasta em que ele rodou. Os dados do dashboard da Sprint 3 ficam em `PI2_PAINEL_SPRINT3` e são publicados por `python scripts/publicar_painel_sprint3.py --origem <pasta data/pronto da Sprint 3>`; os relatórios e o pacote da base vetorial, em `PI2_VETORIAL_RELATORIOS` e `PI2_VETORIAL_MODELOS`. Antes do ensaio, `python scripts/verificar_filtros_painel.py` aciona os filtros na janela real sobre o lote publicado e compara cada tela com uma conta independente feita direto nas tabelas do lote. O comando `--so-lote` precisa da base da Sprint 3 em `data/pronto`, que é reconstruída com `python etl_sefin.py --offline --sem-banco`.

### 7. Verificação

Os testes de `tests/ml/test_painel_qt.py` abrem o painel Qt em modo offscreen sobre um lote sintético gerado pelo experimento completo. Eles conferem:

- que ranking, filtros, projeção, faixas, mapa e exportação mostram os mesmos números de `pipeline.ml.painel`;
- que os quatro cenários de lote inválido da revisão crítica viram mensagem sem números;
- que "Tentar novamente" e "Atualizar dados" leem o lote quando ele aparece ou muda;
- que todo controle interativo tem nome acessível;
- que a ordem de tabulação alcança os controles principais e que as setas percorrem a navegação;
- que os pares de cores passam no contraste da WCAG;
- que a tela Cenários do M2 mostra os números de `pipeline.ml.cenarios` em cada cenário, partição e regra de faixa, e que a publicação ausente ou adulterada vira mensagem só nessa tela;
- que as telas Receita tributária, Renda e simulação e Base vetorial mostram os números de `pipeline.ml.receita` e de `pipeline.vetorial.painel`, respondem ao período, ao tributo, à medida do mapa e à tarefa, e viram mensagem só nelas quando a publicação falta.

Os testes do Streamlit continuam em `tests/ml/test_painel.py`, com o `AppTest` [streamlit_apptest], e percorrem as nove telas, as matrizes de confusão, o ranking do setor, os créditos do devedor, a seleção vazia e a persistência dos controles. A leitura verificada do experimento e a reprodução da primeira semente pelo simulador congelado estão em `tests/ml/test_cenarios.py`; a procedência e as medidas do dashboard da Sprint 3, comparadas com contas feitas direto nos CSV, em `tests/ml/test_receita.py`; e a leitura conferida da base vetorial, em `tests/vetorial/test_painel_vetorial.py`. Em 16/11/2026, o roteiro `scripts/verificar_filtros_painel.py` acionou os filtros na janela real sobre o lote publicado, com clique de mouse na lista, busca, "Mostrar todas", "Limpar filtros", ordenação, quantidade, "Atualizar dados", passagem do mapa ao ranking do setor e exportação, e as 117 verificações conferiram com a conta independente.

## Conclusão

O painel Qt cumpre os três conteúdos do E4 com os números do pipeline real. Ele os apresenta de modo que o analista entenda o que cada número significa: o aviso de dados sintéticos nunca sai da tela, o score vem acompanhado da explicação e do limite do M2, e um lote que não passa na conferência não mostra número algum. O desenho no Figma fixou as decisões de forma antes do código, e o gov.br DS deu a elas uma estrutura pública e conhecida. A troca de paleta mostrou que escolher cores não dispensa medir: o pérola e o dourado da equipe ficaram onde o contraste os permite, e não onde a estética os pediria.

O resultado esperado da demonstração cabe em cinco minutos:

1. **Um minuto:** o aviso e as duas perguntas na tela Resumo.
2. **Um minuto:** o achado do M2 na tela Sobre o modelo e, na tela Cenários do M2, o que o mesmo procedimento aprende quando a simulação planta um sinal.
3. **Dois minutos:** filtrar uma região, ordenar, abrir os créditos de um devedor e ver o mapa e a projeção mudarem juntos.
4. **Um minuto:** a rastreabilidade, com o lote conferido no cabeçalho, o manifesto e o arquivo do Figma, e, no grupo do dashboard da Sprint 3, a receita real ao lado da inadimplência simulada.

Ficam como trabalho futuro o teste com analistas reais e a revisão do desenho com dados da Sefin, porque só eles dirão se a simplicidade medida pela persona se confirma no uso.

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `govbr_ds`, `nielsen1994`, `streamlit_apptest`, `wcag22`.
