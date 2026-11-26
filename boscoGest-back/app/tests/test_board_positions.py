"""Board positions are descriptive and are scoped to the user's active memberships."""
from datetime import date, datetime
import pytest

from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.role_model import Role
from app.models.user_model import User
from app.models.board_position_model import BoardPosition
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture
def board_context(db_session, test_membership, test_entity):
    """National 1 -> confederation 2 -> federal 3 -> local 4."""
    federation_parent = Entity(name="Confederation Board Test", level=2,
                               parent_id=test_entity.id)
    db_session.add(federation_parent)
    db_session.flush()
    federation = Entity(name="Federation Board Test", level=3,
                        parent_id=federation_parent.id)
    other_federation = Entity(name="Other Federation Board Test", level=3,
                              parent_id=federation_parent.id)
    db_session.add_all([federation, other_federation])
    db_session.flush()
    local = Entity(name="Local Board Test", level=4, parent_id=federation.id)
    other_local = Entity(name="Other Local Board Test", level=4,
                         parent_id=other_federation.id)
    db_session.add_all([local, other_local])
    db_session.flush()

    def person(code):
        p = User(email=f"{code}@example.com",
                 password_hash=get_password_hash("test-password-123"),
                 name=code, surname="Board", birthdate=date(1990, 1, 1),
                 is_active=True, created_at=datetime.utcnow())
        db_session.add(p)
        db_session.flush()
        return p

    federal_admin = person("federal-board-admin")
    local_admin = person("local-board-admin")
    member = person("board-member")
    outsider = person("other-board-member")
    role = test_membership.role
    socio = db_session.query(Role).filter(Role.name == "socio").one()
    assert role is not None
    db_session.add_all([
        Membership(user_id=federal_admin.id, role_id=role.id, entity_id=federation.id),
        Membership(user_id=local_admin.id, role_id=role.id, entity_id=local.id),
        Membership(user_id=member.id, role_id=role.id, entity_id=local.id),
        Membership(user_id=outsider.id, role_id=role.id, entity_id=other_local.id),
        # Like real memberships, these users also carry a root 'socio'
        # enrollment. That must not turn a local administrator into national.
        Membership(user_id=local_admin.id, role_id=socio.id, entity_id=test_entity.id),
        Membership(user_id=federal_admin.id, role_id=socio.id, entity_id=test_entity.id),
    ])
    db_session.commit()

    def headers(p):
        return {"Authorization": f"Bearer {create_access_token({'sub': str(p.id)})}"}

    return {
        "national": test_membership.user,
        "federal": federal_admin,
        "local_admin": local_admin,
        "member": member,
        "outsider": outsider,
        "local": local,
        "other_local": other_local,
        "federation": federation,
        "other_federation": other_federation,
        "headers": headers,
    }


