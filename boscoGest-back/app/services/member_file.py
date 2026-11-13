"""Reading the member file, whether it arrives as a CSV or as an Excel workbook.

Most of the people who prepare these files have never knowingly met a CSV: they
open the template in Excel, fill it in and save it. Asking them to "save as CSV
UTF-8, comma delimited" is where the process used to break, so the workbook is
accepted as it is and turned into the same rows a CSV would have produced.

Everything downstream — the dry-run validator, the header check when the job is
created and the importer itself — goes through ``read_member_file``, so the
three of them see exactly the same rows whatever the format.
"""

import csv
import io
from datetime import date, datetime, time
from typing import Dict, List, Tuple

from app.schemas.user import ALLOWED_SIZES
from app.services.csv_validation import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

ACCEPTED_EXTENSIONS = (".csv", ".xlsx")

# The sheet the template writes the members to. A workbook saved while the
# instructions sheet was showing has *that* one as active, so the data sheet is
# looked up by name first and the first sheet is only the fallback.
DATA_SHEET = "Usuarios"


class UnreadableFile(ValueError):
    """The file cannot be turned into rows. The message is meant for a person."""


def is_excel(filename: str) -> bool:
    return (filename or "").lower().endswith(".xlsx")


def check_extension(filename: str) -> None:
    name = (filename or "").lower()
    if name.endswith(".xls"):
        raise UnreadableFile(
            "Es un Excel antiguo (.xls). Ábrelo y guárdalo como «Libro de "
            "Excel (.xlsx)» o usa la plantilla Excel de esta pantalla."
        )
    if not name.endswith(ACCEPTED_EXTENSIONS):
        raise UnreadableFile(
            "El archivo debe ser un Excel (.xlsx) o un CSV (.csv)."
        )


def read_member_file(
    content: bytes, filename: str
) -> Tuple[List[str], List[Dict[str, str]]]:
    """Return the header and the rows, every value as a string.

    Strings everywhere because that is what a CSV gives and what the rules in
    ``csv_validation`` expect; it also keeps the rows JSON-serialisable for the
    failure report the job stores.
    """
    check_extension(filename)
    if is_excel(filename):
        return _read_xlsx(content)
    return _read_csv(content)


def _read_csv(content: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UnreadableFile(
            "El archivo no está en UTF-8. Vuelve a exportarlo eligiendo esa "
            "codificación (o súbelo directamente como Excel .xlsx); con otra, "
            "los acentos y las eñes llegan corruptos."
        )

    try:
        reader = csv.DictReader(
            io.StringIO(decoded), quoting=csv.QUOTE_ALL, skipinitialspace=True
        )
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    except csv.Error as e:
        raise UnreadableFile(f"No se ha podido leer el CSV: {e}")

    return columns, rows


def _read_xlsx(content: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
    # Imported here so that importing this module, and the user service with
    # it, does not pay for openpyxl when nobody uploads a workbook.
    from openpyxl import load_workbook

    try:
        # read_only streams the sheet instead of building it in memory;
        # data_only returns what a formula last evaluated to, not the formula.
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception:
        raise UnreadableFile(
            "No se ha podido abrir el Excel. Comprueba que es un archivo .xlsx "
            "y que no está protegido con contraseña."
        )

    try:
        ws = wb[DATA_SHEET] if DATA_SHEET in wb.sheetnames else wb.worksheets[0]
        values = ws.iter_rows(values_only=True)

        header = next(values, None) or ()
        columns = [_cell_to_str(h) for h in header]
        # Excel often reports trailing columns that only ever had formatting.
        while columns and not columns[-1]:
            columns.pop()

        rows: List[Dict[str, str]] = []
        for raw in values:
            cells = [_cell_to_str(v) for v in raw[: len(columns)]]
            # Rows that were formatted or cleared but hold nothing. A CSV
            # reader skips blank lines too, so both formats count alike.
            if not any(cells):
                continue
            cells += [""] * (len(columns) - len(cells))
            rows.append(dict(zip(columns, cells, strict=True)))
    finally:
        wb.close()

    return columns, rows


def _cell_to_str(value) -> str:
    """Turn what Excel stored into what someone would have typed in a CSV."""
    if value is None:
        return ""
    # datetime before date: a datetime is also a date. Excel has no date-only
    # type, so a birthdate comes back as midnight of that day.
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, bool):
        return "1" if value else "0"
    # A phone typed into a number cell is stored as 612345678.0.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


# ──────────────────────────────────────────────
# The Excel template
# ──────────────────────────────────────────────

# In the order the template shows them, with what each header comment says.
TEMPLATE_COLUMNS: List[Tuple[str, str]] = [
    ("name", "Nombre. Obligatorio."),
    ("surname", "Apellidos. Obligatorio."),
    ("birthdate", "Fecha de nacimiento. Obligatorio. Escríbela como 15/01/1950, con el año completo."),
    ("dni", "DNI o NIE. Opcional; si se facilita, no puede repetirse."),
    ("email", "Correo electrónico. Opcional; permite recibir el enlace de activación."),
    ("phone", "Teléfono. Opcional; permite identificar la cuenta al iniciar sesión si tiene contraseña."),
    ("address", "Dirección postal. Opcional."),
    ("iban", "Cuenta bancaria (IBAN). Opcional."),
    ("size", "Talla de ropa. Opcional. Elígela de la lista desplegable."),
    ("hobbies", "Aficiones. Opcional."),
    ("job_position", "Profesión o puesto de trabajo. Opcional."),
]

# Two made-up members, shown on the instructions sheet only. On the data sheet
# they would be imported the day somebody forgets to delete them.
TEMPLATE_EXAMPLES = [
    {
        "name": "Juan", "surname": "Pérez", "birthdate": date(1950, 1, 15),
        "dni": "12345678A", "email": "juan.perez@ejemplo.com",
        "phone": "612345678", "address": "Calle Ejemplo 123",
        "iban": "ES1234567890123456789012", "size": "M",
        "hobbies": "Lectura, Senderismo", "job_position": "Jubilado",
    },
    {
        "name": "María", "surname": "García", "birthdate": date(1948, 5, 20),
        "dni": "87654321B", "email": "", "phone": "687654321",
        "address": "Avenida Principal 456", "iban": "", "size": "S",
        "hobbies": "Música", "job_position": "",
    },
]

# Columns Excel would otherwise "help" with: a phone loses its leading +, a
# long IBAN turns into 1,23E+21 and a DNI that is all digits loses its zeros.
_TEXT_COLUMNS = {"dni", "email", "phone", "iban"}

_TEMPLATE_ROWS = 500

# Smallest to largest, as anyone would look for them; sorted() would put L
# before S.
_SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

assert {c for c, _ in TEMPLATE_COLUMNS} == set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS) - {"photo"}


