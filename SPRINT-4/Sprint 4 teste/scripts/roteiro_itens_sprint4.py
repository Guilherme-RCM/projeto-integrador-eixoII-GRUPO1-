"""Itens do roteiro "Etapas de um Projeto" com a situação de cada um na Sprint 4 e a justificativa.

Fonte única do relatório das etapas: as tabelas de cada etapa e o quadro-resumo saem desta lista, de modo
que a contagem de itens por situação nunca diverge do texto. Os números das justificativas entram por
marcadores {nome}, preenchidos por scripts/gerar_relatorio_etapas_sprint4.py a partir dos arquivos da sprint.
As métricas ficam fora desta lista porque os valores delas vêm das predições do teste.
"""
from __future__ import annotations

USADO, SO_RELATORIO, NAO_APLICAVEL, NAO_TESTADO, NAO_USADO = (
    "Usado", "Só neste relatório", "Não aplicável", "Não testado", "Não usado")

ENCODERS = "Encoders"
TRANSFORMACOES = "Transformações"
ALGORITMOS = "Algoritmos"
METRICAS = "Métricas"
FERRAMENTAS = "Ferramentas"
ETAPA_DO_GRUPO = {ENCODERS: "1 · Modelagem", TRANSFORMACOES: "1 · Modelagem", ALGORITMOS: "2 · Treinamento",
                  METRICAS: "3 · Avaliação", FERRAMENTAS: "4 · Publicação"}

