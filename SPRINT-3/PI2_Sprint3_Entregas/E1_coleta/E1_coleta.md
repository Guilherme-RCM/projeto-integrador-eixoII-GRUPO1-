# E1 — Coleta automatizada

Código: `pipeline/coleta/` · Execução de referência: `20261021T065740-9b9054` (21/10/2026, código `ea64aa6`), 7 fontes completas, 61 requisições, 57 s, nenhuma falha.

## 1. O que a coleta garante

A coleta foi construída para que o dado chegue sozinho e chegue íntegro, porque o modelo da Sprint 4 será treinado sobre o que este pipeline entregar. Um único comando (`python etl_sefin.py`) consulta todas as fontes, respeita as regras de cada servidor, confere o que recebeu e grava o bruto datado, sem passo manual escondido. Além disso, cada fonte é isolada das demais: se uma falha, a falha fica registrada no log e no relatório, e as outras seguem. Desse modo, a coleta pode rodar todos os dias, e a transformação sempre sabe qual foi a última coleta completa de cada fonte.

## 2. Mapa das fontes

| Fonte | Via | Endereço | Formato e volume | Atualização | Cuidados legais e éticos | Uso no projeto | Prioridade |
|---|---|---|---|---|---|---|---|
| Arrecadação da Prefeitura de Palmas | API REST (Django REST Framework), paginada por `next` | `integracao.palmas.to.gov.br/apirest/arrecadacao/` | JSON, 36 páginas, 3.542 registros (exercícios 2010–2018) | histórico encerrado (última atualização em 01/06/2021) | pública, sem autenticação; robots.txt inexistente (404, sem regras); dado agregado por conta, sem pessoa | série histórica da receita até 2017 | alta |
| Receita da Prefeitura — extração oficial NUCLEOGOV (fonte da entrega) | arquivo distribuído pela coordenação | cópia local (`PI2_NUCLEOGOV_ARQUIVO`) ou pasta `dados/` do repositório da coordenação (`--nucleogov-github`) | CSV, 176.993 linhas, 28 MB (extração de 07/07/2026) | pontual | cópia aceita só se o hash Git conferir com o arquivo publicado; dado agregado por conta | receita de 2019 a julho de 2026 e previsão orçamentária | alta |
| Receita da Prefeitura — API do portal NUCLEOGOV (alternativa, `--nucleogov-api`) | `POST` de formulário, ação `sgreceitas/listar`, paginada por deslocamento (manual de coleta da coordenação, §3) | `acessoainformacao.palmas.to.gov.br/api`, com os cookies da página `/cidadao/transparencia/sgreceitas` | JSON em páginas de 1.000 registros (180.976 em 19/10/2026, segundo o manual), convertidas num CSV no layout da extração oficial | até o mês corrente | pública por lei; o firewall recusa User-Agent de biblioteca (manual, armadilha 5.1), e o agente usado é declarado pelo operador (`PI2_NUCLEOGOV_USER_AGENT`, ADR-002); robots.txt consultado com o mesmo agente; dado agregado por conta | receita até o mês corrente, quando a equipe adotar a API | alternativa |
| Quadras do GeoPalmas (SEDUSR) | API JSON do portal de mapas | `geo.palmas.to.gov.br/mapas/getshape/` e `/getplacemarker/<região>/` | JSON, 6 regiões e 284 quadras com polígono | quando a Prefeitura aprova loteamentos | pública; robots.txt inexistente; sem pessoa | quadras, regiões e cruzamento com os setores | média |
| Setores censitários 2022 (IBGE) | serviço WFS 2.0 (OGC), paginado por `count`/`startIndex` | `geoservicos.ibge.gov.br/geoserver/ows`, camada `CGMAT:qg_2022_600_setcensitario__v02` | GeoJSON, 4 páginas, 733 setores de Palmas | por revisão da malha | pública; robots.txt inexistente | unidade territorial da análise e dos mapas | alta |
| Renda do responsável por setor, Censo 2022 (IBGE) | arquivo descoberto por raspagem do índice do servidor | `ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/` | ZIP com CSV nacional (9,4 MB; 30,6 MB descompactado) e dicionário XLSX | por revisão do IBGE (sufixo AAAAMMDD no nome) | pública; sigilo do IBGE ("X") preservado | renda, moradores e domicílios por setor | alta |
| IPCA, série 433 do SGS (Banco Central) | API REST, paginada por janelas de 10 anos | `api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados` | JSON, 3 janelas, 321 meses | mensal | pública; robots.txt inexistente | deflação da receita para valores reais | alta |
| Repositório da coordenação no GitHub | API do GitHub (opcional) | só com `--nucleogov-github` | — | — | acessado apenas com pedido explícito | alternativa à cópia local do NUCLEOGOV | opcional |

