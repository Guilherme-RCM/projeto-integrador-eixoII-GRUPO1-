# Protocolos de segurança de conexão e auditoria

Referência principal: KUROSE, J. F.; ROSS, K. W. *Redes de computadores e a Internet: uma abordagem top-down*. 6. ed. São Paulo: Pearson, 2013. Páginas citadas pela numeração impressa do livro.

Complementa [E3_integracao_segura.md](E3_integracao_segura.md) e os requisitos RF-01 a RF-03, RNF-01 a RNF-03 e RNF-14 de REQUISITOS_UML.md.

> **Atualização de algoritmos.** Esta edição do livro usa como exemplos MD5, SHA-1, DES/3DES e SSL/TLS 1.1 (RFC 4346). Os **princípios** do livro continuam válidos e são a base deste documento. Os **algoritmos** foram atualizados por fontes de fora do livro, marcadas com *[fora do livro]*: TLS 1.0 e 1.1 foram descontinuados (RFC 8996); MD5 e SHA-1 não devem ser usados para segurança (RFC 6151, RFC 6194); recomendações atuais de TLS em BCP 195 (RFC 9325).

---

## 1. Modelo de ameaças

Kurose (§8.1, p. 496–497) define o intruso ("Trudy") como alguém capaz de **monitorar** mensagens e de **modificar, inserir ou eliminar** mensagens no canal. Disso decorrem os ataques de escuta, personificação, sequestro de sessão e negação de serviço.

Canais do sistema expostos a esse intruso:

| Canal | Origem → destino | Situação |
|---|---|---|
| C1 | Cliente de coleta (ETL) → portais da Prefeitura | Existe (Sprint 3 automatiza) |
| C2 | Aplicação → MySQL | Existe (local) |
| C3 | Navegador do usuário → sistema web | Futuro |
| C4 | Sefin → sistema (dados restritos de dívida ativa) | Futuro, depende do PA-12 |
| C5 | Operação: firewall, detecção de invasão, monitoramento | Futuro (implantação) |

## 2. Propriedades exigidas

As quatro propriedades de comunicação segura de Kurose (§8.1, p. 496) são o critério para cada canal:

| Propriedade (Kurose p. 496) | Mecanismo no livro | C1 | C2 | C3 | C4 |
|---|---|---|---|---|---|
| **Confidencialidade** | Criptografia (§8.2) | TLS | TLS | TLS | IPsec ESP ou TLS mútuo |
| **Integridade de mensagem** | Hash criptográfico e MAC (§8.3) | MAC do TLS + SHA-256 do arquivo | MAC do TLS | MAC do TLS | MAC do ESP |
| **Autenticação do ponto final** | Certificados e nonce (§8.3.3, §8.4) | Certificado do servidor | Certificado do servidor + usuário/senha | Certificado + login (Gov.br) | Certificados dos dois lados |
| **Segurança operacional** | Firewall e IDS (§8.9) | — | Porta do banco fechada | Firewall + IDS | Firewall + IDS |

---

## 3. Protocolos de segurança de conexão

### P1 — HTTPS/TLS em toda conexão externa (C1 e C3)

**Base no livro (§8.6, p. 524–528).** O SSL/TLS acrescenta ao TCP sigilo, integridade e autenticação do ponto final. O livro mostra os ataques que cada ausência permite: sem sigilo, o invasor lê os dados; sem integridade, altera o pedido; sem autenticação do servidor, um impostor se passa pelo site (p. 524). A conexão tem três fases (p. 525):

1. **Apresentação (handshake):** o servidor envia um certificado assinado por uma autoridade certificadora (CA), que liga a chave pública à identidade (§8.3.3, p. 514). O cliente **verifica o certificado** antes de continuar (p. 527, passo 3).
2. **Derivação de chaves:** chaves **separadas** para criptografia e para MAC em cada sentido (p. 525–526).
3. **Transferência:** os dados vão em registros, cada um com MAC (p. 526).

Defesas que o livro associa ao protocolo e que devem estar ativas:

