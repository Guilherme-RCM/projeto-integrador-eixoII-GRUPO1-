# Decisões de arquitetura da Sprint 4 (ADR-ML-01 a ADR-ML-15)

Cada registro segue o formato contexto, decisão, alternativa considerada, consequência e evidência de aceite, porque uma decisão sem o motivo e sem a forma de conferi-la não pode ser revista com segurança quando o contexto mudar. As referências entre colchetes estão em [REFERENCIAS.md](REFERENCIAS.md), com os DOIs conferidos no Crossref.

## ADR-ML-01 — Monólito modular e inferência em lote

**Contexto.** O sistema das Sprints 2 e 3 é um monólito modular em Python, com MySQL, pipes e filtros e contratos de dependência verificados pelo import-linter. A Sprint 4 acrescenta treino, avaliação, inferência e um painel, e o prazo é de quatro dias.

**Decisão.** A camada de aprendizado de máquina entra como o pacote `pipeline/ml`, no mesmo monólito, e a inferência é feita em lote: `treinar_sprint4.py` treina, avalia, empacota e publica um lote de scores, e o painel Streamlit apenas lê esse lote. Dois contratos novos do import-linter tornam a separação verificável: a camada de ML não acessa rede, banco nem coleta, e `inferencia`, `lote` e `painel` não importam `modelos`, `experimento`, `pacote` nem `documentos`.

**Alternativa considerada.** Um serviço de predição separado, com API, foi descartado porque não há consumidor externo que o justifique e porque acrescentaria implantação, autenticação e versionamento de API sem ganho para os entregáveis; Valente [valente_esm] (cap. 7) lembra que a arquitetura deve responder a uma necessidade demonstrada, e o monólito modular preserva a fronteira entre módulos sem o custo da distribuição.

**Consequência.** O painel nunca treina nem reajusta transformador durante a interação, e um modelo novo só chega ao painel por um lote novo, com manifesto e hashes. Por outro lado, o score não é calculado sob demanda para um crédito novo; isso exige rodar o lote de novo.

**Evidência de aceite.** `lint-imports`: 11 contratos mantidos, entre eles os dois novos; o teste `test_predicao_nao_reajusta_transformador` confere que o objeto do modelo não muda depois de `predict_proba`.

## ADR-ML-02 — Dois alvos, duas populações e dois horizontes

**Contexto.** O enunciado pede um classificador de inadimplência e um score de recuperabilidade da dívida ativa. As duas perguntas se aplicam a créditos diferentes, em momentos diferentes.

**Decisão.** O **M1** prevê, em t0 = 1º de janeiro do exercício, se o crédito ficará sem pagamento até o vencimento; o **M2** prevê, numa fotografia da carteira, se um crédito inscrito e aberto em t0 será pago em (t0, t0 + 365 dias]. Cada tarefa tem população, atributos, rótulo e modelo próprios.

**Alternativa considerada.** Usar 1 − P(inadimplência) como recuperabilidade foi descartado, porque o M1 se aplica a todos os créditos antes do vencimento e o M2 só aos já inscritos; misturar as perguntas produziria um score sem população definida.

**Consequência.** O painel mostra o M1 no mapa de risco do exercício de teste (2025) e o M2 no ranking da carteira de 31/07/2026, sempre com a data e o horizonte de cada um.

**Evidência de aceite.** Contratos C-ML-01 e C-ML-02 em `E1_metodologia.md` (entrega E1); `tests/ml/test_dados_tempo.py` calcula à mão a população e o rótulo de cada tarefa.

## ADR-ML-03 — Divisões por data, disponibilidade dos atributos e rótulo imaturo

**Contexto.** A base da Sprint 3 traz colunas que olham para a data de corte (atraso até o pagamento ou até 31/07/2026, saldo e situação no corte), e o valor lançado de cada exercício foi calibrado com a arrecadação real do próprio ano.

**Decisão.** As fotografias são reconstruídas a partir dos eventos em cada t0; uma lista de colunas proibidas recusa qualquer atributo que olhe para depois de t0, que tenha sido calibrado com dado posterior ou que identifique renda ou território; as divisões seguem datas (M1: 2021–2023 / 2024 / 2025; M2: 29/06/2022 e 30/06/2023 / 01/07/2024 / 31/07/2025), e rótulo cuja janela não terminou fica ausente, nunca vira classe 0 [kaufman2012; kapoor2023; roberts2017].

**Alternativa considerada.** `TimeSeriesSplit` sobre a posição das linhas foi descartado, porque a ordem das linhas não garante que o rótulo de uma linha anterior esteja disponível na data de decisão da seguinte; a documentação do scikit-learn trata a divisão de séries como princípio, e as janelas daqui foram definidas por data e por maturidade do rótulo [sklearn_doc].

**Consequência.** O desempenho medido inclui a mudança de distribuição entre os exercícios (a prevalência do M1 sobe de 30,7% no treino para 36,7% no teste), em vez de escondê-la. O experimento é uma validação temporal em dados sintéticos retrospectivos, e não um backtest realista de Palmas.

