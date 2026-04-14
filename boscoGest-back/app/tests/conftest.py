import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.utils.auth import get_sync_db, create_access_token, get_password_hash
from app.models.user_model import User
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.models.permission_model import Permission
from app.models.membership_model import Membership
from datetime import datetime

# Force local storage backend for tests BEFORE importing app
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("UPLOAD_DIR", "uploads")

from app.services.storage import reset_storage_service
reset_storage_service()

from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_sync_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_permissions(db_session):
    permissions_data = [
        ("users:create", "users", "create", "Create user"),
        ("users:read", "users", "read", "Read user"),
        ("users:update", "users", "update", "Update user"),
        ("users:delete", "users", "delete", "Delete user"),
        ("users:list", "users", "list", "List users"),
        ("users:manage", "users", "manage", "Manage users"),
        ("entities:create", "entities", "create", "Create entity"),
        ("entities:read", "entities", "read", "Read entity"),
        ("entities:update", "entities", "update", "Update entity"),
        ("entities:delete", "entities", "delete", "Delete entity"),
        ("entities:list", "entities", "list", "List entities"),
        ("entities:manage_all", "entities", "manage_all", "Manage all entities"),
        ("roles:create", "roles", "create", "Create role"),
        ("roles:read", "roles", "read", "Read role"),
        ("roles:update", "roles", "update", "Update role"),
        ("roles:delete", "roles", "delete", "Delete role"),
        ("roles:list", "roles", "list", "List roles"),
        ("roles:assign", "roles", "assign", "Assign permissions to roles"),
        ("roles:manage", "roles", "manage", "Manage roles"),
        ("memberships:create", "memberships", "create", "Create membership"),
        ("memberships:read", "memberships", "read", "Read membership"),
        ("memberships:update", "memberships", "update", "Update membership"),
        ("memberships:delete", "memberships", "delete", "Delete membership"),
        ("memberships:list", "memberships", "list", "List memberships"),
        ("memberships:manage", "memberships", "manage", "Manage memberships"),
        ("permissions:create", "permissions", "create", "Create permission"),
        ("permissions:read", "permissions", "read", "Read permission"),
        ("permissions:update", "permissions", "update", "Update permission"),
        ("permissions:delete", "permissions", "delete", "Delete permission"),
        ("permissions:list", "permissions", "list", "List permissions"),
        ("permissions:assign", "permissions", "assign", "Assign permissions to roles"),
        ("groups:create", "groups", "create", "Create group"),
        ("groups:read", "groups", "read", "Read group"),
        ("groups:update", "groups", "update", "Update group"),
        ("groups:delete", "groups", "delete", "Delete group"),
        ("groups:list", "groups", "list", "List groups"),
        ("groups:assign", "groups", "assign", "Assign users/roles to groups"),
        ("activities:create", "activities", "create", "Create activity"),
        ("activities:read", "activities", "read", "Read activity"),
        ("activities:update", "activities", "update", "Update activity"),
        ("activities:delete", "activities", "delete", "Delete activity"),
        ("activities:list", "activities", "list", "List activities"),
        ("activities:manage", "activities", "manage", "Manage activity registrations"),
        ("communications:create", "communications", "create", "Create communication"),
        ("communications:read", "communications", "read", "Read communication"),
        ("communications:edit", "communications", "edit", "Edit communication"),
        ("communications:delete", "communications", "delete", "Delete communication"),
        ("communications:manage_all", "communications", "manage_all", "Manage all communications"),
        ("comment:create", "comment", "create", "Create comment"),
        ("comment:read", "comment", "read", "Read comment"),
        ("comment:edit", "comment", "edit", "Edit comment"),
        ("comment:delete", "comment", "delete", "Delete comment"),
        ("comment:manage_all", "comment", "manage_all", "Manage all comments"),
        ("resources:create", "resources", "create", "Create resource"),
        ("resources:read", "resources", "read", "Read resource"),
        ("resources:update", "resources", "update", "Update resource"),
        ("resources:delete", "resources", "delete", "Delete resource"),
        ("resources:list", "resources", "list", "List resources"),
        ("resources:manage_all", "resources", "manage_all", "Manage all resources"),
    ]

    # Permissions that should NOT inherit to descendant entities
    non_inheritable = {
        ("entities", "create"), ("entities", "update"), ("entities", "delete"),
        ("memberships", "create"), ("memberships", "read"), ("memberships", "update"),
        ("memberships", "delete"), ("memberships", "list"), ("memberships", "manage"),
        ("roles", "create"), ("roles", "update"), ("roles", "delete"), ("roles", "assign"),
    }

    permissions = []
    for name, resource, action, description in permissions_data:
        perm = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
            inheritable=(resource, action) not in non_inheritable
        )
        db_session.add(perm)
        permissions.append(perm)

    db_session.commit()
    return permissions