def build_template_xlsx() -> bytes:
    """A workbook that is hard to fill in wrongly.

    The header names are the ones the importer reads, so they stay as they
    are; everything else — the comments on each header, the date and text
    formats, the drop-down for the size and the instructions sheet — is there
    so that whoever fills it in does not need to know any of that.
    """
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = DATA_SHEET

    required = set(REQUIRED_COLUMNS)
    bold = Font(bold=True, color="FFFFFF")
    fill_required = PatternFill("solid", fgColor="3D4E7C")
    fill_optional = PatternFill("solid", fgColor="7A88AD")

    for idx, (column, help_text) in enumerate(TEMPLATE_COLUMNS, start=1):
        cell = ws.cell(row=1, column=idx, value=column)
        cell.font = bold
        cell.fill = fill_required if column in required else fill_optional
        cell.alignment = Alignment(horizontal="center")
        cell.comment = Comment(help_text, "BoscoGest", width=260, height=80)
        ws.column_dimensions[get_column_letter(idx)].width = max(16, len(column) + 6)

        number_format = None
        if column == "birthdate":
            number_format = "DD/MM/YYYY"
        elif column in _TEXT_COLUMNS:
            number_format = "@"
        if number_format:
            for row in range(2, _TEMPLATE_ROWS + 2):
                ws.cell(row=row, column=idx).number_format = number_format

    columns = [c for c, _ in TEMPLATE_COLUMNS]
    size_letter = get_column_letter(columns.index("size") + 1)
    sizes = DataValidation(
        type="list",
        formula1='"' + ",".join(
            [t for t in _SIZE_ORDER if t in ALLOWED_SIZES]
            + sorted(set(ALLOWED_SIZES) - set(_SIZE_ORDER))
        ) + '"',
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Talla no válida",
        error="Elige una talla de la lista.",
    )
    ws.add_data_validation(sizes)
    sizes.add(f"{size_letter}2:{size_letter}{_TEMPLATE_ROWS + 1}")

    ws.freeze_panes = "A2"

    _add_instructions_sheet(wb)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _add_instructions_sheet(wb) -> None:
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet("Instrucciones")
    ws.column_dimensions["A"].width = 18

    lines = [
        ("Cómo rellenar esta plantilla", True),
        ("", False),
        ("1. Escribe los datos en la hoja «Usuarios» (abajo, en las pestañas): una fila por persona.", False),
        ("2. No cambies ni borres la primera fila: el programa la usa para saber qué es cada columna.", False),
        ("3. Las columnas en azul oscuro son obligatorias: name (nombre), surname (apellidos), birthdate (fecha de nacimiento). DNI, email y teléfono son opcionales.", False),
        ("4. Cada persona necesita un correo (email) o un teléfono (phone). Si no tiene correo, deja la celda vacía.", False),
        ("5. Escribe la fecha de nacimiento como 15/01/1950, con el año completo (1950, no 50).", False),
        ("6. La talla (size) se elige de la lista desplegable.", False),
        ("7. Guarda el archivo tal cual, como Excel (.xlsx). No hace falta convertirlo a CSV.", False),
        ("", False),
        ("La asociación y el rol no van en el archivo: se eligen en la pantalla de importación.", False),
        ("Si dejas el ratón sobre el nombre de una columna verás qué hay que escribir en ella.", False),
        ("Antes de importar, pulsa «Comprobar el archivo»: te dice qué filas hay que corregir sin crear ningún usuario.", False),
        ("", False),
        ("Así quedaría la hoja «Usuarios» con dos personas (es solo un ejemplo, no las copies):", True),
    ]
    for r, (text, title) in enumerate(lines, start=1):
        cell = ws.cell(row=r, column=1, value=text)
        if title:
            cell.font = Font(bold=True, size=14 if r == 1 else 11)

    start = len(lines) + 2
    for idx, (column, _) in enumerate(TEMPLATE_COLUMNS, start=1):
        ws.cell(row=start, column=idx, value=column).font = Font(bold=True)
        for offset, example in enumerate(TEMPLATE_EXAMPLES, start=1):
            value = example.get(column) or None
            cell = ws.cell(row=start + offset, column=idx, value=value)
            cell.alignment = Alignment(horizontal="left")
            if column == "birthdate":
                cell.number_format = "DD/MM/YYYY"
