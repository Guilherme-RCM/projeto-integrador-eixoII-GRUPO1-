# Validação da continuação — 16/11/2026

A integração das nove telas do Qt com o Streamlit foi concluída. Filtros de região, faixa e setor selecionam os mesmos devedores nas quatro telas da carteira; as escolhas persistem ao navegar. O ranking mostra os créditos do devedor e recebe o setor escolhido no mapa. A tela Sobre o modelo apresenta as matrizes M1 e M2.

| Verificação executada | Resultado |
|---|---|
| `python -m pytest -m "not integracao" -q` | 1.102 aprovados; 57 testes MySQL desmarcados; um teste FAISS pulado porque a biblioteca opcional não está instalada |
| Testes finais `test_painel.py` e `test_painel_qt.py` | 66 aprovados |
| `python scripts/verificar_filtros_painel.py` | 117/117 verificações sobre a carteira publicada |
| `lint-imports` | 13 contratos preservados |
| Pyright nos módulos compartilhados e aplicativo Streamlit | Zero erros no ambiente de execução |
| Navegador real, nove telas | Abertura e capturas conferidas |
| Download CSV com região NORTE | 760 créditos de 498 devedores; identificadores conferidos diretamente contra o lote |
| Integridade de `data/pronto`, `models/sprint4/v1` e `reports/sprint4/lote` | Todos os 20 arquivos mantiveram seus SHA-256 |

Os logs e hashes estão em [reports/sprint4/validacao_interface](../resultados/validacao_interface). A verificação de tipagem usou o interpretador do ambiente com Streamlit 1.67.0 e PySide6 6.12.0; o Python global não tem essas bibliotecas. Os relatórios anteriores de treino permanecem como registros da execução original.

As [capturas Qt](capturas_qt) e [capturas Streamlit](capturas_streamlit) documentam o conteúdo atual. Os dois PDFs de relatório foram regenerados e revisados. A matriz de confusão já existente no Qt continua conferida contra o lote. O Streamlit mantém o mesmo conteúdo, com a interação própria do navegador.

Não foram executados testes de integração com MySQL nem o teste opcional de FAISS. O arquivo do Figma ainda representa as cinco telas originais e a paleta anterior, conforme a pendência documentada em E4; não foi alterado nesta continuação.