**Evidência de aceite.** Nove invariantes por tarefa em `reports/sprint4/splits.json`; caso sentinela (pagamento futuro não muda atributo) no notebook e na suíte.

## ADR-ML-04 — Uso sintético e limites do simulador

**Contexto.** A camada individual é sintética (ADR-003 da Sprint 3). No gerador, a espera até o pagamento depois da inscrição é exponencial, com a mesma probabilidade anual de recuperação, 12%, para todas as dívidas (convertida numa taxa diária constante por −ln(1 − 0,12)/365) e sem relação com nenhum atributo.

**Decisão.** O simulador não é alterado. O M2 é treinado e avaliado como especificado, e o resultado — nenhum modelo supera o preditor constante — é publicado como achado, com a explicação do mecanismo [morris2019].

**Alternativa considerada.** Redefinir o M2 para incluir créditos vencidos ainda não inscritos, cuja chance de pagamento cai com o tempo de atraso na simulação, daria um modelo com sinal; a alternativa foi descartada para esta entrega porque mudaria a pergunta pedida (recuperabilidade da dívida ativa) depois de conhecido o resultado, e fica registrada como trabalho futuro, a decidir antes de qualquer novo teste.

**Consequência.** O ranking por score do M2 quase não diferencia devedores; o painel avisa isso e oferece a ordenação por valor esperado como opção distinta.

**Evidência de aceite.** `metadata.json` (`supera_referencia: false` no M2) e a seção 8 do notebook (ROC-AUC 0,508 e ganho de Brier de 0,005% no teste).

## ADR-ML-05 — Pacote de liberação e versionamento

**Contexto.** O E3 exige o modelo serializado e versionado em `/models`; a desserialização de joblib/pickle executa código, e o scikit-learn não oferece suporte a carregar um modelo treinado com outra versão da biblioteca [sklearn_doc].

**Decisão.** `models/sprint4/v1` guarda os dois pipelines completos (imputação, escala, estimador e limiar fixo), `metadata.json` (dados, código, protocolo, ambiente, semente), `feature_contract.json`, `metrics.json`, a ficha do modelo [mitchell2019] e `checksums.sha256`. A carga só acontece por `artefatos.carregar_modelo`, que confere o SHA-256 e a versão do scikit-learn antes do `joblib.load`. Os arquivos do pacote e do lote ficam como `-text` no `.gitattributes`, para que o fim de linha não mude num clone e o hash continue conferindo.

**Alternativa considerada.** O formato `skops.io`, que não executa código ao carregar, foi considerado; o joblib foi mantido porque o enunciado pede `.pkl`/`.joblib` e porque o pacote é gerado e lido só pelo próprio sistema, com hash conferido.

**Consequência.** Um modelo de outra versão do scikit-learn é recusado com mensagem clara, e o ambiente exato fica em `requirements.lock`.

**Evidência de aceite.** O notebook treina de novo e obtém os mesmos SHA-256 dos dois pipelines versionados; os testes de adulteração (`test_arquivo_adulterado_ou_versao_diferente_bloqueiam_a_carga`) passam.

## ADR-ML-06 — Ordenação, agregação por devedor e projeção

**Contexto.** O E4 pede ranking de devedores por score de recuperabilidade, mapa por setor e projeção de arrecadação. A base não tem vínculo entre contribuinte e imóvel.

**Decisão.** Adota-se a hipótese declarada "1 imóvel = 1 devedor sintético", que não representa pessoa real. O score do devedor é a média dos scores dos créditos ponderada pelo principal em aberto, o que equivale à fração esperada do principal recuperada; a ordenação inicial é pelo score, e a ordenação por valor esperado (principal × probabilidade) é uma opção separada. A projeção soma principal × probabilidade dos créditos elegíveis, em centavos inteiros, e o manifesto concilia a soma por crédito com a soma por devedor. As faixas (baixa < 0,33 ≤ média < 0,66 ≤ alta) são cortes de apresentação, não política pública, e ficam registradas no manifesto de cada lote, de onde o painel tira a legenda. Os filtros do painel selecionam devedores, e o mesmo conjunto sustenta ranking, mapa, projeção e exportação.

**Alternativa considerada.** Faixas por quantis do score foram descartadas, porque dariam nome de "alta" a scores de cerca de 13% e esconderiam que o M2 não discrimina.

**Consequência.** Com a simulação atual, toda a carteira cai na faixa baixa, e o painel mostra as três faixas com o zero explícito. A projeção não é aumento causal de arrecadação: ela estima a chance de pagamento, não o efeito de uma ação de cobrança.

**Evidência de aceite.** O manifesto do lote ativo (`concilia: true`, 78.122 créditos, 52.510 devedores) e os testes de ranking, projeção, conciliação e filtro de faixa em `tests/ml/test_painel.py`.

