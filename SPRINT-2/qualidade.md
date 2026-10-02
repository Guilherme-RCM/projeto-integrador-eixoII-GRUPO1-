[qualidade.md](https://github.com/user-attachments/files/32973810/qualidade.md)
# Quality gates

Gerado por `python scripts/quality_gate.py` em 01/10/2026 12:33. Nenhuma integração na `main` é aceita com gate reprovado.

| Gate | Verificação | Limite | Obtido | Situação |
|---|---|---|---|---|
| G1 | Testes unitários | 100% passando, nenhum ignorado | 217/217 | ✅ passou |
| G2 | Testes de integração (MySQL) | 100% passando, nenhum ignorado | 32/32 | ✅ passou |
| G3 | Testes de aceitação (Gherkin) | 100% passando, nenhum ignorado | 15/15 | ✅ passou |
| G4 | Cobertura de linhas e ramos | total ≥ 90%, cada módulo ≥ 80% | 98.1% | ✅ passou |
| G5 | Complexidade ciclomática | ≤ 10 por função | máx. 8 (componentes_sem_pai), média 2.8 | ✅ passou |
| G6 | Índice de manutenibilidade | ≥ 20 por módulo | mín. 43.1 (parser.py) | ✅ passou |
| G7 | Tamanho de módulos e funções | módulo ≤ 250 SLOC, função ≤ 50 linhas | maior módulo 202 SLOC; maior função 31 linhas | ✅ passou |
| G8 | Controle de dependências (import-linter) | todos os contratos mantidos | 4/4 contratos | ✅ passou |
| G9 | Verificação de tipos (Pyright) | 0 erros no código de produção | 0 erro(s) | ✅ passou |
| G10 | Testes de mutação | score ≥ 80% em cada módulo | 93.0% (816/877 mortos, nesta rodada) | ✅ passou |
