"""Quality gates: o G14 roda sem o bruto real, como no CI, com os exercícios da mini-Palmas."""
import importlib.util
import sys
from pathlib import Path

import pytest

from pipeline.camadas import Camadas

pytestmark = pytest.mark.sprint3
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "quality_gate.py"


def test_g14_sem_bruto_real_transforma_a_mini_palmas_com_os_parametros_dela(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))   # o script insere a raiz no sys.path ao ser carregado
    spec = importlib.util.spec_from_file_location("quality_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    quality_gate = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "quality_gate", quality_gate)   # o @dataclass procura o módulo aqui
    spec.loader.exec_module(quality_gate)
    monkeypatch.setattr(Camadas, "do_projeto", classmethod(lambda _cls: Camadas(tmp_path)))   # sem data/bruto, como no CI

    gate = quality_gate.gate_reprodutibilidade()

    assert gate.passou is True, gate.detalhes
    assert "mini-Palmas" in gate.obtido
