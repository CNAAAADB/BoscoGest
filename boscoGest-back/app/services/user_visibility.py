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

    @classmethod
    def for_viewer(
        cls, auth_service: "AuthorizationService", viewer: "User"
    ) -> "UserVisibility":
        return cls(
            can_read_contact=auth_service.has_global_permission(
                viewer, "users", "read"
            ),
            can_read_sensitive=auth_service.has_global_permission(
                viewer, "users", "read_sensitive"
            ),
        )

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
        allowed = self.visible_fields(is_self=viewer_id is not None and user.id == viewer_id)

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
    allowed = visibility.visible_fields(is_self=user.id == viewer.id)

    for field in CONTACT_FIELDS | SENSITIVE_FIELDS:
        if field not in allowed:
            setattr(details, field, None)
    return details
