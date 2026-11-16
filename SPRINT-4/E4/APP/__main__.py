"""Execução do painel Qt: python -m app.qt [--capturas PASTA]

Sem argumentos, abre a janela com o lote publicado em reports/sprint4/lote e o pacote models/sprint4/v1 (as
pastas podem ser trocadas por PI2_LOTE_SPRINT4 e PI2_MODELOS_SPRINT4, como no Streamlit). A tela Cenários do
M2 lê o experimento publicado em reports/sprint4/m2_cenarios (PI2_CENARIOS_M2 troca a pasta). Com --capturas,
renderiza as nove telas fora da tela e grava uma imagem de cada, para a documentação.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Painel Qt da Sprint 4 (dados sintéticos).")
    parser.add_argument("--capturas", type=Path, help="grava uma imagem de cada tela nesta pasta e sai")
    args = parser.parse_args(argumentos)
    if args.capturas:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from app.qt import tema
    from app.qt.janela import JanelaPrincipal
    from app.qt.servico import Painel, pastas_padrao
    app = QApplication.instance() or QApplication(sys.argv[:1])
    tema.aplicar(app)
    janela = JanelaPrincipal(Painel(*pastas_padrao()))
    if args.capturas:
        janela.resize(1366, 768)
        janela.show()
        for caminho in janela.capturar(args.capturas):
            print(caminho)
        return 0
    janela.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
