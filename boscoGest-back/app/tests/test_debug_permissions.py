import pytest


def test_debug_permissions(db_session, test_user, test_membership, test_permissions):
    """Debug test to see what permissions the test user has"""

    # Refresh to load relationships
    db_session.refresh(test_membership)
    db_session.refresh(test_user)

    print("\n=== DEBUG INFO ===")
    print(f"User: {test_user.email}")
    print(f"Membership ID: {test_membership.id}")
    print(f"Entity ID: {test_membership.entity_id}")
    print(f"Role: {test_membership.role.name}")
    print(f"Role ID: {test_membership.role.id}")
    print(f"\nAll test_permissions ({len(test_permissions)}):")
    for perm in test_permissions:
        print(f"  - {perm.name} | resource={perm.resource} | action={perm.action}")

    print(f"\nRole permissions ({len(test_membership.role.permissions)}):")
    for perm in test_membership.role.permissions:
        print(f"  - {perm.name} | resource={perm.resource} | action={perm.action}")

    # Check for communications permissions specifically
    communications_perms = [p for p in test_membership.role.permissions if p.resource == "communications"]
    print(f"\nCommunications permissions found: {len(communications_perms)}")
    for perm in communications_perms:
        print(f"  - action={perm.action}")

    # Assert that we have at least some communications permissions
    assert len(communications_perms) > 0, "No communications permissions found!"