| Ataque (Kurose) | Defesa do TLS | Regra do projeto |
|---|---|---|
| Servidor impostor (p. 524) | Certificado assinado por CA (p. 514, 525) | **Nunca** desligar a verificação de certificado (`verify=False` proibido) |
| Repetição de uma conexão inteira (p. 528) | Nonces do cliente e do servidor no handshake | Usar a biblioteca TLS padrão, sem desabilitar recursos |
| Repetição ou reordenação de registros (p. 526–528) | Números de sequência no MAC | Idem |
| Rebaixamento para algoritmos fracos (p. 527) | MAC de todas as mensagens do handshake | Aceitar só TLS 1.2 ou superior, preferindo 1.3 *[fora do livro: RFC 8996, RFC 8446]* |
| **Truncamento** (p. 528): o invasor encerra a conexão com TCP FIN antes do fim | Registro de encerramento autenticado | O download só é válido se terminar sem erro **e** o tamanho conferir; o arquivo é identificado pelo SHA-256 (`fonte_snapshot`) antes de qualquer carga |

**No código atual:** o cliente de coleta ainda não existe (Sprint 3). A carga já calcula o SHA-256 do arquivo e o registra em `fonte_snapshot` ([etl/carregar_receita.py](etl/carregar_receita.py)). Os dois portais usam HTTPS com certificado válido e redirecionam HTTP para HTTPS (verificado em 29/09/2026, ver E3).

### P2 — TLS entre aplicação e banco (C2)

**Base no livro:** o mesmo §8.6. Credenciais do banco atravessando a rede sem TLS podem ser **monitoradas** (p. 496–497).

| Regra | Situação atual |
|---|---|
| Banco escuta só em `127.0.0.1` enquanto for local | ✅ `bind-address=127.0.0.1` |
| Se o banco sair da máquina da aplicação, exigir TLS no servidor (`require_secure_transport=ON`) e no usuário (`REQUIRE SSL`) | ❌ **Ainda não:** `etl/config.py` não pede TLS na conexão. Aceitável só com banco local |
| O cliente valida o certificado do servidor MySQL | ❌ Pendente, junto com o item anterior |
| Usuário da aplicação com privilégio mínimo | ⚠️ Parcial: `pi2_app` não tem privilégio global, mas ainda pode alterar e apagar a tabela de auditoria (ver A5) |

### P3 — Sessão do usuário web (C3, futuro)

**Base no livro:** o HTTP é **sem estado** (§2.2.1, p. 73), e a sessão do usuário é construída sobre ele com **cookies** (§2.2.4, p. 79–81). Autenticar o ponto final exige provar que o outro lado está **"ao vivo"**, e não repetindo uma mensagem gravada. O livro resolve isso com um **nonce**, número usado uma única vez (protocolo ap4.0, §8.4.5, p. 518).

| Regra | Base |
|---|---|
| Todo acesso por HTTPS (P1); HTTP só redireciona | §8.6, p. 524 |
| Identificador de sessão aleatório, imprevisível e de uso único por login | Nonce, p. 518 |
| Formulários que alteram dados carregam um token de uso único (proteção contra requisição forjada) | Mesmo princípio do nonce, p. 518 |
| Cookie de sessão com os atributos `Secure`, `HttpOnly` e `SameSite` e com expiração | *[fora do livro: RFC 6265; `SameSite` na revisão draft-ietf-httpbis-rfc6265bis]* |
| Senhas guardadas só como hash lento com sal (argon2 ou bcrypt), nunca em texto | RNF-01; *[fora do livro]* |
| Login do cidadão pelo Gov.br quando homologado | PA-08 |

### P4 — Canal institucional com a Sefin (C4, futuro)

**Base no livro (§8.7, p. 528–531):** uma VPN leva o tráfego entre instituições pela Internet pública, cifrado. No IPsec, o protocolo **ESP** fornece autenticação da origem, integridade e sigilo; o AH não fornece sigilo (p. 530). Os dois lados estabelecem **associações de segurança** (SA), uma por sentido (p. 530–531).

