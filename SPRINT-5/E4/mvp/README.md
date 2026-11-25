# Componente A — Artefatos Executáveis do MVP (`sprint4-v1`)

**Este subdiretório reúne os artefatos executáveis, os modelos serializados e o lote assinado criptograficamente que compõem o Componente A (MVP) do Portfólio Revisado.** Na arquitetura de engenharia do Grupo 1, as aplicações gráficas são estritamente desacopladas do treinamento: tanto a interface principal de mesa em Qt (`app/qt`) quanto a interface web de contingência em Streamlit (`app/painel_sprint4.py`) operam em modo somente leitura sobre a mesma camada de negócios (`codigo/painel.py`) e validam os hashes **SHA-256** do lote ativo e do pacote `sprint4-v1` antes de apresentar qualquer indicador. A documentação técnica completa, as nove telas e a conciliação contábil em centavos encontram-se detalhadas em [`../docs/MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md`](../docs/MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md).

---

## Conteúdo Verificável desta Pasta

| Subpasta | Artefatos Reunidos | Papel no Componente A (MVP) |
|---|---|---|
| `app/qt/` | `janela.py`, `telas.py`, `mapa.py`, `graficos.py`, `componentes.py`, `tema.py`, `servico.py`, fontes `Raleway` | Interface principal Desktop concebida segundo `@govbr-ds/core`, contraste `WCAG 2.2` e 10 heurísticas de Nielsen. |
| `app/painel_sprint4.py` | Aplicação Streamlit e `.streamlit/config.toml` | Interface web de reserva homologada com paridade integral de números, filtros e avisos éticos. |
| `codigo/` | `painel.py`, `lote.py`, `publicacao.py`, `artefatos.py`, `inferencia.py`, `config.py`, `sprint4.yaml`, `requirements*.txt` | Regras compartilhadas de leitura coordenada, conciliação em centavos, supressão territorial (`< 10` imóveis) e publicação atômica. |
| `modelos/v1/` | `inadimplencia.joblib`, `recuperabilidade.joblib`, `metadata.json`, `feature_contract.json`, `metrics.json`, `model_card.md`, `checksums.sha256` | Pacote oficial congelado `sprint4-v1` auditado na Sprint 5 pelo [Model Card](../docs/MODEL_CARD.md) e pelo [RIA](../docs/RELATORIO_IMPACTO_ALGORITMICO.md). |
| `resultados/lote/` | `ativo.json` e lote `20261108T042152-6f13fb/` (`manifesto.json`, `devedores_m2.csv.gz`, `creditos_m2.csv.gz`, `risco_m1.csv.gz`, `setores.geojson`) | Carteira sintética demonstrativa (`78.122` créditos, `52.510` devedores, `R$ 60.118.722,19` em aberto e `R$ 6.948.081,53` esperado em 365d). |
