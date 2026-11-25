"""Gera a tabela SINTÉTICA de imóveis protegidos pelo IPTU Social (Sprint 5, E3).

Premissa declarada: a base da Sprint 3 não tem dados de pessoas. Esta tabela é
uma simulação separada, com semente própria, para não alterar os hashes do
gerador da Sprint 3 nem os pacotes de modelos da Sprint 4.

Ela guarda só o id_imovel e indicadores sim/não: nenhum dado pessoal (LGPD).
As taxas abaixo são PREMISSAS, não observações de Palmas. Troque pelo cadastro
real da Sefin se ele for obtido.
"""
import numpy as np
import pandas as pd

SEMENTE = 20261125          # própria desta tabela; não reutiliza a semente da Sprint 3
N_IMOVEIS = 111_252         # ids 1..111252, conferidos nos arquivos M1 e M2
TAXAS = {                   # premissas (fração de imóveis com o perfil)
    "idoso": 0.14,
    "aposentado": 0.10,
    "pensionista": 0.04,
    "pcd_baixa_renda": 0.03,
}


def gerar(n: int = N_IMOVEIS, semente: int = SEMENTE) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    tabela = pd.DataFrame({"id_imovel": np.arange(1, n + 1)})
    for perfil, taxa in TAXAS.items():
        tabela[perfil] = (rng.random(n) < taxa).astype(int)
    tabela["protegido_iptu_social"] = tabela[list(TAXAS)].max(axis=1)
    tabela["origem_dado"] = "SINTETICO"
    return tabela


if __name__ == "__main__":
    t = gerar()
    t.to_csv("protegidos_iptu_social.csv", index=False)
    print(t[list(TAXAS) + ["protegido_iptu_social"]].mean().round(4))
    print("imóveis protegidos:", int(t["protegido_iptu_social"].sum()), "de", len(t))
