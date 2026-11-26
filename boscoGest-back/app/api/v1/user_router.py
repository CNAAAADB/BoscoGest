from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, Request, Response, UploadFile, File, status
from typing import List, Dict, Any, Optional
from app.models.user_model import User
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    UserDetails,
    PasswordChange,
    FirstTimePasswordChange,
    PaginatedUsers,
    ConsentStatus,
    ConsentAccept,
    AccountDeletionRequest,
    AccountDeletionResult,
)
from app.utils.auth import (
    require_permission,
    get_current_active_user,
    get_sync_db,
    oauth2_scheme,
)
from app.services.auth_service import AuthService, get_auth_service
from app.services.user_service import UserService, get_user_service, process_bulk_upload_job
from app.services.user_visibility import redact_user, redact_user_details
from app.services.consent_service import ConsentService
from app.services.email_service import send_welcome_email
from app.services import activation_service
from app.services.member_file import build_template_xlsx

user_router = APIRouter(prefix="/users", tags=["User Management"])


@user_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    db_user = service.create_user(
        user,
        current_user,
        ip_address=request.client.host if request else None,
    )
    # The password was generated here and never shown to them, so the email
    # carries a one-shot link instead. Issued now, synchronously, because the
    # background task needs the secret to put in the message.
    activation_url = None
    if db_user.email:
        raw_token = activation_service.issue_token(service.db, db_user)
        activation_url = activation_service.build_activation_url(raw_token)

    if db_user.email:
        background_tasks.add_task(
            send_welcome_email,
            db_user.email,
            f"{db_user.name} {db_user.surname}",
            activation_url,
        )
    return db_user