ITENS: list[dict] = [
    # ---------------------------------------------------------------- etapa 1: encoders
    {"grupo": ENCODERS, "item": "Dummy Encoder",
     "oque": "Transforma uma categoria (por exemplo, a região) em uma coluna de 0 e 1 para cada valor possível; "
             "também se chama codificação one-hot.",
     "situacao": NAO_APLICAVEL,
     "texto": "Nenhum atributo autorizado é categórico: os onze atributos são numéricos, e os dois binários, um em "
              "cada modelo, já aparecem como 0 ou 1. O plano da sprint previa o `OneHotEncoder`, que ficou fora do "
              "código porque não havia categoria a codificar."},
    {"grupo": ENCODERS, "item": "Target Encoder",
     "oque": "Troca cada categoria pela média do alvo observada nela, com um amortecimento que aproxima as "
             "categorias raras da média geral (Micci-Barreca, 2001).",
     "situacao": NAO_APLICAVEL,
     "texto": "Seria o caminho natural para setor, quadra e região, mas esses campos ficaram fora dos preditores de "
              "propósito, porque carregam a renda do Censo 2022. Num uso futuro, exigiria o ajuste com validação "
              "cruzada interna (`fit_transform`), que a documentação do scikit-learn recomenda para que o rótulo "
              "não vaze para a representação do treino."},
    {"grupo": ENCODERS, "item": "Frequency Encoder",
     "oque": "Troca cada categoria pela frequência com que ela aparece nos dados.",
     "situacao": NAO_APLICAVEL,
     "texto": "Sem categorias entre os preditores, não há o que substituir; setor e região, os candidatos naturais, "
              "não entram no modelo."},
    # ---------------------------------------------------------------- etapa 1: transformações
    {"grupo": TRANSFORMACOES, "item": "Logística",
     "oque": "Função em S que comprime qualquer número para o intervalo entre 0 e 1.",
     "situacao": NAO_TESTADO,
     "texto": "A função logística aparece só como função de ligação da regressão logística, que converte a soma "
              "ponderada dos atributos em probabilidade. Como transformação de atributo, não foi aplicada nem "
              "testada."},
    {"grupo": TRANSFORMACOES, "item": "Box-Cox",
     "oque": "Potência de parâmetro λ que deixa mais simétrica a distribuição de um atributo positivo; λ = 0 "
             "equivale ao logaritmo, e o λ ideal sai da máxima verossimilhança (Box e Cox, 1964).",
     "situacao": NAO_TESTADO,
     "texto": "Seria aplicável às duas razões `valor_relativo_*`, as únicas estritamente positivas e muito "
              "assimétricas: no treino, as assimetrias de {sk_ant} e {sk_cred} cairiam para {sk_ant_dep} e "
              "{sk_cred_dep}, com λ de {lam_ant} e {lam_cred}, perto do logaritmo. Não foi testada, porque mudar o "
              "pré-processamento depois de ver resultados exige nova versão do protocolo; as árvores, que dividem "
              "os dados por limiares, não mudam com transformações monótonas."},
    {"grupo": TRANSFORMACOES, "item": "Arcoseno",
     "oque": "Aplica o arco-seno à raiz de uma proporção entre 0 e 1 para estabilizar a variância; o uso em "
             "análise de proporções é discutido por Warton e Hui (2011).",
     "situacao": NAO_APLICAVEL,
     "texto": "Nenhum atributo é uma proporção: os atributos são contagens, dias, razões em torno de 1 e "
              "indicadores 0 ou 1."},
    # ---------------------------------------------------------------- etapa 2: algoritmos
    {"grupo": ALGORITMOS, "item": "Logistic Regression",
     "oque": "Estima a probabilidade de uma classe como função logística de uma soma ponderada dos atributos.",
     "situacao": USADO,
     "texto": "Baseline exigido pelo enunciado, escolhido nas duas tarefas: foi a melhor família na validação do M1 "
              "e a mais simples entre as empatadas, e a regra de um erro-padrão a manteve (C = {c_m1} no M1 e "
              "{c_m2} no M2). No M2, porém, não superou o Dummy."},
    {"grupo": ALGORITMOS, "item": "KNN",
     "oque": "Classifica um exemplo pelo rótulo dos exemplos de treino mais próximos dele.",
     "situacao": NAO_TESTADO,
     "texto": "Ficou fora do orçamento definido antes do treino (logística, árvore e Random Forest), e a falta de "
              "teste não indica desempenho pior, apenas ausência de medida. O método guarda os {n_treino} créditos "
              "de treino e busca vizinhos a cada pontuação (Hastie et al., 2009, cap. 13)."},
    {"grupo": ALGORITMOS, "item": "Naive Bayes",
     "oque": "Calcula a probabilidade de cada classe supondo que os atributos sejam independentes entre si dentro "
             "da classe.",
     "situacao": NAO_TESTADO,
     "texto": "A suposição de independência não vale aqui: `inadimplencias_anteriores`, `exercicios_anteriores` e "
              "`debitos_abertos_t0` são contagens do mesmo histórico e se relacionam por construção (scikit-learn, "
              "guia de Naive Bayes)."},
    {"grupo": ALGORITMOS, "item": "Random Forest",
     "oque": "Média de centenas de árvores de decisão treinadas em amostras diferentes dos dados e dos atributos "
             "(Breiman, 2001).",
     "situacao": USADO,
     "texto": "Candidato de maior capacidade, com 200 árvores fixas e 12 combinações de profundidade, tamanho "
              "mínimo da folha e atributos por divisão. No M1, ficou dentro de um erro-padrão da logística sem "
              "superá-la e consumiu {seg_rf} s de busca, contra {seg_lr} s; no M2, empatou com o Dummy."},
    {"grupo": ALGORITMOS, "item": "Redes Neurais",
     "oque": "Camadas de unidades que combinam os atributos de forma não linear.",
     "situacao": NAO_TESTADO,
     "texto": "O plano da sprint as dispensou. No M1, o Random Forest, que capta interações não lineares, não "
              "superou a logística, e no M2 nada superou o Dummy; os resultados sugerem que os atributos não têm "
              "estrutura adicional a explorar, mas não substituem um teste (Hastie et al., 2009, cap. 11)."},
    {"grupo": ALGORITMOS, "item": "XGBoost",
     "oque": "Soma árvores pequenas, cada uma corrigindo os erros das anteriores, técnica chamada boosting "
             "(Chen e Guestrin, 2016).",
     "situacao": USADO,
     "texto": "Avaliado como análise extra, depois do protocolo congelado (ADR-ML-08), com as mesmas divisões, "
              "atributos e dobras da v1 e 16 combinações declaradas antes da execução. Na validação do M1, a Average "
              "Precision foi {ap_xgb}, contra {ap_lr} da logística, com ganho pareado de {ganho_xgb} e IC95% abaixo "
              "de zero; no M2, não superou a média da carteira. A busca levou {seg_xgb} s. O resultado não troca o "
              "modelo escolhido nem entra no pacote."},
    {"grupo": ALGORITMOS, "item": "Extra Trees",
     "oque": "Variante do Random Forest que sorteia também os limiares de divisão das árvores (Geurts et al., 2006).",
     "situacao": NAO_TESTADO,
     "texto": "Pertence à mesma família de florestas do Random Forest, que não superou a logística no M1; o "
              "orçamento do protocolo ficou com uma só floresta."},
    {"grupo": ALGORITMOS, "item": "SVM",
     "oque": "Separa as classes pela fronteira de maior margem entre elas, que funções chamadas kernels podem "
             "curvar.",
     "situacao": NAO_TESTADO,
     "texto": "O ajuste do SVM com kernel custa entre o quadrado e o cubo do número de amostras, segundo o guia do "
              "scikit-learn; com {n_treino} créditos, o termo quadrático sozinho passa de 10^11. A versão linear "
              "(`LinearSVC`) escala quase linearmente, mas separa as classes por fronteira linear, como a "
              "regressão logística já treinada."},
    {"grupo": ALGORITMOS, "item": "Regressão Linear",
     "oque": "Ajusta uma reta (ou um plano) para prever um número contínuo.",
     "situacao": NAO_APLICAVEL,
     "texto": "Os dois alvos são classes (0 ou 1), e não valores contínuos. Só teria uso num terceiro modelo, que "
              "previsse o valor recuperado em reais, e a sprint não o propõe."},
    {"grupo": ALGORITMOS, "item": "K-Means",
     "oque": "Divide os exemplos em k grupos de centros próximos, sem usar rótulo.",
     "situacao": NAO_APLICAVEL,
     "texto": "É aprendizado não supervisionado (Hastie et al., 2009, cap. 14): forma grupos sem rótulo, e os dois "
              "problemas têm rótulo observado. Um agrupamento de setores serviria a uma análise exploratória à "
              "parte."},
    {"grupo": ALGORITMOS, "item": "Hierarchical",
     "oque": "Funde ou divide grupos em etapas e produz uma árvore de agrupamentos, o dendrograma.",
     "situacao": NAO_APLICAVEL,
     "texto": "Mesmo motivo do K-Means: agrupa sem rótulo, e os dois problemas têm rótulo observado (Hastie et "
              "al., 2009, cap. 14)."},
    {"grupo": ALGORITMOS, "item": "Holt-Winters Exponential Smoothing",
     "oque": "Projeta uma série no tempo dando mais peso aos valores recentes, com componentes de nível, "
             "tendência e sazonalidade.",
     "situacao": NAO_APLICAVEL,
     "texto": "Projeta uma série numérica no tempo (Hyndman e Athanasopoulos, cap. 8). A projeção de arrecadação do "
              "E4 foi implementada como valor esperado de recuperação da carteira, a soma de principal × "
              "probabilidade, e não como previsão de série. A receita mensal real está em "
              "`data/pronto/receita_tributaria.csv`, e um modelo de série poderia projetar o total arrecadado, que "
              "é uma pergunta diferente."},
    {"grupo": ALGORITMOS, "item": "DBSCAN",
     "oque": "Agrupa pontos em regiões densas e marca como ruído os pontos isolados.",
     "situacao": NAO_APLICAVEL,
     "texto": "Mesmo motivo do K-Means: agrupa sem rótulo, e os dois problemas têm rótulo observado."},
    {"grupo": ALGORITMOS, "item": "ARIMA",
     "oque": "Modela uma série pelos valores passados dela e pelos erros passados de previsão.",
     "situacao": NAO_APLICAVEL,
     "texto": "Mesmo motivo do Holt-Winters: prevê séries no tempo (Hyndman e Athanasopoulos, cap. 9)."},
    # ---------------------------------------------------------------- etapa 4: ferramentas
    {"grupo": FERRAMENTAS, "item": "Flask",
     "oque": "Microframework web em Python para criar serviços HTTP.",
     "situacao": NAO_USADO,
     "texto": "O plano não prevê serviço de predição: o ADR-ML-01 descartou uma API, isto é, uma interface pela qual "
              "outros programas consultariam o modelo, porque não há consumidor externo, e o painel lê o lote em "
              "arquivo."},
    {"grupo": FERRAMENTAS, "item": "FastAPI",
     "oque": "Framework web em Python para APIs, com validação de tipos.",
     "situacao": NAO_USADO,
     "texto": "Mesmo motivo do Flask (ADR-ML-01)."},
    {"grupo": FERRAMENTAS, "item": "Heroku",
     "oque": "Plataforma de hospedagem em nuvem para aplicações web.",
     "situacao": NAO_USADO,
     "texto": "Publicar em nuvem enviaria o painel e o lote a um serviço externo. A diretriz da sprint é preparar a "
              "entrega para revisão, sem colocar o sistema em operação, e os dados individuais são sintéticos."},
    {"grupo": FERRAMENTAS, "item": "AWS",
     "oque": "Serviços de nuvem da Amazon.",
     "situacao": NAO_USADO,
     "texto": "Mesmo motivo do Heroku."},
    {"grupo": FERRAMENTAS, "item": "GCP",
     "oque": "Serviços de nuvem do Google.",
     "situacao": NAO_USADO,
     "texto": "Mesmo motivo do Heroku."},
    {"grupo": FERRAMENTAS, "item": "Azure",
     "oque": "Serviços de nuvem da Microsoft.",
     "situacao": NAO_USADO,
     "texto": "Mesmo motivo do Heroku."},
    {"grupo": FERRAMENTAS, "item": "Streamlit",
     "oque": "Biblioteca Python que transforma um script em painel web interativo.",
     "situacao": USADO,
     "texto": "`app/painel_sprint4.py`, com Streamlit {streamlit}, executado em `localhost`, testado sem navegador "
              "com o `AppTest` e aberto com o lote real. O enunciado pede painel \"Streamlit (ou equivalente)\" "
              "demonstrável ao vivo."},
    {"grupo": FERRAMENTAS, "item": "Power BI",
     "oque": "Ferramenta de painéis da Microsoft.",
     "situacao": NAO_USADO,
     "texto": "O enunciado da Sprint 4 aceita Streamlit. A Sprint 3 documentou a montagem do painel em "
              "`docs/sprint3/power_bi.md`, e o arquivo `.pbix` consta como pendência em `SPRINT3.md`."},
    {"grupo": FERRAMENTAS, "item": "Tableau",
     "oque": "Ferramenta de painéis da Salesforce.",
     "situacao": NAO_USADO,
     "texto": "O MVP em Streamlit atende ao enunciado, e uma ferramenta comercial acrescentaria licença e "
              "dependência."},
    {"grupo": FERRAMENTAS, "item": "GSheets",
     "oque": "Planilhas do Google.",
     "situacao": NAO_USADO,
     "texto": "Pôr o lote numa planilha de serviço externo o enviaria a terceiros; o lote fica em arquivos locais "
              "versionados."},
    {"grupo": FERRAMENTAS, "item": "GData Studio",
     "oque": "Ferramenta de painéis do Google, hoje chamada Looker Studio.",
     "situacao": NAO_USADO,
     "texto": "Mesmo motivo do Google Sheets: a leitura dos dados passaria por serviço externo."},
    {"grupo": FERRAMENTAS, "item": "Metabase",
     "oque": "Ferramenta de código aberto para consultas e painéis sobre bancos de dados.",
     "situacao": NAO_USADO,
     "texto": "Exigiria servidor e banco de consulta; o painel lê o lote em arquivo, e as tabelas de scores no "
              "MySQL ficaram como proposta."},
]

