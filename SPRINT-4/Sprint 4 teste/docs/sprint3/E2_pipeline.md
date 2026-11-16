# E2 — Pipeline ETL de ponta a ponta

Código: `etl_sefin.py` e `pipeline/` · Execução de referência: `20261021T065740-9b9054` (21/10/2026, código `ea64aa6`): extract 57 s, transform 12 s, load 140 s, EDA 4 s; 33 de 33 validações impeditivas aprovadas; código de saída 0.

## 1. Arquitetura: pipes e filtros

O pipeline foi organizado como uma sequência de filtros independentes que só conversam pelos dados, porque cada fonte e cada regra mudam em ritmos diferentes. No estilo de pipes e filtros, cada filtro recebe uma entrada, produz uma saída e não conhece os demais (Garlan; Shaw, 1993; Valente, 2020, §7.7); assim, a limpeza da arrecadação pode mudar sem tocar no cruzamento territorial, e um filtro pode ser testado sozinho, com dados montados à mão. Parnas (1972) já recomendava decompor um sistema pelas decisões que tendem a mudar, e não pelas etapas do fluxograma; por isso, há um módulo por fonte na limpeza e um por assunto no enriquecimento.

A independência entre os filtros não é só uma intenção, e sim um contrato verificado a cada integração. O `import-linter` mantém nove contratos (gate G8): os filtros de limpeza, enriquecimento, simulação e atributos não importam rede, banco nem coleta; os filtros não importam uns aos outros; a coleta não conhece a transformação; e a EDA só lê as camadas. Perry e Wolf (1992) definem a arquitetura também pelas restrições que ela impõe, e esses contratos são exatamente as restrições do estilo escolhido (ADR-001).

```
fontes ─► extract (pipeline/coleta) ─► data/bruto + manifesto
                                          │
                     transform: limpar ─► [V01–V06, V12] ─► enriquecer ─► [V07–V08]
                                          ─► simular + atributos ─► [V09–V11] ─► data/limpo, data/pronto
                                          │
                     load (pipeline/carga) ─► MySQL da Sprint 2 (transacional, idempotente)
                                          │
                     EDA (pipeline/eda) ─► docs/sprint3/EDA.md, GALERIA.md, figuras/
```

## 2. O script único: `etl_sefin.py`

O script expõe as três funções pedidas, `extract`, `transform` e `load`, orquestradas por um `main`, e delega o trabalho a uma fachada. A fachada (`pipeline/orquestrador.py`; Valente, 2020, §6.6) abre o log da execução, registra o início e o fim no banco e transforma cada falha num código de saída, de modo que o script continue curto e legível. Os códigos são 0 (sucesso), 2 (validação de qualidade reprovada), 3 (falha de coleta) e 1 (outro erro), o que permite a um agendador distinguir um servidor fora do ar de um dado inválido (apostila de ETL, §12.3).

| Comando | Efeito |
|---|---|
| `python etl_sefin.py` | coleta o que falta hoje, transforma, carrega no MySQL e gera a EDA |
| `python etl_sefin.py --offline` | não acessa a rede: transforma a última coleta completa de cada fonte |
| `python etl_sefin.py --sem-banco` | para em `data/limpo` e `data/pronto` |
| `python etl_sefin.py --recoletar` | pede tudo de novo às fontes, mesmo o já coletado hoje |
| `python etl_sefin.py --sem-eda` | não gera o relatório de EDA |
| `--nucleogov-arquivo CAMINHO` | cópia local da extração NUCLEOGOV (padrão: `PI2_NUCLEOGOV_ARQUIVO`) |
| `--nucleogov-github` | baixa a extração NUCLEOGOV do repositório da coordenação |
| `--nucleogov-api` | receita pela API do portal NUCLEOGOV (manual de coleta da coordenação, §3), com o agente declarado em `PI2_NUCLEOGOV_USER_AGENT`, em vez da extração |

## 3. Limpeza, enriquecimento e atributos

A limpeza transforma cada fonte numa tabela tipada e conta tudo o que entra e sai. Cada filtro devolve as linhas aceitas, as rejeitadas com o motivo (a quarentena) e as descartadas por duplicidade idêntica, e a identidade lidos = aceitos + rejeitados + descartados é exigida para todas as fontes (validação V02; apostila de ETL, §10.2). As decisões de cada fonte, com justificativa e efeito, estão no [registro de decisões](limpeza_decisoes.md).

O enriquecimento com o IBGE leva a renda do Censo 2022 até a unidade territorial da análise. A renda do responsável, os moradores e os domicílios de cada setor censitário (Censo 2022) são ligados à malha de setores do WFS e cruzados com as quadras do GeoPalmas pela área de interseção; cada setor recebe densidade, logaritmo da renda, escore-z e quintil, e cada quadra recebe estimativas por interpolação areal (Lam, 1983). Na execução de referência, 733 setores e 283 quadras formaram 1.635 pares, e 94,2% dos domicílios ficaram em setores com quadra do GeoPalmas.