## ADR-ML-07 — Publicação do lote: versões imutáveis, ponteiro e compatibilidade com o pacote

**Contexto.** A revisão crítica de 07/11/2026 mostrou três falhas na ligação entre o pacote, o lote e o painel: o lote aceitava um protocolo com outro horizonte ou outras faixas (F02), o painel aceitava manifesto sem hashes e lote de outra versão de modelo (F03), e a publicação renomeava a pasta em dois passos, de modo que uma falha entre eles deixava o painel sem lote (F04).

**Decisão.** O pacote registra a definição dos modelos — janelas, atributos, horizonte, grades, seleção e semente —, e o lote recusa pontuar se o protocolo atual a mudar; faixas, mínimo de supressão e fotografia são política de apresentação, registrada no manifesto. Cada lote é gravado numa pasta imutável, conferido e só então ativado pela troca de um ponteiro (`ativo.json`) com `os.replace`, sob uma trava de publicação; a versão anterior fica preservada para reversão. O painel resolve o ponteiro uma vez por carga, valida o esquema do manifesto e a lista exata dos arquivos e confere a versão e o SHA-256 dos modelos contra o pacote aprovado [sklearn_doc].

**Alternativa considerada.** Restaurar a pasta antiga quando a segunda renomeação falhasse corrigiria só parte do problema, porque o caminho do lote continuaria vazio entre as duas renomeações; um link simbólico como ponteiro foi descartado porque, no Windows, criá-lo exige privilégio de administrador ou modo de desenvolvedor.

**Consequência.** Uma publicação interrompida deixa o painel com um lote inteiro, o anterior ou o novo, e `python treinar_sprint4.py --reverter-lote` volta ao anterior. O SHA-256 detecta divergência em relação ao manifesto, mas não autentica quem gravou os dois; a origem continua garantida pelas permissões da pasta local e pelo pacote versionado no Git. Como só o lote ativo é versionado, a versão anterior de uma publicação local fica apenas no disco.

**Evidência de aceite.** `tests/ml/test_publicacao.py` simula falha na gravação, na renomeação, na troca do ponteiro e na limpeza e confere que o leitor sempre encontra um lote inteiro; `TestCompatibilidade` recusa horizonte, atributos e períodos diferentes e aceita faixas novas com valores, legenda e manifesto coerentes; os testes do aplicativo recusam, pela mesma chamada da interface, manifesto vazio, hashes incompletos, versão incompatível e conteúdo alterado.

## ADR-ML-08 — XGBoost como análise extra, depois do protocolo congelado

**Contexto.** O enunciado do E2 cita "Random Forest/XGBoost" como exemplo de classificador, e o protocolo v1 testou só o Random Forest. Quando a ausência do boosting foi notada, em 09/11/2026, o teste já tinha sido aberto, e incluir uma família nova na seleção depois de ver o teste faria dele mais uma etapa de escolha [varma2006].

**Decisão.** O XGBoost [chen2016] entra como análise posterior ao protocolo, com protocolo complementar declarado antes da execução (`configs/analise_extra_xgboost.yaml`, 16 combinações, SHA-256 registrado). A análise usa as mesmas fotografias, os mesmos atributos, as mesmas dobras temporais, o pré-processamento das árvores e a métrica de cada tarefa. Na validação, compara o XGBoost ao modelo escolhido na v1 e ao Dummy por bootstrap pareado de imóveis; no teste, só descreve. O script confere os seis SHA-256 do pacote v1 antes e depois e não grava nada se algum mudar. O `import` do XGBoost fica dentro da função, para que o restante do pipeline não dependa dele (`requirements-analise.txt`).

**Alternativa considerada.** Refazer busca, seleção, teste, pacote, lote e notebook com o XGBoost como candidato oficial respeitaria a letra do enunciado, mas violaria o congelamento do protocolo e trocaria todos os hashes a dois dias do prazo. Na Matriz de Esforço × Impacto da AULA01 [rocha_aula01], essa alternativa cai no quadrante a evitar: esforço alto e impacto negativo sobre a validade da avaliação.

**Consequência.** O resultado não pode trocar o modelo escolhido. Ele serve como evidência de que a escolha da v1 não dependeu da ausência de uma família e como entrada do protocolo v2. Na execução de 09/11/2026, o XGBoost não superou a regressão logística em nenhuma tarefa: no M1, o ganho pareado foi de −0,0032 de Average Precision, com IC95% abaixo de zero; no M2, nenhum modelo supera a média.

**Evidência de aceite.** `tests/ml/test_analise_extra.py` confere que o protocolo complementar recusa grade vazia e semente própria, que a busca usa só o treino com as dobras e os atributos da v1, que o limiar vem da validação, que o modelo escolhido na v1 mantém os números publicados, que as três faixas aparecem no M2 e que uma alteração no pacote durante a análise interrompe a execução sem gravar nada. Duas execuções sobre a base real produziram tabelas idênticas.