| Regra | Base |
|---|---|
| Dados restritos da Sefin (créditos, dívida ativa) só por VPN IPsec em **modo túnel com ESP**, ou por TLS com certificado dos dois lados | p. 530–531 |
| Nunca usar só AH para esses dados | AH não cifra (p. 530) |
| Integridade do ESP com algoritmo atual (HMAC-SHA-256 ou AES-GCM), não com MD5 | Livro cita HMAC com MD5 (p. 531); *[fora do livro: RFC 6151]* |

### P5 — Segurança operacional (C5, na implantação)

**Base no livro (§8.9, p. 538–545).** O firewall isola a rede interna, e todo o tráfego passa por ele (p. 538). A filtragem usa endereço, protocolo, porta e flags TCP (p. 539). O IDS faz inspeção profunda de pacotes e gera alertas: por **assinatura**, que não enxerga ataques novos, ou por **anomalia** (p. 544–545). Servidores públicos ficam numa **zona desmilitarizada (DMZ)** (Figura 8.36, p. 545).

| Regra | Base |
|---|---|
| Entrada permitida só na porta 443 do servidor web; o resto é bloqueado | Filtro de pacotes, p. 539 (exemplo da porta 80) |
| Porta 3306 do MySQL nunca exposta para fora da rede interna | p. 539 |
| Servidor web na DMZ; banco na rede interna | Fig. 8.36, p. 545 |
| IDS com assinaturas e detecção de anomalia; alertas enviados à auditoria (A1) | p. 544–545 |
| Monitoramento de rede só com **SNMPv3** (autenticação, criptografia, anti-repetição e controle de acesso) | §9.3.4, p. 570–572 |

---

## 4. Protocolo de auditoria

A auditoria aplica ao **registro de eventos** os mesmos mecanismos que o livro usa para proteger mensagens: integridade por MAC, ordem por número de sequência, detecção de truncamento e controle de acesso por visão. O Git registra a evolução do código, mas **não substitui** a auditoria do sistema.

### A1 — O que registrar

Campos obrigatórios (já em `registro_auditoria`, RF-03): correlação, data e hora, tipo de ator (usuário, serviço ou tarefa), ator, recurso, ação, permissão, resultado e IP. **Nunca** senha, token ou documento completo (CHECK `ck_aud_ator` e regra do RF-03).

Eventos de conexão e rede que passam a ser registrados:

| Evento | Resultado | Base no livro |
|---|---|---|
| Login com sucesso ou falha | PERMITIDO / NEGADO | Autenticação do ponto final, §8.4 |
| Operação negada por falta de permissão | NEGADO | Controle de acesso, §9.3.4, p. 572 |
| Falha de verificação de certificado ou de handshake TLS em coleta | ERRO | §8.6, p. 525–527 |
| Download incompleto ou com SHA-256 divergente (possível truncamento) | ERRO | p. 528 |
| Carga de snapshot (novo ou repetido) | PERMITIDO | Integridade, §8.3 |
| Alerta de firewall ou IDS | ERRO | §8.9.2, p. 544–545 |

### A2 — Integridade do registro: cadeia de MAC

**Base no livro (§8.3.2, p. 510):** um MAC é H(m + s), o hash da mensagem concatenada a um segredo compartilhado. Quem não conhece o segredo não consegue produzir um MAC válido, e qualquer alteração na mensagem é detectada. O livro indica o **HMAC** como padrão mais usado (p. 510).

Protocolo:

```text
mac(n) = HMAC-SHA-256( K_auditoria , campos(n) || mac(n-1) )      mac(0) = constante fixa
```

- Cada registro guarda seu `mac`, calculado sobre os próprios campos **e o MAC do registro anterior**. Alterar ou apagar qualquer registro quebra todos os MACs seguintes, e a verificação aponta o primeiro registro inválido.
- `K_auditoria` é uma chave **própria da auditoria**, diferente da senha do banco e da chave de pseudonimização (`PSEUDONIMO_CHAVE`). É o mesmo princípio do TLS de usar chaves diferentes para cada finalidade (p. 525–526). Ela fica fora do banco e fora do Git.
- HMAC-SHA-256 em vez de HMAC-MD5 ou SHA-1, citados no livro (p. 509–510) *[fora do livro: RFC 6151, RFC 6194]*.

