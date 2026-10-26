import pytest
from datetime import datetime
from io import BytesIO


def test_create_communication(client, auth_headers, test_entity, test_membership, db_session):
    """Test creating communication - entity_id is auto-assigned from active membership"""

    # Debug: check permissions
    db_session.refresh(test_membership)
    print(f"\n=== DEBUG: Role = {test_membership.role.name}, Permissions count = {len(test_membership.role.permissions)}")
    for perm in test_membership.role.permissions:
        if perm.resource == "communications":
            print(f"  - Communications permission: action={perm.action}")

    communication_data = {
        "title": "Test Communication",
        "content": "This is a test communication article with some content.",
        "image_url": "https://example.com/image.jpg",
        "entity_id": test_entity.id
    }

    response = client.post("/communications", json=communication_data, headers=auth_headers)

    print(f"\nResponse status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response body: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Communication"
    assert data["content"] == "This is a test communication article with some content."
    assert data["entity_id"] == test_entity.id  # Auto-assigned from active membership
    assert data["is_active"] is True


def test_create_communication_without_permission(client, db_session, test_entity):
    """Test that creating communication fails when user doesn't have create permission"""
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token

    # Create user without communications:create permission
    user = User(
        email="nopermission@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="Permission",
        phone="444444444",
        birthdate=datetime(1990, 1, 1).date(),
        dni="44444444D",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.flush()

    # Create role without communication permissions
    role = Role(
        name="viewer",
        description="Viewer role without communication create permission"
    )
    db_session.add(role)
    db_session.flush()

    # Create membership
    membership = Membership(
        user_id=user.id,
        entity_id=test_entity.id,
        role_id=role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(membership)
    db_session.commit()

    # Create token
    token = create_access_token({"sub": str(user.id), "membership_id": membership.id})
    headers = {"Authorization": f"Bearer {token}"}

    communication_data = {
        "title": "Should Fail Communication",
        "content": "Should fail due to lack of permission",
        "entity_id": test_entity.id
    }

    response = client.post("/communications", json=communication_data, headers=headers)

    assert response.status_code == 403


def test_create_communication_unauthorized(client):
    """Test that creating communication requires authentication"""
    communication_data = {
        "title": "Unauthorized Communication",
        "content": "Should fail"
    }

    response = client.post("/communications", json=communication_data)

    assert response.status_code == 401


def test_list_communications(client, auth_headers, db_session, test_entity, test_user):
    """Test listing communications - should only show communications from user's entities"""
    from app.models.communication_model import Communication
    from app.models.entity_model import Entity

    # Communication in user's entity
    communication_in_user_entity = Communication(
        title="User Entity Communication",
        content="Communication from user's entity",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication_in_user_entity)

    # Create another entity where user is NOT a member
    other_entity = Entity(
        name="Other Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Communication in other entity (user shouldn't see this)
    communication_in_other_entity = Communication(
        title="Other Entity Communication",
        content="Communication from other entity",
        entity_id=other_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication_in_other_entity)
    db_session.commit()

    # List communications
    response = client.get("/communications", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Only communications from user's entity
    assert data[0]["title"] == "User Entity Communication"


def test_list_communications_with_pagination(client, auth_headers, db_session, test_entity, test_user):
    """Test communication pagination"""
    from app.models.communication_model import Communication

    # Create multiple communications
    for i in range(15):
        communication = Communication(
            title=f"Communication {i}",
            content=f"Content {i}",
            entity_id=test_entity.id,
            created_by_id=test_user.id
        )
        db_session.add(communication)
    db_session.commit()

    # Get first page (10 items)
    response = client.get("/communications?skip=0&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10

    # Get second page (5 items)
    response = client.get("/communications?skip=10&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_count_communications(client, auth_headers, db_session, test_entity, test_user):
    """Test counting communications"""
    from app.models.communication_model import Communication

    # Create communications
    for i in range(5):
        communication = Communication(
            title=f"Communication {i}",
            content=f"Content {i}",
            entity_id=test_entity.id,
            created_by_id=test_user.id
        )
        db_session.add(communication)
    db_session.commit()

    response = client.get("/communications/count", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5


def test_get_communication_by_id(client, auth_headers, db_session, test_entity, test_user):
    """Test getting specific communication by ID"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="Specific Communication",
        content="Specific content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    response = client.get(f"/communications/{communication.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Specific Communication"
    assert data["id"] == communication.id


def test_get_communication_not_found(client, auth_headers):
    """Test getting non-existent communication"""
    response = client.get("/communications/99999", headers=auth_headers)

    assert response.status_code == 404


def test_get_communication_no_access(client, db_session, test_entity, test_user):
    """Test that user cannot access communications from entities they're not a member of"""
    from app.models.communication_model import Communication
    from app.models.entity_model import Entity
    from app.models.user_model import User
    from app.models.role_model import Role
    from app.models.membership_model import Membership
    from app.utils.auth import get_password_hash, create_access_token

    # Create another entity
    other_entity = Entity(
        name="Other Entity",
        level=1,
        parent_id=None,
        created_at=datetime.utcnow()
    )
    db_session.add(other_entity)
    db_session.flush()

    # Create communication in other entity
    communication = Communication(
        title="Other Entity Communication",
        content="Content",
        entity_id=other_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    # Create user in test_entity (not in other_entity)
    user = User(
        email="noaccess@example.com",
        password_hash=get_password_hash("password"),
        name="No",
        surname="Access",
        phone="555555555",
        birthdate=datetime(1990, 1, 1).date(),
        dni="55555555E",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.flush()

    # Use socio role (no manage_all) — user should NOT see communications from other entities
    socio_role = db_session.query(Role).filter(Role.name == "socio").first()

    membership = Membership(
        user_id=user.id,
        entity_id=test_entity.id,
        role_id=socio_role.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(membership)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "membership_id": membership.id})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/communications/{communication.id}", headers=headers)

    assert response.status_code == 403


def test_update_communication(client, auth_headers, db_session, test_entity, test_user):
    """Test updating communication"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="Original Title",
        content="Original content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    update_data = {
        "title": "Updated Title",
        "content": "Updated content"
    }

    response = client.put(f"/communications/{communication.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"


def test_update_communication_not_found(client, auth_headers):
    """Test updating non-existent communication"""
    update_data = {
        "title": "Updated Title",
        "content": "Updated content"
    }

    response = client.put("/communications/99999", json=update_data, headers=auth_headers)

    assert response.status_code == 404


def test_delete_communication(client, auth_headers, db_session, test_entity, test_user):
    """Test soft deleting communication"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="To Delete",
        content="Will be deleted",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    response = client.delete(f"/communications/{communication.id}", headers=auth_headers)

    assert response.status_code == 200

    # Verify soft delete
    db_session.refresh(communication)
    assert communication.is_active is False


def test_delete_communication_not_found(client, auth_headers):
    """Test deleting non-existent communication"""
    response = client.delete("/communications/99999", headers=auth_headers)

    assert response.status_code == 404


def test_create_comment(client, auth_headers, db_session, test_entity, test_user):
    """Test creating a comment on communication"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="Communication with comments",
        content="Content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    comment_data = {
        "content": "This is a test comment"
    }

    response = client.post(f"/comments/communications/{communication.id}/comments", json=comment_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "This is a test comment"
    assert data["communication_id"] == communication.id
    assert data["user_id"] == test_user.id


def test_get_communication_with_comments(client, auth_headers, db_session, test_entity, test_user):
    """Test getting communication with its comments"""
    from app.models.communication_model import Communication
    from app.models.comment_model import Comment

    communication = Communication(
        title="Communication with comments",
        content="Content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.flush()

    # Add comments
    for i in range(3):
        comment = Comment(
            content=f"Comment {i}",
            communication_id=communication.id,
            user_id=test_user.id
        )
        db_session.add(comment)
    db_session.commit()
    db_session.refresh(communication)

    response = client.get(f"/communications/{communication.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["comments"]) == 3


def test_delete_comment(client, auth_headers, db_session, test_entity, test_user):
    """Test deleting a comment"""
    from app.models.communication_model import Communication
    from app.models.comment_model import Comment

    communication = Communication(
        title="Communication",
        content="Content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.flush()

    comment = Comment(
        content="To be deleted",
        communication_id=communication.id,
        user_id=test_user.id
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    response = client.delete(f"/comments/comments/{comment.id}", headers=auth_headers)

    assert response.status_code == 200

    # Verify comment is deleted
    from app.models.comment_model import Comment as CommentModel
    deleted_comment = db_session.query(CommentModel).filter(CommentModel.id == comment.id).first()
    assert deleted_comment is None


def test_delete_comment_not_found(client, auth_headers):
    """Test deleting non-existent comment"""
    response = client.delete("/comments/comments/99999", headers=auth_headers)

    assert response.status_code == 404


def test_upload_communication_image(client, auth_headers, db_session, test_entity, test_user):
    """Test uploading an image for communication"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="Communication with image",
        content="Content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    # Create a fake image file
    file_content = b"fake image content"
    file = BytesIO(file_content)

    response = client.post(
        f"/communications/{communication.id}/upload-image",
        files={"file": ("test.jpg", file, "image/jpeg")},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "image_url" in data
    assert "/uploads/communications/" in data["image_url"]


def test_upload_communication_image_invalid_type(client, auth_headers, db_session, test_entity, test_user):
    """Test uploading invalid file type for communication image"""
    from app.models.communication_model import Communication

    communication = Communication(
        title="Communication",
        content="Content",
        entity_id=test_entity.id,
        created_by_id=test_user.id
    )
    db_session.add(communication)
    db_session.commit()
    db_session.refresh(communication)

    # Create a fake text file
    file_content = b"not an image"
    file = BytesIO(file_content)

    response = client.post(
        f"/communications/{communication.id}/upload-image",
        files={"file": ("test.txt", file, "text/plain")},
        headers=auth_headers
    )

    assert response.status_code == 400