## ADR-ML-09 — Painel Qt como interface principal, desenhado no Figma, e Streamlit como reserva

**Contexto.** O E4 pede um painel "Streamlit (ou equivalente)" que um analista da Sefin consiga usar. Em 09/11/2026, o grupo decidiu adotar uma aplicação Qt de interface simples e obrigatoriamente intuitiva, concebida por uma persona especialista em governança digital, com a modelagem visual feita antes no Figma. O painel Streamlit já funcionava e estava testado.

**Decisão.** O painel Qt (PySide6) passa a ser a interface principal, e o Streamlit continua no repositório como reserva para a demonstração. As duas interfaces só apresentam: a leitura verificada do lote, os filtros, o ranking, o mapa e a projeção ficam em `pipeline.ml.painel`, e por isso os números das duas são sempre os mesmos. O desenho usa os tokens do Padrão Digital de Governo [govbr_ds], com duas correções de contraste exigidas pela WCAG 2.2 [wcag22]: borda de controles em #888888 (`--border-color-alternative`) e texto do selo "alta" em #216E1F. A fonte é a Raleway, a alternativa à Rawline prevista no padrão, embutida sob a licença OFL 1.1. A interface não usa brasão nem logotipo oficial e se identifica como protótipo acadêmico com dados sintéticos.

**Alternativa considerada.** Substituir o Streamlit pelo Qt reduziria o código a manter, mas deixaria a demonstração sem reserva se o Qt falhasse no computador da apresentação. Usar o Qt apenas como protótipo não atenderia à decisão do grupo de oferecer ao analista uma aplicação de mesa.

**Consequência.** O MVP passa a ter duas interfaces sobre a mesma lógica, e uma correção de regra de negócio vale para as duas. O PySide6 e o pytest-qt ficam em `requirements-interface.txt`, fora do `requirements.lock` do pacote v1. Sem eles, os testes da interface Qt são pulados, e a integração contínua continua rodando o restante.

**Evidência de aceite.** `tests/ml/test_painel_qt.py` (22 testes, em modo offscreen) confere que a interface mostra os mesmos números de `pipeline.ml.painel` para ranking, filtros, projeção, faixas, mapa e exportação. Também confere:

- que um lote recusado vira mensagem clara, sem nenhum número;
- que todo controle interativo tem nome acessível e lugar na ordem de tabulação;
- que as setas percorrem a navegação como abas;
- que os pares de cores passam no contraste da WCAG.

O arquivo de desenho está no Figma, e as capturas das cinco telas estão em `docs/sprint4/capturas_qt`.

## ADR-ML-10 — Base vetorial em arquivos, dimensões de setor e protocolo próprio

**Contexto.** O pacote v1 descreve cada crédito por cinco ou seis atributos de histórico, e no treino do M1 menos da metade dos créditos tem um vetor de histórico que não se repete em outro crédito. Em 10/11/2026, a equipe pediu um banco vetorial com busca por similaridade cosseno para treinar os modelos, com dimensões de idade e escolaridade, ou outras respaldadas pela literatura, divisão 80/20 ou 70/30 e cuidado com a LGPD. O protocolo 1.0.0 estava congelado, o teste já tinha sido aberto, e a lista de colunas proibidas do E1 excluía renda e território dos atributos.

**Decisão.** A base vetorial entra como protocolo próprio (`configs/base_vetorial.yaml`, versão `vetorial-1.0.0`), no pacote `pipeline/vetorial`, sem alterar `pipeline/ml`, o pacote v1 nem o painel. Cinco escolhas a definem:

- **Banco em arquivos:** vetores NumPy em 32 bits, metadados e manifesto com SHA-256; busca exata por produto interno com o FAISS [johnson2021] e, sem ele, em NumPy.
- **Dimensões em grupos:** quatro grupos e quatro espaços aninhados (histórico, sociodemográfico, socioeconômico e territorial), com idade e alfabetização do Censo 2022 [ibge_censo2022_setores], escolhidas pelo respaldo de [hofmann2017] e [richardson2006].
- **Normalização do treino:** taxas, logaritmo, mediana e padronização, com os parâmetros gravados no manifesto.
- **Divisão por blocos temporais inteiros:** 80/20 no M1 e 69/31 no M2, este com fotografias trimestrais no treino; a proporção segue [joseph2022] e a ordem temporal, [roberts2017].
- **Proteção de dados no banco:** só agregados públicos de setor, supressão abaixo de dez imóveis [sweeney2002], pseudônimos por HMAC-SHA-256, setor fora dos metadados e exclusão de cor ou raça, sexo e recortes de povos tradicionais [lgpd2018].