@user_router.get("/directory")
def get_member_directory(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    entity_id: Optional[int] = Query(None, ge=1),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Public member directory for signed-in members.

    Only name and surname are exposed, never DNI, email, telephone, dates,
    account status or administrator-only review flags. Users can contact
    another member through the application's internal chat.
    """
    return service.get_member_directory(
        skip=skip, limit=limit, search=search, entity_id=entity_id
    )


@user_router.get("/manageable-associations")
def get_manageable_associations(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "manage")),
):
    """Only local associations whose members the caller may manage."""
    return service.get_manageable_local_associations(current_user)


@user_router.get("/managed", response_model=PaginatedUsers)
def get_managed_users(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Case-insensitive match on name, surname, email, DNI or phone.",
    ),
    review_only: bool = Query(
        False,
        description="Only member records requiring administrative data review.",
    ),
    entity_id: Optional[int] = Query(
        None, ge=1, description="Exact local association (level 4).",
    ),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "manage")),
):
    return service.get_managed_users(
        current_user, skip=skip, limit=limit, search=search,
        review_only=review_only, entity_id=entity_id,
    )


@user_router.get("", response_model=PaginatedUsers)
def get_users(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Case-insensitive match on name, surname, email, DNI or phone.",
    ),
    entity_id: Optional[int] = Query(None, ge=1),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "list")),
):
    return service.get_users(
        current_user, skip=skip, limit=limit, search=search, entity_id=entity_id
    )


@user_router.get("/search/email/{email}", response_model=UserResponse)
def search_user_by_email(
    email: str,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    found = service.ensure_reachable(
        current_user, service.search_by_email(email), "read",
        detail=f"User with email '{email}' not found",
    )
    result = redact_user(service.auth_service, current_user, found)
    if result.email is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@user_router.get("/search/dni/{dni}", response_model=UserResponse)
def search_user_by_dni(
    dni: str,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    found = service.ensure_reachable(
        current_user, service.search_by_dni(dni), "read",
        detail=f"User with DNI '{dni}' not found",
    )
    result = redact_user(service.auth_service, current_user, found)
    if result.dni is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@user_router.get("/creatable-entities", response_model=List[Dict[str, Any]])
def get_creatable_entities(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Entities (asociaciones) where the user may create users — used to
    populate the association selector of the bulk import."""
    return service.get_user_creatable_entities(current_user)


@user_router.get("/assignable-roles", response_model=List[Dict[str, Any]])
def get_assignable_roles(
    entity_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Roles of a given association that the current user may assign — used to
    populate the role selector of the bulk import (conditioned on the selected
    association)."""
    return service.get_assignable_roles(entity_id, current_user)


@user_router.get("/me", response_model=UserDetails)
def get_my_profile(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_user(current_user.id)


@user_router.put("/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserUpdate,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Allows the authenticated user to update their own profile fields."""
    return service.update_own_profile(
        current_user,
        user_update,
        ip_address=request.client.host if request else None,
    )


@user_router.post("/me/photo", response_model=UserResponse)
def upload_my_photo(
    file: UploadFile = File(...),
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """The authenticated user uploads their own profile photo."""
    content = file.file.read()
    return service.set_user_photo(
        current_user.id,
        content,
        file.content_type,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.post("/{user_id}/photo", response_model=UserResponse)
def upload_user_photo(
    user_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "update")),
):
    content = file.file.read()
    updated = service.set_user_photo(
        user_id,
        content,
        file.content_type,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return redact_user(service.auth_service, current_user, updated)


# ──────────────────────────────────────────────
# GDPR consent
# ──────────────────────────────────────────────
#
# Declared before the /{user_id} routes: FastAPI matches in declaration order,
# and "/me/consent" would otherwise be captured by "/{user_id}".

@user_router.get("/me/consent", response_model=ConsentStatus)
def get_my_consent(
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_sync_db),
):
    """Whether the caller has accepted the current data-processing clause.

    Returns the clause text when they have not, so the client shows exactly
    what is being agreed to.
    """
    return ConsentService(db).get_status(current_user)


@user_router.post("/me/consent", response_model=ConsentStatus)
def accept_my_consent(
    payload: ConsentAccept,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_sync_db),
):
    """Record acceptance of the clause, with the version and a timestamp."""
    return ConsentService(db).accept(current_user, payload.version)


@user_router.delete("/me", response_model=AccountDeletionResult)
def delete_my_account(
    deletion: AccountDeletionRequest,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
):
    """Delete the caller's own account.

    Reachable by every signed-in user, with no permission attached: this is the
    in-app deletion route Google Play requires of an app that lets people
    register themselves, and it has to work for the accounts that used that
    form. Declared above "/{user_id}" because FastAPI matches in declaration
    order and would otherwise read "me" as an id.
    """
    ip_address = request.client.host if request else None
    service.delete_own_account(current_user, deletion.password, ip_address=ip_address)
    # The session outlives the account it belongs to unless the token is
    # revoked here: it stays valid until it expires on its own.
    auth_service.logout(current_user, token, ip_address=ip_address)
    return AccountDeletionResult(
        message="Tu cuenta ha sido eliminada y tus datos personales borrados."
    )


@user_router.get("/{user_id}", response_model=UserDetails)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    db_user = service.ensure_reachable(current_user, service.get_user(user_id), "read")
    return redact_user_details(service.auth_service, current_user, db_user)


@user_router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "update")),
):
    updated = service.update_user(
        user_id,
        user_update,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return redact_user(service.auth_service, current_user, updated)


@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "delete")),
):
    service.delete_user(
        user_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.get("/bulk-upload/template.xlsx")
def download_bulk_upload_template(
    current_user: User = Depends(get_current_active_user),
):
    """The Excel template for the bulk import.

    Built here rather than in the browser so that the column names come from
    the same rules the importer applies. Declared before /bulk-upload/{job_id},
    which would otherwise capture it.
    """
    return Response(
        content=build_template_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla_usuarios.xlsx"'},
    )


@user_router.post("/bulk-upload/validate", status_code=status.HTTP_200_OK)
def validate_bulk_upload(
    file: UploadFile = File(...),
    entity_id: int = Form(...),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Check a member file (CSV or Excel) and report on it without creating anything.

    Deliberately not a dry-run flag on the import endpoint: this creates no
    job, leaves no trace, and can be run as many times as it takes to get the
    file right. No role is needed either — the role only matters once users are
    actually created.
    """
    content = file.file.read()
    return service.validate_bulk_csv(content, file.filename, entity_id, current_user)


@user_router.post("/bulk-upload", status_code=status.HTTP_202_ACCEPTED)
def bulk_upload_users(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    entity_id: int = Form(...),
    role_id: int = Form(...),
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    content = file.file.read()
    job = service.create_bulk_upload_job(
        content, file.filename, current_user, entity_id, role_id
    )
    ip = request.client.host if request else None
    background_tasks.add_task(process_bulk_upload_job, job.id, current_user.id, ip)
    return {"job_id": job.id, "status": job.status}


@user_router.get("/bulk-upload/jobs", response_model=List[Dict[str, Any]])
def list_bulk_upload_jobs(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(require_permission("users", "create")),
):
    jobs = service.list_bulk_upload_jobs(current_user)
    return [_job_to_dict(j) for j in jobs]


@user_router.get("/bulk-upload/{job_id}", response_model=Dict[str, Any])
def get_bulk_upload_job(
    job_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(require_permission("users", "create")),
):
    job = service.get_bulk_upload_job(job_id, current_user)
    return _job_to_dict(job)


def _job_to_dict(job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "csv_filename": job.csv_filename,
        "total_rows": job.total_rows,
        "processed_rows": job.processed_rows,
        "successful": job.successful,
        "failed": job.failed,
        "errors": job.errors or [],
        "created_users": job.created_users or [],
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_by_id": job.created_by_id,
    }


@user_router.post("/{user_id}/activation-link", status_code=status.HTTP_200_OK)
def issue_activation_link(
    user_id: int,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    """Get a fresh sign-in link to hand to someone in person.

    For members the welcome email cannot reach: registered with a phone and no
    address, or the message never arrived. Only for accounts that have never
    set a password of their own — see the service for why that limit matters.
    """
    return service.issue_activation_link(
        user_id,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: PasswordChange,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.change_password(
        password_data,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.post(
    "/first-time-password-change", status_code=status.HTTP_200_OK
)
def first_time_password_change(
    password_data: FirstTimePasswordChange,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.first_time_password_change(
        password_data,
        current_user,
        ip_address=request.client.host if request else None,
    )