### A3 — Ordem e repetição: número de sequência

**Base no livro:** o TLS usa números de sequência para impedir repetição e reordenação de registros numa sessão (p. 526–528). O SNMPv3 usa um contador que funciona como nonce contra reprodução (p. 572).

Protocolo: `id_registro` é sequencial e já faz parte do MAC. A verificação exige sequência sem lacunas; um buraco na numeração indica remoção.

### A4 — Truncamento: selo periódico

**Base no livro:** no TLS, encerrar a conexão só com TCP FIN permite o **ataque por truncamento**, e a defesa é um registro de encerramento autenticado (p. 528).

Protocolo: uma tarefa grava periodicamente um **registro de selo** com o total de registros e o último MAC, e guarda uma cópia do selo **fora do banco**. Se os últimos registros forem apagados, o banco deixa de conferir com o último selo guardado.

### A5 — Quem pode ler e escrever a auditoria

**Base no livro:** o SNMPv3 controla **quais informações cada usuário pode consultar ou alterar** por meio de visões (*view-based access control*, §9.3.4, p. 572).

| Papel | Permissão na tabela `registro_auditoria` |
|---|---|
| Usuário da aplicação | Somente `INSERT` (sem `UPDATE` nem `DELETE`) |
| Auditor | Somente `SELECT` |
| Administrador técnico | Nenhum acesso aos dados fiscais por padrão (PA-10) |

**Situação atual:** ❌ `pi2_app` tem `UPDATE` e `DELETE` em todo o banco, inclusive na auditoria. É preciso criar um usuário de banco só para escrever na auditoria, ou restringir os privilégios.

### A6 — Verificação e retenção

- Um verificador recalcula a cadeia (A2), confere a sequência (A3) e compara com o último selo (A4). Deve rodar diariamente e antes de cada entrega; qualquer falha gera alerta.
- Prazo de retenção definido por finalidade e base legal (PA-11); a LGPD não fixa um prazo único.

---

## 5. Situação atual e pendências

| Item | Situação | Onde |
|---|---|---|
| HTTPS nos portais de origem | ✅ Verificado | E3 §2 |
| SHA-256 de cada arquivo carregado; carga idempotente | ✅ | `fonte_snapshot`, `etl/carregar_receita.py` |
| Credenciais fora do código e do Git | ✅ | `.env`, `.gitignore`, `etl/config.py` |
| Banco escuta só localmente | ✅ | `my.ini` |
| Campos de auditoria e proibição de senha/token | ✅ | `registro_auditoria`, `ck_aud_ator` |
| TLS entre aplicação e banco | ❌ Obrigatório quando o banco sair da máquina local | P2 |
| Cadeia de MAC, sequência sem lacunas e selo da auditoria | ❌ Especificado, não implementado | A2–A4 |
| Auditoria somente-inserção para a aplicação | ❌ | A5 |
| Cliente de coleta com TLS verificado, repetição com espera e registro de falhas | ❌ Sprint 3 | P1, E3 §5 |
| Sessão web, firewall, IDS, VPN com a Sefin | Futuro (implantação) | P3–P5 |

## 6. Referências

- KUROSE, J. F.; ROSS, K. W. *Redes de computadores e a Internet*. 6. ed. Pearson, 2013. §2.2.1 e §2.2.4 (p. 73, 79–81); §8.1 (p. 496–497); §8.3.1–8.3.3 (p. 508–514); §8.4.5 (p. 518); §8.6 (p. 524–528); §8.7 (p. 528–531); §8.9 (p. 538–545); §9.3.4 (p. 570–572).
- *[fora do livro]* RFC 8446 (TLS 1.3); RFC 8996 (descontinuação de TLS 1.0 e 1.1); RFC 9325 / BCP 195 (recomendações de uso de TLS); RFC 2104 (HMAC); RFC 6151 (MD5); RFC 6194 (SHA-1); RFC 6265 e draft-ietf-httpbis-rfc6265bis (cookies HTTP).
