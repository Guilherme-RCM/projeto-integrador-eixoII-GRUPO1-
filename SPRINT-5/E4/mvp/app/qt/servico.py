"""Serviço do painel Qt: a ponte entre a interface e pipeline.ml.painel, sem regra de negócio nova.

A interface Qt não lê arquivo nem calcula indicador por conta própria; pede tudo a esta classe, que só
encadeia as funções puras já testadas do painel (as mesmas do Streamlit) e guarda o lote carregado. Por isso,
os números da interface principal e os da reserva são sempre os mesmos. Os textos e os formatos vêm de
pipeline.ml.explicacoes, pipeline.ml.filtros e pipeline.ml.formatos, também comuns às duas interfaces
(ADR-ML-15). Nada aqui importa o Qt, e por isso o serviço é testado sem janela.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

from pipeline.ml import cenarios, painel, receita
from pipeline.ml import explicacoes as ex
from pipeline.ml import filtros as fl
from pipeline.ml.formatos import NOMES_FAIXA, NOMES_MODELO, decimal, numero, percentual, pontos
from pipeline.ml.painel import ErroLote, Lote, Selecao
from pipeline.vetorial import painel as painel_vetorial

__all__ = ["FAIXAS", "MEDIDAS", "NOMES_FAIXA", "NOMES_MODELO", "Estado", "Painel", "decimal", "numero", "percentual",
           "pontos", "pasta_cenarios_padrao", "pasta_sprint3_padrao", "pastas_padrao", "pastas_vetorial_padrao"]

RAIZ = Path(__file__).resolve().parent.parent.parent
FAIXAS = fl.FAIXAS
MEDIDAS = ex.MEDIDAS


def pastas_padrao() -> tuple[Path, Path]:
    """As mesmas pastas e variáveis de ambiente do painel Streamlit."""
    return (Path(os.environ.get("PI2_LOTE_SPRINT4", RAIZ / "reports" / "sprint4" / "lote")),
            Path(os.environ.get("PI2_MODELOS_SPRINT4", RAIZ / "models" / "sprint4" / "v1")))


def pasta_cenarios_padrao() -> Path:
    """Pasta do experimento M2-Cenários publicado (ADR-ML-12); PI2_CENARIOS_M2 a troca, como nos testes."""
    return Path(os.environ.get("PI2_CENARIOS_M2", RAIZ / "reports" / "sprint4" / "m2_cenarios"))


def pasta_sprint3_padrao() -> Path:
    """Dados publicados do dashboard da Sprint 3 (ADR-ML-14); PI2_PAINEL_SPRINT3 troca a pasta."""
    return Path(os.environ.get("PI2_PAINEL_SPRINT3", RAIZ / "reports" / "sprint4" / "painel_sprint3"))


def pastas_vetorial_padrao() -> tuple[Path, Path]:
    """Relatórios e pacote da base vetorial (ADR-ML-10); PI2_VETORIAL_RELATORIOS e PI2_VETORIAL_MODELOS as trocam."""
    return (Path(os.environ.get("PI2_VETORIAL_RELATORIOS", RAIZ / "reports" / "sprint4" / "base_vetorial")),
            Path(os.environ.get("PI2_VETORIAL_MODELOS", RAIZ / "models" / "sprint4" / "vetorial-v1")))


@dataclass(frozen=True)
class Estado:
    """O que o analista escolheu: filtros, ordenação do ranking e quantos devedores mostrar."""
    regioes: tuple[str, ...] = ()
    faixas: tuple[str, ...] = ()
    setores: tuple[str, ...] = ()
    ordem: str = "valor_esperado"
    k: int = fl.QUANTIDADE_PADRAO

    def filtro(self) -> painel.Filtro:
        return painel.Filtro(self.regioes, self.setores, self.faixas)

    def com(self, **mudancas: object) -> Estado:
        return replace(self, **mudancas)  # type: ignore[arg-type]


@dataclass
class Painel:
    """Lote carregado e verificado, com as consultas que as telas fazem."""
    pasta_lote: Path
    pasta_modelos: Path
    lote: Lote | None = None
    assinatura: str = ""
    erros: list[str] = field(default_factory=list)
    pasta_cenarios: Path = field(default_factory=pasta_cenarios_padrao)
    experimento: cenarios.Cenarios | None = None
    pasta_sprint3: Path = field(default_factory=pasta_sprint3_padrao)
    pastas_vetorial: tuple[Path, Path] = field(default_factory=pastas_vetorial_padrao)
    dados_sprint3: receita.Receita | None = None
    base_vetorial: painel_vetorial.Vetorial | None = None

    def carregar(self) -> Lote:
        """Lê o lote ativo pela mesma função do Streamlit; ErroLote sobe com a mensagem clara do painel."""
        # "Atualizar dados" também confere de novo as publicações que as telas complementares leem
        self.experimento, self.dados_sprint3, self.base_vetorial = None, None, None
        self.assinatura = painel.assinatura_lote(self.pasta_lote, self.pasta_modelos)
        self.lote = painel.carregar_lote(self.pasta_lote, self.pasta_modelos)
        return self.lote

    def m2_cenarios(self) -> cenarios.Cenarios:
        """O experimento M2-Cenários, conferido contra o manifesto na primeira consulta; ErroCenarios se recusado.

        É independente do lote: os números dele vêm de pagamentos simulados de novo e nunca entram no ranking,
        no mapa nem na projeção.
        """
        if self.experimento is None:
            self.experimento = cenarios.carregar(self.pasta_cenarios)
        return self.experimento

    def sprint3(self) -> receita.Receita:
        """Dados do dashboard da Sprint 3, conferidos contra o manifesto; ErroReceita se recusados."""
        if self.dados_sprint3 is None:
            self.dados_sprint3 = receita.carregar(self.pasta_sprint3)
        return self.dados_sprint3

    def vetorial(self) -> painel_vetorial.Vetorial:
        """Relatórios da base vetorial, com o pacote conferido arquivo por arquivo; ErroVetorial se recusados."""
        if self.base_vetorial is None:
            self.base_vetorial = painel_vetorial.carregar(*self.pastas_vetorial)
        return self.base_vetorial

    def exigir(self) -> Lote:
        if self.lote is None:
            raise ErroLote("nenhum lote carregado")
        return self.lote

    def ha_lote_novo(self) -> bool:
        """O ponteiro ou o pacote mudaram desde a última carga (outra publicação, por exemplo)."""
        return painel.assinatura_lote(self.pasta_lote, self.pasta_modelos) != self.assinatura

    def manifesto(self) -> dict:
        return self.exigir().manifesto

    def opcoes(self) -> dict[str, list[str]]:
        """As opções de cada filtro: regiões e setores com devedor na carteira, e as três faixas."""
        return fl.opcoes(self.exigir())

    def rotulos_filtros(self) -> dict[str, dict[str, str]]:
        """O texto de cada opção dos filtros, com quantos devedores da carteira ela reúne."""
        return fl.rotulos(self.exigir())

    def resumo_filtros(self, estado: Estado, sel: Selecao) -> str:
        """O que está filtrado e quantos devedores restaram, na frase que as duas interfaces mostram."""
        return fl.resumo(estado.filtro(), len(sel.devedores), len(self.exigir().devedores))

    def nomes_faixa(self) -> dict[str, str]:
        return painel.legenda_faixas(self.manifesto()["politica"])

    def selecionar(self, estado: Estado) -> Selecao:
        return painel.selecionar(self.exigir(), estado.filtro())

    def indicadores(self, sel: Selecao) -> dict:
        return painel.projecao(sel.creditos)

    def faixas(self, sel: Selecao) -> pd.DataFrame:
        return painel.por_faixa(sel.devedores)

    def ranking(self, sel: Selecao, estado: Estado) -> pd.DataFrame:
        return painel.ranking(sel.devedores, estado.ordem, estado.k)

    def mapa(self, sel: Selecao) -> pd.DataFrame:
        return painel.mapa_setores(sel.risco, sel.creditos, int(self.manifesto()["politica"]["k_minimo_imoveis"]))

    def creditos_do_devedor(self, sel: Selecao, id_imovel: object) -> pd.DataFrame:
        return painel.creditos_do_devedor(sel.creditos, id_imovel)

    def exportar(self, sel: Selecao, caminho: Path) -> int:
        """Os créditos dos devedores selecionados, no mesmo formato da exportação do Streamlit."""
        Path(caminho).write_bytes(painel.csv_creditos(sel.creditos))
        return len(sel.creditos)

    def comparacao_no_teste(self) -> pd.DataFrame:
        return ex.comparacao_no_teste(self.exigir())

    def achado_m2(self) -> dict | None:
        return painel.achado_m2(self.exigir())

    def precisao_no_topo(self, fracao: float = 0.1) -> float:
        return painel.precisao_no_topo(self.exigir().risco, fracao)
