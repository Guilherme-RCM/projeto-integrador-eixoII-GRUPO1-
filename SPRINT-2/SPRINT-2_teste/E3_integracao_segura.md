# E3 — Integração segura com a fonte de dados

Os protocolos de conexão e de auditoria, com fundamentação em Kurose & Ross (6. ed.), estão em [PROTOCOLOS_SEGURANCA_AUDITORIA.md](PROTOCOLOS_SEGURANCA_AUDITORIA.md).

## 1. Fontes

| Fonte | Host | Cobertura | Uso no projeto |
|---|---|---|---|
| Portal de Acesso à Informação (NUCLEOGOV) | `acessoainformacao.palmas.to.gov.br` | Dados atuais; receitas 2018–jul/2026 | `receita_acessoinformacao.csv` (176.993 linhas), extraído em 07/07/2026 |
| API antiga de integração | `integracao.palmas.to.gov.br` | Histórico até jun/2021 | `receita_palmas.csv` (3.542 linhas) |

Fonte das informações de cobertura: `dados_transparencia_palmas.docx`, que registra que os totais baixados conferem com os informados pela API do portal.

## 2. Verificação feita nesta sprint (29/09/2026, 20:06 UTC)

| Teste | acessoainformacao | integracao |
|---|---|---|
| HTTPS com certificado válido (cadeia verificada pelo cliente) | Sim | Sim |
| HTTP simples redireciona para HTTPS | Sim (301) | Sim (301) |
| Resposta na raiz via HTTPS | 403 Forbidden | 404 Not Found |
| `robots.txt` | 403 | 404 (inexistente) |

**Nova verificação em 30/09/2026, 13:06 (16:06 UTC)**, com detalhe do TLS:

| Teste | acessoainformacao | integracao |
|---|---|---|
| Versão de TLS negociada | **TLS 1.3** (TLS_AES_256_GCM_SHA384) | **TLS 1.2** (ECDHE-RSA-AES256-GCM-SHA384) |
| Emissor do certificado | Let's Encrypt, válido até 22/11/2026 | Let's Encrypt, válido até 20/12/2026 |
| HTTP simples | Redireciona para HTTPS (301) | Redireciona para HTTPS (301) |
| Raiz via HTTPS | 403 (uma tentativa excedeu 20 s; duas seguintes responderam 403 em ~0,5 s) | 404 |

As duas versões de TLS estão dentro do mínimo recomendado atualmente (TLS 1.2; RFC 8996 e RFC 9325).

**Leitura:** as duas origens só aceitam tráfego cifrado. O 403 do portal NUCLEOGOV, inclusive no `robots.txt`, indica bloqueio da origem da requisição (firewall de aplicação, filtro por rede ou por cliente). **Não tentamos contornar o bloqueio** (troca de User-Agent, proxy etc.): isso violaria a regra de ética da coleta. O 404 da API antiga na raiz é esperado para uma API sem página inicial.

**Pendência para a Sprint 3:** a equipe que fez a extração de 07/07/2026 deve registrar aqui os **caminhos exatos dos endpoints**, os parâmetros de paginação e a data de consulta. Este documento não inventa caminhos que não foram verificados.

## 3. Autenticação

- Os dados usados são **públicos** (transparência ativa, Lei 12.527/2011). Nenhuma credencial foi necessária para a extração registrada.
- Se a Sefin liberar dados não públicos (créditos, dívida ativa — ver PA-12 em `REQUISITOS_UML.md`), o acesso deve usar token ou credencial institucional, por canal formal, com escopo mínimo.

## 4. Tratamento de credenciais no projeto

| Regra | Implementação |
|---|---|
| Nenhum segredo no código ou no Git | Credenciais lidas de variáveis de ambiente ou `.env` ([`etl/config.py`](etl/config.py)); `.env` está no `.gitignore`; o repositório só tem `.env.example`, sem valores |
| Menor privilégio no banco | Usuário `pi2_app` sem privilégio global; `GRANT` restrito aos bancos `pi2_tributario` e `pi2_tributario_teste`; o root não é usado pela aplicação |
| Senhas fortes e únicas | Geradas aleatoriamente (`secrets.token_urlsafe`), fora do repositório |
| Banco não exposto | MySQL escuta só em `127.0.0.1` (`bind-address`) |
| Sem segredo em log | Scripts não imprimem a configuração; auditoria proíbe senha, token e documento completo (`ck_aud_ator`, RF-03) |
| Dados pessoais | **Regra especificada, ainda sem código** (o piloto não tem dados pessoais): CPF/CNPJ só entram pseudonimizados por `HMAC-SHA-256(chave, documento)`, com a chave em `PSEUDONIMO_CHAVE` no `.env`, fora do banco e do Git. HMAC é a construção padronizada de hash com chave (RFC 2104; Kurose §8.3.2). Pseudonimização **não** é anonimização: quem tem a chave reverte a associação (LGPD, art. 13, §4º) |

## 5. Regras do cliente de coleta (Sprint 3)

1. Somente `https://`, com verificação de certificado ativa (nunca `verify=False`).
2. Ler e respeitar `robots.txt` e os termos de uso antes de coletar; registrar a data da leitura.
3. Identificar o cliente com User-Agent honesto (projeto acadêmico + contato institucional).
4. Intervalo mínimo entre requisições (sugestão inicial: 2 s) e *retry* com espera exponencial em 429/5xx, com limite de tentativas.
5. Gravar cada download como snapshot imutável com SHA-256 (já implementado em `fonte_snapshot`); reimportar o mesmo arquivo não duplica dados.
6. Falha de rede ou de esquema não pode deixar carga parcial: a publicação é transacional (`etl/carregar_receita.py`).
7. Coletar apenas o necessário à finalidade; nada de dado pessoal além do indispensável.
