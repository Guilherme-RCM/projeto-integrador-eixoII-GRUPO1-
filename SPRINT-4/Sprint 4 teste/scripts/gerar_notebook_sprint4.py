"""Monta e executa notebooks/04_modelos_sprint4.ipynb (E3): trilha EDA → pré-processamento → treino → avaliação.

Uso:
    python scripts/gerar_notebook_sprint4.py             # monta e executa do início ao fim (≈ 7 min)
    python scripts/gerar_notebook_sprint4.py --sem-executar

O notebook chama as mesmas funções de treinar_sprint4.py (pipeline/ml); por isso não guarda
lógica própria nem depende de estado oculto de células. Ele treina de novo, grava o pacote numa
pasta de conferência (saida/notebook_sprint4) e compara o SHA-256 de cada pipeline com o pacote
versionado em models/sprint4/v1: a igualdade é a evidência de reprodutibilidade.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "notebooks" / "04_modelos_sprint4.ipynb"

CELULAS: list[tuple[str, str]] = [
    ("md", """# Sprint 4 — Modelo de IA e MVP: inadimplência e recuperabilidade da dívida ativa de Palmas

**Projeto Integrador, Eixo II (BIINAR/UFT, 2026/2), Opção D — Grupo 1.** Notebook do entregável E3, executado do início ao fim por `python scripts/gerar_notebook_sprint4.py`.

> **Dados individuais sintéticos.** Os créditos de IPTU e os imóveis desta base são simulados (ADR-003 da Sprint 3) sobre os setores censitários reais de Palmas. A acurácia obtida demonstra que o pipeline funciona, não que o modelo funciona no mundo real, e nenhuma linha corresponde a um contribuinte."""),
    ("md", """## 1. Introdução

Este notebook percorre a trilha completa do aprendizado de máquina da Sprint 4, da exploração dos dados à avaliação final, e o faz chamando as funções de `pipeline/ml`, que são as mesmas usadas pelo comando `python treinar_sprint4.py`. Essa escolha evita duas versões da mesma lógica, porque uma regra escrita só no notebook poderia divergir da regra que gera os modelos versionados; desse modo, o notebook documenta e reproduz, e o pacote em `models/sprint4/v1` é a fonte única dos artefatos.

O trabalho responde a duas perguntas distintas, e a separação é deliberada. O **M1** estima, em 1º de janeiro, se o crédito do exercício ficará sem pagamento até o vencimento; o **M2** estima, numa fotografia da carteira, se um crédito já inscrito em dívida ativa e ainda aberto será pago nos 365 dias seguintes. Como população, momento de decisão e horizonte diferem, usar 1 − P(inadimplência) como recuperabilidade misturaria as perguntas, e por isso cada tarefa tem alvo, janela e modelo próprios.

O método segue o CRISP-ML(Q), que acrescenta garantia de qualidade a cada fase do CRISP-DM (Studer et al., 2021, DOI 10.3390/make3020020), e o protocolo, com janelas, atributos autorizados, grades e regras de decisão, foi fixado em `configs/sprint4.yaml` antes de qualquer contato com o teste. Por conseguinte, o teste é avaliado uma única vez, com modelo, limiar e calibração já congelados."""),
    ("code", """import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

from pipeline.ml import artefatos, avaliacao, dados, experimento, figuras, modelos, pacote
from pipeline.ml.config import RAIZ