Duas fontes foram mapeadas e deliberadamente deixadas fora da coleta, e a razão de cada exclusão é técnica e ética. O SIG da Prodata, que publica a transparência de Palmas, exige uma sessão proprietária (`x-auth-token`) obtida pela interface; automatizá-la equivaleria a contornar o controle de acesso do sistema. A API de localidades do IBGE (`servicodados.ibge.gov.br`) não respondeu ao pedido de robots.txt, e a política do cliente trata servidor inalcançável como "não permitido" (RFC 9309, §2.3.1); como os códigos de município já vêm na malha do WFS, nada se perde. Assim, a cobertura da coleta é a máxima possível sem violar a vontade expressa dos operadores.

## 3. O protocolo de cada requisição

Toda requisição passa pelo mesmo cliente (`pipeline/coleta/http.py`), e por isso a política de coleta vale igualmente para todas as fontes. O cliente aplica, nesta ordem, as regras descritas a seguir; cada regra tem um teste que a exercita com respostas gravadas, sem rede (`tests/test_coleta_*.py`). O POST de formulário, usado só nas consultas de leitura da API do NUCLEOGOV, passa pelas mesmas regras, inclusive a repetição, que é segura porque a consulta não altera nada no servidor.

O transporte só aceita HTTPS com certificado verificado e TLS 1.2 ou superior, porque sem TLS um intermediário pode ler e alterar o dado em trânsito. Kurose e Ross (2013, §8.6) descrevem como o TLS garante confidencialidade, integridade e autenticação do servidor, e a RFC 8996 descontinuou o TLS 1.0 e o 1.1; por conseguinte, o contexto TLS recusa essas versões e falha se a verificação de certificado ou de nome estiver desligada. Os links `next` da API da Prefeitura vêm em `http://`, e o cliente os promove para `https://` no mesmo host, nunca seguindo para outro servidor.

O robots.txt de cada host é consultado antes do primeiro acesso, e a resposta é interpretada como a RFC 9309 determina. Um robots.txt com status 2xx traz as regras; um 4xx significa que não há regras; um 5xx ou um servidor inalcançável significa que nada pode ser coletado (§2.3.1). Na execução de referência, cinco hosts responderam 404 ao robots.txt, e o portal NUCLEOGOV respondeu 403; cada resposta foi gravada no bruto como evidência datada (`robots_<host>_<data>.txt`).

O ritmo das requisições respeita um intervalo mínimo por host, e o Crawl-delay prevalece quando for maior. O cliente mantém a conexão persistente com cada servidor (Kurose; Ross, 2013, §2.2.2) e espera pelo menos um segundo entre duas requisições ao mesmo host. Desse modo, as 36 páginas da API da Prefeitura levam cerca de 36 segundos, carga desprezível para o servidor público.

Falhas transitórias são repetidas com espera exponencial aleatória, e falhas definitivas interrompem a fonte. Conexão recusada, tempo esgotado, HTTP 429 e 5xx são transitórios (RFC 9110, §15.6; RFC 6585, §4); a espera antes da tentativa n é sorteada entre zero e o mínimo entre o teto e base × 2ⁿ, a mesma ideia do recuo exponencial binário do Ethernet (Kurose; Ross, 2013, §5.3.2, p. 339; Metcalfe; Boggs, 1976), para que vários clientes não voltem todos ao mesmo tempo. O cabeçalho Retry-After (RFC 9110, §10.2.3) e os cabeçalhos de limite de taxa prevalecem sobre o sorteio; uma espera pedida acima de cinco minutos interrompe a fonte em vez de prender a execução. Erros como 403 e 404 não são repetidos, porque repetir uma recusa seria insistência, e não robustez.

O conteúdo recebido é conferido antes de virar bruto. O tamanho recebido precisa conferir com o `Content-Length` (defesa contra truncamento, Kurose; Ross, 2013, §8.6, p. 528); o ZIP do Censo precisa abrir e ter o CRC de cada membro correto; a cópia do NUCLEOGOV precisa ter o hash de objeto do Git publicado pela coordenação (blob `449ca775…`, 28.136.842 bytes). Para os arquivos grandes do IBGE, o pedido seguinte é um GET condicional (`If-None-Match`/`If-Modified-Since`): a resposta "304 Not Modified" reaproveita o bruto anterior sem novo download (Kurose; Ross, 2013, §2.2.6, p. 83–85).

