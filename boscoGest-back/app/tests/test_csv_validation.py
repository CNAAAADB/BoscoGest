"""Checking a member CSV without importing it."""

import io


def _subir(client, headers, contenido: str, entity_id: int):
    return client.post(
        "/users/bulk-upload/validate",
        files={"file": ("padron.csv", io.BytesIO(contenido.encode("utf-8")), "text/csv")},
        data={"entity_id": str(entity_id)},
        headers=headers,
    )


CABECERA = '"email","phone","name","surname","birthdate","dni"\n'
BUENA = '"ana@ejemplo.com","611000001","Ana","Ruiz","1990-01-01","10000001A"\n'


def test_a_clean_file_reports_no_problems(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    r = _subir(client, auth_headers, CABECERA + BUENA, test_entity.id)

    assert r.status_code == 200
    d = r.json()
    assert d["valid"] is True
    assert d["total_rows"] == 1
    assert d["valid_rows"] == 1
    assert d["problems"] == []


def test_nothing_is_created(
    client, auth_headers, db_session, test_entity, test_membership, test_permissions
):
    """The whole point: you can run it as often as you like."""
    from app.models.user_model import User
    from app.models.bulk_upload_job_model import BulkUploadJob

    antes = db_session.query(User).count()
    trabajos = db_session.query(BulkUploadJob).count()

    _subir(client, auth_headers, CABECERA + BUENA, test_entity.id)
    _subir(client, auth_headers, CABECERA + BUENA, test_entity.id)

    assert db_session.query(User).count() == antes
    assert db_session.query(BulkUploadJob).count() == trabajos


def test_it_reports_every_problem_of_a_row_at_once(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """The importer stops at the first; here the file gets fixed in one pass."""
    mala = '"0","","Ana","","32-13-1990","10000002B"\n'
    r = _subir(client, auth_headers, CABECERA + mala, test_entity.id)

    d = r.json()
    campos = {p["field"] for p in d["problems"]}
    assert "email" in campos      # "0" no es una dirección
    assert "surname" in campos    # vacío
    assert "birthdate" in campos  # formato
    assert d["valid"] is False
    assert d["invalid_rows"] == 1


def test_it_catches_the_zero_that_spreadsheets_export(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """The exact failure that broke production: 206 rows with email "0"."""
    filas = "".join(
        f'"0","61100{i:04d}","Socio{i}","Apellido","1990-01-01","2000000{i}C"\n'
        for i in range(3)
    )
    d = _subir(client, auth_headers, CABECERA + filas, test_entity.id).json()

    assert d["invalid_rows"] == 3
    assert any("no es una dirección de correo" in p["message"] for p in d["problems"])
    # Y agrupado, para no leer 206 líneas iguales.
    assert d["summary"][0]["count"] == 3


def test_it_catches_duplicates_inside_the_file(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    dos = (
        '"ana@ejemplo.com","611000001","Ana","Ruiz","1990-01-01","10000001A"\n'
        '"ana@ejemplo.com","611000002","Otra","Persona","1991-01-01","10000002B"\n'
    )
    d = _subir(client, auth_headers, CABECERA + dos, test_entity.id).json()

    assert any("ya aparece en la fila 2" in p["message"] for p in d["problems"])


def test_it_catches_values_already_in_the_database(
    client, auth_headers, test_user, test_entity, test_membership, test_permissions
):
    fila = f'"{test_user.email}","611999999","Ana","Ruiz","1990-01-01","10000009X"\n'
    d = _subir(client, auth_headers, CABECERA + fila, test_entity.id).json()

    assert any("Ya existe un usuario con este email" in p["message"] for p in d["problems"])


def test_it_catches_a_field_longer_than_its_column(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """The IBAN of 52 characters that leaked a member's whole record."""
    cab = '"email","phone","name","surname","birthdate","dni","iban"\n'
    fila = f'"ana@ejemplo.com","611000001","Ana","Ruiz","1990-01-01","10000001A","{"ES" + "1" * 60}"\n'
    d = _subir(client, auth_headers, cab + fila, test_entity.id).json()

    assert any(p["field"] == "iban" and "máximo" in p["message"] for p in d["problems"])


def test_it_names_the_columns_that_are_missing(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    d = _subir(client, auth_headers, '"email","name"\n"a@b.es","Ana"\n', test_entity.id).json()

    assert d["valid"] is False
    assert set(d["missing_columns"]) == {"surname", "birthdate"}


def test_member_without_contact_or_dni_is_valid(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    file = '"name","surname","birthdate"\n"Ana","Ruiz","1990-01-01"\n'
    d = _subir(client, auth_headers, file, test_entity.id).json()
    assert d["valid"] is True, d["problems"]
    assert d["missing_columns"] == []


def test_it_flags_the_columns_it_will_ignore(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    cab = '"email","phone","password","role_id","name","surname","birthdate","dni"\n'
    fila = '"ana@ejemplo.com","611000001","Clave123","2","Ana","Ruiz","1990-01-01","10000001A"\n'
    d = _subir(client, auth_headers, cab + fila, test_entity.id).json()

    assert set(d["ignored_columns"]) == {"password", "role_id"}
    assert d["valid"] is True


def test_a_file_that_is_not_utf8_says_so(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """Latin-1 is what Excel produces by default on Spanish Windows."""
    contenido = (CABECERA + '"ana@ejemplo.com","611000001","Begoña","Ruiz","1990-01-01","10000001A"\n')
    r = client.post(
        "/users/bulk-upload/validate",
        files={"file": ("padron.csv", io.BytesIO(contenido.encode("latin-1")), "text/csv")},
        data={"entity_id": str(test_entity.id)},
        headers=auth_headers,
    )

    assert r.status_code == 400
    assert "UTF-8" in r.json()["detail"]


def test_the_validator_and_the_importer_apply_the_same_rules():
    """They share one module on purpose.

    A validator that passes a file the importer then rejects is worse than no
    validator, so the importer must not carry its own copy of these checks.
    """
    import inspect

    from app.services import user_service

    from app.services import csv_validation

    # Una sola expresión, la del módulo de reglas: no hay copia en el importador.
    assert user_service.EMAIL_RE is csv_validation.EMAIL_RE
    assert "EMAIL_RE = " not in inspect.getsource(user_service)

    # Y el importador la usa de verdad al procesar cada fila.
    assert "EMAIL_RE.match" in inspect.getsource(user_service.process_bulk_upload_job)


def test_dates_written_day_first_are_accepted(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """15/01/1950 is how anyone here writes a date."""
    filas = (
        '"ana@ejemplo.com","611000001","Ana","Ruiz","15/01/1950","10000001A"\n'
        '"luis@ejemplo.com","611000002","Luis","Gil","5-3-1948","10000002B"\n'
        '"eva@ejemplo.com","611000003","Eva","Sanz","1951-07-30","10000003C"\n'
    )
    d = _subir(client, auth_headers, CABECERA + filas, test_entity.id).json()

    assert d["valid"] is True, d["problems"]


def test_a_two_digit_year_is_rejected_rather_than_guessed(
    client, auth_headers, test_entity, test_membership, test_permissions
):
    """15/01/50 could be 1950 or 2050; a wrong guess is a century off."""
    fila = '"ana@ejemplo.com","611000001","Ana","Ruiz","15/01/50","10000001A"\n'
    d = _subir(client, auth_headers, CABECERA + fila, test_entity.id).json()

    assert [p["field"] for p in d["problems"]] == ["birthdate"]
    assert "año completo" in d["problems"][0]["message"]


def test_an_impossible_date_is_rejected():
    from app.services.csv_validation import parse_birthdate

    assert parse_birthdate("31/02/1950") is None
    assert parse_birthdate("1950-13-01") is None
    assert parse_birthdate("01/15/1950") is None  # mes 15: no se lee al revés
    assert parse_birthdate("15/01/1950").isoformat() == "1950-01-15"


def test_the_importer_reads_dates_with_the_validator_s_function():
    import inspect

    from app.services import csv_validation, user_service

    assert user_service.parse_birthdate is csv_validation.parse_birthdate
    source = inspect.getsource(user_service.process_bulk_upload_job)
    assert "parse_birthdate(" in source
    assert "strptime" not in source
