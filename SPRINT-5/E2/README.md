# E2 — Relatório de Impacto Algorítmico (RIA)

**Projeto Integrador II — BIINAR/UFT — 2026/2 — Grupo 1**

## 1. Objetivo

Esta entrega apresenta o Relatório de Impacto Algorítmico dos modelos M1 e M2 desenvolvidos no projeto de análise de créditos de IPTU.

O documento avalia aspectos de:

- Privacidade e proteção de dados conforme a LGPD;
- Equidade e possíveis vieses algorítmicos;
- Explicabilidade das previsões por meio de SHAP;
- Impactos sociais potenciais;
- Governança e recomendações para uso responsável.

## 2. Escopo da avaliação

A análise utiliza dados sintéticos de créditos e imóveis, associados a agregados públicos de setores censitários de Palmas/TO.

Os resultados possuem finalidade exclusivamente acadêmica e não autorizam a utilização dos modelos em decisões reais de cobrança tributária.

## 3. Estrutura da entrega

```text
E2/
├── README.md
├── codigo/
│   └── analise_shap_m1.py
├── documentacao/
│   ├── README.md
│   └── RELATORIO_IMPACTO_ALGORITMICO.md
└── resultados/
    ├── shap_summary_m1.png
    └── shap_waterfall_m1.png
```

## 4. Análise de explicabilidade

Foi utilizada a técnica SHAP para interpretar o comportamento do modelo M1.

Os resultados identificaram os atributos com maior contribuição média absoluta:

1. Inadimplência no exercício anterior;
2. Valor relativo anterior;
3. Quantidade de inadimplências anteriores.

Os gráficos gerados estão disponíveis na pasta `resultados/`.

## 5. Como reproduzir

Execute o projeto no ambiente Python/Google Colab, a partir da raiz do repositório.

```bash
python3 SPRINT-5/E2/codigo/analise_shap_m1.py
```

O script utiliza os dados e o modelo da Sprint 4 e gera os gráficos SHAP na pasta `SPRINT-5/E2/resultados/`.

Consulte o relatório completo para conhecer as dependências, metodologia, métricas e limitações da análise.

## 6. Documentação principal

O relatório completo está disponível em:

`documentacao/RELATORIO_IMPACTO_ALGORITMICO.md`

## 7. Limitação de uso