# métricas do roteiro: (nome, o que mede, situação); os valores e as observações são montados no gerador
METRICAS_DO_ROTEIRO = [
    ("RMSE", "Raiz do erro quadrático médio: o tamanho típico do erro de uma previsão numérica.", SO_RELATORIO),
    ("MAE", "Erro absoluto médio: a média do quanto a previsão se afasta do valor real.", SO_RELATORIO),
    ("ROC Curve", "Curva que cruza, para cada limiar, a taxa de acertos entre os positivos e a taxa de erros "
                  "entre os negativos (Fawcett, 2006).", USADO),
    ("MAPE", "Erro percentual absoluto médio: o erro dividido pelo valor real, em porcentagem.", NAO_APLICAVEL),
    ("Matriz de Confusão", "Tabela que cruza a classe real com a prevista: verdadeiros negativos (VN), falsos "
                           "positivos (FP), falsos negativos (FN) e verdadeiros positivos (VP).", USADO),
    ("Acurácia", "Fração das previsões que acertam a classe.", USADO),
    ("Recall", "Entre os positivos reais, a fração que o modelo encontrou: VP ÷ (VP + FN).", USADO),
    ("Precision", "Entre os previstos positivos, a fração que de fato era positiva: VP ÷ (VP + FP).", USADO),
    ("F1-Score", "Média harmônica da precisão e do recall.", USADO),
]