A engenharia de atributos produz, por crédito, os três atributos pedidos na Sprint 3 e o histórico de pagamento. O tempo de inadimplência conta os dias entre o vencimento e o pagamento, ou até a data de corte; a sazonalidade entra como o mês, o trimestre e o índice sazonal real do mês de vencimento; as faixas de valor usam limites legíveis por um gestor. Como alguns desses atributos só são conhecidos depois do vencimento, o [dicionário da base analítica](dicionario_base_analitica.md) classifica cada coluna pelo momento em que ela fica disponível, para evitar vazamento de informação no modelo da Sprint 4 (Kaufman et al., 2012).

A inadimplência por imóvel é simulada, porque nenhuma fonte pública contém dívida por contribuinte. A simulação distribui os 111.252 imóveis tributáveis de Palmas pelos setores urbanos reais, na proporção dos domicílios, e decide quem atrasa com um modelo logístico cuja direção vem da literatura (Alm et al., 2014) e cuja intensidade é premissa declarada (ADR-003). Todos os créditos simulados levam `origem_dado = SINTETICO`, ficam em tabelas próprias no banco e aparecem marcados como simulados em todos os gráficos.

## 4. Validações de qualidade

As validações são avaliadas entre os filtros, e um filtro nunca recebe uma entrada já reprovada. Cada regra devolve um resultado com a dimensão de qualidade, a etapa e a evidência numérica; todas as regras de um bloco são avaliadas e registradas, e só então, se alguma impeditiva reprovou, o pipeline para com `ErroQualidade` (código 2) e nada é gravado em `data/limpo`, `data/pronto` ou no banco. Esse desenho segue a recomendação de classificar as regras em impeditivas e informativas e de nunca publicar em silêncio uma redução da população (apostila de ETL, §10.3), e se aproxima da verificação declarativa de qualidade que Schelter et al. (2018) propõem para dados que alimentam modelos.

| Regra | Dimensão (Wang; Strong, 1996; Batini et al., 2009) | Etapa | O que exige | Tipo |
|---|---|---|---|---|
| V01 | completude | coleta | coleta completa e com o total anunciado | impeditiva |
| V02 | consistência | limpeza | lidos = aceitos + rejeitados + descartados | impeditiva |
| V03 | validade | limpeza | no máximo 1% de rejeições por fonte | impeditiva |
| V04 | unicidade | limpeza | chaves naturais sem repetição | impeditiva |
| V05 | validade | limpeza | contrato do NUCLEOGOV e do Censo (colunas e tipos) | impeditiva |
| V06 | consistência | limpeza | conta-pai igual à soma dos quatro componentes | impeditiva |
| V07 | completude | enriquecimento | IPCA contínuo e com índice para toda competência da receita | impeditiva |
| V08 | integridade | enriquecimento | todo setor do Censo existe na malha | impeditiva |
| V09 | consistência | atributos | cruzamento crédito × imóvel × setor sem perda nem multiplicação de linhas | impeditiva |
| V10 | exatidão | simulação | taxa simulada igual ao alvo ± 0,5 ponto | impeditiva |
| V11 | validade | atributos | faixas e meses dentro do domínio | impeditiva |
| V12 | integridade | coleta | cadeia de hashes do manifesto e arquivos conferidos | impeditiva |
| I01 | atualidade | coleta | IPCA com no máximo 120 dias de defasagem | informativa |
| I02, I03 | completude | enriquecimento | cobertura das quadras; setores sob sigilo | informativa |
| I04, I05 | consistência | enriquecimento | linhas antes e depois da unificação da receita e do cruzamento setor × quadra | informativa |

As validações têm testes que as reprovam de propósito, e não apenas testes que as veem passar. Na mini-Palmas usada pelos testes, uma rejeição de 1 em 14 registros interrompe a execução com V03, um arquivo do Censo sem a coluna V06004 interrompe com V05, um setor do Censo fora da malha interrompe com V08 e um bruto adulterado é recusado antes da leitura (`tests/test_transformacao.py`, `tests/test_orquestrador.py`). Por conseguinte, cada validação demonstrou ao menos uma vez que interrompe a execução quando deve.

## 5. Log da execução

O log conta a história da execução numa linha por evento, e cada linha leva o identificador da execução. O identificador (por exemplo, `20261021T065740-9b9054`) é ordenável pela data e aparece em todas as linhas do `logs/etl_<id>.log`, no registro `execucao_pipeline` do banco e no relatório de qualidade, o que liga as três evidências (Simmhan; Plale; Gannon, 2005). Cada etapa registra início, fim, duração e contagens; cada requisição registra status, tamanho, tempo de transferência e pausa de cortesia; e cada validação registra o resultado e a evidência no momento em que é avaliada, inclusive as contagens antes e depois de cada cruzamento.

