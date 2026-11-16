"""Camada de aprendizado de máquina da Sprint 4 (ADR-ML-01).

Fluxo: base da Sprint 3 → fotografias em t0 (dados) → conjuntos temporais (divisao)
→ candidatos e busca (modelos) → avaliação (avaliacao) → pacote versionado
(artefatos) → pontuação em lote (inferencia) → leitura do painel (painel).

Treino e inferência ficam separados: `inferencia` e `painel` não importam `modelos`,
regra verificada pelo import-linter, de modo que o painel nunca treina nem reajusta
um transformador. Todos os créditos e imóveis da base são sintéticos (ADR-003 da Sprint 3).
"""
