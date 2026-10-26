# Quality gates

Gerado por `python scripts/quality_gate.py` em 21/10/2026 07:07. Nenhuma integração na `main` é aceita com gate reprovado.

| Gate | Verificação | Limite | Obtido | Situação |
|---|---|---|---|---|
| G1 | Testes unitários | 100% passando, nenhum ignorado | 689/689 | ✅ passou |
| G2 | Testes de integração (MySQL) | 100% passando, nenhum ignorado | 45/45 | ✅ passou |
| G3 | Testes de aceitação (Gherkin) | 100% passando, nenhum ignorado | 15/15 | ✅ passou |
| G4 | Cobertura de linhas e ramos | total ≥ 90%, cada módulo ≥ 80% | 99.3% | ✅ passou |
| G5 | Complexidade ciclomática | ≤ 10 por função | máx. 10 (gravado_hoje), média 2.9 | ✅ passou |
| G6 | Índice de manutenibilidade | ≥ 20 por módulo | mín. 34.7 (secoes_receita.py) | ✅ passou |
| G7 | Tamanho de módulos e funções | módulo ≤ 250 SLOC, função ≤ 50 linhas | maior módulo 202 SLOC; maior função 36 linhas | ✅ passou |
| G8 | Controle de dependências (import-linter) | todos os contratos mantidos | 9/9 contratos | ✅ passou |
| G9 | Verificação de tipos (Pyright) | 0 erros no código de produção | 0 erro(s) | ✅ passou |
| G10 | Testes de mutação | score ≥ 80% em cada módulo | 93.7% (2576/2748 mortos, resultado de 21/10/2026 06:54) | ✅ passou |
| G11 | Desempenho das consultas do painel (RNF-04) | P95 ≤ 3 s por consulta | pior P95 1.38 s (mapa por setor) | ✅ passou |
| G12 | Qualidade dos dados da última execução | 100% das impeditivas; banco = arquivos | 33/33 impeditivas; banco = arquivos (execução 20261021T065740-9b9054) | ✅ passou |
| G13 | Referências com DOI conferido no Crossref | todos os DOIs da bibliografia | 0/52 DOIs conferidos no cache; sem conferência: ['alm2014', 'alm2016', 'waldhart2012', 'chirico2019', 'allingham1972', 'slemrod2019', 'wang1996', 'batini2009', 'pipino2002', 'vassiliadis2009', 'wickham2014', 'schelter2018', 'polyzotis2018', 'sandve2013', 'wilson2017', 'wilkinson2016', 'buneman2001', 'simmhan2005', 'gebru2021', 'krotov2020', 'fielding2002', 'metcalfe1976', 'rfc9309', 'rfc9110', 'rfc6585', 'rfc8996', 'rfc8446', 'rfc7946', 'rfc4180', 'kaufman2012', 'dougherty1995', 'cleveland1984', 'anscombe1973', 'mcgill1978', 'weissgerber2015', 'brewer2002', 'robinson1950', 'moran1950', 'fotheringham1991', 'lam1983', 'sweeney2002', 'limpert2001', 'morris2019', 'box1976', 'hosmer2013', 'drechsler2011', 'persons1919', 'parnas1972', 'garlan1993', 'perry1992', 'mccabe1976', 'demillo1978'] | ❌ falhou |
| G14 | Reprodutibilidade das camadas limpo e pronto | mesmos bytes em duas transformações | 17/17 arquivos idênticos (bruto real) | ✅ passou |

## G11 — detalhes

- `mapa por setor: P95 1.376 s`
- `faixas de valor: P95 0.687 s`
- `receita real anual: P95 0.003 s`
- `indicadores: P95 0.002 s`
- `condições: 556260 créditos simulados; 30 repetições por consulta, uma de cada vez (concorrência 1); cache aquecido; MySQL local, sem latência de rede; Windows-11-10.0.26200-SP0, 12 CPUs lógicas`

## G13 — detalhes

- `0/52 DOIs conferidos no cache; sem conferência: ['alm2014', 'alm2016', 'waldhart2012', 'chirico2019', 'allingham1972', 'slemrod2019', 'wang1996', 'batini2009', 'pipino2002', 'vassiliadis2009', 'wickham2014', 'schelter2018', 'polyzotis2018', 'sandve2013', 'wilson2017', 'wilkinson2016', 'buneman2001', 'simmhan2005', 'gebru2021', 'krotov2020', 'fielding2002', 'metcalfe1976', 'rfc9309', 'rfc9110', 'rfc6585', 'rfc8996', 'rfc8446', 'rfc7946', 'rfc4180', 'kaufman2012', 'dougherty1995', 'cleveland1984', 'anscombe1973', 'mcgill1978', 'weissgerber2015', 'brewer2002', 'robinson1950', 'moran1950', 'fotheringham1991', 'lam1983', 'sweeney2002', 'limpert2001', 'morris2019', 'box1976', 'hosmer2013', 'drechsler2011', 'persons1919', 'parnas1972', 'garlan1993', 'perry1992', 'mccabe1976', 'demillo1978']`
