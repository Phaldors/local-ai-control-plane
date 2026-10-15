"""PII redaction for anything that is persisted (traces, audit log, eval outcomes).

Regex + checksum based, on purpose: deterministic and testable. It is a safety net for stored
artifacts, not a guarantee; free-form names and addresses are out of scope.
"""

import re
from typing import Any

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IBAN = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b")
# 13-19 digits, optionally grouped by spaces or dashes; validated with Luhn below.
CARD = re.compile(r"(?<![\d.])\d(?:[ -]?\d){12,18}(?![\d])")
TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
PHONE = re.compile(
    r"(?<![\w+])(?:\+\d{1,3}[\s-]?)?(?:\(?0?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
)


def _luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        n = int(char)
        if index % 2 == 1:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def _tckn_valid(value: str) -> bool:
    d = [int(c) for c in value]
    if d[0] == 0:
        return False
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def redact_pii(text: str) -> str:
    text = EMAIL.sub("[EMAIL]", text)
    text = IBAN.sub("[IBAN]", text)
    text = CARD.sub(lambda m: "[CARD]" if _luhn(re.sub(r"\D", "", m.group())) else m.group(), text)
    text = TCKN.sub(lambda m: "[TCKN]" if _tckn_valid(m.group()) else m.group(), text)
    return PHONE.sub("[PHONE]", text)


def contains_pii(text: str) -> bool:
    return redact_pii(text) != text


def redact_obj(value: Any) -> Any:
    """Recursively redact every string inside a JSON-like structure."""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    return value
