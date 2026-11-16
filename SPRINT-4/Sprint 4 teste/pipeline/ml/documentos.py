"""Ficha do modelo (model card) gerada a partir dos metadados e das métricas medidas.

A estrutura segue Mitchell et al. (2019, DOI 10.1145/3287560.3287596): detalhes,
uso pretendido, fatores, métricas, dados, análises quantitativas, considerações
éticas e ressalvas. Os números vêm dos arquivos da execução, e as frases que dependem
do resultado (por exemplo, se o modelo supera o preditor constante) são escolhidas a
partir dele, para que a ficha nunca afirme o que a medição não sustentou.
"""
from __future__ import annotations

import pandas as pd


def _pct(valor: float | None) -> str:
    return "n/d" if valor is None else f"{100 * valor:.1f}%".replace(".", ",")


def _num(valor: float | None, casas: int = 3) -> str:
    return "n/d" if valor is None else f"{valor:.{casas}f}".replace(".", ",")


def _tabela_comparacao(comparacao: pd.DataFrame, tarefa: str) -> str:
    linhas = ["| Modelo | AP | ROC-AUC | Brier | F1 | Escolhido |", "|---|---|---|---|---|---|"]
    teste = comparacao.loc[(comparacao["tarefa"] == tarefa) & (comparacao["conjunto"] == "teste")]
    for _, r in teste.iterrows():
        linhas.append(f"| {r['modelo']} | {_num(r['average_precision'])} | {_num(r['roc_auc'])} | "
                      f"{_num(r['brier'], 4)} | {_num(r['f1'])} | {'sim' if r['escolhido'] else ''} |")
    return "\n".join(linhas)


def _secao_tarefa(tarefa: str, m: dict, met: dict, comparacao: pd.DataFrame) -> str:
    c, pr = met["classificacao"], met["probabilidade"]
    supera = m["selecao"]["supera_referencia"]
    leitura = (f"O modelo escolhido supera o preditor constante (Dummy) na validação por mais de um erro-padrão, "
               f"e por isso o ganho medido não se explica só pela variação amostral." if supera else
               f"O modelo escolhido não supera o preditor constante (Dummy) por mais de um erro-padrão na validação; "
               f"por conseguinte, os scores desta tarefa não ordenam os créditos melhor que a prevalência do treino, "
               f"e o resultado é publicado como achado, sem alteração do simulador.")
    return f"""## {tarefa} — {m['pergunta']}

O {tarefa} usa a família `{m['familia']}` com os hiperparâmetros `{m['hiperparametros']}`, escolhida na validação pela regra de um erro-padrão, e responde a uma pergunta delimitada: {m['pergunta']} A população é formada por {m['populacao']}, o momento da decisão é {m['t0']} e a classe positiva é {m['classe_positiva']}. {leitura}

No teste congelado, com limiar {_num(m['limiar'])} fixado na validação, o modelo obteve acurácia {_pct(c['acuracia'])}, precisão {_pct(c['precisao'])}, recall {_pct(c['recall'])} e F1 {_num(c['f1'])}, sobre n = {c['n']} créditos com prevalência {_pct(c['prevalencia'])}; a matriz de confusão é [[VN, FP], [FN, VP]] = {c['matriz_confusao']}. As probabilidades tiveram Average Precision {_num(pr['average_precision'])}, ROC-AUC {_num(pr['roc_auc'])}, Brier {_num(pr['brier'], 4)} e ganho de Brier sobre o preditor constante de {_pct(pr['ganho_brier_sobre_constante'])}, o que mede quanto o modelo melhora a probabilidade que a simples prevalência do treino daria.

{_tabela_comparacao(comparacao, tarefa)}
"""


def ficha_modelo(meta: dict, metricas: dict[str, dict], comparacao: pd.DataFrame) -> str:
    """Model card em Markdown, com os números da execução registrada nos metadados."""
    corpo = "\n".join(_secao_tarefa(t, meta["modelos"][t], metricas[t], comparacao) for t in sorted(meta["modelos"]))
    return f"""# Ficha do modelo — {meta['versao_modelo']}

> Gerada por `pipeline/ml/documentos.py` na execução `{meta['execucao']}` (código `{meta['codigo']['commit']}`, protocolo {meta['versao_protocolo']}). Dados individuais **sintéticos**: as métricas demonstram que o pipeline funciona, não que o modelo funciona no mundo real.

## Detalhes e uso pretendido

O pacote contém dois classificadores independentes, porque inadimplência e recuperabilidade diferem em população, momento de decisão e horizonte, e usar 1 − P(inadimplência) como recuperabilidade misturaria perguntas diferentes. Os dois são pipelines do scikit-learn {meta['ambiente']['scikit-learn']} (imputação pela mediana do treino com indicador de ausência, escala só na logística e estimador), treinados com semente {meta['semente']} em Python {meta['ambiente']['python']}. O uso pretendido é apoio ao analista da Sefin em demonstração acadêmica: o M1 alimenta o mapa de risco e o M2 ordena a carteira de dívida ativa; nenhum dos dois decide cobrança, e nenhum deve ser usado com dados reais sem homologação, base legal e revisão humana.

## Fatores, dados e limites

Os dados de treino e de teste são créditos de IPTU simulados sobre os setores censitários reais de Palmas (base da Sprint 3, `{meta['dados']['versao_dados']}`, simulação `{meta['dados']['simulacao']['assinatura'][:12]}`), e essa origem limita o que as métricas significam. A simulação usa probabilidade anual constante de recuperação depois da inscrição e calibra o valor lançado com a arrecadação real do próprio ano; por isso, o valor do lançamento corrente, a renda do Censo 2022 e os identificadores territoriais ficaram fora dos atributos, e a renda e a região foram guardadas só para a auditoria por subgrupo da Sprint 5. O valor relativo do imóvel continua como atributo e é um substituto (proxy) da renda do setor, de modo que retirar a renda direta não demonstra equidade.

{corpo}
## Considerações éticas e recomendações

Um score de risco aplicado a contribuintes pode concentrar a cobrança em grupos de menor renda, mesmo sem a renda entre os atributos, porque o histórico de pagamento e o valor do imóvel carregam essa informação. Por esse motivo, as predições do teste ficam guardadas com a faixa de renda e a região (`reports/sprint4/predicoes_*.csv.gz` e `metricas_subgrupos.csv`), e a análise da Sprint 5 deve tratar uma disparidade como sinal para investigação, não como certificado de injustiça ou de conformidade (NIST AI RMF 1.0, DOI 10.6028/NIST.AI.100-1). Antes de qualquer uso real, o modelo precisa de dados autorizados, avaliação prospectiva em período posterior e separado do desenvolvimento, e de um responsável pela aprovação, revisão e suspensão do modelo.
"""
