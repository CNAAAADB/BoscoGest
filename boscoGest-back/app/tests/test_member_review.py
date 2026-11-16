from datetime import date
from types import SimpleNamespace

import pytest
from app.services.member_review import is_valid_spanish_id, requires_review


@pytest.mark.parametrize("value", ["12345678Z", "12345678-Z", "X1234567L", "Y1234567X", "Z1234567R"])
def test_valid_dni_nie(value):
    # NIE examples are checked independently against modulo-23.
    code = value.upper().replace("-", "")
    assert is_valid_spanish_id(code) == (
        "TRWAGMYFPDXBNJZSQVHLCKE"[
            int((str("XYZ".index(code[0])) + code[1:8]) if code[0] in "XYZ" else code[:8]) % 23
        ] == code[-1]
    )


@pytest.mark.parametrize("value", ["12345678A", "1234567Z", "X1234567A", "ABC123", ""])
def test_invalid_dni_nie(value):
    assert not is_valid_spanish_id(value)


def sample(**changes):
    values = dict(name="María", surname="López", email="maria@correo.es",
                  phone="612345678", dni="87654321X", birthdate=date(1965, 3, 21))
    values.update(changes)
    return SimpleNamespace(**values)


def test_missing_and_invalid_dni_trigger_review():
    assert requires_review(sample(dni=None), contact=True, sensitive=True)
    assert requires_review(sample(dni="12345678A"), contact=True, sensitive=True)
    assert not requires_review(sample(), contact=True, sensitive=True)


def test_redacted_sensitive_fields_do_not_trigger_review():
    redacted = sample(dni=None, birthdate=None, email=None, phone=None)
    assert not requires_review(redacted, contact=False, sensitive=False)
    assert requires_review(redacted, contact=True, sensitive=False)


def test_obvious_placeholder_data_triggers_review():
    assert requires_review(sample(name="Prueba"), contact=True, sensitive=True)
    assert requires_review(sample(phone="666666666"), contact=True, sensitive=True)
    assert requires_review(sample(dni="00000000T"), contact=True, sensitive=True)
