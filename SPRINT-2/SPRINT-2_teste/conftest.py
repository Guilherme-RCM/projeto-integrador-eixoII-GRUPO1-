"""Garante que os pacotes etl/ e src/ sejam importáveis nos testes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