**Alternativa considerada.** Três alternativas foram descartadas. Um serviço de banco vetorial com índice aproximado [malkov2020] acrescentaria operação e enviaria os vetores a outro processo sem acrescentar capacidade, porque a base tem menos de um milhão de vetores de até 14 dimensões e comporta busca exata. Incluir as dimensões novas no protocolo 1.0.0 e substituir o pacote v1 violaria o congelamento, trocaria todos os hashes na véspera do prazo e levaria atributos territoriais ao painel antes da decisão sobre equidade. A divisão aleatória em 80/20 daria a proporção pedida, mas misturaria períodos e violaria o E1.

**Consequência.** O repositório passa a ter dois pacotes de modelos: `models/sprint4/v1`, que alimenta o painel, e `models/sprint4/vetorial-v1`, publicado como evidência. Na execução de referência, o M1 escolheu o espaço socioeconômico, de 12 dimensões, com Random Forest, e a Average Precision no teste passou de 0,606 para 0,641; no M2, nenhum candidato superou o preditor constante. As dimensões de setor reintroduzem, por agregados, a renda e o território que o E1 havia excluído: a calibração por quintil de renda melhora, e a taxa de falsos positivos no quintil mais pobre sobe, como prevê [chouldechova2017]. Por isso a adoção do pacote vetorial na cobrança fica condicionada à análise de equidade da Sprint 5 e à decisão da gestão. As dimensões do Censo descrevem 2022 e têm data de publicação posterior ao t0 do treino e da validação. O FAISS fica em `requirements-vetorial.txt`, fora do `requirements.lock`, e a execução completa leva cerca de 30 minutos.

**Evidência de aceite.** `tests/vetorial` (78 testes) confere a leitura do Censo com sigilo, a normalização ajustada só no treino, a concordância entre os motores FAISS e NumPy, a recusa de banco adulterado ou incompatível com as fotografias, a ausência de identificadores diretos e de setor nos metadados, a regra de um erro-padrão e a execução de ponta a ponta; a cobertura é de 100% em cada módulo de `pipeline/vetorial`. O `import-linter` mantém os doze contratos, e o Pyright não acusa erro no código de produção. Duas execuções completas sobre a base real gravaram o banco com os mesmos SHA-256 e geraram os dois modelos com os mesmos bytes. `python base_vetorial.py conferir` recalcula os hashes do banco, e a dissertação `E5_base_vetorial.md` (entrega E2) é gerada dos relatórios versionados, com interrupção se o texto deixar de corresponder aos resultados.

## ADR-ML-11 — Versão 2 do M1 com dados do IBGE, sem renda

**Contexto.** A base vetorial (ADR-ML-10) reintroduziu a renda do setor entre as dimensões do M1, embora o protocolo 1.0.0 a tivesse excluído para não usá-la como critério de cobrança. Em 15/11/2026, a equipe decidiu definir quais dados do IBGE podem entrar nos modelos sem recorrer à renda.

**Decisão.** A versão 2 do M1 soma aos cinco atributos do histórico do imóvel seis medidas do setor censitário: idade mediana, proporção de 0 a 14 anos, proporção de 60 anos ou mais, taxa de alfabetização, proporção de filhos e proporção de netos e avós. Ficam excluídos a renda, o quintil de renda, a densidade, o número de moradores por domicílio, o sexo, a cor ou raça e os identificadores. A análise segue protocolo complementar declarado antes da execução (`configs/sprint4_v2_sem_renda.yaml`), com a divisão temporal e a métrica da v1, regressão logística com C = 10 e conferência dos SHA-256 do pacote v1 antes e depois.

**Alternativa considerada.** Retreinar o pacote oficial com as medidas do setor trocaria os hashes da entrega e levaria ao painel um modelo cuja questão de equidade não foi decidida. Manter a renda, como na base vetorial, contrariaria o protocolo 1.0.0.

**Consequência.** A Average Precision do M1 no teste passou de 0,606 para 0,620, com ganho pareado de 0,0171 na validação. O ganho, porém, equivale ao que o quintil de renda produz sozinho, porque as medidas do setor acompanham a renda; excluir a coluna não exclui a informação. A v2 não substitui a v1 nem alimenta o painel, e o uso de medidas do setor na cobrança depende da análise de equidade da Sprint 5.

**Evidência de aceite.** `reports/sprint4/v2_sem_renda/metricas.json`, com o SHA-256 do protocolo e os seis SHA-256 do pacote v1 conferidos; `python scripts/analise_v2_sem_renda.py` reproduz os números a partir de `data/limpo`.

## ADR-ML-12 — Experimento M2-Cenários como análise complementar e sexta tela do painel

**Contexto.** O M2 do pacote v1 não distingue devedores: o ROC-AUC no teste é de 0,508, e toda a carteira cai na faixa baixa. A causa provável está no gerador dos dados, porque o simulador da Sprint 3 dá a toda dívida inscrita a mesma probabilidade anual de pagamento, de 12% (ADR-ML-04). Em 15/11/2026, um experimento isolado, o M2-Cenários, pôs essa explicação à prova: simulou de novo os pagamentos posteriores à inscrição sob quatro mecanismos declarados e aplicou a cada um o mesmo procedimento de treino e avaliação, com o protocolo e o código registrados por SHA-256 antes do primeiro ajuste. A equipe pediu que o experimento passasse a integrar a Sprint 4 e pudesse ser visto no painel.