## 4. Autenticação, paginação e limite de taxa

A autenticação é tratada pelo cliente, ainda que as fontes usadas hoje sejam públicas. Credenciais ficam apenas no ambiente ou no `.env`, nunca no código, no Git ou na linha de comando; cada credencial é associada a um único host e só é enviada a ele, e o filtro de log mascara o valor caso algum código o escreva por engano (`pipeline/observabilidade.py`). Hoje, apenas o caminho opcional do GitHub usa token (`GITHUB_TOKEN`); quando a Sefin disponibilizar uma API autenticada, basta registrar a variável do host, sem mudar o código das fontes.

As quatro formas de paginação encontradas foram traduzidas para um único laço de coleta, e cada uma tem o seu critério de parada. A API da Prefeitura informa o total (`count`) e o link da página seguinte (`next`), e a coleta para quando `next` vem vazio; o WFS do IBGE informa o total em `numberMatched` e é percorrido por `count`/`startIndex` com ordenação estável (`sortBy=cd_setor`); o SGS do Banco Central aceita no máximo dez anos por consulta, e a coleta percorre janelas decenais até a data de hoje; e a API do portal NUCLEOGOV recebe a consulta num POST de formulário, com o deslocamento no campo `limit`, e para quando a página vem vazia, curta ou alcança o total, o mesmo critério do manual de coleta da coordenação (§3.4). Em todos os casos, o total anunciado não pode mudar no meio da coleta, e o número de registros obtidos precisa igualar o anunciado, caso contrário a coleta fica marcada como incompleta (validação V01).

O limite de taxa é respeitado de duas maneiras: preventivamente, pelo ritmo mínimo por host, e reativamente, pelos sinais do servidor. Respostas 429 ou 503 com Retry-After, e cabeçalhos `X-RateLimit-*` com cota esgotada, fazem o cliente esperar o tempo pedido antes de tentar de novo. Assim, o pipeline se adapta ao servidor em vez de exigir dele mais do que oferece.

## 5. A camada bruta (`data/bruto`)

O bruto é gravado exatamente como chegou, com nome datado, e nunca é sobrescrito. O nome segue o padrão `fonte_assunto_AAAA-MM-DD[_pNNNN][_vN].ext` (por exemplo, `palmas-apirest_arrecadacao_2026-10-21_p0001.json`); conteúdo diferente no mesmo dia ganha um sufixo de versão, e o mesmo conteúdo é reaproveitado. Cada arquivo tem uma linha no manifesto (`data/bruto/manifesto.jsonl`), com URL, status HTTP, tamanho, SHA-256 e o hash da linha anterior; essa cadeia de hashes é conferida antes de toda transformação (validação V12), de modo que um arquivo trocado ou uma linha apagada do manifesto interrompe o pipeline.

Quando vem da API do portal (`--nucleogov-api`), a receita do NUCLEOGOV ocupa duas camadas do bruto, e a segunda deriva da primeira de modo verificável. As páginas da API são gravadas como chegaram (`palmas-nucleogov_receita-paginas_AAAA-MM-DD_pNNNN.json`); com a coleta completa, elas viram um CSV no layout da extração oficial (`palmas-nucleogov_receita_AAAA-MM-DD.csv`), as 14 colunas da fonte separadas por `;`, em UTF-8 com BOM, como na gravação incremental do manual (§6.1). O manifesto registra o CSV com a lista das páginas de origem e os campos que a API mandou; como a conversão é determinística, as mesmas páginas geram sempre os mesmos bytes, e a limpeza, as validações e a carga do snapshot da Sprint 2 leem a receita sem mudança de contrato.

A transformação nunca lê "o que estiver na pasta", e sim a coleta completa mais recente que o manifesto registra para cada fonte. Uma coleta parcial (por exemplo, interrompida por queda de rede) fica registrada como incompleta e não substitui a anterior; se não houver nenhuma coleta completa de uma fonte, a transformação para com código de saída 3. Por conseguinte, a reprodutibilidade não depende de quem limpou a pasta por último.

## 6. Ética e LGPD

