# E4 — Reprodutibilidade (15% da nota da sprint)

**Responsável:** _(nome)_

**O que o enunciado pede.** README atualizado: como executar o pipeline do zero, dependências, estrutura de pastas (bruto/limpo/pronto) e divisão de trabalho da equipe nesta sprint.

**O que a rubrica observa.** Reconstrói do zero seguindo só o README.

## Documentos desta pasta

Cópias de 26/10/2026; os originais ficam na pasta `PI2_Sprint3` e no repositório Git.

| Documento | Conteúdo |
|---|---|
| [README_do_projeto.md](README_do_projeto.md) | cópia do README.md da raiz, que é o próprio entregável E4 |
| [qualidade.md](qualidade.md) | resultado dos quality gates G1 a G14 |
| [mutacao.md](mutacao.md) | testes de mutação, com os mutantes sobreviventes |
| [rastreabilidade_historias.md](rastreabilidade_historias.md) | histórias de usuário × entregas da Sprint 3 |

## Código e dados no repositório

O código deste entregável não foi copiado para esta pasta, e a razão é técnica. Os quatro entregáveis são etapas de um único programa: `python etl_sefin.py` coleta (E1), transforma e carrega (E2) e gera a EDA (E3), e cada etapa importa módulos comuns e lê as camadas `data/bruto`, `data/limpo` e `data/pronto` que a etapa anterior produziu. Uma cópia do código aqui não rodaria sozinha e ficaria desatualizada na primeira correção; por isso, a tabela abaixo leva ao código no repositório, na pasta `PI2_Sprint3`, que é a versão que roda, que os testes conferem e que o avaliador lê no GitHub.

| Arquivo ou pasta | Papel |
|---|---|
| [`README.md`](../../PI2_Sprint3/README.md) | como executar do zero, dependências, pastas e divisão de trabalho (o entregável em si) |
| [`requirements.txt`](../../PI2_Sprint3/requirements.txt) | dependências de execução, com faixas de versão |
| [`requirements-dev.txt`](../../PI2_Sprint3/requirements-dev.txt) | dependências de testes e quality gates |
| [`.env.example`](../../PI2_Sprint3/.env.example) | modelo de configuração, sem credenciais |
| [`tests`](../../PI2_Sprint3/tests) | 780 testes: unitários, de integração com o MySQL e de aceitação em Gherkin |
| [`scripts/quality_gate.py`](../../PI2_Sprint3/scripts/quality_gate.py) | quality gates G1 a G14, inclusive a reprodutibilidade (G14) |
| [`scripts/mutacao.py`](../../PI2_Sprint3/scripts/mutacao.py) | testes de mutação (G10) |
| [`.github/workflows/qualidade.yml`](../../PI2_Sprint3/.github/workflows/qualidade.yml) | integração contínua: os gates a cada envio ao GitHub e a mutação toda segunda-feira |
