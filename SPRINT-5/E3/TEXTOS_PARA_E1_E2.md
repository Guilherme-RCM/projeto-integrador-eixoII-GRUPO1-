\# Textos do E3 para o Model Card (E1) e o RIA (E2)



\## Para o Model Card — "Usos proibidos"

\- O sistema NÃO pode ser usado para priorizar ou direcionar ações de cobrança contra imóveis protegidos pelo IPTU Social (idosos, aposentados, pensionistas e pessoas com deficiência de baixa renda).

\- A exclusão é feita fora do modelo, por duas travas: filtro dos créditos antes da pontuação e validação da lista final de cobrança. Um teste automatizado (pytest) falha se algum protegido aparecer.



\## Para o RIA — "Impactos sociais" e premissas

\- A base da Sprint 3 é sintética e não tem dados de pessoas (idade, aposentadoria, pensão, deficiência ou renda individual).

\- A tabela de protegidos é uma simulação separada, com semente própria. Guarda só o id do imóvel e indicadores sim/não (sem dado pessoal, o que ajuda na LGPD).

\- As taxas usadas (cerca de 14% idosos, 10% aposentados, 4% pensionistas, 3% PcD de baixa renda; 27,94% de imóveis protegidos) são premissas, NÃO dados de Palmas.

\- O teste prova que o mecanismo de exclusão funciona. Não prova que os beneficiários reais foram identificados.

\- Limitação: o mecanismo ainda não foi ligado ao pipeline da Sprint 4. Recomendação: antes de uso real, obter o cadastro da Sefin, ligar as travas ao pipeline e conferir se a lei de Palmas define corte de renda para PcD.

