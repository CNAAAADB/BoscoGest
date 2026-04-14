import pytest
from datetime import datetime
from io import BytesIO

from app.models.resource_model import Resource, ResourceType
from app.models.resource_category_model import ResourceCategory
from app.models.entity_model import Entity
from app.models.user_model import User
from app.models.role_model import Role
from app.models.membership_model import Membership
from app.utils.auth import get_password_hash, create_access_token


# =====================
# Resource Link CRUD
# =====================

def test_create_resource_link(client, auth_headers, test_entity):
    """Test creating a link resource."""
    data = {
        "title": "Angular Docs",
        "description": "Official Angular documentation",
        "resource_type": "link",
        "url": "https://angular.io/docs",
        "tags": "angular,frontend,docs",
        "entity_id": test_entity.id,
    }
    response = client.post("/resources/link", json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Angular Docs"
    assert body["resource_type"] == "link"
    assert body["url"] == "https://angular.io/docs"
    assert body["entity_id"] == test_entity.id
    assert body["tags"] == "angular,frontend,docs"


def test_create_resource_video(client, auth_headers, test_entity):
    """Test creating a video resource."""
    data = {
        "title": "Python Tutorial",
        "resource_type": "video",
        "url": "https://youtube.com/watch?v=abc123",
        "entity_id": test_entity.id,
    }
    response = client.post("/resources/link", json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["resource_type"] == "video"
    assert body["url"] == "https://youtube.com/watch?v=abc123"


def test_create_resource_link_requires_url(client, auth_headers, test_entity):
    """Test that link resources require a URL."""
    data = {
        "title": "Missing URL",
        "resource_type": "link",
        "entity_id": test_entity.id,
    }
    response = client.post("/resources/link", json=data, headers=auth_headers)
    assert response.status_code == 400


def test_create_resource_link_rejects_document_type(client, auth_headers, test_entity):
    """Test that link endpoint rejects document/image types."""
    data = {
        "title": "Wrong Type",
        "resource_type": "document",
        "url": "https://example.com",
        "entity_id": test_entity.id,
    }
    response = client.post("/resources/link", json=data, headers=auth_headers)
    assert response.status_code == 400


# =====================
# Resource File Upload
# =====================

def test_create_resource_document(client, auth_headers, test_entity):
    """Test uploading a document resource."""
    file_content = b"%PDF-1.4 fake pdf content"
    response = client.post(
        "/resources/",
        data={
            "title": "Test Document",
            "resource_type": "document",
            "entity_id": str(test_entity.id),
            "description": "A test PDF document",
            "tags": "test,pdf",
        },
        files={"file": ("test.pdf", BytesIO(file_content), "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Test Document"
    assert body["resource_type"] == "document"
    assert body["original_filename"] == "test.pdf"
    assert body["file_path"] is not None


def test_create_resource_image(client, auth_headers, test_entity):
    """Test uploading an image resource."""
    # Minimal valid PNG header
    file_content = b"\x89PNG\r\n\x1a\n fake png"
    response = client.post(
        "/resources/",
        data={
            "title": "Test Image",
            "resource_type": "image",
            "entity_id": str(test_entity.id),
        },
        files={"file": ("photo.png", BytesIO(file_content), "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["resource_type"] == "image"
    assert body["original_filename"] == "photo.png"


def test_create_resource_document_rejects_invalid_ext(client, auth_headers, test_entity):
    """Test that document upload rejects invalid file extensions."""
    response = client.post(
        "/resources/",
        data={
            "title": "Bad File",
            "resource_type": "document",
            "entity_id": str(test_entity.id),
        },
        files={"file": ("malware.exe", BytesIO(b"bad"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert response.status_code == 400


# =====================
# Permission Checks
# =====================

def test_create_resource_requires_permission(client, db_session, test_entity):
    """Test that creating a resource requires resources:create permission."""
    # Create user with no permissions (no membership)
    user = User(
        email="noperm@example.com",
        password_hash=get_password_hash("password123A"),
        name="No", surname="Perm", phone="000000000",
        birthdate=datetime(1990, 1, 1).date(), dni="00000000Z",
        is_active=True, created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "title": "Should Fail",
        "resource_type": "link",
        "url": "https://example.com",
        "entity_id": test_entity.id,
    }
    response = client.post("/resources/link", json=data, headers=headers)
    assert response.status_code == 403


# =====================
# List & Filter
# =====================

def test_list_resources(client, auth_headers, db_session, test_entity, test_user):
    """Test listing resources from accessible entities."""
    r1 = Resource(
        title="Resource 1", resource_type=ResourceType.LINK,
        url="https://example.com/1", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    r2 = Resource(
        title="Resource 2", resource_type=ResourceType.LINK,
        url="https://example.com/2", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    response = client.get("/resources/", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2


def test_list_resources_filter_by_type(client, auth_headers, db_session, test_entity, test_user):
    """Test filtering resources by type."""
    link = Resource(
        title="Link Res", resource_type=ResourceType.LINK,
        url="https://example.com", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    vid = Resource(
        title="Video Res", resource_type=ResourceType.VIDEO,
        url="https://youtube.com", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add_all([link, vid])
    db_session.commit()

    response = client.get("/resources/?type=link", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert all(r["resource_type"] == "link" for r in body)


def test_list_resources_filter_by_tags(client, auth_headers, db_session, test_entity, test_user):
    """Test filtering resources by tags."""
    r = Resource(
        title="Tagged", resource_type=ResourceType.LINK,
        url="https://example.com", tags="python,backend",
        entity_id=test_entity.id, created_by=test_user.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(r)
    db_session.commit()

    response = client.get("/resources/?tags=python", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert any("python" in (r.get("tags") or "") for r in body)


def test_list_resources_search(client, auth_headers, db_session, test_entity, test_user):
    """Test searching resources by title/description."""
    r = Resource(
        title="SQLAlchemy Guide", description="How to use SQLAlchemy ORM",
        resource_type=ResourceType.LINK, url="https://example.com",
        entity_id=test_entity.id, created_by=test_user.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(r)
    db_session.commit()

    response = client.get("/resources/?search=SQLAlchemy", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert any("SQLAlchemy" in r["title"] for r in body)


# =====================
# Get Single & File
# =====================

def test_get_resource(client, auth_headers, db_session, test_entity, test_user):
    """Test getting a single resource by ID."""
    r = Resource(
        title="Single Resource", resource_type=ResourceType.LINK,
        url="https://example.com/single", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)

    response = client.get(f"/resources/{r.id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Single Resource"
    assert body["id"] == r.id


def test_get_resource_not_found(client, auth_headers):
    """Test getting a non-existent resource."""
    response = client.get("/resources/99999", headers=auth_headers)
    assert response.status_code == 404


# =====================
# Update
# =====================

def test_update_resource(client, auth_headers, db_session, test_entity, test_user):
    """Test updating resource metadata."""
    r = Resource(
        title="Old Title", resource_type=ResourceType.LINK,
        url="https://example.com", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)

    update_data = {"title": "New Title", "tags": "updated,tag"}
    response = client.put(f"/resources/{r.id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New Title"
    assert body["tags"] == "updated,tag"


# =====================
# Delete
# =====================

def test_delete_resource(client, auth_headers, db_session, test_entity, test_user):
    """Test deleting a resource."""
    r = Resource(
        title="To Delete", resource_type=ResourceType.LINK,
        url="https://example.com/delete", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)

    response = client.delete(f"/resources/{r.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/resources/{r.id}", headers=auth_headers)
    assert response.status_code == 404


# =====================
# Categories
# =====================

def test_create_category(client, auth_headers, test_entity):
    """Test creating a resource category."""
    data = {
        "name": "Tutorials",
        "description": "Tutorial resources",
        "entity_id": test_entity.id,
    }
    response = client.post("/resource-categories/", json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Tutorials"
    assert body["entity_id"] == test_entity.id


def test_list_categories(client, auth_headers, db_session, test_entity):
    """Test listing categories for an entity."""
    cat1 = ResourceCategory(
        name="Cat 1", entity_id=test_entity.id, created_at=datetime.utcnow(),
    )
    cat2 = ResourceCategory(
        name="Cat 2", entity_id=test_entity.id, created_at=datetime.utcnow(),
    )
    db_session.add_all([cat1, cat2])
    db_session.commit()

    response = client.get(
        f"/resource-categories/?entity_id={test_entity.id}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2


def test_update_category(client, auth_headers, db_session, test_entity):
    """Test updating a category."""
    cat = ResourceCategory(
        name="Old Name", entity_id=test_entity.id, created_at=datetime.utcnow(),
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    response = client.put(
        f"/resource-categories/{cat.id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_category(client, auth_headers, db_session, test_entity):
    """Test soft-deleting a category."""
    cat = ResourceCategory(
        name="To Delete", entity_id=test_entity.id, created_at=datetime.utcnow(),
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    response = client.delete(f"/resource-categories/{cat.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's soft-deleted (still in DB but is_active=False)
    db_session.refresh(cat)
    assert cat.is_active is False


def test_list_resources_filter_by_category(client, auth_headers, db_session, test_entity, test_user):
    """Test filtering resources by category."""
    cat = ResourceCategory(
        name="Test Cat", entity_id=test_entity.id, created_at=datetime.utcnow(),
    )
    db_session.add(cat)
    db_session.flush()

    r_with_cat = Resource(
        title="Categorized", resource_type=ResourceType.LINK,
        url="https://example.com/cat", entity_id=test_entity.id,
        category_id=cat.id, created_by=test_user.id,
        created_at=datetime.utcnow(),
    )
    r_without_cat = Resource(
        title="Uncategorized", resource_type=ResourceType.LINK,
        url="https://example.com/nocat", entity_id=test_entity.id,
        created_by=test_user.id, created_at=datetime.utcnow(),
    )
    db_session.add_all([r_with_cat, r_without_cat])
    db_session.commit()

    response = client.get(f"/resources/?category_id={cat.id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert all(r["category_id"] == cat.id for r in body)
    assert len(body) >= 1


# =====================
# Hierarchical Permissions
# =====================

def test_hierarchical_permission_inheritance(client, db_session, test_permissions):
    """Test that admin at parent entity can manage resources in child entity."""
    # Create parent entity (L1)
    parent = Entity(name="Parent Org", level=1, created_at=datetime.utcnow())
    db_session.add(parent)
    db_session.flush()

    # Create child entity (L2)
    child = Entity(
        name="Child Org", level=2, parent_id=parent.id, created_at=datetime.utcnow()
    )
    db_session.add(child)
    db_session.flush()

    # Get admin role
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Admin")
        db_session.add(admin_role)
        db_session.flush()
        admin_role.permissions.extend(test_permissions)

    # Create user with admin membership at PARENT only
    user = User(
        email="hierarchy_admin@example.com",
        password_hash=get_password_hash("password123A"),
        name="Hierarchy", surname="Admin", phone="111111111",
        birthdate=datetime(1990, 1, 1).date(), dni="11111111H",
        is_active=True, created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.flush()

    membership = Membership(
        user_id=user.id, entity_id=parent.id,
        role_id=admin_role.id, is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()

    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Admin at parent should be able to create resource in child entity
    # (resources:create is inheritable)
    data = {
        "title": "Child Resource",
        "resource_type": "link",
        "url": "https://example.com/child",
        "entity_id": child.id,
    }
    response = client.post("/resources/link", json=data, headers=headers)
    assert response.status_code == 201
    assert response.json()["entity_id"] == child.id