```
… pipeline: início da etapa transform
… pipeline: validação V02-reconciliacao-arrecadacao-api ok [consistencia, impeditiva] lidos 3542 = aceitos 3542 + rejeitados 0 + descartados 0
… pipeline: validação I05-cruzamento-setor-quadra ok [consistencia, informativa] 733 setores × 283 quadras → 1635 pares com interseção de pelo menos 1 m²
… pipeline: validação V09-cardinalidade-base-analitica ok [consistencia, impeditiva] 556260 linha(s) antes, 556260 depois do cruzamento
… pipeline: fim da etapa transform em 11.7 s · validacoes=33/33 impeditivas · creditos_simulados=556260 · receita=2055
```

O log não contém senha, token, caminho local nem dado pessoal. As variáveis sensíveis (`DB_PASSWORD`, `GITHUB_TOKEN`, `PSEUDONIMO_CHAVE`, `PI2_TOKEN_API`) são mascaradas por um filtro mesmo que algum código as escreva por engano, e do arquivo NUCLEOGOV local entra só o nome, nunca o caminho do computador (apostila de ETL, §12.2). O log completo da execução de referência está em [evidencias/etl.log](evidencias/etl.log).

## 6. Carga no banco da Sprint 2

A carga é transacional e idempotente, porque uma execução repetida não pode duplicar dados nem deixar o banco pela metade (RNF-06). Os dados reais (manifesto do bruto, IPCA, arrecadação, receita, setores, renda, quadras, cruzamento e indicadores) entram numa transação; a simulação entra noutra, uma única vez por assinatura de parâmetros; e a receita NUCLEOGOV completa, no CSV do layout da extração oficial, venha ele da API do portal ou da própria extração, entra no módulo A da Sprint 2 como snapshot identificado pelo SHA-256, com a origem e a data da coleta na descrição. As estratégias seguem a apostila de ETL (§7.1): inserção que ignora o já existente para o bruto, UPSERT pela chave natural para as tabelas de estado, dimensão de vigência (SCD tipo 2) para as quadras e substituição completa, dentro da transação, para o cruzamento e os indicadores.

O registro da execução fica fora das transações da carga, para que uma falha continue registrada mesmo quando a carga é desfeita. A linha de `execucao_pipeline` é gravada antes da carga e atualizada no fim, com a situação, o resumo e todas as validações em `validacao_execucao` (apostila de ETL, §16.7). Os testes de integração exercitam esse comportamento: uma queda simulada entre o DELETE e o INSERT dos indicadores deixa o banco exatamente como estava, e uma execução reprovada aparece como FALHA, com a regra que a reprovou.

Os valores derivados continuam fora das tabelas, como decidido na Sprint 2, e as views que os calculam são conferidas contra o Python. O valor real (`v_receita_real`), os atributos da base analítica (`v_credito_atributos` e `v_base_analitica_credito`) e os agregados do painel (`v_inadimplencia_setor` e `v_faixa_valor_simulacao`) são views; um teste diferencial compara cada uma com o resultado do pipeline e exige igualdade ao centavo ou ao dia. A execução de referência também completou a carga das 176.993 linhas do NUCLEOGOV que ficara pendente na Sprint 2 (snapshot 2, publicado, com 1.092 componentes e nenhuma divergência).

## 7. Desempenho e reprodutibilidade

As consultas agregadas do painel atendem ao RNF-04, e a medição declara as condições em que foi feita. Com 556.260 créditos simulados no banco, o pior P95 entre 30 execuções foi de 1,38 s (mapa por setor), abaixo do limite de 3 s ([evidencias/qualidade.md](evidencias/qualidade.md)); a medição usa concorrência 1, cache aquecido e MySQL local, sem latência de rede (gate G11). A primeira versão da view de faixas de valor levava de 6 a 9 s, porque o MySQL calculava a função de janela do histórico para todos os créditos; separar os atributos de linha numa view fundível reduziu a consulta a 0,4 s.

O pipeline é reprodutível no sentido mais estrito: a mesma entrada gera os mesmos bytes. Duas transformações do bruto real em pastas novas produziram os 17 arquivos de `data/limpo` e `data/pronto` idênticos (gate G14), porque a simulação usa semente fixa, os CSV têm formato determinístico e os compactados não guardam data. Sandve et al. (2013) apontam a reprodutibilidade como condição para que um resultado computacional possa ser verificado; aqui, ela é verificada a cada rodada dos quality gates.

## Referências

Entradas completas, com o DOI conferido no Crossref, em [REFERENCIAS.md](REFERENCIAS.md). Citadas neste documento, pelo identificador do catálogo: `alm2014`, `batini2009`, `garlan1993`, `kaufman2012`, `lam1983`, `parnas1972`, `perry1992`, `sandve2013`, `schelter2018`, `simmhan2005`, `wang1996`; `valente_esm` (livro, por seção) e `apostila_etl` (material didático, por seção).