**Decisão.** O experimento entra no projeto como análise complementar, separada do lote, em cinco partes:

1. O código e o protocolo ficam em `experimentos/m2_cenarios`, copiados sem alteração; os cinco arquivos registrados antes do treino mantêm os mesmos SHA-256.
2. Os resultados compactos ficam em `reports/sprint4/m2_cenarios`, com manifesto e SHA-256 por arquivo. O script `scripts/publicar_m2_cenarios.py` faz a publicação e a recusa se a cadeia de registro não conferir: código e protocolo iguais aos registrados, execução concluída, origem preservada, auditoria aprovada e base analítica igual à do projeto.
3. O módulo `pipeline/ml/cenarios.py` lê a publicação só depois de conferir os hashes e devolve `ErroCenarios` quando ela falta, está incompleta ou foi alterada.
4. O painel Qt ganha a sexta tela, "Cenários do M2", e o Streamlit, a quinta aba, com os mesmos números. O analista escolhe o cenário, a partição de teste e a regra das faixas.
5. Um adendo exploratório (`configs/sprint4_m2_cenarios_adendo.yaml`), declarado depois do aceite e antes do cálculo, mede sobre as previsões já gravadas o que a literatura de avaliação de modelos preditivos recomenda além da discriminação: faixas pelos cortes do lote e por capacidade, ganhos acumulados, intercepto e inclinação de calibração, teto atingível e número de eventos no teste.

**Alternativas consideradas.** Trocar o M2 do lote pelo modelo do cenário moderado preencheria as faixas do painel, mas poria no ranking de devedores um modelo treinado em pagamentos gerados por hipóteses didáticas, trocaria os hashes do pacote v1 e contrariaria o ADR-ML-04 e o próprio protocolo do experimento, que veda o uso dos modelos fora da demonstração. Alterar o simulador da Sprint 3 mudaria a base analítica e todos os resultados já entregues. Deixar o experimento fora do projeto o esconderia da banca e do analista, que continuariam sem resposta para a pergunta "por que todos estão na faixa baixa?".

**Consequência.** O experimento confirma a explicação e delimita o que o M2 pode prometer. No controle sem sinal, a validação escolhe a previsão constante nas 20 réplicas, e o ROC-AUC fica em 0,500. No cenário de sinal moderado, a regressão logística alcança ROC-AUC de 0,783 e lift de 3,13 no topo de 10%, com 83% do ganho de Brier de quem conhecesse a probabilidade verdadeira; em imóveis fora do desenvolvimento, o ROC-AUC é de 0,782. Quando a relação se inverte depois da validação, o ROC-AUC cai para 0,272. O adendo acrescenta um achado sobre o ADR-ML-06: com os cortes de 0,33 e 0,66, a faixa alta fica vazia nas 20 réplicas e 99,99% dos créditos caem na baixa, mesmo com o modelo discriminando; nem a referência ideal poria mais de 4,0% dos créditos acima de 0,33, porque a taxa de pagamento da carteira é de cerca de 9% ao ano. As faixas por capacidade (10%, 20% e 70% do ranking) separam o pagamento em 27,0%, 18,0% e 3,3%, mas só informam quando o modelo discrimina: no controle sem sinal, as três pagam o mesmo, e a objeção do ADR-ML-06 às faixas por posição continua válida para o lote. O ADR-ML-06 permanece em vigor; a revisão dos cortes fica para quando houver dado real, com a regra condicionada à discriminação medida no teste. O pacote v1, o lote e `data/pronto` não mudam.

**Evidência de aceite.** `reports/sprint4/m2_cenarios/manifesto.json`, com a cadeia de registro, o SHA-256 dos 25 arquivos publicados e os SHA-256 do pacote v1; `tests/ml/test_cenarios.py`, que confere a publicação, a recusa de pasta adulterada, a igualdade entre a faixa alta por capacidade e o topo de 10% do protocolo e a reprodução da primeira semente pelo simulador congelado; os testes das duas interfaces em `tests/ml/test_painel_qt.py` e `tests/ml/test_painel.py`; a captura `docs/sprint4/capturas_qt/06_cenarios_do_m2.png`.

## ADR-ML-13 — Paleta de identidade do painel

**Contexto.** O painel Qt e o Streamlit usavam as cores do Padrão Digital de Governo (gov.br DS), com a primária #1351B4. Em 15/11/2026, a equipe definiu para o painel da entrega E4 uma paleta de identidade de quatro cores: azul-petróleo escuro (#293F49), vinho (#42313F), dourado envelhecido (#A38B55) e branco pérola acinzentado (#C9C9C4).

**Decisão.** A paleta substitui as cores, e a estrutura do gov.br DS continua: espaçamentos, raios, componentes e foco tracejado. Cada cor tem um papel fixo, para que a mesma cor signifique sempre a mesma coisa:

1. O azul-petróleo é a cor primária: navegação, botões, valores dos cartões, primeira série dos gráficos e extremo escuro do mapa.
2. O vinho é o apoio escuro: cabeçalho, item ativo da navegação, botão sob o mouse e dica de ferramenta.
3. O dourado é o realce: foco do teclado, filete do cabeçalho, marca do item ativo, segunda série dos gráficos e aviso de dados sintéticos.
4. O pérola é o neutro: bordas, botão desabilitado e texto secundário sobre o petróleo e o vinho.

Os fundos claros são misturas dessas cores com o branco, na fração anotada em `app/qt/tema.py`, e o erro mantém o vermelho do gov.br DS. O Streamlit recebe a mesma paleta pelo tema de `.streamlit/config.toml`, e a rampa do mapa, que as duas interfaces compartilham em `pipeline/ml/painel.py`, vai do petróleo a 12% sobre o branco ao petróleo puro.

**Alternativa considerada.** Manter o gov.br DS daria ao protótipo a aparência dos serviços públicos federais, mas o painel é acadêmico, não usa brasão e a equipe definiu identidade própria. Usar o pérola como contorno dos campos, como a paleta sugeria, reprovaria a WCAG 2.2: o pérola tem 1,7:1 contra o branco, abaixo dos 3:1 exigidos para limites de componentes; os contornos passaram a #6F7F86, derivado do petróleo, com 4,2:1.

**Consequência.** Os 20 pares de cor usados em texto passam de 4,5:1, com mínimo de 6,3:1, e os 8 pares de marcas gráficas passam de 3:1; `test_contraste_das_cores_do_tema` confere as duas listas. O dourado, com 3,3:1 contra o branco, nunca carrega texto. As duas séries dos gráficos têm 3,4:1 entre si e diferem na luminância. A fonte embutida, a Raleway, não tem letras gregas, e por isso a interface escreve "Spearman" e "beta" por extenso. O arquivo do Figma ainda guarda as cores do gov.br DS, e atualizá-lo ficou como pendência.

**Evidência de aceite.** `app/qt/tema.py`, `.streamlit/config.toml`, o teste de contraste em `tests/ml/test_painel_qt.py`, o teste da rampa em `tests/ml/test_painel.py` e as capturas de `docs/sprint4/capturas_qt`.

## ADR-ML-14 — Dashboard da Sprint 3 e base vetorial no painel

**Contexto.** A equipe tinha montado o dashboard da Sprint 3 à parte, com aplicativo Qt e Streamlit próprios, outra paleta e alguns números escritos no código. Em 16/11/2026, pediu que esse dashboard entrasse no painel Qt e no Streamlit da entrega E4 e que os modelos da base vetorial (ADR-ML-10) também pudessem ser vistos no painel.

**Decisão.** As telas do dashboard foram reconstruídas dentro dos dois painéis, e não copiadas, para seguir a arquitetura do E4: uma leitura pura e testada em `pipeline/`, que confere os dados antes de devolver qualquer número, e uma interface que só apresenta. A decisão tem cinco partes:

1. **Dados.** Os cinco arquivos da camada pronta da Sprint 3 que o dashboard lê ficam em `reports/sprint4/painel_sprint3`, sem alteração e com manifesto. O script `scripts/publicar_painel_sprint3.py` só os publica se o número de linhas de cada um for o registrado em `data/pronto/qualidade_dados.json` e se a tabela de setores for idêntica, byte a byte, à de `data/pronto`. A pasta `data/pronto` não muda.
2. **Leituras.** `pipeline/ml/receita.py` confere o SHA-256 de cada arquivo e calcula as medidas das telas; `pipeline/vetorial/painel.py` confere o pacote `models/sprint4/vetorial-v1` arquivo por arquivo e a coerência entre os relatórios, isto é, o mesmo candidato escolhido e a mesma métrica do teste nas métricas, na seleção e na comparação. Contratos do import-linter impedem as duas de importar o treino e o banco vetorial.
3. **Telas.** O Qt ganha "Base vetorial", "Receita tributária" e "Renda e simulação" (Ctrl+7 a Ctrl+9), e a navegação passa a três grupos: carteira do lote, modelos e dashboard da Sprint 3. O Streamlit ganha as três abas correspondentes. Os filtros da carteira valem só nas quatro telas do lote.
4. **Medidas recalculadas.** Os valores saem dos dados a cada abertura, e não de textos fixos. A "variação real média" do dashboard, média simples das variações anuais entre tributos, foi trocada pela taxa de crescimento real composta do período, que reproduz os números citados no próprio dashboard (+9,5% ao ano no ISSQN e −2,9% no IPTU, de 2019 a 2025) e avisa quando o período atravessa a troca de fonte de 2019. A renda no mapa é colorida pela posição do setor na ordem de renda, por ser assimétrica.
5. **Paleta.** As telas usam a paleta do E4 (ADR-ML-13), e não a do dashboard original, para que o painel tenha uma só linguagem visual.

