# Respaldo acadêmico do M2-Cenários

Referências conferidas em 15/11/2026 nas páginas das editoras, dos autores e em repositórios institucionais. Este anexo foi acrescentado após a execução, para fundamentação bibliográfica. Não altera o protocolo congelado, os modelos ou as métricas. As referências complementares não devem ser apresentadas como se todas constassem do protocolo antes da execução.

A descrição metodológica mais precisa é: **estudo de simulação de Monte Carlo com mecanismo gerador heterogêneo de pagamento, eventos temporalmente coerentes, classificação probabilística regularizada e avaliação temporal sob cenários controlados**. O cadastro de entrada também é sintético. O código é uma implementação própria que combina princípios estabelecidos; não é reprodução integral de um único artigo.

## Referências e alcance

1. **MORRIS, Tim P.; WHITE, Ian R.; CROWTHER, Michael J.** Using simulation studies to evaluate statistical methods. *Statistics in Medicine*, v. 38, n. 11, p. 2074–2102, 2019. DOI: [10.1002/sim.8086](https://doi.org/10.1002/sim.8086).

   É a referência principal para o desenho do experimento: definir objetivo, mecanismo gerador, quantidades de interesse, métodos e medidas de desempenho (ADEMP); executar repetições e explicitar incerteza Monte Carlo. Sustenta a avaliação controlada de métodos sob mecanismos conhecidos. Não estabelece os coeficientes, o número de 20 réplicas ou os limiares de aceite adotados aqui como padrões universais.

2. **BAYNES, Sam; COTTER, Simon L.; RUSSELL, Paul T.; RYAN, Edmund M.; WAITE, Timothy W.** Efficient forecasting and uncertainty quantification for large-scale account level Monte Carlo models of debt recovery. *Journal of the Royal Statistical Society Series C: Applied Statistics*, v. 72, n. 1, p. 188–212, 2023. DOI: [10.1093/jrsssc/qlad008](https://doi.org/10.1093/jrsssc/qlad008).

   É a ligação mais direta com recuperação de dívidas: simulações de modelos estocásticos de pagamento individual e agregação de previsões, considerando heterogeneidade e incerteza. O artigo trata de empréstimos de consumo inadimplidos, não de IPTU de Palmas. Seus métodos de alocação ótima de simulações e emulação por processos gaussianos não foram implementados neste experimento. Sua contribuição sustenta a abordagem geral, não uma equivalência entre implementações.

3. **BELLOTTI, Anthony; BRIGO, Damiano; GAMBETTI, Paolo; VRINS, Frédéric.** Forecasting recovery rates on non-performing loans with machine learning. *International Journal of Forecasting*, v. 37, n. 1, p. 428–444, 2021. DOI: [10.1016/j.ijforecast.2020.06.009](https://doi.org/10.1016/j.ijforecast.2020.06.009).

   Analisa dados de uma agência europeia de cobrança e compara métodos de previsão de taxas de recuperação. Históricos anteriores do processo de recuperação e de pagamentos acrescentam informação preditiva no estudo. Isso motiva investigar atributos comportamentais, mas não valida nossos coeficientes ou sua transferência para tributos municipais. O alvo do artigo é taxa de recuperação de empréstimos, diferente de pagamento integral em 365 dias. Versão dos autores: [repositório UCLouvain](https://research.dial.uclouvain.be/server/api/core/bitstreams/703ad786-9b96-40c1-a8b5-df9b51405e04/content).

4. **BENDER, Ralf; AUGUSTIN, Thomas; BLETTNER, Maria.** Generating survival times to simulate Cox proportional hazards models. *Statistics in Medicine*, v. 24, n. 11, p. 1713–1723, 2005. DOI: [10.1002/sim.2059](https://doi.org/10.1002/sim.2059).

   Fundamenta a relação entre risco, sobrevivência e geração de tempos de evento, incluindo distribuições exponenciais. No experimento, a probabilidade anual p é convertida em taxa diária λ=−ln(1−p)/365; com E~Exponencial(1), o tempo é obtido pela inversão do risco acumulado. O princípio matemático é relacionado ao discutido no artigo. **Não ajustamos um modelo de Cox**, nem reproduzimos integralmente sua especificação de riscos proporcionais. O cenário de mudança usa risco constante por trechos.

5. **LE CESSIE, Saskia; VAN HOUWELINGEN, J. C.** Ridge Estimators in Logistic Regression. *Journal of the Royal Statistical Society Series C: Applied Statistics*, v. 41, n. 1, p. 191–201, 1992. DOI: [10.2307/2347628](https://doi.org/10.2307/2347628).

   Sustenta regressão logística com penalização ridge/L2 para estabilização de estimativas e previsão. A aplicação empírica do artigo é de outra área; ele fundamenta o método estatístico, não uma superioridade universal da logística em cobrança. A página da editora mantém o ano do fascículo de 1992, embora exiba também uma data posterior de disponibilização eletrônica: [Oxford Academic](https://academic.oup.com/jrsssc/article/41/1/191/6990520).

6. **ROBERTS, David R. et al.** Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, v. 40, n. 8, p. 913–929, 2017. DOI: [10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881).

   Fundamenta considerar dependência temporal e agrupamentos na avaliação, com partições adequadas à pergunta de generalização. É respaldo para a decisão de separar períodos e avaliar imóveis reservados. Seu contexto empírico é ecológico; a conexão com o M2 é metodológica. O experimento usa holdouts temporais fixos e um teste separado por imóvel, não uma reprodução de todas as estratégias de validação cruzada do artigo.

7. **GAMA, João; ŽLIOBAITĖ, Indrė; BIFET, Albert; PECHENIZKIY, Mykola; BOUCHACHIA, Abdelhamid.** A survey on concept drift adaptation. *ACM Computing Surveys*, v. 46, n. 4, art. 44, p. 1–37, 2014. DOI: [10.1145/2523813](https://doi.org/10.1145/2523813).

   Fundamenta estudar mudanças na relação entre atributos e resultado ao longo do tempo. O cenário de inversão de efeitos é um estresse explícito desse tipo. Não implementamos métodos de adaptação ao drift; avaliamos a perda de desempenho de um modelo mantido fixo. O artigo não diz que a inversão específica que simulamos ocorrerá em uma carteira real.

8. **BRIER, Glenn W.** Verification of Forecasts Expressed in Terms of Probability. *Monthly Weather Review*, v. 78, n. 1, p. 1–3, 1950. DOI: [10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2](https://doi.org/10.1175/1520-0493%281950%29078%3C0001%3AVOFEIT%3E2.0.CO%3B2).

   É a referência fundadora da avaliação quadrática de previsões probabilísticas. No caso binário, utilizamos a convenção Brier=mean((p−y)²). O escore original soma sobre as categorias; na forma binária completa isso difere por fator constante da convenção usual implementada. A redução relativa usada no relatório não é afetada por esse fator. Um Brier menor não demonstra sozinho melhor calibração; por isso também mostramos frequências observadas por faixa de probabilidade.

## O que estas referências não demonstram

- Que 12% seja a taxa real de recuperação de IPTU em Palmas.
- Que os coeficientes 1,5, −0,7 e −1,1 correspondam a relações empíricas locais.
- Que AUC 0,783 ou lift 3,13 serão reproduzidos em dados reais.
- Que a regeneração de pagamentos tenha melhorado o modelo sobre os mesmos rótulos originais.
- Que logística seja superior a outros algoritmos em qualquer mecanismo: o gerador com logito linear favorece essa família.

Há respaldo para **realizar e relatar o estudo de simulação**. A validade aplicada dos valores e efeitos exige dados reais e validação externa. As hipóteses numéricas usadas continuam explicitamente experimentais.

## Formulação sugerida para o texto acadêmico

“Realizou-se um estudo de simulação de Monte Carlo estruturado segundo ADEMP (Morris, White e Crowther, 2019), com regeneração de tempos de pagamento sob mecanismos heterogêneos previamente especificados. A utilização de modelos estocásticos individuais em recuperação de dívidas encontra precedente em Baynes et al. (2023). Compararam-se modelos probabilísticos com uma referência constante, empregando avaliação temporal e um teste adicional em imóveis excluídos do desenvolvimento. Os resultados demonstram desempenho sob os mecanismos simulados, sem constituir validação empírica da recuperabilidade real da dívida ativa municipal.”
