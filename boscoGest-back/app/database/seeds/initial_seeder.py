from alembic import op
import sqlalchemy as sa
from app.utils.auth import get_password_hash
from datetime import date

def seed():
    """Seed initial data using raw SQL to avoid ORM model drift.

    This runs in migration 731a72582ecd, right after create_initial_tables.
    Only references columns that exist at that point in the schema.
    """
    bind = op.get_bind()

    # ----------------------------
    # Roles
    # ----------------------------
    bind.execute(sa.text(
        "INSERT INTO roles (name, description, is_active) VALUES "
        "(:n1, :d1, true), (:n2, :d2, true), (:n3, :d3, true)"
    ), {
        "n1": "superadmin", "d1": "Superadmin role with all permissions",
        "n2": "admin", "d2": "Administrator role with full permissions",
        "n3": "socio", "d3": "Member role with read-only permissions",
    })

    superadmin_role_id = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'superadmin'")).scalar()
    admin_role_id = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'admin'")).scalar()
    socio_role_id = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'socio'")).scalar()

    # ----------------------------
    # Users (only columns from initial migration)
    # ----------------------------
    password_hash = get_password_hash("superadmin123")
    bind.execute(sa.text(
        "INSERT INTO users (password_hash, email, is_active, name, surname, phone, address, birthdate, dni, photo, iban, size) "
        "VALUES (:pw, :email, true, :name, :surname, :phone, :addr, :birth, :dni, :photo, :iban, :size)"
    ), {
        "pw": password_hash, "email": "superadmin@boscogest.com",
        "name": "BoscoGest", "surname": "Superadmin",
        "phone": "000000000", "addr": "", "birth": date(1990, 1, 1),
        "dni": "00000000X", "photo": "", "iban": "", "size": "",
    })

    user_id = bind.execute(sa.text("SELECT id FROM users WHERE email = 'superadmin@boscogest.com'")).scalar()

    # ----------------------------
    # Entity inicial
    # ----------------------------
    bind.execute(sa.text(
        "INSERT INTO entities (name, level, is_active) VALUES (:name, :level, true)"
    ), {"name": "superentity", "level": 1})

    entity_id = bind.execute(sa.text("SELECT id FROM entities WHERE name = 'superentity'")).scalar()

    # ----------------------------
    # Membership (includes is_current from initial schema)
    # ----------------------------
    bind.execute(sa.text(
        "INSERT INTO memberships (user_id, role_id, entity_id, is_active, is_current) "
        "VALUES (:uid, :rid, :eid, true, true)"
    ), {"uid": user_id, "rid": superadmin_role_id, "eid": entity_id})

    # ----------------------------
    # Permissions
    # ----------------------------
    permission_resources = ["users", "roles", "groups", "permissions", "entities", "memberships", "activities", "resources", "notifications"]
    permission_actions = ["create", "list", "read", "update", "delete", "assign", "manage"]

    all_permission_ids = []
    read_only_permission_ids = []

    for resource in permission_resources:
        for action in permission_actions:
            permission_name = f"{resource}_{action}_permission"
            bind.execute(sa.text(
                "INSERT INTO permissions (name, resource, action, is_active) "
                "VALUES (:name, :resource, :action, true)"
            ), {"name": permission_name, "resource": resource, "action": action})

            pid = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE name = :name"
            ), {"name": permission_name}).scalar()

            all_permission_ids.append(pid)
            if action in ["read", "list"]:
                read_only_permission_ids.append(pid)

    # Associate ALL permissions to superadmin and admin roles
    for pid in all_permission_ids:
        bind.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
        ), {"rid": superadmin_role_id, "pid": pid})
        bind.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
        ), {"rid": admin_role_id, "pid": pid})

    # Associate read-only permissions to socio role
    for pid in read_only_permission_ids:
        bind.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
        ), {"rid": socio_role_id, "pid": pid})

    # ----------------------------
    # Associate roles to initial entity
    # ----------------------------
    for rid in [superadmin_role_id, admin_role_id, socio_role_id]:
        bind.execute(sa.text(
            "INSERT INTO entity_roles (entity_id, role_id) VALUES (:eid, :rid)"
        ), {"eid": entity_id, "rid": rid})