@pytest.fixture(scope="function")
def test_entity(db_session, test_permissions):
    # Crear o reutilizar rol admin global
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(
            name="admin",
            description="Administrator role with full permissions"
        )
        db_session.add(admin_role)
        db_session.flush()
        admin_role.permissions.extend(test_permissions)
        db_session.commit()

    # Crear o reutilizar rol socio global
    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    if not socio_role:
        socio_role = Role(
            name="socio",
            description="Member role with read-only permissions"
        )
        db_session.add(socio_role)
        db_session.flush()
        # Asignar solo permisos de lectura al rol socio
        read_actions = ["read", "list"]
        socio_permissions = [p for p in test_permissions if p.action in read_actions]
        socio_role.permissions.extend(socio_permissions)
        db_session.commit()

    # Crear entidad
    entity = Entity(
        name="Test Organization",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(entity)
    db_session.flush()

    # Asociar roles admin y socio a la entidad
    entity.roles.extend([admin_role, socio_role])
    db_session.commit()
    db_session.refresh(entity)
    return entity


@pytest.fixture(scope="function")
def test_role(db_session, test_entity):
    # Retornar el rol admin global asociado a la entidad
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    return admin_role


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        name="Test",
        surname="User",
        phone="123456789",
        birthdate=datetime(1990, 1, 1).date(),
        dni="12345678A",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_membership(db_session, test_user, test_entity, test_role):
    membership = Membership(
        user_id=test_user.id,
        entity_id=test_entity.id,
        role_id=test_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


@pytest.fixture(scope="function")
def auth_token(test_user, test_membership):
    token_data = {
        "sub": test_user.email,
        "membership_id": test_membership.id
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# --- Hierarchical RBAC fixtures ---

@pytest.fixture(scope="function")
def entity_hierarchy(db_session):
    """Creates a 4-level entity hierarchy: L1 → L2 → L3 → L4."""
    superentity = Entity(name="Superentity", level=1, created_at=datetime.utcnow())
    db_session.add(superentity)
    db_session.flush()

    confederation = Entity(name="Confederation", level=2, parent_id=superentity.id, created_at=datetime.utcnow())
    db_session.add(confederation)
    db_session.flush()

    federation = Entity(name="Federation", level=3, parent_id=confederation.id, created_at=datetime.utcnow())
    db_session.add(federation)
    db_session.flush()

    local = Entity(name="Local", level=4, parent_id=federation.id, created_at=datetime.utcnow())
    db_session.add(local)
    db_session.flush()

    db_session.commit()
    return {
        "superentity": superentity,
        "confederation": confederation,
        "federation": federation,
        "local": local,
    }


@pytest.fixture(scope="function")
def hierarchy_permissions(db_session):
    """Creates a focused set of permissions with correct inheritable flags for hierarchy tests."""
    perms = {}
    data = [
        ("users", "create", True),
        ("users", "read", True),
        ("users", "list", True),
        ("users", "delete", True),
        ("entities", "delete", False),
        ("entities", "read", True),
        ("entities", "manage_all", True),
        ("branding", "update", False),
        ("branding", "read", False),
        ("memberships", "create", False),
        ("activities", "create", True),
    ]
    for resource, action, inheritable in data:
        p = Permission(
            name=f"{resource}:{action}",
            resource=resource,
            action=action,
            inheritable=inheritable,
        )
        db_session.add(p)
        perms[(resource, action)] = p
    db_session.commit()
    return perms
