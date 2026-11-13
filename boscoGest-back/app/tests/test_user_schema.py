"""Unit tests for UserCreate/UserBase validation rules (no DB)."""
import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


def _base_kwargs(**overrides):
    data = dict(
        name="Ana",
        surname="García",
        birthdate="1990-01-01",
        dni="12345678A",
    )
    data.update(overrides)
    return data


def test_user_create_with_email_only_is_valid():
    user = UserCreate(**_base_kwargs(email="ana@example.com"))
    assert user.email == "ana@example.com"
    assert user.phone is None


def test_user_create_with_phone_only_is_valid():
    user = UserCreate(**_base_kwargs(phone="600123456"))
    assert user.phone == "600123456"
    assert user.email is None


def test_user_create_with_both_is_valid():
    user = UserCreate(**_base_kwargs(email="ana@example.com", phone="600123456"))
    assert user.email == "ana@example.com"
    assert user.phone == "600123456"


def test_user_create_without_any_identifiers_is_valid():
    user = UserCreate(**_base_kwargs(dni=None))
    assert user.email is None
    assert user.phone is None
    assert user.dni is None


def test_user_create_accepts_omitted_dni():
    assert UserCreate(name="Ana", surname="García", birthdate="1990-01-01").dni is None


def test_user_create_rejects_invalid_size():
    with pytest.raises(ValidationError, match="Talla no válida"):
        UserCreate(**_base_kwargs(email="ana@example.com", size="L-grande"))


@pytest.mark.parametrize("size", ["XS", "S", "M", "L", "XL", "XXL", "XXXL"])
def test_user_create_accepts_valid_sizes(size):
    user = UserCreate(**_base_kwargs(email="ana@example.com", size=size))
    assert user.size == size
