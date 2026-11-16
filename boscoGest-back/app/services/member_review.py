"""Suggestions for incomplete/placeholder member records.

These indicators are only administrative review prompts. A checksum cannot
verify whether a DNI belongs to a particular person.
"""
import re
import unicodedata

CONTROL_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def is_valid_spanish_id(value: str) -> bool:
    code = re.sub(r"[\s-]", "", value).upper()
    if re.fullmatch(r"[0-9]{8}[A-Z]", code):
        number = int(code[:8])
    elif re.fullmatch(r"[XYZ][0-9]{7}[A-Z]", code):
        number = int(str("XYZ".index(code[0])) + code[1:8])
    else:
        return False
    return CONTROL_LETTERS[number % 23] == code[-1]


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFD", (value or "").strip().lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _missing(value: str | None) -> bool:
    return not value or not value.strip()


def requires_review(user, *, contact: bool, sensitive: bool) -> bool:
    """Evaluate only fields the requester may see; no private-data inference."""
    if _missing(user.name) or _missing(user.surname):
        return True
    placeholders = {"test", "testing", "prueba", "demo", "ejemplo",
                    "ficticio", "fake", "xxx"}
    for part in (user.name, user.surname):
        p = _norm(part)
        if p in placeholders or re.fullmatch(r"a{4,}|n{2,}", p):
            return True

    if contact:
        if _missing(user.email) or _missing(user.phone):
            return True
        email = _norm(user.email)
        if (re.search(r"@(?:example\.(?:com|org|net)|example|test|invalid|localhost)(?:$|\.)", email)
                or re.match(r"^(?:test|prueba|demo|ficticio|fake)[0-9]*@", email)):
            return True
        digits = re.sub(r"\D", "", user.phone or "")
        if len(digits) >= 9 and (len(set(digits)) == 1 or digits in {"123456789", "987654321", "000000000"}):
            return True

    if sensitive:
        if _missing(user.dni) or _missing(str(user.birthdate) if user.birthdate else None):
            return True
        code = re.sub(r"[\s-]", "", user.dni or "").upper()
        if (re.fullmatch(r"(?:0{8}[A-Z]?|1{8}[A-Z]?|X{8,9}|12345678[A-Z]?|99999999[A-Z]?)", code)
                or not is_valid_spanish_id(user.dni)):
            return True
        if str(user.birthdate) in {"1900-01-01", "1901-01-01", "1970-01-01"}:
            return True

    return False