def test_multiple_board_roles_with_entity_and_custom_label(
    client, db_session, board_context,
):
    c = board_context
    url = f"/board-positions/users/{c['member'].id}"
    headers = c["headers"](c["federal"])
    options = client.get(url + "/available-entities", headers=headers)
    assert options.status_code == 200
    assert [e["id"] for e in options.json()] == [c["local"].id]
    president = client.post(url, headers=headers, json={
        "entity_id": c["local"].id, "role_code": "presidente"
    })
    assert president.status_code == 201, president.text
    assert president.json()["title"] == "Presidente"
    custom = client.post(url, headers=headers, json={
        "entity_id": c["local"].id, "role_code": "otro",
        "custom_title": "Vocal de formación"
    })
    assert custom.status_code == 201, custom.text
    assert custom.json()["title"] == "Vocal de formación"
    listed = client.get(url, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    duplicate = client.post(url, headers=headers, json={
        "entity_id": c["local"].id, "role_code": "otro",
        "custom_title": "vocal de formación"
    })
    assert duplicate.status_code == 409
    assert db_session.query(BoardPosition).count() == 2

    removed = client.delete(f"/board-positions/{president.json()['id']}",
                            headers=headers)
    assert removed.status_code == 204
    assert len(client.get(url, headers=headers).json()) == 1


def test_only_federal_or_national_may_assign_within_scope(client, board_context):
    c = board_context
    url = f"/board-positions/users/{c['member'].id}"
    payload = {"entity_id": c["local"].id, "role_code": "secretario"}
    local_response = client.post(url, json=payload, headers=c["headers"](c["local_admin"]))
    assert local_response.status_code == 403
    federal_response = client.post(url, json=payload, headers=c["headers"](c["federal"]))
    assert federal_response.status_code == 201
    wrong_local = client.post(
        f"/board-positions/users/{c['outsider'].id}",
        json={"entity_id": c["other_local"].id, "role_code": "presidente"},
        headers=c["headers"](c["federal"]),
    )
    assert wrong_local.status_code == 403
    national = client.post(
        f"/board-positions/users/{c['outsider'].id}",
        json={"entity_id": c["other_local"].id, "role_code": "presidente"},
        headers=c["headers"](c["national"]),
    )
    assert national.status_code == 201, national.text
    assert client.delete(f"/board-positions/{national.json()['id']}",
                         headers=c["headers"](c["federal"])).status_code == 403


def test_reject_membership_not_assigned_and_bad_custom_role(client, board_context):
    c = board_context
    url = f"/board-positions/users/{c['member'].id}"
    headers = c["headers"](c["national"])
    wrong_entity = client.post(url, headers=headers, json={
        "entity_id": c["other_local"].id, "role_code": "presidente"
    })
    assert wrong_entity.status_code == 422
    invalid = client.post(url, headers=headers, json={
        "entity_id": c["local"].id, "role_code": "otro", "custom_title": " "
    })
    assert invalid.status_code == 422
    invalid_fixed = client.post(url, headers=headers, json={
        "entity_id": c["local"].id, "role_code": "tesorero",
        "custom_title": "Superadministrador"
    })
    assert invalid_fixed.status_code == 422


def test_organigram_is_structured_and_federation_isolated(client, board_context):
    c = board_context
    national = c["headers"](c["national"])
    local_id = c["local"].id
    other_id = c["other_local"].id
    for user_id, entity_id in ((c["member"].id, local_id),
                               (c["outsider"].id, other_id)):
        response = client.post(
            f"/board-positions/users/{user_id}", headers=national,
            json={"entity_id": entity_id, "role_code": "presidente"}
        )
        assert response.status_code == 201, response.text
    fed = c["headers"](c["federal"])
    roster = client.get(f"/board-positions/organigram/{c['federation'].id}",
                        headers=fed)
    assert roster.status_code == 200, roster.text
    assert [row["user_id"] for row in roster.json()] == [c["member"].id]
    assert all("email" not in row and "dni" not in row for row in roster.json())
    blocked = client.get(f"/board-positions/organigram/{c['other_federation'].id}",
                         headers=fed)
    assert blocked.status_code == 403
    all_roster = client.get(f"/board-positions/organigram/{c['federation'].parent_id}",
                            headers=national)
    assert all_roster.status_code == 200
    assert len(all_roster.json()) == 2


def test_superentity_cannot_receive_board_positions(client, board_context):
    c = board_context
    root_id = c["federation"].parent.parent_id
    # The national administrator has an active membership at level 1.
    national = c["national"]
    response = client.post(
        f"/board-positions/users/{national.id}",
        json={"entity_id": root_id, "role_code": "presidente"},
        headers=c["headers"](national),
    )
    assert response.status_code == 403
    choices = client.get(
        f"/board-positions/users/{national.id}/available-entities",
        headers=c["headers"](national),
    )
    assert choices.status_code == 200
    assert root_id not in {entity["id"] for entity in choices.json()}
    organigram = client.get(
        f"/board-positions/organigram/{root_id}",
        headers=c["headers"](national),
    )
    assert organigram.status_code == 403
