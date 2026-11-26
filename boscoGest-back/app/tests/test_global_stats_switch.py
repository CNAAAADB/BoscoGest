"""The global statistics switch is private to Superentity superadministration."""
from app.models.role_model import Role
from app.models.entity_model import Entity
from app.models.membership_model import Membership


def test_stats_switch_is_root_only_and_requires_superadmin(
    client, db_session, test_entity, test_user, test_membership,
    test_permissions, auth_headers,
):
    root_id = test_entity.id
    conf = Entity(name="View scope conf", level=2, parent_id=root_id)
    db_session.add(conf)
    db_session.commit()

    endpoint = f"/view-configs/entity/{root_id}/view/member_stats"
    local_endpoint = f"/view-configs/entity/{conf.id}/view/member_stats"
    initial = client.get("/view-configs/member-stats/availability",
                         headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json() == {"is_enabled": False}

    # Even an admin role with views:update on level 1 is not a superadmin.
    denied = client.put(endpoint, json={"is_enabled": True},
                        headers=auth_headers)
    assert denied.status_code == 403
    hidden = client.get(f"/view-configs/entity/{root_id}", headers=auth_headers)
    assert hidden.status_code == 200
    assert "member_stats" not in {c["view_name"] for c in hidden.json()["configs"]}

    superadmin = Role(name="superadmin", description="Global superadmin")
    db_session.add(superadmin)
    db_session.flush()
    superadmin.permissions.extend(test_permissions)
    test_membership.role_id = superadmin.id
    db_session.commit()

    config = client.get(f"/view-configs/entity/{root_id}", headers=auth_headers)
    assert config.status_code == 200
    assert "member_stats" in {c["view_name"] for c in config.json()["configs"]}
    enabled = client.put(endpoint, json={"is_enabled": True}, headers=auth_headers)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["is_enabled"] is True
    assert client.get("/view-configs/member-stats/availability",
                      headers=auth_headers).json()["is_enabled"] is True

    # Global superadmin must still not edit stats per level-2+ entity.
    denied_child = client.put(local_endpoint, json={"is_enabled": False},
                              headers=auth_headers)
    assert denied_child.status_code == 403
    root_forbidden = client.get(f"/member-stats/entity/{root_id}",
                                headers=auth_headers)
    assert root_forbidden.status_code == 403
