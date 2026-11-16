from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.schemas.token import (
    Token,
    RefreshRequest,
    ActivationRequest,
    ActivationResendRequest,
    PasswordForgotRequest,
)
from app.schemas.user import PasswordResetConfirm
from app.schemas.membership_request import RegisterRequest, MembershipRequestResponse
from app.models.user_model import User
from app.utils.auth import (
    get_current_active_user,
    get_sync_db,
    get_password_hash,
)
from app.services.auth_service import AuthService, get_auth_service
from app.services.refresh_session_service import rotate_session, revoke_session
from app.services.membership_request_service import MembershipRequestService
from app.services.user_service import UserService, get_user_service
from app.services.email_service import send_password_reset_email, send_welcome_email
from app.services import activation_service
from app.services.activation_service import ActivationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

_REFRESH_COOKIE = "boscogest_refresh"

# Native WebViews require the refresh secret in their encrypted OS vault.
# Browser JavaScript must never receive the persistent secret; it uses a
# HttpOnly cookie. Browsers cannot forge the Origin header.
_NATIVE_ORIGINS = {"capacitor://localhost", "https://localhost"}


def _tokens_for_origin(request: Request | None, tokens: dict) -> dict:
    origin = (request.headers.get("origin") if request else None)
    if origin and origin not in _NATIVE_ORIGINS:
        return {**tokens, "refresh_token": None}
    return tokens



def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth",
        max_age=30 * 24 * 3600,
    )


@auth_router.post("/refresh", response_model=Token)
def refresh_login(
    response: Response,
    request: Request,
    credentials: RefreshRequest | None = None,
    db: Session = Depends(get_sync_db),
):
    """Rotate a device credential; no expired access JWT is required."""
    raw = (credentials.refresh_token if credentials else None) or request.cookies.get(_REFRESH_COOKIE)
    access, fresh = rotate_session(db, raw or "")
    _set_refresh_cookie(response, fresh)
    return _tokens_for_origin(
        request,
        {"access_token": access, "refresh_token": fresh, "token_type": "bearer"},
    )


@auth_router.post("/session/revoke", status_code=204)
def revoke_device_session(
    response: Response,
    request: Request,
    credentials: RefreshRequest | None = None,
    db: Session = Depends(get_sync_db),
):
    raw = (credentials.refresh_token if credentials else None) or request.cookies.get(_REFRESH_COOKIE)
    revoke_session(db, raw)
    response.delete_cookie(_REFRESH_COOKIE, path="/auth", secure=True, httponly=True, samesite="lax")
    return None



@auth_router.post("/token", response_model=Token)
def login_for_access_token(
    identifier: str = Form(..., description="Email o teléfono del usuario"),
    password: str = Form(...),
    response: Response = None,
    request: Request = None,
    service: AuthService = Depends(get_auth_service),
):
    ip_address = request.client.host if request else None
    tokens = service.login(identifier, password, ip_address=ip_address)
    _set_refresh_cookie(response, tokens["refresh_token"])
    return _tokens_for_origin(request, tokens)


@auth_router.post("/activate", response_model=Token)
def activate_account(
    activation_in: ActivationRequest,
    response: Response,
    request: Request = None,
    db: Session = Depends(get_sync_db),
    service: AuthService = Depends(get_auth_service),
):
    """Sign in with a one-shot link from a welcome email.

    People an administrator created never learn the password generated for
    them, so this is how they get in the first time. The session it returns is
    an ordinary one, and the account still carries must_change_password, which
    is what sends them straight to choosing a password.
    """
    ip_address = request.client.host if request else None
    try:
        user = activation_service.redeem_token(db, activation_in.token)
    except ActivationError as exc:
        # 410 rather than 401: the link was real, it simply cannot be spent any
        # more, and the screen shows a different way out for each reason.
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if exc.reason == "invalid"
            else status.HTTP_410_GONE
        )
        raise HTTPException(
            status_code=status_code,
            detail={"reason": exc.reason, "message": exc.message},
        )

    tokens = service.session_for(user, ip_address=ip_address, method="activation_link")
    _set_refresh_cookie(response, tokens["refresh_token"])
    return _tokens_for_origin(request, tokens)


@auth_router.post("/activate/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_activation(
    resend_in: ActivationResendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db),
):
    """Send a fresh link to someone whose old one expired or was used.

    Answers the same way whatever happens. Saying "no such account" here would
    turn the form into a way of testing whether an address belongs to a member,
    and the accounts in question have not been used yet, so nobody would notice
    it being probed.
    """
    identifier = resend_in.identifier.strip()
    user = db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    ).scalars().first()

    # Only for accounts still waiting to set a password. Anyone else already
    # has one and should use it, or reset it the usual way.
    if user and user.is_active and user.must_change_password and user.email:
        raw_token = activation_service.issue_token(db, user)
        background_tasks.add_task(
            send_welcome_email,
            user.email,
            f"{user.name} {user.surname}",
            activation_service.build_activation_url(raw_token),
        )

    return {
        "message": (
            "Si esa cuenta existe y aún no tiene contraseña, te hemos enviado "
            "un enlace nuevo."
        )
    }