Todas as fontes são oficiais, públicas e agregadas, e nenhum dado pessoal é coletado. A arrecadação vem por conta contábil e mês, o Censo por setor censitário, as quadras sem proprietário; portanto, a coleta não precisa pseudonimizar nada, e a regra de pseudonimizar identificadores antes do armazenamento (LGPD, art. 12 e art. 13, §4º) fica pronta para a base da Sefin, que ainda não chegou. Krotov, Johnson e Silva (2020) mostram que a legalidade da raspagem depende tanto dos termos de uso e do robots.txt quanto da carga imposta ao servidor; por isso, o cliente se identifica por um User-Agent honesto (`PI2-UFT-Sefin-ETL/0.3`), sem e-mail e sem endereço de repositório, em todas as fontes salvo o portal NUCLEOGOV, tratado no parágrafo seguinte.

O agente usado no portal NUCLEOGOV é decisão explícita do operador, e a forma de tomá-la é parte do resultado. Em 20/10/2026, o portal respondeu 403 ao agente do projeto, inclusive no robots.txt, e a equipe tratou a resposta como recusa, passando a ler a extração oficial que a coordenação distribuiu. O manual de coleta da coordenação, porém, atribui esse 403 a um firewall de aplicação que barra User-Agents de biblioteca, e não o acesso, e classifica o agente de navegador como contorno legítimo, porque o dado é público por lei e o acesso é o mesmo de um navegador (armadilha 5.1). Por isso, desde 26/10/2026, a API do portal está implementada como alternativa explícita (`--nucleogov-api`), consultada só com o agente declarado em `PI2_NUCLEOGOV_USER_AGENT`, aplicado apenas a esse host e também ao robots.txt, que continua consultado; o ADR-002 recomenda começar por um agente compatível que ainda identifique o projeto. A entrega da Sprint 3 manteve a extração oficial, por decisão da equipe. Proxy, VPN e quebra de autenticação ou de CAPTCHA continuam fora de questão, e o acesso ao GitHub da coordenação, que traz a extração oficial, só acontece com a opção `--nucleogov-github`.

## 7. Evidências da execução de referência

| Fonte | Arquivos no bruto | Registros | Situação |
|---|---|---|---|
| `palmas-apirest/arrecadacao` | 36 | 3.542 de 3.542 anunciados | completa |
| `palmas-nucleogov/receita` | 1 (cópia local conferida) | 176.993 linhas | completa; portal: HTTP 403 registrado |
| `palmas-geo/regioes` e `quadras` | 1 + 6 | 6 regiões, 284 quadras | completa |
| `ibge-wfs/setores-palmas` | 4 | 733 de 733 anunciados | completa |
| `ibge-censo2022/renda-responsavel-setores` | 1 ZIP + índice | 1 arquivo | completa |
| `ibge-censo2022/dicionario-renda` | 1 XLSX + índice | 1 arquivo | completa |
| `bcb-sgs/ipca` | 3 | 321 meses | completa |
| `robots` | 6 | — | 5 hosts com 404, 1 com 403 |

O log completo da execução está em [evidencias/etl.log](../E2_pipeline/etl.log), e cada linha traz o identificador da execução. Os arquivos brutos não vão para o Git, por tamanho e porque o próprio pipeline os coleta de novo, ainda que com conteúdo possivelmente diferente; o manifesto e o log, entretanto, permitem conferir o que foi coletado, quando e com qual SHA-256.

## 8. Limitações

A coleta é completa para as fontes disponíveis, mas as fontes disponíveis ainda não contêm a dívida ativa por contribuinte. A API antiga da Prefeitura encerrou o histórico em 2021, a receita recente do NUCLEOGOV vem da extração pontual de 07/07/2026 (a API do portal, que traria o mês corrente, depende de `--nucleogov-api` e do agente declarado), e nenhuma fonte pública traz crédito, devedor ou pagamento individual (PA-12). Por isso, a inadimplência da Sprint 3 é simulada sobre os setores reais (ADR-003), e o próximo passo da coleta é a integração com a base da Sefin, pseudonimizada na entrada.

## Referências

Entradas completas, com o DOI conferido no Crossref, em [REFERENCIAS.md](../referencias/REFERENCIAS.md). Citadas neste documento, pelo identificador do catálogo: `kurose2013` (livro, citado por seção e página), `krotov2020`, `metcalfe1976`, `rfc6585`, `rfc8996`, `rfc9110` e `rfc9309`; LGPD (Lei nº 13.709/2018).
