"""Idempotent seed for a freshly migrated database.

Creates the minimum a usable BoscoGest install needs: the permission
catalogue, the three default roles, the level-1 entity and a superadmin
membership. Safe to re-run — every insert is guarded by an existence check.

Run it *after* ``alembic upgrade head``:

    python -m app.database.seeds.initial_seeder

The superadmin password is read from ``SEED_SUPERADMIN_PASSWORD``. There is no
default: a well-known bootstrap password on an internet-facing deployment is a
back door, so the script refuses to run without one.

The previous version of this file was dead code — it inserted into a
``memberships.is_current`` column that no longer exists and referenced a
migration revision (``731a72582ecd``) that is not in the tree, so it could
never have run against the current schema.
"""

import argparse
import os
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SyncSessionLocal
from app.database.seeds.permissions_catalog import (
    ALL_PERMISSIONS,
    READ_ONLY_PERMISSIONS,
)
from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.permission_model import Permission
from app.models.role_model import Role
from app.models.user_model import User
from app.utils.auth import get_password_hash

# Shown in the roles screen, so the wording is for whoever reads it there.
DEFAULT_ROLES = [
    ("superadmin", "Control total de la plataforma"),
    ("admin", "Gestiona su asociación: socios, contenidos y cuotas"),
    ("socio", "Consulta los contenidos de su asociación y sus propias cuotas"),
]


def _seed_permissions(db: Session) -> dict:
    existing = {
        (p.resource, p.action): p
        for p in db.execute(select(Permission)).scalars()
    }
    created = 0
    for spec in ALL_PERMISSIONS:
        key = (spec.resource, spec.action)
        if key in existing:
            # The catalogue stays authoritative on re-runs. The description
            # matters as much as the flag: permissions created by earlier
            # migrations have none, and the roles screen shows it to whoever is
            # deciding what a role can do.
            existing[key].inheritable = spec.inheritable
            existing[key].description = spec.description
            continue
        perm = Permission(
            name=spec.name,
            resource=spec.resource,
            action=spec.action,
            description=spec.description,
            inheritable=spec.inheritable,
            is_active=True,
        )
        db.add(perm)
        existing[key] = perm
        created += 1
    db.flush()
    print(f"  permissions: {created} created, {len(ALL_PERMISSIONS) - created} already present")
    return existing


def _seed_roles(db: Session, permissions: dict) -> dict:
    roles = {r.name: r for r in db.execute(select(Role)).scalars()}
    for name, description in DEFAULT_ROLES:
        if name not in roles:
            role = Role(name=name, description=description, is_active=True)
            db.add(role)
            roles[name] = role
        else:
            # Same reason as the permissions: earlier runs left English text
            # that the roles screen shows to Spanish-speaking administrators.
            roles[name].description = description
    db.flush()

    all_perms = list(permissions.values())
    read_only = [permissions[(p.resource, p.action)] for p in READ_ONLY_PERMISSIONS]

    for role_name, granted in (
        ("superadmin", all_perms),
        ("admin", all_perms),
        ("socio", read_only),
    ):
        role = roles[role_name]
        current = {p.id for p in role.permissions if p.id is not None}
        for perm in granted:
            if perm.id is None or perm.id not in current:
                role.permissions.append(perm)
        print(f"  role '{role_name}': {len(role.permissions)} permissions")
    db.flush()
    return roles


def _seed_entity(db: Session, roles: dict, entity_name: str) -> Entity:
    entity = db.execute(
        select(Entity).where(Entity.level == 1)
    ).scalars().first()
    if entity is None:
        entity = Entity(name=entity_name, level=1, parent_id=None, is_active=True)
        db.add(entity)
        db.flush()
        print(f"  entity: created level-1 '{entity_name}' (id={entity.id})")
    else:
        print(f"  entity: level-1 '{entity.name}' already exists (id={entity.id})")

    for role in roles.values():
        if entity not in role.entities:
            role.entities.append(entity)
    db.flush()
    return entity


def _seed_superadmin(db: Session, entity: Entity, roles: dict, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalars().first()
    if user is None:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            name="BoscoGest",
            surname="Superadmin",
            phone=None,
            address="",
            birthdate=date(1990, 1, 1),
            dni="00000000X",
            photo="",
            iban=None,
            size=None,
            is_active=True,
            # Forces a password change on first login instead of leaving the
            # bootstrap credential valid indefinitely.
            must_change_password=True,
        )
        db.add(user)
        db.flush()
        print(f"  user: created superadmin '{email}' (id={user.id})")
    else:
        print(f"  user: superadmin '{email}' already exists (id={user.id})")

    membership = db.execute(
        select(Membership).where(
            Membership.user_id == user.id, Membership.entity_id == entity.id
        )
    ).scalars().first()
    if membership is None:
        db.add(Membership(
            user_id=user.id,
            role_id=roles["superadmin"].id,
            entity_id=entity.id,
            is_active=True,
        ))
        print("  membership: superadmin bound to the level-1 entity")
    else:
        print("  membership: already present")
    db.flush()
    return user


def seed(entity_name: str = "superentity", email: str = "superadmin@boscogest.com") -> None:
    password = os.getenv("SEED_SUPERADMIN_PASSWORD", "").strip()
    if not password:
        sys.exit(
            "SEED_SUPERADMIN_PASSWORD is not set.\n"
            "Refusing to seed with a hardcoded bootstrap password. Set it, e.g.:\n"
            '  SEED_SUPERADMIN_PASSWORD="$(python -c \'import secrets;'
            "print(secrets.token_urlsafe(16))')\" python -m app.database.seeds.initial_seeder"
        )
    if len(password) < 12:
        sys.exit("SEED_SUPERADMIN_PASSWORD must be at least 12 characters long.")

    with SyncSessionLocal() as db:
        print("Seeding BoscoGest…")
        permissions = _seed_permissions(db)
        roles = _seed_roles(db, permissions)
        entity = _seed_entity(db, roles, entity_name)
        _seed_superadmin(db, entity, roles, email, password)
        db.commit()
        print("Done. The superadmin must change its password on first login.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a freshly migrated BoscoGest database.")
    parser.add_argument("--entity-name", default="superentity", help="Name of the level-1 entity")
    parser.add_argument("--email", default="superadmin@boscogest.com", help="Superadmin email")
    args = parser.parse_args()
    seed(entity_name=args.entity_name, email=args.email)


if __name__ == "__main__":
    main()
