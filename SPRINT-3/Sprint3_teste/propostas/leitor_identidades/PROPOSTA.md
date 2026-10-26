# Leitor de identidades: proposta de implementação da HU-04

Pasta separada do pipeline da Sprint 3 · situação: protótipo com dados sintéticos · avaliação de 21/10/2026

## 1. Origem e situação

O leitor de identidades é um protótipo da HU-04 e, por essa razão, permanece fora do pipeline da Sprint 3. A HU-04 do artigo *Histórias de usuário e transformação de dados não estruturados em estruturados para a cobrança tributária municipal* (equipe do PI2, 2026, §4.2; cópia em `docs/pesquisa/`) pede que documentos enviados pelo contribuinte virem registros revisáveis, com o trecho de origem de cada campo. A Sprint 3, entretanto, trabalha apenas com fontes públicas agregadas, que não trazem documento nem identificador de pessoa (PA-12). Por conseguinte, misturar este código ao pipeline criaria uma dependência sem dado de entrada, e a separação física em `propostas/` preserva os dois trabalhos sem acoplamento.

A procedência do pacote é registrada para que a análise possa ser auditada. O conteúdo veio do arquivo `arquitetura_cpf_pacote.zip`, fornecido pelo integrante a partir da pasta `Desktop\Codex\output`, com SHA-256 `a065f6a5d3924abdbe2185add8d4bb7dd2438dd4ae3cdcdafadc74ea9f7c01c9`, e foi copiado sem alteração de código. Além disso, os 13 testes do próprio pacote foram executados em 21/10/2026 com `python -m unittest discover -s tests -v` e passaram, o que confirma a afirmação do `README.md` original. Desse modo, o que está nesta pasta é exatamente o que foi avaliado.

## 2. O que pode ser aproveitado

A regra de dígitos verificadores do CPF é a parte diretamente reaproveitável, porque é determinística e não depende de banco nem de interface. A função `valid_cpf` (`cpf_app/domain.py`) aplica o módulo 11 e rejeita sequências repetidas, exatamente a validação que o artigo exige antes de qualquer publicação (§5.4). Ademais, ela mantém o identificador como texto, o que preserva zeros à esquerda, conforme a recomendação da apostila de ETL (§5.1). Assim, a regra pode virar um filtro do pipeline quando os dados da Sefin chegarem, desde que o resultado seja pseudonimizado logo em seguida (seção 3).

O registro de evidência por ocorrência atende ao critério de aceitação da HU-04 e confirma o princípio de linhagem já adotado no projeto. Cada candidato guarda página, posição no texto e trecho de contexto, de modo que a decisão humana se apoia na fonte, e não na saída do extrator. Esse desenho é coerente com a noção de proveniência de Buneman e Tan (2007), que associa a confiança no dado à capacidade de reconstruir sua origem. Portanto, o contrato de evidência deve ser mantido em qualquer evolução, inclusive se um OCR substituir o leitor textual.

A idempotência e a trilha somente-inserção repetem decisões que o projeto já valida, o que reduz o risco de adoção. A chave (unidade, SHA-256, versão do extrator, versão das regras) tem a mesma lógica do snapshot da Sprint 2 (SHA-256 e versão do parser), e os gatilhos que bloqueiam `UPDATE` e `DELETE` na auditoria oferecem um caminho concreto para a pendência A5 do `PROTOCOLOS_SEGURANCA_AUDITORIA.md`. Contudo, como o próprio pacote reconhece, um administrador do banco remove gatilhos; logo, eles complementam, e não substituem, a cadeia de MAC especificada em A2.

## 3. O que impede a integração direta

O armazenamento em texto claro é o impedimento principal, pois contraria os requisitos de privacidade do projeto. O pacote grava o CPF e o documento original (BLOB) sem pseudonimização, enquanto o RNF-13 exige pseudonimizar identificadores antes do armazenamento analítico, e o artigo da equipe prevê pseudônimos por HMAC (§5.7). Além disso, Sweeney (2002) mostra que a combinação de atributos permite reidentificar pessoas, de modo que esconder o CPF da tela não elimina o risco. Por isso, o próprio `README.md` do pacote restringe o uso a documentos sintéticos, e essa restrição continua valendo enquanto a pseudonimização não for implementada.

