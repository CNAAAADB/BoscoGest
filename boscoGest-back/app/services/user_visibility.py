"""Field-level visibility for user records (GDPR data minimisation).

REQ-USR-01 marks DNI and IBAN as private, but `UserResponse` returned them —
along with home address and date of birth — to anyone holding `users:read`.
Every listing leaked the personal data of every member in scope.

Fields are grouped in three tiers, and a record is redacted to the tier the
viewer is entitled to. Redacted fields come back as `null` rather than being
dropped, so the response shape stays stable and clients need no special case.

A user always sees their own record in full.
"""

from typing import TYPE_CHECKING, Optional, Set

from app.schemas.user import UserResponse
from app.services.scoped_permissions import ScopedPermissions


if TYPE_CHECKING:  # pragma: no cover
    from app.models.user_model import User
    from app.services.authorization_service import AuthorizationService


# Identifying but not sensitive: the minimum needed to show a member in a list.
PUBLIC_FIELDS: Set[str] = {
    "id",
    "name",
    "surname",
    "photo",
    "job_position",
    "is_active",
    "created_at",
    "must_change_password",
}

# Needed to get in touch with a member. Requires `users:read`.
CONTACT_FIELDS: Set[str] = {"email", "phone", "size", "hobbies"}

# Special-category or high-risk data. Requires `users:read_sensitive`, which is
# granted to roles that genuinely need it — a treasurer needs the IBAN to manage
# fees, an administrator needs the DNI to verify identity.
SENSITIVE_FIELDS: Set[str] = {"dni", "iban", "address", "birthdate"}


class UserVisibility:
    """Decides, once per request, which tiers the viewer may see."""

    def __init__(self, can_read_contact: bool, can_read_sensitive: bool):
        self.can_read_contact = can_read_contact
        self.can_read_sensitive = can_read_sensitive
        self.contact_ids = None
        self.sensitive_ids = None
        self.root_superadmin = False

    @classmethod
    def for_viewer(
        cls, auth_service: "AuthorizationService", viewer: "User"
    ) -> "UserVisibility":
        scope = ScopedPermissions(auth_service.db)
        visibility = cls(False, False)
        visibility.contact_ids = scope.ids(viewer, "users", "read", inherit=False)
        visibility.sensitive_ids = scope.ids(viewer, "users", "read_sensitive", wildcard=False)
        visibility.root_superadmin = scope.is_root_superadmin(viewer)
        return visibility

    def tiers_for(self, user: "User", viewer_id: Optional[int] = None):
        if user.id == viewer_id or self.root_superadmin:
            return True, True
        if self.contact_ids is None:
            return self.can_read_contact, self.can_read_sensitive
        # Ancestor memberships automatically created as socio must not expose
        # a local treasurer's sensitive access to unrelated local associations.
        memberships = ScopedPermissions.active_memberships(user)
        deepest = [m for m in memberships if m.entity.level > 1]
        ids = {m.entity_id for m in memberships}
        sensitive = {m.entity_id for m in deepest} if deepest else ids
        return bool(ids & self.contact_ids), bool(sensitive & self.sensitive_ids)

    def visible_fields(self, is_self: bool) -> Set[str]:
        if is_self:
            return PUBLIC_FIELDS | CONTACT_FIELDS | SENSITIVE_FIELDS
        fields = set(PUBLIC_FIELDS)
        if self.can_read_contact:
            fields |= CONTACT_FIELDS
        if self.can_read_sensitive:
            fields |= SENSITIVE_FIELDS
        return fields

    def serialize(
        self, user: "User", viewer_id: Optional[int] = None
    ) -> UserResponse:
        """Build a UserResponse with anything the viewer may not see set to None."""
        response = UserResponse.model_validate(user)
        contact, sensitive = self.tiers_for(user, viewer_id)
        allowed = UserVisibility(contact, sensitive).visible_fields(is_self=False)

        for field in CONTACT_FIELDS | SENSITIVE_FIELDS:
            if field not in allowed:
                setattr(response, field, None)
        return response


def redact_user(
    auth_service: "AuthorizationService", viewer: "User", user: "User"
) -> UserResponse:
    """Convenience wrapper for single-record endpoints."""
    return UserVisibility.for_viewer(auth_service, viewer).serialize(
        user, viewer_id=viewer.id
    )


def redact_user_details(
    auth_service: "AuthorizationService", viewer: "User", user: "User"
):
    """Same redaction for the detail endpoint, which also carries relations.

    UserDetails extends UserResponse, so the sensitive columns are just as
    exposed there; redacting only the list endpoints would leave the leak open
    one request away.
    """
    from app.schemas.user import UserDetails

    details = UserDetails.model_validate(user)
    visibility = UserVisibility.for_viewer(auth_service, viewer)
    contact, sensitive = visibility.tiers_for(user, viewer.id)
    allowed = UserVisibility(contact, sensitive).visible_fields(is_self=False)

    for field in CONTACT_FIELDS | SENSITIVE_FIELDS:
        if field not in allowed:
            setattr(details, field, None)
    # Nested membership user objects must not disclose redacted fields.
    for membership in details.memberships:
        if membership.user is not None:
            for field in CONTACT_FIELDS | SENSITIVE_FIELDS:
                if field not in allowed:
                    setattr(membership.user, field, None)
    return details
