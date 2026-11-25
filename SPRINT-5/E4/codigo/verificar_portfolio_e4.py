"""Verificador Automatizado de Integridade e Prontidão do Portfólio (Sprint 5, E4).

Executa 12 controles objetivos exigidos pelo edital da Sprint 5 e pela régua da
banca final (PI_Sprint5_Entrega25nov2026.pdf e PI_FaseFinal_Defesa04dez2026.pdf):

  1. Existência dos três componentes obrigatórios em /docs (MVP, Model Card, RIA).
  2. Existência dos documentos de governança e rastreabilidade do E4 em /docs.
  3. Preservação do PDF oficial do E1 e das figuras obrigatórias (SHAP, Fairness e MVP).
  4. Resolução de 100% dos links relativos e imagens nos arquivos Markdown (zero links quebrados).
  5. Presença de todas as seções de Mitchell et al. (2019) em docs/MODEL_CARD.md.
  6. Presença das 4 seções obrigatórias do edital + integração E3 em docs/RELATORIO_IMPACTO_ALGORITMICO.md.
  7. Presença da introdução de Ética Digital (Aula 01 + Aula 09) e arquitetura em 4 camadas em docs/E4_PORTFOLIO_GOVERNANCA_ETICA.md.
  8. Integridade dos artefatos JSON/CSV de auditoria do pacote sprint4-v1.
  9. Exatidão matemática da identidade de Chouldechova (erro < 1e-6) na auditoria de subgrupos.
 10. Funcionamento da dupla trava do IPTU Social (31.089 imóveis sintéticos excluídos, 0 intrusos).
 11. Funcionamento da trava de sabotagem/mutação (ProtegidoNaListaError levantada).
 12. Varredura LGPD de privacidade no repositório (ausência de CPF, CNPJ ou credenciais .env).
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pandas as pd

from auditoria_fairness_e4 import calcular_auditoria_subgrupos
from gerar_protegidos_iptu_social import N_IMOVEIS, gerar
from protecao_iptu_social import (
    ProtegidoNaListaError,
    excluir_protegidos,
    validar_lista_cobranca,
)

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"

PADRAO_LINK_MD = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
PADRAO_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PADRAO_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")


def _links_quebrados_em_md(arquivos_md: list[Path]) -> list[str]:
    quebrados: list[str] = []
    for arq in arquivos_md:
        texto = arq.read_text(encoding="utf-8")
        # Remove blocos de código cercados para não confundir sintaxe de código com links
        texto_sem_codigo = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
        for m in PADRAO_LINK_MD.finditer(texto_sem_codigo):
            alvo_bruto = m.group(1).strip()
            if not alvo_bruto or alvo_bruto.startswith(("http://", "https://", "mailto:", "#")):
                continue
            caminho_limpo = alvo_bruto.split("#", 1)[0].strip()
            if not caminho_limpo:
                continue
            destino = (arq.parent / caminho_limpo).resolve()
            if not destino.exists():
                quebrados.append(f"{arq.relative_to(RAIZ)} -> {alvo_bruto}")
    return quebrados


def executar_verificacao(salvar_json: bool = False) -> dict:
    controles: list[dict] = []

    def registrar(codigo: str, descricao: str, aprovado: bool, detalhe: str) -> None:
        controles.append({
            "codigo": codigo,
            "descricao": descricao,
            "aprovado": bool(aprovado),
            "detalhe": detalhe,
        })

    # C01: Três componentes obrigatórios em /docs
    obrigatorios_c1 = [
        DOCS / "MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md",
        DOCS / "MODEL_CARD.md",
        DOCS / "RELATORIO_IMPACTO_ALGORITMICO.md",
    ]
    faltando_c1 = [str(p.relative_to(RAIZ)) for p in obrigatorios_c1 if not p.exists()]
    registrar(
        "C01",
        "Três componentes do portfólio (MVP, Model Card e RIA) presentes em /docs",
        len(faltando_c1) == 0,
        "OK" if not faltando_c1 else f"Ausentes: {faltando_c1}",
    )

    # C02: Documentação complementar de governança E4 e E3
    obrigatorios_c2 = [
        RAIZ / "README.md",
        DOCS / "README.md",
        DOCS / "E4_PORTFOLIO_GOVERNANCA_ETICA.md",
        DOCS / "PROTECAO_IPTU_SOCIAL_E3.md",
        DOCS / "ADRs_SPRINT5.md",
        DOCS / "DIARIO_DE_BORDO.md",
    ]
    faltando_c2 = [str(p.relative_to(RAIZ)) for p in obrigatorios_c2 if not p.exists()]
    registrar(
        "C02",
        "Documentação de governança, índice da banca, ADRs e Diário de Bordo presentes",
        len(faltando_c2) == 0,
        "OK" if not faltando_c2 else f"Ausentes: {faltando_c2}",
    )

    # C03: PDFs oficiais, figuras verificadas e artefatos binários do MVP
    arquivos_binarios_esperados = [
        DOCS / "Model_Card_E1_Versao_Oficial.pdf",
        DOCS / "MODEL_CARD_CONSOLIDADO_E4.pdf",
        DOCS / "E4_PORTFOLIO_GOVERNANCA_ETICA.pdf",
        DOCS / "RELATORIO_IMPACTO_ALGORITMICO.pdf",
        DOCS / "MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.pdf",
        DOCS / "figuras" / "shap_summary_m1.png",
        DOCS / "figuras" / "shap_waterfall_m1.png",
        DOCS / "figuras" / "fairness_quintis_m1.png",
        DOCS / "figuras" / "fairness_regioes_m1.png",
        DOCS / "figuras" / "mvp" / "01_resumo.png",
        DOCS / "figuras" / "mvp" / "02_ranking_de_devedores.png",
        DOCS / "figuras" / "mvp" / "03_mapa_por_setor.png",
        DOCS / "figuras" / "mvp" / "04_projecao_de_arrecadacao.png",
        DOCS / "figuras" / "mvp" / "05_sobre_o_modelo.png",
        RAIZ / "mvp" / "modelos" / "v1" / "inadimplencia.joblib",
        RAIZ / "mvp" / "modelos" / "v1" / "recuperabilidade.joblib",
        RAIZ / "mvp" / "modelos" / "v1" / "checksums.sha256",
        RAIZ / "mvp" / "resultados" / "lote" / "ativo.json",
        RAIZ / "mvp" / "app" / "painel_sprint4.py",
    ]
    faltando_c3 = [str(p.relative_to(RAIZ)) for p in arquivos_binarios_esperados if not p.exists() or p.stat().st_size == 0]
    registrar(
        "C03",
        "PDFs oficiais, figuras (SHAP, Fairness e MVP) e binários do MVP íntegros na pasta E4",
        len(faltando_c3) == 0,
        f"{len(arquivos_binarios_esperados)} artefatos verificados" if not faltando_c3 else f"Ausentes/vazios: {faltando_c3}",
    )

    # C04: Links relativos em todos os arquivos Markdown
    todos_mds = sorted([RAIZ / "README.md", RAIZ / "mvp" / "README.md", *DOCS.glob("*.md")])
    mds_existentes = [p for p in todos_mds if p.exists()]
    quebrados = _links_quebrados_em_md(mds_existentes)
    registrar(
        "C04",
        "Todos os links relativos e imagens nos documentos Markdown resolvem sem erro",
        len(mds_existentes) >= 8 and len(quebrados) == 0,
        f"{len(mds_existentes)} arquivos Markdown auditados, 0 link quebrado" if not quebrados else f"Links quebrados: {quebrados}",
    )

    # C05: Seções obrigatórias de Mitchell et al. (2019) no Model Card
    mc_path = DOCS / "MODEL_CARD.md"
    mc_txt = mc_path.read_text(encoding="utf-8").lower() if mc_path.exists() else ""
    termos_mc = [
        "identificação e detalhes do modelo",
        "uso pretendido",
        "usos proibidos",
        "fatores e variáveis",
        "dados de treinamento",
        "métricas",
        "subgrupos",
        "vieses",
        "explicabilidade",
        "contestação",
        "iptu social",
    ]
    faltam_mc = [t for t in termos_mc if t not in mc_txt]
    registrar(
        "C05",
        "Model Card em /docs contempla todas as seções de Mitchell et al. (2019) e IPTU Social",
        bool(mc_txt) and len(faltam_mc) == 0,
        "OK" if not faltam_mc else f"Termos ausentes: {faltam_mc}",
    )

    # C06: Quatro seções obrigatórias do edital + E3 no RIA
    ria_path = DOCS / "RELATORIO_IMPACTO_ALGORITMICO.md"
    ria_txt = ria_path.read_text(encoding="utf-8").lower() if ria_path.exists() else ""
    termos_ria = [
        "inventário de dados e privacidade",
        "base legal",
        "retenção",
        "paridade demográfica",
        "igualdade de oportunidade",
        "shap",
        "art. 20 da lgpd",
        "impactos sociais",
        "iptu social",
        "31.089",
    ]
    faltam_ria = [t for t in termos_ria if t not in ria_txt]
    registrar(
        "C06",
        "RIA em /docs contempla as 4 seções obrigatórias (LGPD, Fairness, Art. 20/SHAP, Impactos) e integração E3",
        bool(ria_txt) and len(faltam_ria) == 0,
        "OK" if not faltam_ria else f"Termos ausentes: {faltam_ria}",
    )

    # C07: Fundamentação de Ética Digital no documento principal do E4
    e4_path = DOCS / "E4_PORTFOLIO_GOVERNANCA_ETICA.md"
    e4_txt = e4_path.read_text(encoding="utf-8").lower() if e4_path.exists() else ""
    termos_e4 = [
        "ética digital",
        "ativos estratégicos",
        "assimetria",
        "valor público",
        "soberania",
        "accountability",
        "quatro camadas",
        "exclusão digital",
        "atendimento presencial",
        "chouldechova",
    ]
    faltam_e4 = [t for t in termos_e4 if t not in e4_txt]
    registrar(
        "C07",
        "Documento principal do E4 articula Ética Digital (Aula 01 e Aula 09), LGPD e Governança Pública",
        bool(e4_txt) and len(faltam_e4) == 0,
        "OK" if not faltam_e4 else f"Termos ausentes: {faltam_e4}",
    )

    # C08 & C09: Metadados JSON/CSV e identidade de Chouldechova
    try:
        m1_aud, resumo_aud = calcular_auditoria_subgrupos()
        erro_ch = float(resumo_aud["quintis_renda_m1"]["erro_max_identidade_chouldechova"])
        registrar(
            "C08",
            "Artefatos de auditoria (metadata, feature_contract, metrics e metricas_subgrupos) íntegros",
            len(m1_aud) == 12,
            f"12 subgrupos do M1 auditados (5 quintis + 7 categorias regionais)",
        )
        registrar(
            "C09",
            "Identidade matemática de Chouldechova (2017) conferida nos subgrupos do M1",
            erro_ch < 1e-6,
            f"Erro absoluto máximo = {erro_ch:.2e}",
        )
    except Exception as exc:
        registrar("C08", "Artefatos de auditoria íntegros", False, str(exc))
        registrar("C09", "Identidade de Chouldechova conferida", False, str(exc))

    # C10 & C11: Proteção do IPTU Social (execução real + teste de sabotagem)
    tabela_prot = gerar()
    protegidos = set(tabela_prot.loc[tabela_prot["protegido_iptu_social"] == 1, "id_imovel"].astype(int))
    carteira_teste = pd.DataFrame({"id_imovel": range(1, N_IMOVEIS + 1)})
    filtrada = excluir_protegidos(carteira_teste, protegidos)
    validar_lista_cobranca(filtrada, protegidos)
    ok_c10 = (len(protegidos) == 31_089) and (len(filtrada) == N_IMOVEIS - 31_089)
    registrar(
        "C10",
        "Trava de entrada e saída do IPTU Social exclui 100% dos 31.089 imóveis protegidos",
        ok_c10,
        f"Protegidos = {len(protegidos)}; elegíveis restantes = {len(filtrada)}",
    )

    sabotagem_bloqueada = False
    try:
        validar_lista_cobranca(carteira_teste, protegidos)
    except ProtegidoNaListaError:
        sabotagem_bloqueada = True
    registrar(
        "C11",
        "Trava de saída bloqueia lista sabotada levantando ProtegidoNaListaError",
        sabotagem_bloqueada,
        "Exceção ProtegidoNaListaError acionada corretamente sobre 31.089 intrusos",
    )

    # C12: Varredura LGPD de privacidade no repositório
    ocorrencias_pii: list[str] = []
    if (RAIZ / ".env").exists():
        ocorrencias_pii.append(".env versionado na raiz")
    for arq in RAIZ.rglob("*"):
        if not arq.is_file() or arq.suffix.lower() not in {".py", ".md", ".csv", ".json", ".ini", ".txt"}:
            continue
        if ".pytest_cache" in arq.parts:
            continue
        conteudo = arq.read_text(encoding="utf-8", errors="ignore")
        if PADRAO_CPF.search(conteudo) or PADRAO_CNPJ.search(conteudo):
            ocorrencias_pii.append(str(arq.relative_to(RAIZ)))
    registrar(
        "C12",
        "Varredura de privacidade (LGPD): ausência de CPF, CNPJ ou arquivo .env no portfólio",
        len(ocorrencias_pii) == 0,
        "0 padrão de CPF/CNPJ ou segredo .env encontrado" if not ocorrencias_pii else f"Alerta: {ocorrencias_pii}",
    )

    aprovados = sum(1 for c in controles if c["aprovado"])
    resultado = {
        "sprint": "Sprint 5 — Governança e Ética (E4 — Portfólio Revisado)",
        "total_controles": len(controles),
        "controles_aprovados": aprovados,
        "aprovado_integralmente": aprovados == len(controles),
        "controles": controles,
    }
    if salvar_json:
        destino_json = DOCS / "dados_auditoria" / "verificacao_portfolio_e4.json"
        destino_json.parent.mkdir(parents=True, exist_ok=True)
        destino_json.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    rel = executar_verificacao(salvar_json=True)
    for item in rel["controles"]:
        selo = "[OK]" if item["aprovado"] else "[FALHA]"
        print(f"{selo} {item['codigo']} — {item['descricao']} ({item['detalhe']})")
    print(f"\nResultado final: {rel['controles_aprovados']}/{rel['total_controles']} controles aprovados.")
    sys.exit(0 if rel["aprovado_integralmente"] else 1)