warnings.filterwarnings("ignore", message="Skipping features without any observed values")
# As threads do Random Forest (n_jobs=10) refazem a lista global de filtros de aviso (o scikit-learn chama
# resetwarnings() em cada uma), e o filtro acima pode sumir por um instante; por isso, um aviso que escape
# é mostrado sem o caminho do arquivo, e a saída publicada não traz caminho da máquina.
warnings.showwarning = lambda mensagem, categoria, *_, **__: print(f"{categoria.__name__}: {mensagem}", file=sys.stderr)
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)
FIGURAS = RAIZ / "reports" / "sprint4" / "figuras"
CONFERENCIA = RAIZ / "saida" / "notebook_sprint4" / "v1"
VERSIONADO = RAIZ / "models" / "sprint4" / "v1\""""),
    ("md", """## 2. Ambiente, protocolo e base congelada

A reprodutibilidade começa pelo registro do que entra no experimento, porque um resultado sem a versão dos dados, do código e das bibliotecas não pode ser refeito (Amershi et al., 2019, DOI 10.1109/ICSE-SEIP.2019.00042). A célula abaixo carrega o protocolo, calcula o SHA-256 de cada insumo e mostra as versões do ambiente; o hash da base deve coincidir com o da execução de referência da Sprint 3, o que confirma que a Sprint 4 parte exatamente da base entregue."""),
    ("code", """ctx = experimento.preparar()
p = ctx.protocolo
display(pd.DataFrame({"insumo": list(ctx.insumos), "sha256": [h[:16] + "…" for h in ctx.insumos.values()]}))
print("protocolo", p.versao, p.sha256[:16], "· semente", p.semente, "· execução", ctx.execucao)
print("simulação", ctx.simulacao["assinatura"][:16], "· execução da Sprint 3", ctx.simulacao["execucao_sprint3"])
print(artefatos.ambiente())"""),
    ("md", """## 3. Qualidade da base

Antes de modelar, a base precisa ser verificada quanto a chave, tipos, ausências e coerência temporal, porque um erro nessa etapa se propaga a todos os modelos. A função `dados.carregar_base` já recusa crédito repetido e crédito sem vencimento; a tabela abaixo descreve o restante: volume por exercício, ausências por coluna e a coerência das datas de pagamento e de inscrição em relação ao vencimento."""),
    ("code", """base = ctx.base
print(f"{len(base):,} créditos · {base['id_imovel'].nunique():,} imóveis · exercícios {sorted(base['exercicio'].unique())}".replace(",", "."))
qualidade = pd.DataFrame({"ausentes": base.isna().sum(), "tipo": base.dtypes.astype(str)})
display(qualidade)
coerencia = {
    "inscrição antes do vencimento": int((base["data_inscricao"] < base["data_vencimento"]).sum()),
    "pagamento em dia com inadimplente = 1": int(((base["data_pagamento"] <= base["data_vencimento"]) & (base["inadimplente"] == 1)).sum()),
    "origem diferente de SINTETICO": int((base["origem_dado"] != "SINTETICO").sum()),
}
coerencia"""),
    ("md", """A base passa nas três verificações de coerência, e as ausências estão onde o domínio as explica: `data_pagamento` falta quando o crédito não foi pago até o corte, e `data_inscricao` falta quando o crédito nunca foi inscrito. Por isso, essas ausências não são erro de dado, mas informação de estado, e é justamente por carregarem o futuro que essas duas colunas ficam fora dos atributos e servem apenas à construção dos rótulos."""),
    ("md", """## 4. Fotografias em t0 e divisão temporal com controles contra vazamento (E1)

Um atributo só pode usar o que já era conhecido no momento da decisão; caso contrário, o modelo aprende com o futuro e parece excelente sem funcionar (Kaufman et al., 2012, DOI 10.1145/2382577.2382579; Kapoor e Narayanan, 2023, DOI 10.1016/j.patter.2023.100804). Por esse motivo, as fotografias são reconstruídas a partir dos eventos — vencimento, inadimplência no vencimento, pagamento e inscrição — em cada data t0, e as colunas de atraso, saldo e situação no corte da Sprint 3 nunca entram como atributo.

A divisão também segue datas, e não a posição das linhas: o M1 treina com os exercícios 2021–2023, valida em 2024 e testa em 2025; o M2 treina com as fotografias de 29/06/2022 e 30/06/2023, valida em 01/07/2024 e testa em 31/07/2025, cuja janela de 365 dias termina exatamente no corte. Roberts et al. (2017, DOI 10.1111/ecog.02881) mostram que a validação aleatória superestima o desempenho quando os dados têm estrutura temporal, e as invariantes abaixo garantem que todo rótulo usado num conjunto já estava disponível antes do primeiro t0 do conjunto seguinte."""),
    ("code", """divisoes = {t: experimento.conjuntos(ctx, t) for t in ("M1", "M2")}
linhas = []
for tarefa, d in divisoes.items():
    for nome, c in d.manifesto["conjuntos"].items():
        linhas.append({"tarefa": tarefa, "conjunto": nome, "n": c["n"], "imóveis": c["imoveis"], "positivos": c["positivos"],
                       "prevalência": c["prevalencia"], "períodos": c["periodos"], "fim do rótulo": c["fim_rotulo"]})
display(pd.DataFrame(linhas))
display(pd.DataFrame([{"tarefa": t, **r} for t, d in divisoes.items() for r in d.manifesto["invariantes"]]))"""),
    ("md", """As nove invariantes passam nas duas tarefas: a chave (tarefa, crédito, t0) não se repete, a cronologia entre treino, validação e teste é respeitada, nenhum rótulo imaturo entra e as duas classes estão presentes em cada conjunto. A prevalência do M1 sobe de 30,7% no treino para cerca de 36% na validação e no teste, porque 2021, o primeiro exercício simulado, não tem histórico de inadimplência; essa mudança de distribuição é real no dado e, por isso, deve aparecer na avaliação temporal, em vez de ser escondida por uma divisão aleatória.

O caso sentinela abaixo torna a regra de disponibilidade verificável: um pagamento posterior a t0 é inserido num crédito, e os atributos da fotografia t0 não podem mudar. O mesmo teste existe na suíte automatizada (`tests/ml/test_dados_tempo.py`)."""),
    ("code", """foto_2025 = divisoes["M1"].conjuntos.teste
aberto = base.loc[(base["exercicio"] == 2024) & base["data_pagamento"].isna()].iloc[0]
alterada = base.copy()
alterada.loc[alterada["id_credito"] == aberto["id_credito"], "data_pagamento"] = pd.Timestamp("2025-06-01")  # depois de t0 = 01/01/2025
antes = dados.fotografia_m1(base, 2025, p.data_corte, ctx.regioes, ctx.versao_dados)
depois = dados.fotografia_m1(alterada, 2025, p.data_corte, ctx.regioes, ctx.versao_dados)
print("atributos idênticos após pagamento futuro:", antes[list(p.m1.atributos)].equals(depois[list(p.m1.atributos)]))"""),
    ("md", """## 5. Análise exploratória no treino

A exploração usa apenas o treino, porque qualquer decisão tomada depois de olhar a validação ou o teste contamina a avaliação. Para o M1, a pergunta é se o histórico do imóvel carrega sinal sobre a inadimplência; para o M2, se algum atributo conhecido em t0 diferencia as dívidas que serão pagas."""),
    ("code", """treino_m1, treino_m2 = divisoes["M1"].conjuntos.treino, divisoes["M2"].conjuntos.treino
media_m1 = float(treino_m1["alvo"].astype(float).mean())
tabela = figuras.taxa_por_atributo(treino_m1.loc[treino_m1["exercicio"] > 2021], "inadimplencias_anteriores")
fig = figuras.barras_taxa(tabela.sort_values("valor"), "A inadimplência cresce com o histórico de inadimplência do imóvel",
                          "M1 · treino 2022–2023 · taxa de inadimplência no vencimento por inadimplências anteriores",
                          "inadimplências anteriores do imóvel", media_m1)
display(Image(filename=figuras.salvar(fig, FIGURAS, "01_m1_historico.png")))"""),
    ("code", """media_m2 = float(treino_m2["alvo"].astype(float).mean())
for atributo, faixas, nome, rotulo in (
        ("dias_desde_inscricao", [0, 180, 365, 730, 2000], "02_m2_tempo_inscricao.png", "dias desde a inscrição em t0"),
        ("valor_relativo_credito", [0, 0.5, 1, 2, 100], "03_m2_valor.png", "valor do crédito ÷ mediana do exercício")):
    tabela = figuras.taxa_por_atributo(treino_m2, atributo, faixas)
    fig = figuras.barras_taxa(tabela, "A recuperação em 365 dias não varia com o atributo",
                              f"M2 · treino (fotografias de 2022 e 2023) · taxa de recuperação por {rotulo}", rotulo, media_m2)
    display(Image(filename=figuras.salvar(fig, FIGURAS, nome)))
print(f"recuperação média no treino: {media_m2:.4f}; parâmetro da simulação: 0,12 ao ano depois da inscrição")"""),
    ("md", """As duas explorações apontam para direções opostas, e essa diferença decorre do mecanismo que gerou os dados. No M1, a taxa de inadimplência cresce de forma nítida com o número de inadimplências anteriores, porque a simulação faz a inadimplência de um ano depender da do ano anterior (β = 1,5) e da renda do setor. No M2, a recuperação fica perto de 12% em todas as faixas, porque o gerador sorteia a espera até o pagamento depois da inscrição de uma distribuição exponencial com taxa diária constante, derivada da probabilidade anual de recuperação de 12% (−ln(1 − 0,12)/365), sem relação com nenhum atributo; como a exponencial não tem memória, a chance de pagar nos próximos 365 dias é a mesma para toda dívida ainda aberta.

Por conseguinte, a expectativa registrada antes do treino é que o M2 não supere o preditor constante. Esse resultado, se confirmado, será publicado como achado, e o simulador não será alterado para produzir métricas favoráveis, porque ajustar o gerador depois de olhar o resultado transformaria o experimento em confirmação do que se quer ver (Morris, White e Crowther, 2019, DOI 10.1002/sim.8086)."""),
    ("md", """## 6. Pré-processamento dentro do Pipeline

Toda transformação aprendida fica dentro de um `Pipeline` com `ColumnTransformer`, para que a mediana de imputação e a escala sejam estimadas só com os dados de ajuste de cada dobra; a documentação do scikit-learn resume a regra em nunca chamar `fit` nos dados de teste ("Common pitfalls", §12.2). Os atributos ausentes recebem a mediana do treino e um indicador de ausência, o que preserva a informação de que o imóvel não tinha exercício anterior; a escala é aplicada só à regressão logística, porque as árvores são invariantes a transformações monotônicas."""),
    ("code", """candidatos = modelos.candidatos(p, p.m1.atributos)
for nome, pipe in candidatos.items():
    print(f"{nome:22s}", " → ".join(f"{n}: {type(o).__name__}" for n, o in pipe.steps))
candidatos["regressao_logistica"]"""),
    ("md", """## 7. Baselines, busca de hiperparâmetros e seleção (E1 e E2)

A comparação parte de referências simples, porque um modelo complexo só se justifica se superar o que uma regra trivial já faz. O `DummyClassifier` com a prevalência do treino é a referência mínima; a regressão logística e a árvore de decisão são os baselines exigidos; o Random Forest é o candidato de maior capacidade (Breiman, 2001, DOI 10.1023/A:1010933404324), com o número de árvores fixo em 200, porque o erro de generalização converge quando as árvores aumentam.

A busca usa `GridSearchCV` com as dobras temporais explícitas dentro do treino — 2021→2022 e 2021–2022→2023 no M1; 2022→2023 no M2 — e a métrica declarada no protocolo: Average Precision no M1, mais informativa que a curva ROC quando as classes são desbalanceadas (Saito e Rehmsmeier, 2015, DOI 10.1371/journal.pone.0118432), e Brier no M2, em que a probabilidade é o produto (Brier, 1950, DOI 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2). A escolha entre famílias usa a validação externa e a regra de um erro-padrão: entre os modelos a até um erro-padrão do melhor, fica o mais simples (Hastie, Tibshirani e Friedman, 2009, §7.10, DOI 10.1007/978-0-387-84858-7). O teste não participa de nenhuma dessas decisões, porque escolher e estimar o erro na mesma amostra enviesa a estimativa (Varma e Simon, 2006, DOI 10.1186/1471-2105-7-91)."""),
    ("code", """treinos = {}
for tarefa in ("M1", "M2"):
    treinos[tarefa] = experimento.treinar(ctx, tarefa, divisoes[tarefa])
    t = treinos[tarefa]
    print(f"{tarefa}: escolhido = {t.selecao.escolhido}; supera o Dummy por mais de 1 erro-padrão = {t.selecao.supera_referencia}; "
          f"limiar (F1 máximo na validação) = {t.limiar:.4f}; calibração = {t.calibracao}")
    display(t.selecao.tabela.drop(columns=["segundos_busca"]).round(5))"""),
    ("code", """busca = pd.concat([b.tentativas.assign(tarefa=t) for t, tr in treinos.items() for b in tr.buscas.values()], ignore_index=True)
display(busca.sort_values(["tarefa", "modelo", "rank_test_score"]).groupby(["tarefa", "modelo"]).head(3)[
    ["tarefa", "modelo", "params", "mean_test_score", "std_test_score", "rank_test_score", "mean_fit_time"]].round(4))"""),
    ("md", """No M1, a regressão logística foi a melhor família na validação e também a mais simples; o Random Forest ficou dentro de um erro-padrão dela, sem ganho que justificasse 200 árvores, e a árvore de decisão ficou abaixo. O ganho da logística sobre o Dummy é grande e estável no bootstrap por imóvel, o que confirma o sinal visto na exploração. No M2, todas as famílias empatam com o Dummy dentro de um erro-padrão; pela regra pré-especificada, a logística é mantida como o candidato mais simples, mas o registro `supera_referencia = False` documenta que nenhum modelo melhora a probabilidade constante. Como a média prevista ficou a menos de 2 pontos percentuais da observada na validação, a calibração adicional não foi aplicada."""),
    ("md", """## 8. Avaliação única no teste congelado (E2)

O teste é aberto agora, com modelo, limiar e calibração já fixados, e nenhuma decisão volta a ele. As métricas exigidas — acurácia, precisão, recall, F1 e matriz de confusão — vêm acompanhadas de n, prevalência e limiar, e são complementadas pela qualidade das probabilidades e pela precisão no topo do ranking. O TRIPOD+AI (Collins et al., 2024, DOI 10.1136/bmj-2023-078378), embora seja uma diretriz clínica, serve de roteiro de relato por analogia: população, momento da predição, desfecho, desempenho com incerteza e limitações."""),
    ("code", """avaliacoes = {t: experimento.avaliar(ctx, t, divisoes[t], treinos[t], pacote.VERSAO_MODELO) for t in ("M1", "M2")}
resumo = []
for tarefa, a in avaliacoes.items():
    c, pr, b = a.metricas["classificacao"], a.metricas["probabilidade"], a.metricas["bootstrap_metrica_principal"]
    resumo.append({"tarefa": tarefa, "modelo": a.metricas["modelo"], "n": c["n"], "prevalência": c["prevalencia"], "limiar": c["limiar"],
                   "acurácia": c["acuracia"], "precisão": c["precisao"], "recall": c["recall"], "F1": c["f1"],
                   "[[VN, FP], [FN, VP]]": c["matriz_confusao"], "AP": pr["average_precision"], "ROC-AUC": pr["roc_auc"],
                   "Brier": pr["brier"], "ganho de Brier": pr["ganho_brier_sobre_constante"],
                   f"IC95% {a.metricas['metrica_principal']}": [round(x, 4) for x in b["ic95"]]})
pd.DataFrame(resumo).round(4)"""),
    ("code", """comparacao = pd.concat([a.comparacao.assign(tarefa=t) for t, a in avaliacoes.items()], ignore_index=True)
display(comparacao.loc[comparacao["conjunto"] == "teste", ["tarefa", "modelo", "escolhido", "acuracia", "precisao", "recall", "f1",
                                                           "average_precision", "roc_auc", "brier", "ganho_brier_sobre_constante"]].round(4))
fig = figuras.comparacao(comparacao, "M1", "average_precision", "No M1, a logística iguala o Random Forest e supera os baselines",
                         "Average Precision na validação (2024) e no teste (2025); escolhido na validação, em destaque no eixo")
display(Image(filename=figuras.salvar(fig, FIGURAS, "04_comparacao_m1.png")))
fig = figuras.comparacao(comparacao, "M2", "roc_auc", "No M2, nenhum modelo ordena melhor que o acaso",
                         "ROC-AUC na validação (01/07/2024) e no teste (31/07/2025); 0,5 = sem discriminação")
display(Image(filename=figuras.salvar(fig, FIGURAS, "05_comparacao_m2.png")))"""),
    ("code", """teste_m1 = avaliacoes["M1"].predicoes.query("split == 'teste'")
fig = figuras.precisao_recall(teste_m1["y_real"].to_numpy(), teste_m1["y_prob"].to_numpy(), treinos["M1"].limiar,
                              "M1 · teste 2025 · curva precisão-recall; a linha tracejada é a prevalência")
display(Image(filename=figuras.salvar(fig, FIGURAS, "06_precisao_recall_m1.png")))
fig = figuras.calibracao({t: a.metricas["calibracao"] for t, a in avaliacoes.items()},
                         "teste congelado · fração observada por decil do score previsto")
display(Image(filename=figuras.salvar(fig, FIGURAS, "07_calibracao.png")))
for t, a in avaliacoes.items():   # o campo monetário leva o alvo: principal inadimplente (M1), recuperado (M2)
    display(Markdown(f"**{t}: os k créditos de maior score**"), pd.DataFrame(a.metricas["topo"]).round(4))"""),
    ("md", """Os resultados do teste confirmam o que a validação indicou, e cada tarefa precisa ser lida pela própria pergunta. No M1, o modelo separa os inadimplentes bem acima da prevalência: a precisão nos 10% de maior risco fica perto de 70%, contra 37% de prevalência. A curva de calibração fica perto da diagonal em todos os decis do score, o que permite ler o score como probabilidade no conjunto do teste; essa leitura não se estende a cada grupo, porque, por quintil de renda, a média prevista se afasta da observada em vários pontos percentuais (seção 9). No M2, a ROC-AUC fica perto de 0,5 e o ganho de Brier sobre o preditor constante é praticamente nulo; o limiar de F1 máximo, escolhido na validação, degenera em prever quase todos os créditos como recuperáveis, e por isso a acurácia do M2 é baixa e o recall é alto. Esse quadro não é defeito do pipeline, mas a consequência esperada de uma simulação em que a recuperação não depende de nenhum atributo; para a dívida ativa simulada, a informação útil para priorizar está no valor da dívida, e o painel oferece a ordenação por valor esperado como opção distinta da ordenação por score."""),
    ("md", """## 9. Métricas por subgrupo para a Sprint 5

O enunciado pede guardar as métricas por faixa de renda e por região, porque a Sprint 5 fará a análise de equidade sobre elas. A renda e a região não entram nos atributos, mas o histórico de pagamento e o valor do imóvel carregam parte dessa informação; por isso, a tabela abaixo mostra, por quintil de renda do setor e por região, a prevalência, a taxa de positivos previstos e as taxas de erro. Uma disparidade é sinal para investigação, não certificado de injustiça (NIST AI RMF 1.0, DOI 10.6028/NIST.AI.100-1).

A tabela também mostra que a calibração do conjunto não garante a de cada grupo. No M1, a média prevista fica abaixo da prevalência observada nos quintis de menor renda e acima nos de maior renda, porque a simulação usa a renda e o modelo não a recebe. Van Calster et al. (2019, DOI 10.1186/s12916-019-1466-7) descrevem quatro níveis de calibração, cada um mais exigente que o anterior, e a calibração na média é o primeiro; a tabela mostra que nem ela nem a curva por decis do score garantem a calibração dentro de cada subgrupo."""),
    ("code", """subgrupos = pd.concat([a.subgrupos for a in avaliacoes.values()], ignore_index=True)
display(subgrupos.loc[subgrupos["tarefa"] == "M1"].round(4))
fig = figuras.subgrupos(subgrupos.loc[subgrupos["tarefa"] == "M1"], "quintil_renda",
                        "No M1, prevalência e positivos previstos caem do quintil de menor renda para o de maior",
                        "teste 2025 · por quintil de renda do setor (1 = menor renda) · insumo da Sprint 5")
display(Image(filename=figuras.salvar(fig, FIGURAS, "08_subgrupos_m1.png")))"""),
    ("md", """## 10. Pacote versionado e reprodutibilidade (E3)

O pacote reúne, para cada tarefa, o pipeline completo (imputação, escala, estimador e limiar), o contrato de atributos, as métricas, os metadados de linhagem e a ficha do modelo (Mitchell et al., 2019, DOI 10.1145/3287560.3287596), todos com SHA-256. O notebook grava o próprio pacote numa pasta de conferência e compara o hash de cada pipeline com o do pacote versionado em `models/sprint4/v1`, gerado por `treinar_sprint4.py`: se os bytes coincidem, o mesmo protocolo e a mesma base reproduziram o mesmo modelo. Em seguida, carrega o pacote versionado pela função que confere hash e versão do scikit-learn antes do `joblib.load`, porque a desserialização de pickle executa código e só pode ocorrer com arquivo de origem confiável (scikit-learn, "Model persistence")."""),
    ("code", """pacote.empacotar(ctx, CONFERENCIA, treinos, avaliacoes)
conferencia, versionado = artefatos.ler_checksums(CONFERENCIA), artefatos.ler_checksums(VERSIONADO)
for nome in ("inadimplencia.joblib", "recuperabilidade.joblib"):
    print(f"{nome:26s} notebook {conferencia[nome][:16]}… · versionado {versionado[nome][:16]}… · iguais: {conferencia[nome] == versionado[nome]}")
recarregado = artefatos.carregar_modelo(VERSIONADO, "inadimplencia.joblib")
X_teste = dados.matriz(divisoes["M1"].conjuntos.teste, p.m1.atributos)
print("previsões do pacote versionado iguais às do notebook:",
      np.allclose(modelos.probabilidades(recarregado, X_teste), modelos.probabilidades(treinos["M1"].final, X_teste), atol=1e-12))
display(Markdown((VERSIONADO / "model_card.md").read_text(encoding="utf-8").split("## M1")[0]))"""),
    ("md", """## 11. Do modelo ao painel (E4)

O painel não treina nem reajusta nada: ele lê o lote ativo publicado por `treinar_sprint4.py`, que pontua com o pacote conferido a carteira inscrita e aberta em 31/07/2026, cujo desfecho em 365 dias ainda é futuro. O lote só é gerado se a definição dos modelos no protocolo atual for a registrada no pacote, e só é lido depois de conferidos o manifesto, o hash de cada arquivo e os modelos do pacote aprovado. O manifesto registra versões, protocolo aplicado, faixas, mínimo de suporte, exclusões e a conciliação entre a soma por crédito e a soma por devedor sintético (hipótese declarada: 1 imóvel = 1 devedor sintético, que não representa pessoa real)."""),
    ("code", """from pipeline.ml import painel
lote = painel.carregar_lote(RAIZ / "reports" / "sprint4" / "lote", VERSIONADO)   # o mesmo caminho do painel
m2 = lote.manifesto["m2"]
print({k: m2[k] for k in ("fotografia", "horizonte_dias", "creditos", "devedores", "concilia")}, m2["exclusoes"])
proj = painel.projecao(lote.creditos)
print(f"principal em aberto {painel.reais(proj['principal_em_aberto_centavos'])} · valor esperado em 365 dias "
      f"{painel.reais(proj['valor_esperado_centavos'])} ({100 * proj['fracao_esperada']:.1f}%)")
display(painel.ranking(lote.devedores, "valor_esperado", 10))"""),
    ("md", """## 12. Conclusão

O padrão comum às duas tarefas é que o pipeline respeita o tempo e mede o que a base permite medir. Para o M1, a base simulada contém sinal no histórico do imóvel, e o modelo o captura: Average Precision perto de 0,61 contra 0,37 do preditor constante, com o mesmo desempenho na validação e no teste e probabilidades calibradas no conjunto do teste, mas não em cada quintil de renda. A proximidade entre validação e teste é compatível com a ausência de vazamento, sem prová-la, porque um vazamento que atingisse os dois conjuntos daria números igualmente próximos; a evidência está nas regras de disponibilidade dos atributos e no caso sentinela da seção 4. Para o M2, a simulação não contém sinal, e o modelo, corretamente, não o inventa. Em ambos os casos, as métricas valem para o mundo sintético da Sprint 3 e demonstram o funcionamento técnico, não a eficácia da cobrança em Palmas.

As limitações também seguem do desenho dos dados. O valor do lançamento corrente foi calibrado com a arrecadação real do próprio ano, e a renda vem do Censo 2022, publicado depois de parte dos exercícios simulados; por isso, esses campos ficaram fora dos atributos, e o experimento deve ser lido como validação temporal em dados sintéticos retrospectivos. Uma avaliação de eficácia exigirá dados reais autorizados, um período posterior e separado do desenvolvimento e revisão humana das decisões de cobrança.

**Referências citadas neste notebook** (DOIs conferidos no Crossref em 07/11/2026; lista completa em `docs/sprint4/REFERENCIAS.md`): Amershi et al. (2019); Breiman (2001); Brier (1950); Collins et al. (2024); Hastie, Tibshirani e Friedman (2009); Kapoor e Narayanan (2023); Kaufman et al. (2012); Mitchell et al. (2019); Morris, White e Crowther (2019); NIST (2023); Roberts et al. (2017); Saito e Rehmsmeier (2015); Studer et al. (2021); Van Calster et al. (2019); Varma e Simon (2006); documentação do scikit-learn 1.9.1 (Common pitfalls; Cross-validation; Model persistence)."""),
]


def montar() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = [nbformat.v4.new_markdown_cell(t) if tipo == "md" else nbformat.v4.new_code_cell(t) for tipo, t in CELULAS]
    return nb


def main(argv: list[str] | None = None) -> int:
    opcoes = argparse.ArgumentParser(description=__doc__)
    opcoes.add_argument("--sem-executar", action="store_true")
    args = opcoes.parse_args(argv)
    nb = montar()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    if not args.sem_executar:
        NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": str(RAIZ)}}).execute()
    nbformat.write(nb, DESTINO)
    print(f"notebook gravado em {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
