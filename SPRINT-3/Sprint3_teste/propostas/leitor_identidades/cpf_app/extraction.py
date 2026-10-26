"""Porta de extração e adaptador local de TXT/PDF com camada textual."""
from dataclasses import dataclass
from io import BytesIO
import re
from typing import Protocol

from .domain import normalize_cpf, valid_cpf


@dataclass(frozen=True)
class Candidate:
    cpf: str
    page: int
    start: int
    end: int
    evidence: str
    consistent: bool


@dataclass(frozen=True)
class Extraction:
    candidates: list[Candidate]
    requires_ocr: bool


class Extractor(Protocol):
    version: str
    def extract(self, content: bytes, suffix: str) -> Extraction: ...


class LocalTextExtractor:
    version = 'pdf-text-regex-1'
    pattern = re.compile(r'(?<![0-9])(?:[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}|[0-9]{11})(?![0-9])')

    def extract(self, content: bytes, suffix: str) -> Extraction:
        if suffix == '.txt':
            pages = [content.decode('utf-8-sig')]
        elif suffix == '.pdf':
            from pypdf import PdfReader
            pdf = PdfReader(BytesIO(content))
            if pdf.is_encrypted or len(pdf.pages) > 30:
                raise ValueError('PDF criptografado ou acima de 30 páginas')
            pages = [p.extract_text() or '' for p in pdf.pages]
        else:
            raise ValueError('Somente TXT UTF-8 e PDF são suportados')
        if sum(map(len, pages)) > 1_000_000:
            raise ValueError('Texto acima do limite do demonstrador')
        candidates = []
        for page, text in enumerate(pages, 1):
            for m in self.pattern.finditer(text):
                candidates.append(Candidate(normalize_cpf(m[0]), page, m.start(), m.end(),
                                            text[max(0, m.start()-60):m.end()+60], valid_cpf(m[0])))
        # Qualquer página vazia pode conter imagem ainda não lida; não liberar vínculo.
        return Extraction(candidates, not pages or any(not t.strip() for t in pages))
