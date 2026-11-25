\# E3 — Proteção do IPTU Social (Sprint 5)



Exclui os imóveis protegidos (idosos, aposentados, pensionistas e PcD de baixa

renda) das ações preditivas de cobrança, com teste automatizado que comprova.



\## Arquivos

\- `gerar\_protegidos\_iptu\_social.py`: gera a tabela SINTÉTICA de imóveis protegidos.

\- `protecao\_iptu\_social.py`: duas travas, fora do modelo. Entrada (`excluir\_protegidos`) e saída (`validar\_lista\_cobranca`).

\- `test\_protecao\_iptu\_social.py`: 5 testes (pytest).



\## Como rodar

```

pip install pytest pandas numpy

python gerar\_protegidos\_iptu\_social.py

python -m pytest -v

```



\## Evidência

\- Código correto: 5 passed.

\- Trava de entrada sabotada de propósito: 2 failed, 3 passed. O teste apontou 31.089 imóveis protegidos na lista. Após desfazer a sabotagem: 5 passed.



\## Limites declarados

\- A base da Sprint 3 não tem dados de pessoas. A tabela de protegidos é SINTÉTICA, com semente própria. As taxas são premissas, não dados de Palmas.

\- O teste prova o mecanismo, não a identificação de beneficiários reais.

\- O módulo ainda NÃO está ligado ao pipeline `pipeline.ml` da Sprint 4. Os testes usam uma carteira simulada.

\- "PcD de baixa renda" está como indicador sim/não. Falta conferir se a lei de Palmas define um corte de renda.

