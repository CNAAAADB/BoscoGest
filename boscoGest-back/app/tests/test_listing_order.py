"""Los listados de roles, permisos y asociaciones salen por orden alfabético.

Sin un ORDER BY, PostgreSQL devuelve las filas en el orden que le conviene, que
no es estable: cambia al actualizar una fila o al replanificar la consulta. En
un desplegable eso se traduce en que las opciones bailan de sitio entre visitas.

Lo que **ya** tenía un orden propio se respeta: `/entities/public` agrupa por
nivel de la jerarquía antes que por nombre, y eso es deliberado.
"""

from datetime import datetime

import pytest

from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.permission_model import Permission
from app.models.role_model import Role


@pytest.fixture
def entidades_desordenadas(db_session, test_entity, test_user, test_role):
    """Asociaciones insertadas a propósito en orden inverso, **con membresía**.

    La membresía importa: los listados de `/entities` y `/entities/admin` salen
    de las asociaciones del usuario, así que sin ella devolverían un único
    elemento y la comprobación del orden pasaría siempre, detectando nada.
    """
    creadas = []
    for nombre in ["Zaragoza", "Albacete", "Mérida", "Badajoz"]:
        e = Entity(
            name=nombre,
            level=2,
            parent_id=test_entity.id,
            created_at=datetime.utcnow(),
        )
        db_session.add(e)
        db_session.flush()
        e.roles.append(test_role)
        db_session.add(
            Membership(
                user_id=test_user.id,
                entity_id=e.id,
                role_id=test_role.id,
                is_active=True,
                created_at=datetime.utcnow(),
            )
        )
        creadas.append(e)
    db_session.commit()
    return creadas


def _nombres(payload):
    return [x["name"] for x in payload]


def test_asociaciones_accesibles_en_orden(
    client, auth_headers, db_session, test_entity, test_membership, entidades_desordenadas
):
    response = client.get("/entities/accessible", headers=auth_headers)

    assert response.status_code == 200
    nombres = _nombres(response.json())
    assert nombres == sorted(nombres)


def test_mis_asociaciones_en_orden(
    client, auth_headers, test_membership, entidades_desordenadas
):
    response = client.get("/entities", headers=auth_headers)

    assert response.status_code == 200
    nombres = _nombres(response.json())
    # Si solo viniera una, la comprobación del orden no probaría nada.
    assert len(nombres) > 1
    assert nombres == sorted(nombres)


def test_asociaciones_administrables_en_orden(
    client, auth_headers, test_membership, entidades_desordenadas
):
    response = client.get("/entities/admin", headers=auth_headers)

    assert response.status_code == 200
    nombres = _nombres(response.json())
    # Si solo viniera una, la comprobación del orden no probaría nada.
    assert len(nombres) > 1
    assert nombres == sorted(nombres)


def test_roles_de_una_asociacion_en_orden(
    client, auth_headers, db_session, test_entity, test_membership
):
    """El desplegable del diálogo de cambio de rol se alimenta de aquí."""
    extra = Role(name="aaa-primero", description="Debe salir el primero")
    db_session.add(extra)
    db_session.flush()
    test_entity.roles.append(extra)
    db_session.commit()

    response = client.get(f"/entities/{test_entity.id}/roles", headers=auth_headers)

    assert response.status_code == 200
    nombres = _nombres(response.json())
    assert nombres == sorted(nombres)
    assert nombres[0] == "aaa-primero"


def test_permisos_en_orden(client, auth_headers, test_permissions, test_membership):
    response = client.get("/permissions", headers=auth_headers)

    assert response.status_code == 200
    nombres = _nombres(response.json())
    assert nombres == sorted(nombres)


def test_el_orden_por_nombre_agrupa_las_acciones_de_cada_recurso(
    client, auth_headers, test_permissions, test_membership
):
    """`name` es "recurso:acción", así que ordenar por él deja juntas todas las
    acciones de un mismo recurso, que es como se leen en la pantalla de roles."""
    response = client.get("/permissions", headers=auth_headers)

    recursos = [x["resource"] for x in response.json()]
    # Cada recurso aparece en un único tramo contiguo.
    tramos = [r for i, r in enumerate(recursos) if i == 0 or recursos[i - 1] != r]
    assert len(tramos) == len(set(tramos))


def test_las_asociaciones_publicas_conservan_su_orden_por_nivel(client, db_session):
    """Ya tenían orden propio —nivel y luego nombre— y no se toca.

    El formulario de alta las enseña agrupadas por nivel de la jerarquía:
    confederaciones, luego federaciones, luego locales. Ordenarlas solo por
    nombre mezclaría los tres niveles.
    """
    for nombre, nivel in [("Zaragoza", 2), ("Albacete", 4), ("Mérida", 3)]:
        db_session.add(
            Entity(name=nombre, level=nivel, created_at=datetime.utcnow())
        )
    db_session.commit()

    response = client.get("/entities/public")

    assert response.status_code == 200
    datos = response.json()
    niveles = [x["level"] for x in datos]
    assert niveles == sorted(niveles)

    # Y dentro de cada nivel, por nombre.
    for nivel in set(niveles):
        del_nivel = [x["name"] for x in datos if x["level"] == nivel]
        assert del_nivel == sorted(del_nivel)
