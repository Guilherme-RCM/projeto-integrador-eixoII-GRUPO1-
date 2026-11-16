# M2-Cenários no projeto da Sprint 4

Esta pasta guarda o código e o protocolo do experimento M2-Cenários, copiados sem alteração da pasta em que ele rodou isolado (ADR-ML-12). O experimento responde a uma pergunta que o M2 do lote deixou aberta: o modelo de recuperabilidade não distingue devedores porque o método falha ou porque a simulação dá a mesma chance de pagamento a toda dívida? Para separar as duas hipóteses, os pagamentos posteriores à inscrição em dívida ativa foram simulados de novo em quatro cenários, e o mesmo procedimento de treino e avaliação foi aplicado a cada um.

O resultado confirma a segunda hipótese. No cenário sem sinal, que repete a regra do lote, nenhum modelo supera a previsão constante. No cenário de sinal moderado, a regressão logística alcança ROC-AUC de 0,783, e os 10% de créditos de maior score pagam 27,0%, contra 8,6% na carteira. No cenário em que a relação se inverte depois da validação, o mesmo modelo cai para ROC-AUC de 0,272. Os três resultados valem para as hipóteses simuladas; nenhum deles mede a recuperação real da dívida ativa de Palmas.

## O que há nesta pasta

| Arquivo | Papel | Registro |
|---|---|---|
| `PROTOCOLO.md`, `protocolo.json` | desenho do experimento: cenários, sementes, modelos, divisão temporal e critérios de aceite | SHA-256 gravado antes do treino |
| `m2_experimento.py`, `executar.py`, `verificar.py` | simulador e avaliação, execução completa e os 16 invariantes | SHA-256 gravado antes do treino |
| `relatar.py`, `auditar_resultados.py` | relatório e auditoria, escritos depois da execução; não treinam modelo | SHA-256 no manifesto da publicação |
| `REPRODUZIR.ps1`, `requirements.lock` | reprodução no ambiente fixado (Python 3.12) | SHA-256 no manifesto da publicação |
| `COMO_FUNCIONA.md`, `REFERENCIAS_DOI.md` | explicação em linguagem simples e respaldo bibliográfico do experimento | SHA-256 no manifesto da publicação |
| `README_ORIGINAL.md` | texto do experimento isolado, mantido como estava | SHA-256 no manifesto da publicação |

Os cinco arquivos das duas primeiras linhas formam o registro prévio do experimento. O executor gravou o SHA-256 de cada um em 15/11/2026, às 15h19 de Palmas, antes de conferir os invariantes e de ajustar o primeiro modelo; o teste `tests/ml/test_cenarios.py` confere que as cópias desta pasta têm os mesmos hashes. O `README_ORIGINAL.md` descreve a situação anterior à publicação. Onde ele afirma que nada foi integrado à Sprint 4, a afirmação continua verdadeira para os modelos: nenhum modelo do experimento entrou no pacote v1 nem no lote do painel.

## Onde estão os resultados

Os resultados ficam em `reports/sprint4/m2_cenarios`, com um manifesto que registra o SHA-256 de cada arquivo publicado.

- `experimento/` traz o que o experimento gravou: o aceite, a auditoria, as métricas das 80 réplicas, o resumo estatístico, as seleções, os invariantes, o relatório em HTML e em Markdown e as três figuras.
- `complementar/` traz o adendo exploratório, declarado em `configs/sprint4_m2_cenarios_adendo.yaml` depois do aceite e antes do cálculo: faixas pelos cortes do lote e por capacidade, ganhos acumulados, calibração, teto atingível e eventos no teste.
- As previsões por crédito (240 arquivos, 258 MB) e o exemplo da primeira semente permanecem na pasta do experimento isolado, porque pesam demais para a entrega. O manifesto guarda um SHA-256 agregado de cada conjunto, para que a origem possa ser conferida.

## Como ver no painel

```powershell
python -m app.qt                       # tela "Cenários do M2" (Ctrl+6)
streamlit run app/painel_sprint4.py    # aba "Cenários do M2"
```

As duas interfaces leem a publicação por `pipeline/ml/cenarios.py`, que confere o manifesto e os hashes antes de mostrar qualquer número. Se a publicação faltar ou tiver sido alterada, a tela mostra só a mensagem, e o restante do painel continua com o lote conferido. O relatório completo abre pelo botão da tela ou direto em `reports/sprint4/m2_cenarios/experimento/RELATORIO.html`.

## Como publicar de novo

```powershell
python scripts/publicar_m2_cenarios.py --origem <pasta do experimento isolado>
```

O script não treina modelo. Ele confere a cadeia de registro (código e protocolo iguais aos gravados antes do treino, execução concluída, origem preservada, auditoria aprovada e base analítica igual à do projeto), copia os arquivos, calcula o adendo sobre as previsões já gravadas e escreve o manifesto. Se algum item da cadeia não conferir, a publicação é recusada. Os SHA-256 do pacote v1 são conferidos antes e depois.

## Como reproduzir

A reprodução parcial roda com os testes do projeto e leva poucos segundos.

```powershell
python -m pytest tests/ml/test_cenarios.py
```

O teste executa o simulador congelado sobre `data/pronto/base_analitica_creditos.csv.gz` e confere, na primeira semente do cenário moderado, os números publicados: os créditos regenerados, os pagamentos gerados até o corte, o tamanho do teste, os pagamentos observados e o ROC-AUC da regressão logística e da referência ideal.

A reprodução completa refaz as 80 réplicas em cerca de dez minutos e exige a disposição de pastas do experimento isolado. O protocolo congelado lê a base no caminho relativo `../Envio ZI´P/Sprint 4 teste`; por isso, a pasta do experimento precisa ficar ao lado da pasta `Envio ZI´P`, que contém o projeto. Com essa disposição, `.\REPRODUZIR.ps1` cria o ambiente de `requirements.lock` e grava os resultados numa pasta nova, sem sobrescrever os anteriores. Trocar o caminho em `protocolo.json` altera o SHA-256 registrado, o que, pelo próprio protocolo, caracteriza um novo experimento.

## O que o experimento permite afirmar

O experimento permite afirmar três coisas. A primeira é que o M2 do lote não distingue devedores por causa do gerador dos dados, e não do procedimento de modelagem. A segunda é que o mesmo procedimento recupera um sinal quando ele existe e não acusa sinal quando ele não existe. A terceira é que um modelo validado deixa de servir quando a relação entre histórico e pagamento muda.

O experimento não permite afirmar que o M2 passou de 0,508 para 0,783 de ROC-AUC, porque os rótulos foram gerados de novo e a comparação não se faz sobre os mesmos pagamentos. Também não permite afirmar ganho de arrecadação, efeito de uma ação de cobrança nem o tamanho do sinal em Palmas: os coeficientes do simulador são hipóteses didáticas, escolhidas antes do treino. A seção 3.9 de `docs/sprint4/E2_modelos.md` traz a análise completa, com as referências.
