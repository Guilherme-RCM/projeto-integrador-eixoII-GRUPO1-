# Arquitetura de referência do leitor de CPF

MVP local para a HU-04: importar um documento, preservar ocorrências de CPF, validar os dígitos, revisar a evidência e registrar um vínculo com um crédito fictício.

Implementação em Python 3.11+ com SQLite. Use somente documentos sintéticos neste demonstrador. O parâmetro `--actor` simula identidades; não é autenticação. O banco contém documento e identificadores em texto claro e não deve receber cadastros reais.

## Executar

No terminal, entre nesta pasta e execute:

```powershell
python -m pip install -r requirements.txt
python -m cpf_app seed-demo
python -m cpf_app ingest examples/requerimento_sintetico.txt
python -m cpf_app inspect 1
python -m cpf_app decide 1 --version 1 --approve --candidate 1 --credit IPTU-DEMO-A --subject-confirmed --reason "Conferidos titular e credito ficticios"
python -m cpf_app inspect 1
python -m unittest discover -s tests -v
```

Os IDs acima pressupõem banco `demo.sqlite` novo. Use os IDs retornados por `ingest` e `inspect` ao trabalhar com outro banco. `--db caminho.sqlite` deve preceder o subcomando. Rejeitar: `python -m cpf_app decide 1 --version 1 --reason "Solicitada complementacao"`.

## Módulos e decisões

| Arquivo | Responsabilidade |
|---|---|
| `cpf_app/domain.py` | Formato, dígitos verificadores, função e unidade permitidas |
| `cpf_app/extraction.py` | Porta `Extractor`, leitura TXT/PDF textual, evidência por página e posição no texto |
| `cpf_app/service.py` | Importação, inspeção e decisão; invariantes do vínculo e transação |
| `cpf_app/storage.py` | Esquema SQLite, unicidade, chaves estrangeiras e eventos |
| `cpf_app/__main__.py` | Interface de linha de comando e atores simulados |
| `tests/test_workflow.py` | Casos negativos, isolamento, atomicidade e decisão desatualizada |

`service.py` usa SQL do adaptador SQLite diretamente: é uma camada de aplicação pragmática, não uma implementação completa de arquitetura hexagonal. A porta de extração permite substituir o leitor textual; migrar a persistência ainda requer refatorar o serviço.

## Estados e contratos

Importação -> `REVIEW`, `OCR_REQUIRED` ou `NO_CPF`. Só `REVIEW` pode ser aprovado. Todos os três podem ser rejeitados com justificativa. `APPROVED` e `REJECTED` são terminais nesta versão; corrigir a fonte ou mudar a versão do extrator produz outra avaliação. Não há reabertura de decisão implementada.

A aprovação exige candidato do mesmo documento, dígitos consistentes, crédito da mesma unidade e CPF, confirmação explícita do papel do titular, justificativa e versão atual. O sistema não deduz se a pessoa é titular ou representante: essa conferência é humana. Vínculo, estado e evento são confirmados na mesma transação. Um documento admite um vínculo neste MVP; pedidos sobre múltiplos créditos exigem extensão do esquema.

Unicidade: `(unidade, SHA-256 do arquivo, versão do extrator, versão das regras)`. O arquivo original fica como BLOB no SQLite. A evidência textual não possui coordenadas geométricas; `start/end` são posições na string extraída da página. A extração é síncrona e pode ser repetida antes da consulta de deduplicação; a persistência é idempotente.

## Implementado e pendente

- Implementado: TXT UTF-8, PDF com texto, múltiplas ocorrências, checksum, revisão explícita, escopo por unidade, bloqueio de escrita do auditor, transações, versões, trilha de importação e decisão.
- PDF sem texto em qualquer página: `OCR_REQUIRED`; nenhum motor OCR é executado. PDF misto com imagem e texto na mesma página pode não ser identificado como incompleto.
- Pendente: OCR real e sua avaliação; interface visual; autenticação institucional; integração municipal; papel de representante; revisão/revogação; auditoria de leitura; criptografia e gestão de chaves; retenção e eliminação; proteção contra documentos maliciosos; restauração e carga concorrente.
- A trilha usa triggers para bloquear UPDATE/DELETE normais, mas um administrador do arquivo SQLite pode remover os controles. Não é log inviolável.
- Nenhum ato de cobrança, baixa de crédito, negociação ou consulta à Receita Federal é executado. A HU-06 e a HU-07 são pontos de integração futura.

## Fundamentação e implantação

Leia `docs/arquitetura_fundamentada.md` e `docs/arquitetura_leitor_cpf_fundamentada.pdf`. A justificativa contém quatro argumentos, quatro críticas com mitigação, desenho de implantação e 11 referências com DOI. O código é uma prova das regras do fluxo, não evidência de redução de inadimplência ou homologação para produção.

Foram aprovados 13 testes e um fluxo de demonstração pela CLI. Os registros estão em `docs/validacao.txt` e `docs/demo_execucao.txt`. A regeneração opcional do PDF usa `docs/gerar_relatorio.py`, requer `reportlab` e `pypdfium2`, além das fontes Times do Windows; essas dependências de documentação não são necessárias para executar o aplicativo.