A persistência paralela em SQLite duplicaria entidades que já existem no banco da Sprint 2. As tabelas `credit` e `document` do pacote correspondem, em parte, a `credito_tributario` e a `sujeito_passivo`, que já têm restrições, histórico e auditoria no MySQL. Ademais, o serviço de aplicação usa SQL do SQLite diretamente, como o `README.md` admite, de modo que trocar o banco exige refatoração. Assim, a integração deve passar por um adaptador de persistência para o esquema existente (Valente, *Engenharia de Software Moderna*, §6.5 e §5.6.3), e não por um segundo banco.

O escopo de identificação ainda é incompleto para a cobrança municipal. O artigo pede CPF e CNPJ (§5.4), mas o pacote valida apenas CPF. Além disso, a Receita Federal instituiu o CNPJ alfanumérico a partir de julho de 2026 (Instrução Normativa RFB nº 2.229/2024), o que muda o cálculo dos dígitos verificadores. Somam-se a isso a ausência de OCR (páginas sem texto vão para `OCR_REQUIRED`) e os atores apenas simulados, sem a autenticação do RF-01. Desse modo, o protótipo demonstra as invariantes do fluxo, mas não está pronto para operar.

## 4. Caminho de integração proposto (sprints seguintes)

A integração deve começar pela proteção do dado, e não pela automação da leitura. A sequência proposta é:

1. pseudonimizar na entrada (HMAC-SHA-256 com a chave `PSEUDONIMO_CHAVE`) e guardar apenas o pseudônimo e um trecho mascarado;
2. validar também o CNPJ, inclusive o alfanumérico;
3. persistir por meio de um adaptador para `sujeito_passivo` e `credito_tributario`;
4. só então acoplar um OCR atrás da porta `Extractor`, avaliado por campo antes do uso.

Fellegi e Sunter (1969) tratam a vinculação de registros como decisão sob incerteza. Além disso, Parasuraman e Manzey (2010) mostram que a revisão humana pode degenerar em confirmação automática. Ambos os resultados justificam medir os erros de vínculo e o comportamento dos revisores antes de ampliar o uso. Por conseguinte, a HU-04 permanece como trabalho futuro com critérios explícitos de continuidade, e não como entrega da Sprint 3.

## 5. Como executar (isolado do pipeline)

```powershell
cd propostas\leitor_identidades
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Os testes desta pasta não fazem parte da suíte nem dos quality gates da Sprint 3, que cobrem `etl/`, `src/` e `pipeline/`. O banco SQLite de demonstração (`*.sqlite`) fica fora do Git (`.gitignore` local).

## Referências

As referências com DOI vêm do pacote (`docs/arquitetura_fundamentada.md`) e do artigo da equipe. A conferência delas pelo `scripts/verificar_referencias.py` ainda está pendente: até lá, valem como citadas pelas fontes.

- BUNEMAN, P.; TAN, W.-C. Provenance in databases. *SIGMOD 2007*, p. 1171–1173. DOI: 10.1145/1247480.1247646.
- FELLEGI, I. P.; SUNTER, A. B. A theory for record linkage. *Journal of the American Statistical Association*, v. 64, n. 328, p. 1183–1210, 1969. DOI: 10.1080/01621459.1969.10501049.
- PARASURAMAN, R.; MANZEY, D. H. Complacency and bias in human use of automation. *Human Factors*, v. 52, n. 3, p. 381–410, 2010. DOI: 10.1177/0018720810376055.
- SWEENEY, L. k-anonymity: a model for protecting privacy. *IJUFKS*, v. 10, n. 5, p. 557–570, 2002. DOI: 10.1142/S0218488502001648.
- VALENTE, M. T. *Engenharia de Software Moderna*. Edição do autor, 2020. §5.6.3 e §6.5.
- Equipe do PI2. *Histórias de usuário e transformação de dados não estruturados em estruturados para a cobrança tributária municipal*. UFT, out. 2026 (`docs/pesquisa/historias_usuario_tributacao_municipal.pdf`).
- BRASIL. Lei nº 13.709/2018 (LGPD), art. 7º, II e III, e art. 23; Instrução Normativa RFB nº 2.229/2024 (CNPJ alfanumérico).
