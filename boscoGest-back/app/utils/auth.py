from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, text
import uuid
from app.database import SyncSessionLocal
from app.models.user_model import User
from app.models.audit_log_model import AuditLog
from app.models.membership_model import Membership
from app.models.role_model import Role
from app.models.group_model import Group
from app.models.revoked_token_model import RevokedToken

# Security configuration — sourced from the environment, never hardcoded.
# Re-exported here so the existing imports across routers keep working.
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database dependency
def get_sync_db():
    with SyncSessionLocal() as session:
        yield session

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # Truncate password to 72 bytes if needed (bcrypt limitation)
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

# JWT token functions
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# User authentication
def authenticate_user(db: Session, identifier: str, password: str) -> Union[User, bool]:
    # El identificador puede ser email o teléfono (cualquiera identifica al usuario)
    stmt = select(User).where(
        (User.email == identifier) | (User.phone == identifier)
    )
    result = db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(password, user.password_hash):
        return False
    if not user.is_active:
        return False
    return user

# Get current user from token
def get_current_user(
    db: Session = Depends(get_sync_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: Optional[str] = payload.get("sub")
        jti: Optional[str] = payload.get("jti")
        if sub is None or jti is None:
            raise credentials_exception

        # Check if token is revoked
        stmt = select(RevokedToken).where(RevokedToken.jti == jti)
        revoked = db.execute(stmt).scalars().first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception

    # El "sub" del token es el id del usuario (soporta usuarios sin email)
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise credentials_exception

    # Every authorisation check walks memberships -> role -> permissions,
    # direct permissions, and groups -> roles -> permissions. Loading them
    # lazily meant each of those traversals issued its own SELECT, on every
    # authenticated request. selectinload fetches each collection in one extra
    # query regardless of how many rows it holds, which keeps the cost flat as
    # a user accumulates memberships.
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.role)
            .selectinload(Role.permissions),
            selectinload(User.direct_permissions),
            selectinload(User.groups)
            .selectinload(Group.roles)
            .selectinload(Role.permissions),
        )
    )
    result = db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Get current active user
def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def is_root_superadmin(user: User) -> bool:
    """Reserved platform authority: an active superadmin membership at the root."""
    return any(
        m.is_active
        and m.role is not None and m.role.is_active and m.role.name == "superadmin"
        and m.entity is not None and m.entity.is_active
        and m.entity.level == 1 and m.entity.parent_id is None
        for m in user.memberships
    )


# ABAC Permission verification
def has_permission(
    user: User,
    resource: str,
    action: str,
    resource_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check if user has permission to perform an action on a resource.
    Implements Attribute-Based Access Control (ABAC) by considering:
    - Direct user permissions
    - Role-based permissions
    - Group-based permissions
    - Contextual conditions
    """
    if is_root_superadmin(user):
        return True
    context = context or {}

    # Helper function to check conditions
    def evaluate_conditions(conditions: Optional[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        if not conditions:
            return True

        # Example condition: {"time_between": ["09:00", "17:00"]}
        for condition_key, condition_value in conditions.items():
            if condition_key == "time_between":
                current_time = context.get("current_time", datetime.now().time())
                start_time = datetime.strptime(condition_value[0], "%H:%M").time()
                end_time = datetime.strptime(condition_value[1], "%H:%M").time()
                if not (start_time <= current_time <= end_time):
                    return False
            elif condition_key == "ip_range":
                ip = context.get("ip_address")
                if not ip or ip not in condition_value:
                    return False
            # Add more condition types as needed

        return True

    # Check direct user permissions
    for permission in user.direct_permissions:
        if (permission.resource == resource and 
            permission.action == action and 
            evaluate_conditions(permission.conditions, context)):
            return True

    # Check role-based permissions (through memberships)
    for membership in user.memberships:
        if membership.is_active:
            for permission in membership.role.permissions:
                if (permission.resource == resource and
                    permission.action == action and
                    evaluate_conditions(permission.conditions, context)):
                    return True

    # Check group-based permissions (through roles)
    for group in user.groups:
        for role in group.roles:
            for permission in role.permissions:
                if (permission.resource == resource and 
                    permission.action == action and 
                    evaluate_conditions(permission.conditions, context)):
                    return True

    return False

# Permission dependency for FastAPI routes
def require_permission(resource: str, action: str):
    def dependency(
        current_user: User = Depends(get_current_active_user)
    ):
        if is_root_superadmin(current_user):
            return current_user
        # Check permissions across all active memberships
        for membership in current_user.memberships:
            if membership.is_active:
                role = membership.role
                for perm in role.permissions:
                    if perm.resource == resource and perm.action == action:
                        return current_user
        raise HTTPException(status_code=403, detail="Permission denied")
    return dependency


def require_root_permission(resource: str, action: str):
    """Like require_permission, but the permission must hold at the root.

    For platform-wide configuration — the permission catalogue, groups, the
    consent clause — where having the permission in any one association used
    to be enough to change it for everyone.
    """
    def dependency(
        db: Session = Depends(get_sync_db),
        current_user: User = Depends(get_current_active_user),
    ):
        # Imported here: authorization_service imports from this module.
        from app.services.authorization_service import AuthorizationService

        if not AuthorizationService(db).has_root_permission(current_user, resource, action):
            raise HTTPException(status_code=403, detail="Permission denied")
        return current_user
    return dependency


# Audit logging utility — delegates to AuditService
def create_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    from app.services.audit_service import AuditService
    return AuditService(db).create_audit_log(
        user_id=user_id, action=action, resource_type=resource_type,
        resource_id=resource_id, details=details, ip_address=ip_address,
    )


def get_current_membership(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user)
) -> Membership:
    """
    Returns the first active membership for the current user.
    This is used for operations that need an entity context (e.g., creating users/roles within an entity).
    """
    stmt = select(Membership).where(
        Membership.user_id == current_user.id,
        Membership.is_active == True
    ).order_by(Membership.created_at.asc())

    result = db.execute(stmt)
    membership = result.scalars().first()

    if not membership:
        raise HTTPException(status_code=403, detail="User has no active memberships")

    return membership


# --- Hierarchical RBAC — delegates to AuthorizationService / EntityRepository ---

def get_entity_ancestor_chain(db: Session, entity_id: int) -> List[int]:
    """Delegates to EntityRepository.get_ancestor_chain()."""
    from app.repositories.entity_repository import EntityRepository
    return EntityRepository(db).get_ancestor_chain(entity_id)


def has_effective_permission(
    db: Session, user: User, target_entity_id: int, resource: str, action: str
) -> bool:
    """Delegates to AuthorizationService.has_effective_permission()."""
    from app.services.authorization_service import AuthorizationService
    return AuthorizationService(db).has_effective_permission(user, target_entity_id, resource, action)


def check_entity_permission(
    db: Session, user: User, target_entity_id: int, resource: str, action: str
) -> None:
    """Delegates to AuthorizationService.check_entity_permission()."""
    from app.services.authorization_service import AuthorizationService
    AuthorizationService(db).check_entity_permission(user, target_entity_id, resource, action)


def get_accessible_entity_ids(db: Session, user: User) -> List[int]:
    """Delegates to EntityRepository.get_accessible_entity_ids()."""
    from app.repositories.entity_repository import EntityRepository
    return EntityRepository(db).get_accessible_entity_ids(user)

