"""The rules a row of the member CSV has to satisfy.

Shared deliberately by two callers: the importer, which applies them as it
creates each user, and the dry-run validator, which applies them to the whole
file and reports without creating anything. Keeping one copy is the point —
a validator that says a file is fine and an importer that then rejects half of
it is worse than no validator at all.

Nothing here touches the database or the network, so it is cheap to run over a
whole file and easy to test.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from app.schemas.user import ALLOWED_SIZES

# Columns a row cannot do without.
REQUIRED_COLUMNS = ["name", "surname", "birthdate"]

# Read when present, ignored when absent.
OPTIONAL_COLUMNS = [
    "email", "phone", "dni", "address", "photo", "iban", "size", "hobbies",
    "job_position",
]

# Present in older exports and deliberately not read. The association and the
# role come from the screen; the password is generated and never disclosed.
IGNORED_COLUMNS = ["password", "role_id", "entity_id"]

# The ways a birthdate may be written. ISO is what the CSV template has always
# asked for; day/month/year is how anyone in Spain writes a date, and what a
# spreadsheet hands over when the cell holds the date as text rather than as a
# date. The year must have four digits: "15/01/50" could be 1950 or 2050, and
# guessing wrong gives somebody a birthday a century off.
BIRTHDATE_FORMATS = [
    (re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"), "%d/%m/%Y"),
    (re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"), "%d-%m-%Y"),
]

# Deliberately loose: the point is to keep values that are obviously not
# addresses out of a column that is read back as an EmailStr, not to police
# what a valid mailbox looks like.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# The column widths the database enforces. Exceeding one fails at INSERT time
# with an error that quotes the whole row, so it is worth catching early.
MAX_LENGTHS: Dict[str, int] = {
    "email": 100,
    "phone": 20,
    "name": 100,
    "surname": 100,
    "dni": 20,
    "iban": 34,
    "address": 255,
    "size": 10,
    "job_position": 100,
}


# Stable identifiers for each kind of problem. The message is written for a
# person and will be reworded; the code is what the summary groups by and what
# the interface can branch on.
PROBLEM_LABELS: Dict[str, str] = {
    "required_empty": "Campo obligatorio vacío",
    "no_contact": "Sin email ni teléfono",
    "email_invalid": "El email no es una dirección válida",
    "birthdate_format": "Fecha de nacimiento con formato incorrecto",
    "size_invalid": "Talla no admitida",
    "too_long": "Un campo supera la longitud máxima",
    "duplicate_in_file": "Valor repetido dentro del archivo",
    "already_exists": "Ya existe un usuario con ese valor",
}


@dataclass
class RowProblem:
    """Something wrong with one row, phrased for whoever has to fix the file."""

    row: int
    field: Optional[str]
    message: str
    code: str = "required_empty"


@dataclass
class ParsedRow:
    """A row that passed the per-row checks, with its values normalised."""

    row: int
    email: Optional[str]
    phone: Optional[str]
    name: str
    surname: str
    birthdate: date
    dni: Optional[str]
    address: Optional[str] = None
    photo: Optional[str] = None
    iban: Optional[str] = None
    size: Optional[str] = None
    hobbies: Optional[str] = None
    job_position: Optional[str] = None
    problems: List[RowProblem] = field(default_factory=list)


def parse_birthdate(value: str) -> Optional[date]:
    """The date in ``value``, or None if it is not one in an accepted format.

    Shared by the validator and the importer, which must agree on what a
    valid date looks like.
    """
    value = value.strip()
    for pattern, fmt in BIRTHDATE_FORMATS:
        if pattern.match(value):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                # Right shape, impossible date: 31/02/1950.
                return None
    return None


def missing_columns(columns: List[str]) -> List[str]:
    """Required columns the header does not have."""
    return [c for c in REQUIRED_COLUMNS if c not in columns]


def ignored_columns_present(columns: List[str]) -> List[str]:
    """Columns in the file that the import will not read."""
    return [c for c in IGNORED_COLUMNS if c in columns]


def unknown_columns(columns: List[str]) -> List[str]:
    """Columns nobody asked for. Harmless, but usually a sign of a wrong file."""
    known = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS + IGNORED_COLUMNS)
    return [c for c in columns if c and c not in known]


def check_row(row: Dict[str, str], row_number: int) -> ParsedRow:
    """Apply every per-row rule and collect *all* the problems, not just the first.

    The importer stops at the first failure because it has nothing useful to do
    with the rest; the validator wants the complete picture so the file can be
    fixed in one pass rather than by trial and error.
    """
    def g(key: str) -> str:
        return (row.get(key) or "").strip()

    problems: List[RowProblem] = []

    def fail(field_name: Optional[str], code: str, message: str) -> None:
        problems.append(
            RowProblem(row=row_number, field=field_name, message=message, code=code)
        )

    email, phone = g("email"), g("phone")
    name, surname, dni = g("name"), g("surname"), g("dni")
    birthdate_str = g("birthdate")

    for key, value in (
        ("name", name), ("surname", surname),
        ("birthdate", birthdate_str),
    ):
        if not value:
            fail(key, "required_empty", "Campo obligatorio vacío")

    if email and not EMAIL_RE.match(email):
        fail(
            "email",
            "email_invalid",
            f"«{email}» no es una dirección de correo. Si esa persona no tiene, "
            "deja la celda vacía",
        )

    birthdate: Optional[date] = None
    if birthdate_str:
        birthdate = parse_birthdate(birthdate_str)
        if birthdate is None:
            fail(
                "birthdate",
                "birthdate_format",
                f"«{birthdate_str}» no es una fecha válida. Escríbela como "
                "15/01/1950, con el año completo",
            )

    size = g("size") or None
    if size and size not in ALLOWED_SIZES:
        fail(
            "size",
            "size_invalid",
            f"Talla «{size}» no admitida. Valores: {', '.join(sorted(ALLOWED_SIZES))}",
        )

    for key, limit in MAX_LENGTHS.items():
        value = g(key)
        if value and len(value) > limit:
            fail(
                key,
                "too_long",
                f"Tiene {len(value)} caracteres y el máximo son {limit}",
            )

    return ParsedRow(
        row=row_number,
        email=email or None,
        phone=phone or None,
        name=name,
        surname=surname,
        birthdate=birthdate or date(1900, 1, 1),
        dni=dni or None,
        address=g("address") or None,
        photo=g("photo") or None,
        iban=g("iban") or None,
        size=size,
        hobbies=g("hobbies") or None,
        job_position=g("job_position") or None,
        problems=problems,
    )


def duplicates_within_file(parsed: List[ParsedRow]) -> List[RowProblem]:
    """Values repeated inside the file itself.

    email, phone and dni are unique in the database, so a repeat means every
    occurrence after the first fails — and the failure names the clash without
    saying it came from the same file, which is confusing.
    """
    problems: List[RowProblem] = []
    etiquetas = {"dni": "DNI", "email": "email", "phone": "teléfono"}

    for campo, etiqueta in etiquetas.items():
        visto: Dict[str, int] = {}
        for p in parsed:
            valor = getattr(p, campo)
            if not valor:
                continue
            if valor in visto:
                problems.append(
                    RowProblem(
                        row=p.row,
                        field=campo,
                        code="duplicate_in_file",
                        message=f"Este {etiqueta} ya aparece en la fila {visto[valor]}",
                    )
                )
            else:
                visto[valor] = p.row

    return problems