**Alternativas consideradas.** Abrir os aplicativos do dashboard a partir do painel manteria duas paletas, dois carregadores de dados sem conferência e números escritos no código. Ler os arquivos direto de outra pasta da máquina deixaria a entrega dependente de um caminho local. O I de Moran citado no dashboard não foi recalculado, porque exige a matriz de vizinhança dos setores; ele continua na EDA da Sprint 3.

**Consequência.** O painel Qt passa a nove telas, e o Streamlit, a oito abas. Nenhuma tela nova lê o lote nem altera o pacote v1. A tela "Renda e simulação" separa por um aviso amarelo a renda, dado real do Censo 2022, da inadimplência, simulada; a tela "Base vetorial" mostra um aviso quando o espaço escolhido usa a renda do setor (ADR-ML-11). O arquivo do Figma não tem as pranchas das telas novas.

**Evidência de aceite.** `reports/sprint4/painel_sprint3/manifesto.json`; `tests/ml/test_receita.py`, que compara cada medida com uma conta feita direto nos CSV; `tests/vetorial/test_painel_vetorial.py`; os testes das telas e das abas em `tests/ml/test_painel_qt.py` e `tests/ml/test_painel.py`; as capturas 07 a 09 de `docs/sprint4/capturas_qt`.

## ADR-ML-15 — Mesmo conteúdo e filtros funcionais no Qt e no Streamlit

**Contexto.** A reserva Streamlit tinha oito abas e não oferecia o Resumo, os créditos do devedor nem a passagem do mapa ao ranking do setor presentes no Qt. A equipe pediu o mesmo conteúdo nas duas interfaces e filtros funcionais em ambas.

**Decisão.** As duas interfaces passam a apresentar as mesmas nove telas, na mesma ordem e nos três grupos do ADR-ML-14. Títulos, explicações, indicadores, matrizes de confusão, colunas e formatos vêm de `pipeline/ml/explicacoes.py`, `explicacoes_complementares.py`, `formatos.py`, `filtros.py` e `pipeline/vetorial/explicacoes.py`. A regra de seleção continua em `pipeline/ml/painel.py`.

Os filtros de região, faixa e setor atuam sobre os mesmos devedores no Resumo, Ranking, Mapa, Projeção e CSV. Cada opção informa a quantidade de devedores da carteira inteira, inclusive zero; o resumo informa o total selecionado, e combinações vazias mostram um aviso. No Qt, clicar no texto ou na caixa marca a opção uma única vez; a busca aceita Enter quando resta uma opção. No Streamlit, os filtros e os controles próprios das telas persistem ao navegar. O mapa permite escolher um setor pelo polígono ou pela lista e abrir seu ranking. Os créditos do devedor podem ser consultados no ranking. O CSV contém todos os créditos da seleção, mesmo quando o ranking mostra apenas o top-k.

O Qt permanece a interface principal e o Streamlit a reserva. A forma de interação acompanha o ambiente: diálogo de créditos e arquivo local no Qt; lista de devedores, detalhes na página e download no navegador. Não há promessa de identidade de pixels. As duas matrizes de confusão são exibidas na tela Sobre o modelo e conferidas contra o lote. A ordem inicial do ranking é valor esperado, recomendada pelo próprio aviso do M2; score continua disponível como opção distinta. Esta escolha de apresentação atualiza a ordem inicial descrita no ADR-ML-06, sem mudar probabilidades, faixas ou modelos.

**Alternativa considerada.** Duplicar textos e formatos nas duas interfaces permitiria divergências mesmo com números iguais. Compartilhar funções puras mantém as regras fora dos componentes visuais. O Streamlit exige a versão 1.67 ou superior, compatível com o ambiente congelado, para os controles e o download sob demanda usados aqui.

**Evidência de aceite.** `tests/ml/test_painel.py` percorre as nove telas, compara matrizes, seleção, filtros, ordenação, detalhes e persistência; `tests/ml/test_painel_qt.py` testa os mesmos fluxos e o clique no texto/caixa/Enter. `scripts/verificar_filtros_painel.py` executa 117 verificações sobre o lote publicado, com contas independentes. Em 16/11/2026, a suíte sem MySQL teve 1.102 testes aprovados, 57 de integração desmarcados e um teste opcional de FAISS pulado por ausência da biblioteca. Os 13 contratos de importação foram preservados. As capturas atuais estão em `docs/sprint4/capturas_qt` e `docs/sprint4/capturas_streamlit`.

**Consequência.** Atualiza a descrição das oito abas do ADR-ML-14. A base `data/pronto`, os modelos v1 e o lote publicado mantêm seus hashes. O Figma continua como referência das cinco telas originais; as quatro telas adicionais e a paleta atual ainda precisam de atualização naquele arquivo.
