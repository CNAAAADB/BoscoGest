"""Importing members from an Excel workbook, alongside the CSV."""

import io
from datetime import datetime

from openpyxl import Workbook, load_workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(filas, cabecera=("email", "phone", "name", "surname", "birthdate", "dni")):
    wb = Workbook()
    ws = wb.active
    ws.title = "Usuarios"
    ws.append(list(cabecera))
    for fila in filas:
        ws.append(list(fila))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _validar(client, headers, contenido: bytes, entity_id: int, nombre="padron.xlsx"):
    return client.post(
        "/users/bulk-upload/validate",
        files={"file": (nombre, io.BytesIO(contenido), XLSX)},
        data={"entity_id": str(entity_id)},
        headers=headers,
    )


def test_a_clean_workbook_reports_no_problems(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    contenido = _xlsx([("ana@ejemplo.com", "611000001", "Ana", "Ruiz", "1990-01-01", "10000001A")])
    d = _validar(client, auth_headers, contenido, test_entity.id).json()

    assert d["valid"] is True, d
    assert d["total_rows"] == 1


def test_what_excel_stores_reads_as_what_a_csv_would_say(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """A date cell is a datetime and a phone typed as a number is a float.

    Neither is what the rules expect, and nobody filling in a sheet should
    have to know that.
    """
    contenido = _xlsx([(None, 611000001.0, "Ana", "Ruiz", datetime(1950, 1, 15), "10000001A")])
    d = _validar(client, auth_headers, contenido, test_entity.id).json()

    assert d["valid"] is True, d["problems"]


def test_a_date_typed_into_a_text_cell_is_accepted(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """Pasted from elsewhere, the cell holds the text "15/01/1950", not a date."""
    contenido = _xlsx([("ana@ejemplo.com", "611000001", "Ana", "Ruiz", "15/01/1950", "10000001A")])
    d = _validar(client, auth_headers, contenido, test_entity.id).json()

    assert d["valid"] is True, d["problems"]


def test_rows_left_empty_are_not_counted(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    contenido = _xlsx([
        ("ana@ejemplo.com", "611000001", "Ana", "Ruiz", "1990-01-01", "10000001A"),
        (None, None, None, None, None, None),
        ("", "", "", "", "", ""),
    ])
    d = _validar(client, auth_headers, contenido, test_entity.id).json()

    assert d["total_rows"] == 1


def test_the_problems_name_the_row_number_excel_shows(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    contenido = _xlsx([
        ("ana@ejemplo.com", "611000001", "Ana", "Ruiz", "1990-01-01", "10000001A"),
        ("0", "", "Luis", "", "1990-01-01", "10000002B"),
    ])
    d = _validar(client, auth_headers, contenido, test_entity.id).json()

    assert {p["row"] for p in d["problems"]} == {3}


def test_the_data_sheet_is_found_by_name_whatever_sheet_was_open(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """Saved while looking at the instructions, the workbook opens on them."""
    wb = Workbook()
    instrucciones = wb.active
    instrucciones.title = "Instrucciones"
    instrucciones.append(["Rellena la hoja Usuarios"])
    datos = wb.create_sheet("Usuarios")
    datos.append(["email", "phone", "name", "surname", "birthdate", "dni"])
    datos.append(["ana@ejemplo.com", "611000001", "Ana", "Ruiz", "1990-01-01", "10000001A"])
    out = io.BytesIO()
    wb.save(out)

    d = _validar(client, auth_headers, out.getvalue(), test_entity.id).json()

    assert d["valid"] is True, d


def test_an_old_xls_is_rejected_with_a_way_out(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    r = _validar(client, auth_headers, b"\xd0\xcf\x11\xe0", test_entity.id, nombre="padron.xls")

    assert r.status_code == 400
    assert ".xlsx" in r.json()["detail"]


def test_a_file_that_is_not_really_a_workbook_says_so(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    r = _validar(client, auth_headers, b"esto no es un excel", test_entity.id)

    assert r.status_code == 400
    assert "Excel" in r.json()["detail"]


def test_other_formats_are_rejected(
    client, auth_headers, test_entity, test_membership, test_permissions, test_role
):
    r = client.post(
        "/users/bulk-upload",
        files={"file": ("padron.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_id": str(test_entity.id), "role_id": str(test_role.id)},
        headers=auth_headers,
    )

    assert r.status_code == 400


def test_the_template_downloads_as_a_workbook(client, auth_headers):
    r = client.get("/users/bulk-upload/template.xlsx", headers=auth_headers)

    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Usuarios", "Instrucciones"]


def test_the_template_needs_a_session(client):
    assert client.get("/users/bulk-upload/template.xlsx").status_code == 401


def test_the_template_has_every_required_column_and_no_example_rows():
    """Example rows on the data sheet get imported the day nobody deletes them."""
    from app.services.csv_validation import REQUIRED_COLUMNS
    from app.services.member_file import build_template_xlsx, read_member_file

    columns, rows = read_member_file(build_template_xlsx(), "plantilla.xlsx")

    assert set(REQUIRED_COLUMNS) <= set(columns)
    assert rows == []


def test_a_filled_in_template_passes_the_validator(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """The template, as someone would fill it in, is a file the import accepts."""
    from app.services.member_file import build_template_xlsx

    wb = load_workbook(io.BytesIO(build_template_xlsx()))
    ws = wb["Usuarios"]
    columnas = [c.value for c in ws[1]]
    valores = {
        "name": "Ana", "surname": "Ruiz", "birthdate": datetime(1950, 1, 15),
        "dni": "10000001A", "phone": "611000001", "size": "M",
    }
    for idx, columna in enumerate(columnas, start=1):
        if columna in valores:
            ws.cell(row=2, column=idx, value=valores[columna])
    out = io.BytesIO()
    wb.save(out)

    d = _validar(client, auth_headers, out.getvalue(), test_entity.id).json()

    assert d["valid"] is True, d
    assert d["unknown_columns"] == []


def test_a_workbook_creates_working_accounts(
    monkeypatch, db_session, test_entity, test_user, test_role, test_membership
):
    """The background job reads the workbook it was given, not just CSVs."""
    from app.models.bulk_upload_job_model import BulkUploadJob
    from app.models.user_model import User as UserModel
    from app.services import user_service
    from app.tests.conftest import TestingSessionLocal

    monkeypatch.setattr(
        "app.database.SyncSessionLocal", TestingSessionLocal, raising=False
    )

    job = BulkUploadJob(
        created_by_id=test_user.id,
        target_entity_id=test_entity.id,
        target_role_id=test_role.id,
        status="pending",
        csv_filename="padron.xlsx",
        csv_content=_xlsx([
            ("nueva@ejemplo.com", 611000111, "Nueva", "Socia", datetime(1952, 4, 4), "10101010X"),
            ("otra@ejemplo.com", "611000112", "Otra", "Socia", "20/11/1949", "10101011Y"),
        ]),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    user_service.process_bulk_upload_job(job.id, test_user.id, None)

    db_session.refresh(job)
    assert job.failed == 0, job.errors
    assert job.successful == 2

    created = db_session.query(UserModel).filter_by(email="nueva@ejemplo.com").one()
    assert created.phone == "611000111"
    assert created.birthdate.isoformat() == "1952-04-04"

    otra = db_session.query(UserModel).filter_by(email="otra@ejemplo.com").one()
    assert otra.birthdate.isoformat() == "1949-11-20"