@auth_router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    forgot_in: PasswordForgotRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db),
):
    """Email a link to choose a new password.

    Answers the same way whatever happens, like the activation resend, so the
    form cannot be used to find out whether an address belongs to a member.
    The answer also says what to do without email, because that is the one
    case the link cannot cover and the person would otherwise just wait.
    """
    identifier = forgot_in.identifier.strip()
    user = db.execute(
        select(User).where(
            (func.lower(User.email) == identifier.lower()) | (User.phone == identifier)
        )
    ).scalars().first()

    if (
        user
        and user.is_active
        and user.email
        # One link at a time. Asking again straight away sends nothing new,
        # so the form cannot be used to flood someone's inbox.
        and not activation_service.issued_recently(
            db, user.id, activation_service.PURPOSE_RESET, activation_service.RESET_COOLDOWN
        )
    ):
        raw_token = activation_service.issue_token(
            db, user, purpose=activation_service.PURPOSE_RESET
        )
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            f"{user.name} {user.surname}",
            activation_service.build_reset_url(raw_token),
        )

    return {
        "message": (
            "Si esa cuenta existe y tiene un correo electrónico, te hemos "
            "enviado un enlace para elegir una contraseña nueva. Si te diste "
            "de alta solo con el teléfono, pide ayuda a la persona que "
            "gestiona tu asociación."
        )
    }


@auth_router.post("/password/reset", response_model=Token)
def reset_password(
    reset_in: PasswordResetConfirm,
    response: Response,
    request: Request = None,
    db: Session = Depends(get_sync_db),
    auth: AuthService = Depends(get_auth_service),
    users: UserService = Depends(get_user_service),
):
    """Choose a new password with the link from the email, and sign in.

    The password comes in the same request as the link, so the link alone
    never opens a session: someone who finds it in an inbox still has to
    replace the password, which the owner will notice the next time.
    """
    ip_address = request.client.host if request else None
    try:
        user = activation_service.redeem_token(
            db, reset_in.token, purpose=activation_service.PURPOSE_RESET
        )
    except ActivationError as exc:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if exc.reason == "invalid"
            else status.HTTP_410_GONE
        )
        raise HTTPException(
            status_code=status_code,
            detail={"reason": exc.reason, "message": exc.message},
        )

    users.reset_password(user, reset_in.new_password, ip_address=ip_address)
    tokens = auth.session_for(user, ip_address=ip_address, method="password_reset")
    _set_refresh_cookie(response, tokens["refresh_token"])
    return _tokens_for_origin(request, tokens)


@auth_router.get("/check-permission")
def check_user_permission(
    resource: str,
    action: str,
    resource_id: Optional[int] = None,
    request: Request = None,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user),
):
    ip_address = request.client.host if request else None
    return service.check_permission(
        current_user, resource, action, resource_id, ip_address=ip_address
    )


@auth_router.post("/logout")
def logout(
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    response: Response = None,
):
    ip_address = request.client.host if request else None
    result = service.logout(current_user, token, ip_address=ip_address,
                            refresh_token=request.cookies.get(_REFRESH_COOKIE) if request else None)
    if response is not None:
        response.delete_cookie(_REFRESH_COOKIE, path="/auth", secure=True, httponly=True, samesite="lax")
    return result


def _already_registered(field: str) -> str:
    return (
        f"Ya existe una cuenta con ese {field}. Si ya te habían dado de alta, "
        "inicia sesión en lugar de registrarte."
    )


def _clashing_field(exc: IntegrityError) -> str:
    detail = str(getattr(exc, "orig", exc)).lower()
    for column, label in (("email", "email"), ("dni", "DNI"), ("phone", "teléfono")):
        if column in detail:
            return label
    return "email, teléfono o DNI"


@auth_router.post(
    "/register",
    response_model=MembershipRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    register_in: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db),
):
    """
    Public endpoint: create a user account and submit a membership request.
    The user can log in immediately but has no permissions until an admin accepts.
    """
    dni = register_in.dni.strip().upper() if register_in.dni else None
    phone = register_in.phone.strip() if register_in.phone else None

    try:
        birthdate = date.fromisoformat(register_in.birthdate)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha de nacimiento no es válida",
        )

    # Email, phone and DNI are all unique. Only the email used to be checked,
    # so a repeated DNI or phone reached the INSERT and came back as a 500: the
    # person saw a generic error and no hint of what to change. It happens to
    # real people — someone already added by a bulk import, or signing up twice.
    # The DNI is compared ignoring case: 12345678a is the same document.
    # NULL is not an identifier: never compare blank optional fields against
    # other accounts. Duplicate checks apply only to supplied values.
    duplicate_checks = [User.email == register_in.email]
    if phone:
        duplicate_checks.append(User.phone == phone)
    if dni:
        duplicate_checks.append(func.upper(User.dni) == dni)
    taken = db.execute(
        select(User).where(or_(*duplicate_checks))
    ).scalars().all()
    for field, clashes in (
        ("email", any(u.email == register_in.email for u in taken)),
        ("DNI", bool(dni) and any((u.dni or "").upper() == dni for u in taken)),
        ("teléfono", bool(phone) and any(u.phone == phone for u in taken)),
    ):
        if clashes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_already_registered(field),
            )

    # Create user account
    new_user = User(
        name=register_in.name,
        surname=register_in.surname,
        email=register_in.email,
        password_hash=get_password_hash(register_in.password),
        phone=phone,
        birthdate=birthdate,
        dni=dni,
        address=register_in.address,
        is_active=True,
        must_change_password=False,
    )
    db.add(new_user)
    try:
        db.flush()
    except IntegrityError as exc:
        # Two sign-ups racing for the same value: the check above passed for
        # both, the unique constraint stops the second.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_already_registered(_clashing_field(exc)),
        )

    # Create membership request
    request_service = MembershipRequestService(db)
    req = request_service.create_request(
        user_id=new_user.id,
        entity_id=register_in.entity_id,
        message=register_in.message,
    )

    background_tasks.add_task(
        send_welcome_email,
        new_user.email,
        f"{new_user.name} {new_user.surname}",
    )

    return req
