"""Base vetorial da Sprint 4: atributos normalizados, busca por similaridade cosseno e treino sobre os vetores.

censo → espaco → banco → modelos → experimento. A camada só lê arquivos: não acessa rede, banco
relacional nem a coleta (contrato no pyproject.toml); a coleta dos agregados do Censo 2022 fica em
scripts/coletar_censo_sociodemografia.py. Decisão registrada no ADR-ML-10 (docs/sprint4/ADRs.md).
"""
