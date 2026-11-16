# M2-Cenários — experimento local isolado

Abra `resultados/RELATORIO.html` para o relatório visual autocontido ou `resultados/RELATORIO.md` para a versão em texto. O veredito calculado, com todos os critérios, fica em `resultados/aceite.json`. A auditoria dos artefatos fica em `resultados/auditoria_final.json`.

Este experimento foi autorizado para avaliar uma alternativa acadêmica com simulação transparente. Não altera, importa ou integra o código/modelos da Sprint 4. A origem `../Envio ZI´P/Sprint 4 teste` é lida e inventariada por SHA-256 antes e depois. A confirmação se encontra em `resultados/integridade_origem.json` e nos inventários completos.

O protocolo foi escrito antes de avaliar os novos modelos. Usa 20 sementes fixas em quatro cenários, com hiperparâmetros fixos e seleção exclusiva na validação. O registro antes do primeiro ajuste guarda os hashes do protocolo e do código existente naquele momento. Relatório e auditor final foram acrescentados como utilitários de apresentação/conferência; não participam do treinamento.

## O que muda na simulação

O cadastro de imóveis e créditos já é sintético. Mantemos seus vencimentos, inscrições e pagamentos antes da inscrição. Regeneramos todos os pagamentos posteriores à inscrição com probabilidades heterogêneas baseadas em históricos conhecidos na inscrição. Os novos históricos são reconstruídos dos eventos, não inventados como observações reais. A variável latente de heterogeneidade é ocultada dos modelos. O cenário nulo conserva 12% iguais para todos; os cenários fraco e moderado variam os efeitos; o cenário de mudança inverte os efeitos observáveis depois do período de validação.

Assim, um ganho no novo cenário **não é melhoria comprovada sobre os rótulos originais nem validação em contribuintes reais**. É um teste controlado de capacidade preditiva e de robustez sob hipóteses explicitadas. Não altere coeficientes ou sementes para conseguir um resultado melhor. Mudanças científicas exigem outro protocolo, outra saída e identificação como novo experimento.

## Reproduzir

Requer Python 3.12 e as versões de `requirements.lock`. O ambiente `.venv` já foi preparado localmente. Pelo PowerShell, dentro desta pasta:

```powershell
.\REPRODUZIR.ps1
```

O script cria uma nova pasta de saída com data e hora; não sobrescreve `resultados`. Alternativamente:

```powershell
.\.venv\Scripts\python.exe -B executar.py --saida reproducao_manual
.\.venv\Scripts\python.exe -B relatar.py --saida reproducao_manual
.\.venv\Scripts\python.exe -B auditar_resultados.py --saida reproducao_manual
```

Para executar somente as verificações de temporalidade e eventos:

```powershell
.\.venv\Scripts\python.exe -B verificar.py
```

O código recusa saídas fora desta pasta ou já existentes. A origem é configurada em `protocolo.json`; se a pasta inteira for transportada, copie também o arquivo de dados da origem ou ajuste o caminho em um novo protocolo. Os modelos `.joblib` são artefatos locais de demonstração e devem ser carregados somente de origem confiável.

## Artefatos

- `PROTOCOLO.md` e `protocolo.json`: desenho experimental, hipóteses, sementes, modelos, divisão temporal e critérios de aceite.
- `m2_experimento.py`: geração de eventos, fotografias, modelos e métricas.
- `executar.py`: execução completa com registro anterior ao treinamento e conferência da origem.
- `verificar.py`: casos de teste relevantes, incluindo sentinelas de futuro, independência dos pagamentos antigos, censura e datas coerentes.
- `resultados/metricas_replicas.csv`: todos os métodos, cenários, sementes e partições; nenhuma réplica omitida.
- `resultados/resumo_estatistico.csv`: médias, desvios, mínimos, máximos, erro Monte Carlo e IC95 da média.
- `resultados/predicoes/`: previsões e rótulos de cada réplica; identificação sintética usada apenas para auditoria.
- `resultados/selecao/`: decisão de cada réplica gravada antes de medir o teste.
- `resultados/exemplo_primeira_semente/`: eventos, fotografias e modelos da primeira semente, predefinida e não escolhida por desempenho.
- `resultados/bootstrap_primeira_semente.json`: IC pareado por imóvel para a primeira réplica.
- `resultados/figuras/`: gráficos PNG exportáveis.
- `resultados/auditoria_final.json`: reconferência de todas as previsões, escolhas, serializações e hashes.

Não confundir o IC da média de 20 réplicas (erro Monte Carlo condicionado ao cadastro) com um intervalo de generalização para dados reais. A comparação por valor não estima o efeito de uma ação de cobrança. O cenário de mudança é publicado mesmo quando o resultado é desfavorável.

Referências metodológicas e interpretação dos resultados estão no protocolo e no relatório. A instalação de dependências e os treinamentos ocorreram somente no ambiente desta pasta.
