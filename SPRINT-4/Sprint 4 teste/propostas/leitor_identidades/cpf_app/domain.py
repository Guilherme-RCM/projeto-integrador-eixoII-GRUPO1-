"""Regras puras: não dependem de OCR, interface ou banco."""
from dataclasses import dataclass
import re

RULE_VERSION = 'cpf-rules-1'


class RuleError(ValueError):
    pass


@dataclass(frozen=True)
class Actor:
    name: str
    role: str
    unit: str


def normalize_cpf(value: str) -> str:
    if not re.fullmatch(r'(?:[0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})', value):
        raise RuleError('Formato de CPF não suportado')
    return re.sub(r'[.-]', '', value)


def valid_cpf(value: str) -> bool:
    try:
        digits = normalize_cpf(value)
    except RuleError:
        return False
    if len(set(digits)) == 1:
        return False
    for size in (9, 10):
        remainder = sum(int(digits[i]) * (size + 1 - i) for i in range(size)) % 11
        expected = 0 if remainder < 2 else 11 - remainder
        if int(digits[size]) != expected:
            return False
    return True


def require(actor: Actor, unit: str, write=False):
    roles = {'reviewer'} if write else {'reviewer', 'auditor'}
    if actor.role not in roles or actor.unit != unit:
        raise PermissionError('Acesso não autorizado para função/unidade')
