# ARCHITECTURE.md — BoscoGest

Documento de arquitectura del sistema BoscoGest para referencia en la memoria del TFG.

---

## 1. Visión General del Sistema

BoscoGest es un sistema de gestión multi-tenant diseñado para organizaciones jerárquicas (Salesianos). Permite gestionar usuarios, membresías, actividades, comunicaciones, revistas y configuración visual, todo ello con un modelo de autorización jerárquico basado en la estructura organizativa.

### Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Backend** | FastAPI + SQLAlchemy (sync) | FastAPI 2.0, SQLAlchemy 2.0 |
| **Base de datos** | PostgreSQL | 15 |
| **Migraciones** | Alembic | — |
| **Frontend** | Angular + Angular Material | Angular 20, Material 3 |
| **Móvil** | Capacitor | 8.1 (Android + iOS) |
| **Autenticación** | JWT (HS256) | python-jose + passlib[bcrypt] |
| **Tareas programadas** | APScheduler (AsyncIOScheduler in-process) | 3.11 — mantenimiento diario de cuotas |
| **Tests** | pytest (backend), Karma+Jasmine (frontend) | — |
| **Despliegue** | Docker Compose + AWS EC2 | — |

### Repositorios

```
TFG/
├── boscoGest/           # Backend (FastAPI)
├── boscoGest-front/     # Frontend (Angular) + Apps nativas (Capacitor)
├── ARCHITECTURE.md      # Este documento
└── CAPACITOR.md         # Documentación de Capacitor (apps móviles)
```

---

## 2. Modelo de Dominio

### 2.1 Jerarquía de Entidades

El núcleo del sistema es una jerarquía de entidades organizativas con hasta 4 niveles:

```
Superentidad (nivel 1) ─── Solo puede existir una
├── Confederación (nivel 2)
│   ├── Federación (nivel 3)
│   │   ├── Local (nivel 4)
│   │   └── Local (nivel 4)
│   └── Federación (nivel 3)
└── Confederación (nivel 2)
```

Cada `Entity` tiene:
- `name` (único), `level` (1-4), `parent_id` (FK auto-referencial)
- `is_active` (soft delete)
- Relaciones: children, memberships, activities, communications, magazines, roles, branding, view_configs

### 2.2 Diagrama Entidad-Relación (Modelos Principales)

```
┌─────────┐     ┌────────────┐     ┌────────┐
│  User   │────<│ Membership │>────│ Entity │
└─────────┘     └────────────┘     └────────┘
     │               │                  │
     │               │                  │
     │          ┌────┘                  │
     │          │                       │
     │     ┌────┴───┐            ┌──────┴──────┐
     │     │  Role  │──<─────>──│ entity_roles │
     │     └────────┘            └─────────────┘
     │          │
     │     ┌────┴──────────┐
     │     │  Permission   │
     │     │  (inheritable)│
     │     └───────────────┘
     │
     ├──<──┤ user_groups ├──>──┌────────┐
     │                         │ Group  │──<──┤ group_roles ├──>── Role
     │
     └──<──┤ user_permissions ├──>── Permission
```

### 2.3 Modelos Completos

| Modelo | Tabla | Campos Clave | Notas |
|--------|-------|-------------|-------|
| **User** | `users` | email (unique), password_hash, name, surname, DNI (unique), phone, birthdate, address, IBAN, photo, size, hobbies, job_position, is_active, must_change_password | Datos personales completos |
| **Entity** | `entities` | name (unique), level, parent_id (self-FK), is_active | Solo 1 entidad de nivel 1 |
| **Membership** | `memberships` | user_id, entity_id, role_id, is_active | Vincula usuario ↔ entidad con rol |
| **MembershipRequest** | `membership_requests` | user_id, entity_id, status (pending/accepted/rejected), message, rejection_reason, reviewed_by_id, reviewed_at, created_at | Solicitudes de alta: el usuario elige entidad, un admin con `memberships:review` acepta/rechaza |
| **Role** | `roles` | name (unique), description, is_active | Roles especiales: superadmin (inmutable), admin, socio |
| **Permission** | `permissions` | name (unique), resource, action, inheritable, conditions (JSON), is_active | `inheritable` controla herencia jerárquica |
| **Group** | `groups` | name, description | Agrupaciones de usuarios, agnóstico a entidades |
| **Activity** | `activities` | title, description, date, capacity, price, allow_waitlist, entity_id, created_by_id, image_url, is_active | Eventos asociados a entidades |
| **ActivityRegistration** | `activity_registrations` | activity_id, user_id, status (pending/accepted/rejected), is_active | Control de inscripciones |
| **Communication** | `communications` | title, content, image_url, entity_id, created_by_id, status (draft/review/published/archived), published_at, is_active | Noticias/comunicados por entidad con workflow editorial |
| **Comment** | `comments` | content, communication_id, user_id | Comentarios en comunicaciones |
| **Magazine** | `magazines` | title, collection, issue_number, description, file_path, entity_id, uploaded_by_id | Revistas PDF por entidad |
| **EntityBranding** | `entity_brandings` | entity_id (1:1), primary_color, secondary_color, accent_color, logo_url, subdomain | Personalización visual por entidad |
| **EntityViewConfig** | `entity_view_configs` | entity_id, view_name, display_name, is_enabled, display_order, icon | Configuración del sidebar por entidad |
| **AuditLog** | `audit_logs` | user_id, action, resource_type, resource_id, details (JSON), ip_address, created_at | Trazabilidad de acciones |
| **RevokedToken** | `revoked_tokens` | jti, expires_at | Blacklist de tokens JWT |
| **Notification** | `notifications` | recipient_id, actor_id, event_type, resource_type, resource_id, entity_id, title, body, data (JSON), is_read, read_at, created_at | Notificaciones in-app con índice compuesto (recipient_id, is_read, created_at) |
| **NotificationPreference** | `notification_preferences` | user_id, event_type, in_app_enabled, email_enabled | Preferencias por tipo de evento; unique (user_id, event_type) |
| **ChatConversation** | `chat_conversations` | type (direct/group), name, description, avatar_url, created_by_id, is_active, created_at, updated_at | Conversación directa o grupal; updated_at se actualiza con cada mensaje |
| **ChatMember** | `chat_members` | conversation_id, user_id, role (admin/member), joined_at, left_at, last_read_at, is_active, is_muted, is_pinned | Miembro de una conversación; índice compuesto (conversation_id, user_id) |
| **ChatMessage** | `chat_messages` | conversation_id, sender_id, content, message_type (text/system/file), reply_to_id, reply_preview, file_url, file_name, file_type, is_deleted, created_at | Mensaje de chat; soporta respuestas anidadas (self-FK) e índice compuesto (conversation_id, created_at) |
| **ChatJoinRequest** | `chat_join_requests` | conversation_id, user_id, status (pending/accepted/rejected), requested_at, reviewed_by_id, reviewed_at | Solicitudes de acceso a grupos; revisadas por admins del grupo |
| **ResourceCategory** | `resource_categories` | name, description, entity_id, is_active, created_at | Categorías de recursos por entidad |
| **Resource** | `resources` | title, description, resource_type (link/document/image/video), url, file_path, original_filename, tags, entity_id, category_id, created_by, is_active | Recursos formativos por entidad |
| **Fee** | `fees` | entity_id, name, **periodicity** (weekly/monthly/quarterly/four_monthly/biannual/annual), **auto_renew**, **reminder_days**, is_active, created_by, created_at | Cuota **con nombre y periodicidad** por entidad; una entidad puede tener varias. `auto_renew`/`reminder_days` controlan la renovación y avisos; el vencimiento se deriva de la periodicidad (fin del período). Soft-delete |
| **FeeConfig** | `fee_configs` | fee_id, amount, valid_from, valid_until, created_by | Versión de importe (histórico) de una cuota. **Inmutable**; `valid_until` opcional, al añadir versión se auto-cierra la anterior (la última es la vigente) |
| **FeeAssignment** | `fee_assignments` | fee_id, user_id, entity_id, fee_config_id, period, amount, status (pending/paid/overdue/cancelled), due_date, paid_at, notes, **reminder_sent** | Cuota debida por un socio en un período (**derivado** de la periodicidad de la cuota + fecha); importe = snapshot del vigente. Unique (user_id, fee_id, period) |
| **FeeMaintenanceRun** | `fee_maintenance_runs` | started_at, finished_at, status (success/error), trigger (scheduled/manual), triggered_by_id, overdue_count, reminded_count, renewed_count, details (JSON), error | Log de cada ejecución del mantenimiento diario de cuotas (vencidas/recordatorios/renovación). Alimenta la vista de monitorización |

### 2.4 Tablas de Relación Many-to-Many

Definidas en `app/models/relationships.py`:

| Tabla | Relación | Propósito |
|-------|----------|-----------|
| `user_groups` | User ↔ Group | Asignar usuarios a grupos |
| `user_permissions` | User ↔ Permission | Permisos directos (bypass de roles) |
| `group_roles` | Group ↔ Role | Asignar roles a grupos |
| `role_permissions` | Role ↔ Permission | Permisos dentro de un rol |
| `entity_roles` | Entity ↔ Role | Roles disponibles por entidad |

---

## 3. Sistema de Autorización

### 3.1 Modelo Conceptual: RBAC Jerárquico + ABAC

El sistema combina:
- **RBAC (Role-Based Access Control)**: Permisos asignados a roles, roles asignados a membresías
- **ABAC (Attribute-Based Access Control)**: Condiciones contextuales (ventanas temporales, rangos IP)
- **Herencia jerárquica**: Permisos heredables descienden por la jerarquía de entidades

### 3.2 Flujo de Autenticación

```
1. POST /auth/token (email + password, OAuth2 form-data)
        │
        ▼
2. Validar credenciales + verificar usuario activo (sin membresía activa = estado pendiente, el frontend redirige a /pending)
        │
        ▼
3. Generar JWT { sub: email, jti: UUID, exp: 30min }
        │
        ▼
4. Cliente almacena token en localStorage
        │
        ▼
5. authInterceptor adjunta "Authorization: Bearer {token}" a cada petición
        │
        ▼
6. Backend: get_current_active_user() valida JWT, comprueba RevokedToken, retorna User
```

### 3.3 Flujo de Autorización Jerárquica

La función central es `AuthorizationService.check_entity_permission(user, target_entity_id, resource, action)`:

```
check_entity_permission(db, user, entity_id=Local_4, "activities", "create")
        │
        ▼
┌─ 1. ¿manage_all? ───── Si el usuario tiene activities:manage_all → PERMITIR
│
├─ 2. ¿Permiso directo? ── user_permissions → PERMITIR
│
├─ 3. Cadena de ancestros (CTE recursiva):
│      [Local_4, Federation_3, Confederation_2, Superentity_1]
│      │
│      ├─ Buscar membresías del usuario en estas entidades (1 query batch)
│      │
│      ├─ i=0 (Local_4, directo): ¿Membresía con activities:create? → PERMITIR
│      ├─ i=1 (Federation_3): ¿Membresía con activities:create AND inheritable=true? → PERMITIR
│      ├─ i=2 (Confederation_2): igual...
│      └─ i=3 (Superentity_1): igual...
│
├─ 4. ¿Permiso de grupo? ── user → groups → roles → permissions → PERMITIR
│
└─ Ninguno → DENEGAR (HTTP 403)
```

**Rendimiento**: Solo 2 queries por verificación:
1. CTE recursiva para la cadena de ancestros (indexada por `id` y `parent_id`)
2. Fetch batch de membresías con eager load de roles+permisos

### 3.4 Permisos Heredables vs No-Heredables

#### Heredables (`inheritable = true`) — Descienden a entidades hijas

| Recurso | Acciones | Justificación |
|---------|----------|---------------|
| users | create, list, read, update, delete, manage | Admin de Federación gestiona usuarios en Locales |
| activities | create, list, read, update, delete, manage | Actividades gestionables desde niveles superiores |
| communications | create, read, edit, delete, publish, review | Publicar noticias en entidades descendientes; publish/review para workflow editorial |
| comment | create, read, edit, delete | Comentar en entidades descendientes |
| magazines | create, list, read, update, delete | Revistas gestionables desde niveles superiores |
| resources | create, list, read, update, delete | Recursos formativos gestionables desde niveles superiores |
| fees | list, read, manage | Consultar/gestionar cuotas y asignaciones en entidades descendientes |
| roles | list, read | Visualizar roles disponibles en descendientes |
| entities | list, read | Visualizar entidades descendientes |

#### No-heredables (`inheritable = false`) — Solo entidad propia

| Recurso | Acciones | Justificación |
|---------|----------|---------------|
| entities | create, update, delete | Crear/modificar sub-entidades es operación local |
| branding | read, update | Personalización visual es específica por entidad |
| views | read, update | Configuración del sidebar es específica por entidad |
| memberships | create, delete, manage, update, list, read, assign, review | Gestión de membresías es local; `review` permite aceptar/rechazar solicitudes de alta |
| roles | create, update, delete, assign | Modificación de roles es local |
| notifications | create, list, read, update, delete, manage, manage_all | Gestión de notificaciones es local (read/list para usuarios) |
| fees | create | Crear cuotas/generar asignaciones es operación local de la entidad |
| fees | maintenance | Ejecutar/monitorizar el mantenimiento de cuotas — capacidad global (cross-entidad), por defecto solo superadmin |

#### manage_all — Bypass global (solo superadmin)

`entities:manage_all`, `branding:manage_all`, `views:manage_all`, `communications:manage_all`, `comment:manage_all`

### 3.5 Patrones de Derivación del entity_id

El `entity_id` objetivo se deriva automáticamente del recurso, sin intervención del frontend:

| Patrón | Routers | Cómo se obtiene entity_id |
|--------|---------|---------------------------|
| **A: Path param** | branding, view_config, entity | `/branding/entity/{entity_id}` |
| **B: Body field** | activity POST, communication POST, membership POST, magazine POST | `request.body.entity_id` |
| **C: Resource lookup** | communication PUT/DELETE, comment, magazine GET/PUT/DELETE | DB lookup → `resource.entity_id` |
| **D: List** | user GET, activity GET | `get_accessible_entity_ids(db, user)` |
| **E: Entity-agnostic** | permission, group, password | `require_permission()` sin entidad |

### 3.6 Resolución de Permisos (Diagrama Completo)

```
                    ┌──────────────────────────┐
                    │     Usuario autenticado    │
                    └────────────┬───────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────┴─────────┐  ┌────┴────────┐  ┌──────┴────────┐
    │ Permisos Directos │  │ Membresías  │  │    Grupos     │
    │ (user_permissions)│  │             │  │               │
    └─────────┬─────────┘  └──────┬──────┘  └──────┬────────┘
              │                   │                  │
              │            ┌──────┴──────┐    ┌─────┴─────┐
              │            │    Role     │    │   Roles   │
              │            └──────┬──────┘    └─────┬─────┘
              │                   │                  │
              │            ┌──────┴──────┐    ┌─────┴─────┐
              │            │ Permissions │    │Permissions│
              │            │(+inheritable│    └───────────┘
              │            │ flag)       │
              │            └─────────────┘
              │                   │
              └───────────────────┘
                        │
                  ┌─────┴─────┐
                  │ ¿Coincide │
                  │ resource + │
                  │ action?    │
                  └─────┬─────┘
                        │
              ┌─────────┼─────────┐
              │ Directo  │ Ancestro│
              │ (i=0)   │ (i>0)  │
              │ → Todos  │→ Solo  │
              │ aplican  │inheritable│
              └──────────┴─────────┘
```

---

## 4. Arquitectura del Backend

### 4.1 Estructura de Directorios

La arquitectura sigue el patrón **Controller → Service → Repository**:

```
boscoGest/
├── app/
│   ├── api/v1/                 # 19 Routers (Controllers) — capa HTTP delgada
│   │   ├── __init__.py         # Lista de routers para registro
│   │   ├── auth_router.py      # /auth — login, logout, check-permission, register (público)
│   │   ├── user_router.py      # /users — CRUD, bulk upload, search
│   │   ├── role_router.py      # /roles — CRUD con permisos
│   │   ├── permission_router.py # /permissions — CRUD, asignación a roles
│   │   ├── group_router.py     # /groups — CRUD de grupos
│   │   ├── entity_router.py    # /entities — CRUD jerárquico + /entities/public (sin auth)
│   │   ├── membership_router.py # /memberships — CRUD
│   │   ├── membership_request_router.py # /membership-requests — solicitudes de alta
│   │   ├── activity_router.py  # /activities — CRUD, inscripciones
│   │   ├── communication_router.py # /communications — CRUD noticias
│   │   ├── comment_router.py   # /comments — CRUD comentarios
│   │   ├── magazine_router.py  # /magazines — CRUD con PDF upload
│   │   ├── branding_router.py  # /branding — personalización visual
│   │   ├── view_config_router.py # /view-configs — sidebar dinámico
│   │   ├── resource_router.py  # /resources + /resource-categories
│   │   ├── notification_router.py # /notifications — REST + WebSocket
│   │   ├── chat_router.py      # /chat — conversaciones, mensajes, grupos, WebSocket
│   │   ├── download_router.py  # /downloads — descarga de archivos (proxy/presigned)
│   │   └── fee_router.py       # /fees — cuotas, histórico, preview, asignaciones, mantenimiento (run/runs)
│   ├── services/               # 24 Services — lógica de negocio
│   │   ├── authorization_service.py  # RBAC jerárquico
│   │   ├── audit_service.py          # Logging de auditoría
│   │   ├── auth_service.py           # Login, logout, token refresh
│   │   ├── user_service.py           # CRUD usuarios, bulk upload (Excel/CSV vía member_file.py)
│   │   ├── entity_service.py         # Gestión jerarquía, roles por defecto
│   │   ├── membership_service.py     # Memberships + auto-creación padres
│   │   ├── membership_request_service.py # Solicitudes de alta: crear, aceptar, rechazar, cancelar
│   │   ├── role_service.py
│   │   ├── permission_service.py
│   │   ├── group_service.py
│   │   ├── activity_service.py
│   │   ├── communication_service.py
│   │   ├── comment_service.py
│   │   ├── magazine_service.py
│   │   ├── branding_service.py
│   │   ├── view_config_service.py
│   │   ├── resource_service.py
│   │   ├── notification_service.py   # Emisión de notificaciones, preferencias
│   │   ├── notification_manager.py   # Singleton WebSocket, cola async (notificaciones)
│   │   ├── chat_service.py           # Lógica chat: conversaciones, mensajes, grupos
│   │   ├── chat_manager.py           # Singleton WebSocket, cola async (chat)
│   │   ├── fee_service.py            # Cuotas: alta multi-entidad, histórico, preview, generación, estados, run_maintenance
│   │   ├── fee_scheduler.py          # APScheduler in-process: job diario de mantenimiento de cuotas
│   │   ├── email_service.py          # Envío de emails (AWS SES) — bienvenida
│   │   └── storage.py               # StorageService (S3 + Local backends)
│   ├── repositories/           # 18 Repositories — acceso a datos
│   │   ├── base_repository.py       # BaseRepository[T] genérico (CRUD)
│   │   ├── entity_repository.py     # CTEs recursivos para jerarquía
│   │   ├── user_repository.py
│   │   ├── membership_repository.py
│   │   ├── membership_request_repository.py
│   │   ├── role_repository.py
│   │   ├── permission_repository.py
│   │   ├── group_repository.py
│   │   ├── activity_repository.py
│   │   ├── communication_repository.py
│   │   ├── comment_repository.py
│   │   ├── magazine_repository.py
│   │   ├── branding_repository.py
│   │   ├── view_config_repository.py
│   │   ├── resource_repository.py
│   │   ├── notification_repository.py
│   │   ├── chat_repository.py       # Queries de conversaciones, miembros, mensajes
│   │   └── fee_repository.py        # FeeRepository + FeeConfigRepository + FeeAssignmentRepository + FeeMaintenanceRunRepository
│   ├── models/                 # 23 Modelos SQLAlchemy ORM
│   │   ├── relationships.py    # Tablas M:M
│   │   ├── chat_model.py       # ChatConversation, ChatMember, ChatMessage, ChatJoinRequest
│   │   └── *.py               # Un modelo por fichero
│   ├── schemas/                # 19 Esquemas Pydantic v2
│   │   └── *.py               # Create/Update/Response por recurso
│   ├── database/
│   │   ├── database.py        # Engine, SessionLocal, Base
│   │   └── seeds/             # Seeder inicial
│   ├── utils/
│   │   └── auth.py            # JWT, passwords, get_current_user (deps FastAPI)
│   ├── tests/
│   │   ├── conftest.py        # Fixtures (SQLite in-memory)
│   │   ├── test_hierarchical_permissions.py # 14 tests de herencia
│   │   └── test_*_router.py   # Tests por router (10 ficheros, 221 tests)
│   └── main.py                # App FastAPI, CORS, mount uploads
├── alembic/
│   ├── env.py
│   └── versions/              # Migraciones
├── Makefile                   # Comandos de desarrollo
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

### 4.2 Flujo de una Petición

```
HTTP Request
    │
    ▼
Router (app/api/v1/xxx_router.py) — capa HTTP delgada
    │
    ├── Depends(get_current_active_user) ── → JWT validation → User
    ├── Depends(get_xxx_service) ── → Service(db)
    │
    ▼
Service (app/services/xxx_service.py) — lógica de negocio
    │
    ├── AuthorizationService.check_entity_permission(user, entity_id, resource, action)
    │       ├── EntityRepository.get_ancestor_chain() ── → CTE recursiva
    │       ├── batch membership fetch ── → Membresías + Roles + Permisos
    │       └── Evaluación de herencia
    │
    ├── Repository.create/update/delete() ── → db.flush()
    │
    ├── AuditService.create_audit_log(...)
    │
    ├── NotificationService.notify(event_type, entity_id, actor, ...) ── → (opcional)
    │       ├── Filtra destinatarios por preferencias
    │       ├── Inserta Notification en BD (bulk)
    │       └── Encola push WebSocket (asyncio.Queue → NotificationManager)
    │
    └── db.commit() — el servicio controla la transacción
    │
    ▼
Pydantic Response Schema → JSON
```

### 4.3 Endpoints API

#### Auth (`/auth`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/token` | Login (OAuth2 form-data) → JWT |
| POST | `/logout` | Revoca token (blacklist) |
| GET | `/check-permission` | Verifica permiso ABAC |
| POST | `/register` | **Público** — crea usuario + solicitud de alta en una entidad |

#### Users (`/users`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | users:create (jerárquico) | Crear usuario + membresía |
| GET | `/` | users:list (jerárquico) | Listar usuarios accesibles |
| GET | `/managed` | users:manage | Usuarios gestionables |
| GET | `/{id}` | users:read | Detalle de usuario |
| PUT | `/{id}` | users:update | Actualizar usuario |
| DELETE | `/{id}` | users:delete | Soft delete |
| GET | `/bulk-upload/template.xlsx` | Autenticado | Plantilla Excel de la importación masiva |
| POST | `/bulk-upload/validate` | users:create (jerárquico) | Comprobar un archivo (.xlsx o .csv) sin crear nada |
| POST | `/bulk-upload` | users:create (jerárquico) | Importación masiva desde Excel (.xlsx) o CSV |
| POST | `/change-password` | Autenticado | Cambio de contraseña |
| POST | `/first-time-password-change` | Autenticado | Primer cambio obligatorio |
| GET | `/search/email/{email}` | users:read | Buscar por email |
| GET | `/search/dni/{dni}` | users:read | Buscar por DNI |

#### Entities (`/entities`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/public` | **Público** | Entidades con `level > 1` para formulario de registro |
| GET | `/` | entities:list | Entidades del usuario |
| GET | `/{id}` | entities:read (jerárquico) | Detalle de entidad |
| GET | `/{id}/roles` | entities:read (jerárquico) | Roles de la entidad |
| GET | `/membership-manageable` | memberships:manage | Entidades gestionables |
| GET | `/admin` | entities:list | Entidades administrables |
| POST | `/` | entities:create (jerárquico en padre) | Crear sub-entidad |
| PUT | `/{id}` | entities:update (jerárquico) | Actualizar nombre |
| DELETE | `/{id}` | entities:delete (jerárquico) | Soft delete cascada |

#### Roles (`/roles`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | roles:create (jerárquico) | Crear rol (sin manage_all) |
| GET | `/` | roles:list (jerárquico) | Roles de la entidad actual |
| GET | `/{id}` | roles:read | Detalle con permisos |
| PUT | `/{id}` | roles:update | Actualizar (superadmin inmutable) |
| DELETE | `/{id}` | roles:delete (jerárquico) | Soft delete |

#### Memberships (`/memberships`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | memberships:create (jerárquico) | Crear membresía + auto-crear padres |
| GET | `/` | Autenticado | Membresías propias del usuario |
| GET | `/{id}` | Autenticado (propia) | Detalle de membresía |
| PUT | `/{id}` | memberships:update (jerárquico) | Actualizar membresía |
| DELETE | `/{id}` | memberships:delete (jerárquico) | Soft delete |

#### Membership Requests (`/membership-requests`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | Autenticado | Crear solicitud de alta (elige entidad) |
| GET | `/mine` | Autenticado | Solicitudes propias del usuario |
| GET | `/` | memberships:review | Listar solicitudes (filtros: entity_id, status) |
| POST | `/{id}/accept` | memberships:review | Aceptar solicitud → crea Membership en entidad + padres |
| POST | `/{id}/reject` | memberships:review | Rechazar solicitud con motivo opcional |
| DELETE | `/{id}` | Autenticado (propia) | Cancelar solicitud propia en estado pending |

#### Activities (`/activities`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | activities:create (jerárquico) | Crear actividad |
| GET | `/` | Autenticado | Listar actividades accesibles |
| GET | `/{id}` | Autenticado | Detalle de actividad |
| PUT | `/{id}` | activities:update (jerárquico) | Actualizar actividad |
| DELETE | `/{id}` | activities:delete (jerárquico) | Soft delete |
| POST | `/{id}/register` | Autenticado | Inscribirse |
| GET | `/{id}/registrations` | activities:manage (jerárquico) | Listar inscripciones |
| POST | `/{id}/registrations/{uid}/accept` | activities:manage (jerárquico) | Aceptar inscripción |
| POST | `/{id}/registrations/{uid}/reject` | activities:manage (jerárquico) | Rechazar inscripción |
| POST | `/{id}/upload-image` | activities:update (jerárquico) | Subir imagen |

#### Communications (`/communications`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | communications:create (jerárquico) | Crear noticia (status=draft por defecto; status=published requiere communications:publish) |
| GET | `/` | Autenticado | Listar noticias accesibles (query param `?status=`) — usuarios con review/publish ven todos los estados, otros solo published |
| GET | `/count` | Autenticado | Contar noticias (query param `?status=`) |
| GET | `/{id}` | communications:read (jerárquico) | Detalle con comentarios |
| PUT | `/{id}` | communications:edit (jerárquico) | Actualizar noticia (solo status draft/review) |
| PATCH | `/{id}/status` | Según transición | Transición de estado (draft→review, draft→published, review→published, review→draft, published→archived) |
| DELETE | `/{id}` | communications:delete (jerárquico) | Soft delete |
| POST | `/{id}/upload-image` | communications:edit (jerárquico) | Subir imagen |

#### Comments (`/comments`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/communications/{id}/comments` | comment:create (jerárquico) | Crear comentario |
| GET | `/communications/{id}/comments` | comment:read (jerárquico) | Listar comentarios |
| PUT | `/comments/{id}` | comment:edit (jerárquico) | Actualizar comentario |
| DELETE | `/comments/{id}` | comment:delete (jerárquico) | Eliminar (hard delete) |

#### Magazines (`/magazines`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | magazines:create (jerárquico) | Subir revista PDF |
| GET | `/` | Autenticado | Listar revistas accesibles |
| GET | `/{id}` | magazines:read (jerárquico) | Detalle de revista |
| GET | `/{id}/file` | magazines:read (jerárquico) | Descargar PDF |
| PUT | `/{id}` | magazines:update (jerárquico) | Actualizar metadatos |
| DELETE | `/{id}` | magazines:delete (jerárquico) | Eliminar (hard delete + fichero) |

#### Branding (`/branding`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/entity/{id}` | branding:read (jerárquico) | Obtener branding |
| GET | `/subdomain/{sub}` | Público | Branding por subdominio |
| POST | `/entity/{id}` | branding:update (jerárquico) | Crear branding |
| PUT | `/entity/{id}` | branding:update (jerárquico) | Actualizar branding |
| DELETE | `/entity/{id}` | branding:update (jerárquico) | Eliminar branding |
| POST | `/entity/{id}/logo` | branding:update (jerárquico) | Subir logo |

#### View Config (`/view-configs`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/entity/{id}` | views:read (jerárquico) | Todas las vistas |
| GET | `/entity/{id}/enabled` | views:read (jerárquico) | Solo vistas habilitadas |
| PUT | `/entity/{id}/view/{name}` | views:update (jerárquico) | Actualizar una vista |
| PUT | `/entity/{id}/bulk` | views:update (jerárquico) | Actualización masiva |
| POST | `/entity/{id}/reset` | views:update (jerárquico) | Restaurar valores por defecto |

#### Resources (`/resources`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/link` | resources:create (jerárquico) | Crear recurso enlace/vídeo |
| POST | `/` | resources:create (jerárquico) | Subir documento/imagen (multipart) |
| GET | `/` | resources:list (jerárquico) | Listar con filtros (tipo, categoría, tags, búsqueda) |
| GET | `/{id}` | resources:read (jerárquico) | Detalle con relaciones |
| GET | `/{id}/file` | resources:read (jerárquico) | URL de descarga (presigned) |
| PUT | `/{id}` | resources:update (jerárquico) | Actualizar metadatos |
| DELETE | `/{id}` | resources:delete (jerárquico) | Hard delete + eliminación fichero |

#### Resource Categories (`/resource-categories`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/` | resources:create (jerárquico) | Crear categoría |
| GET | `/entity/{id}` | resources:list (jerárquico) | Listar categorías de entidad |
| PUT | `/{id}` | resources:update (jerárquico) | Actualizar categoría |
| DELETE | `/{id}` | resources:delete (jerárquico) | Soft delete |

#### Notifications (`/notifications`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/` | Autenticado | Listar notificaciones del usuario (paginado) |
| GET | `/unread-count` | Autenticado | Contador de no leídas |
| PUT | `/{id}/read` | Autenticado | Marcar como leída |
| PUT | `/read-all` | Autenticado | Marcar todas como leídas |
| DELETE | `/{id}` | Autenticado | Eliminar notificación (hard delete) |
| GET | `/preferences` | Autenticado | Obtener preferencias de notificación |
| PUT | `/preferences` | Autenticado | Actualizar preferencias por tipo de evento |
| WS | `/ws?token=JWT` | Autenticado (JWT en query) | WebSocket para notificaciones en tiempo real |

#### Chat (`/chat`)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/conversations` | Autenticado | Listar conversaciones del usuario (pinned first, con unread count) |
| POST | `/conversations/direct` | Autenticado | Crear o recuperar conversación directa con otro usuario |
| POST | `/conversations/group` | Autenticado | Crear conversación de grupo |
| GET | `/conversations/{id}/messages` | Miembro | Mensajes paginados (cursor `before_id`, limit 50) |
| POST | `/conversations/{id}/messages` | Miembro | Enviar mensaje de texto (con `reply_to_id` opcional) |
| POST | `/conversations/{id}/messages/files` | Miembro | Enviar mensaje con archivo (multipart, max 20 MB) |
| GET | `/conversations/{id}/messages/search` | Miembro | Buscar mensajes por texto (ILIKE) |
| DELETE | `/conversations/{id}/messages/{mid}` | Remitente | Soft delete de mensaje propio |
| GET | `/conversations/{id}/members` | Miembro | Listar miembros con presencia online |
| POST | `/conversations/{id}/members` | Admin del grupo | Añadir miembro |
| DELETE | `/conversations/{id}/members/{uid}` | Admin del grupo | Expulsar miembro |
| PUT | `/conversations/{id}/members/{uid}/role` | Admin del grupo | Cambiar rol (admin/member) |
| GET | `/conversations/{id}/presence` | Miembro | Presencia online de todos los miembros |
| POST | `/conversations/{id}/join-request` | Autenticado | Solicitar unirse a grupo |
| GET | `/conversations/{id}/join-requests` | Admin del grupo | Listar solicitudes pendientes |
| PUT | `/conversations/{id}/join-requests/{rid}` | Admin del grupo | Aceptar/rechazar solicitud |
| PUT | `/conversations/{id}` | Admin del grupo | Actualizar nombre y descripción del grupo |
| POST | `/conversations/{id}/avatar` | Admin del grupo | Subir avatar del grupo |
| PUT | `/conversations/{id}/mute` | Miembro | Silenciar conversación |
| DELETE | `/conversations/{id}/mute` | Miembro | Activar notificaciones |
| PUT | `/conversations/{id}/pin` | Miembro | Fijar conversación al inicio |
| DELETE | `/conversations/{id}/pin` | Miembro | Desfijar conversación |
| POST | `/conversations/{id}/read` | Miembro | Marcar conversación como leída (actualiza `last_read_at`) |
| DELETE | `/conversations/{id}/leave` | Miembro | Abandonar grupo |
| GET | `/users/search` | Autenticado | Buscar usuarios por nombre/email para añadir a grupos |
| WS | `/ws/{conversation_id}?token=JWT` | Miembro activo | WebSocket bidireccional para chat en tiempo real |

---

## 5. Sistema de Notificaciones en Tiempo Real

### 5.1 Arquitectura

El sistema combina persistencia en PostgreSQL con entrega en tiempo real vía WebSocket:

```
Acción en servicio (sync)
    │
    ▼
NotificationService.notify()
    │
    ├── 1. Resolución de destinatarios
    │       ├── recipient_ids explícitos (ej: inscripción aceptada → solo el usuario)
    │       └── Miembros de la entidad (ej: nueva actividad → todos los miembros)
    │
    ├── 2. Filtrado por preferencias (NotificationPreference.in_app_enabled)
    │
    ├── 3. Persistencia: INSERT bulk en tabla notifications
    │
    └── 4. Push WebSocket: loop.call_soon_threadsafe(queue.put_nowait, payload)
            │
            ▼
    NotificationManager (singleton async)
        │
        ├── asyncio.Queue recibe payloads
        ├── dispatch_loop() consume la cola
        └── Envía JSON a conexiones WebSocket activas por user_id
```

### 5.2 Puente Sync → Async

Los servicios de negocio ejecutan en el thread pool síncrono de FastAPI, pero WebSocket es async. El puente usa:

```python
# En NotificationService.notify() (sync, thread pool)
loop = notification_manager.loop                    # Event loop del servidor
loop.call_soon_threadsafe(queue.put_nowait, payload) # Thread-safe enqueue

# En NotificationManager._dispatch_loop() (async, event loop)
payload = await self._queue.get()                   # Espera no bloqueante
await self._send_to_user(user_id, json_data)        # Envío WebSocket
```

### 5.3 Tipos de Evento

| EventType | Trigger | Destinatarios |
|-----------|---------|---------------|
| `magazine_published` | Crear revista | Miembros de la entidad |
| `activity_created` | Crear actividad | Miembros de la entidad |
| `activity_updated` | Actualizar actividad | Miembros de la entidad |
| `registration_accepted` | Aceptar inscripción | Usuario inscrito |
| `registration_rejected` | Rechazar inscripción | Usuario inscrito |
| `communication_published` | Publicar comunicación (transición a status "published") | Miembros de la entidad |
| `comment_added` | Crear comentario | Autor de la comunicación + comentaristas previos |
| `resource_published` | Crear recurso | Miembros de la entidad |
| `membership_created` | Crear membresía | Usuario añadido |
| `chat_message_received` | Nuevo mensaje de chat | Usuarios offline no silenciados de la conversación |
| `membership_request_created` | Nueva solicitud de alta | Usuarios con `memberships:review` en la entidad solicitada |
| `membership_request_accepted` | Solicitud de alta aceptada | El usuario solicitante |
| `membership_request_rejected` | Solicitud de alta rechazada | El usuario solicitante |

### 5.4 Preferencias

Cada usuario puede deshabilitar tipos de evento específicos. Por defecto, todo está habilitado (si no existe registro en `notification_preferences`, se asume `in_app_enabled=True`).

---

## 6. Arquitectura del Frontend

### 6.1 Estructura de Directorios

```
boscoGest-front/
├── android/                     # Proyecto Android Studio (auto-generado por Capacitor)
├── ios/                         # Proyecto Xcode (auto-generado por Capacitor)
├── capacitor.config.ts          # Configuración de Capacitor
├── public/assets/fonts/         # Roboto + Material Icons (bundleadas localmente)
├── src/app/
│   ├── auth/                    # Servicio de autenticación, guards, interceptor
│   │   ├── register/            # Formulario de auto-registro (3 pasos: datos → entidad → confirmación)
│   │   └── pending-approval/    # Pantalla de espera post-registro (WebSocket para auto-redirección)
│   ├── layout/                  # Componente layout (sidebar + contenido principal)
│   ├── sidebar/                 # Sidebar dinámico con menú basado en EntityViewConfig
│   ├── main/                    # Área de contenido principal (responsive)
│   ├── breadcrumb/              # Navegación por migas de pan
│   ├── dashboard/               # Calendario (FullCalendar) + actividades + noticias
│   ├── login/                   # Formulario de login + enlace a registro
│   ├── users/                   # Gestión de usuarios (CRUD, importación Excel/CSV)
│   ├── entities/                # Gestión de entidades/asociaciones
│   ├── roles/                   # Gestión de roles y permisos
│   ├── activities/              # Gestión de actividades e inscripciones
│   ├── communications/          # Gestión de noticias y comentarios
│   ├── magazines/               # Gestión de revistas PDF
│   ├── settings/                # Configuración (branding + vistas)
│   ├── my-profile/              # Perfil del usuario
│   ├── permissions/             # Servicio de permisos
│   ├── models/                  # Interfaces TypeScript
│   ├── utils/                   # Utilidades (file-download cross-platform)
│   ├── pipes/                   # SafePipe (sanitización HTML/URL)
│   ├── confirm-dialog/          # Diálogo de confirmación reutilizable
│   ├── change-password-dialog/  # Diálogo de cambio de contraseña
│   ├── first-time-password-dialog/
│   ├── membership-requests/     # Solicitudes de alta de usuarios
│   │   ├── membership-request.service.ts  # register, getMyRequests, accept, reject, cancel, getPublicEntities
│   │   └── membership-requests-list/      # Panel admin: tabla, aceptar, rechazar (con diálogo de motivo)
│   ├── notifications/           # Sistema de notificaciones in-app
│   │   ├── notification.service.ts      # REST + WebSocket (notificaciones)
│   │   ├── notification-bell/           # Campana con badge y panel desplegable
│   │   └── notification-preferences/   # Toggle por tipo de evento
│   ├── chat/                    # Sistema de mensajería en tiempo real
│   │   ├── chat.service.ts              # REST + WebSocket (chat), estado de conversaciones
│   │   ├── chat.component.ts/html/css   # Contenedor principal: lista + vista
│   │   ├── conversation-list/           # Lista de conversaciones con badges unread
│   │   ├── conversation-view/           # Mensajes, indicador de escritura, reply, adjuntos
│   │   ├── new-conversation-dialog/     # Crear conversación directa o grupo
│   │   └── group-settings-dialog/       # Miembros, solicitudes, avatar del grupo
│   ├── app.routes.ts            # Definición de rutas
│   ├── app.config.ts            # Proveedores (router, HTTP, interceptores)
│   └── app.ts                   # Componente raíz (+ back button Android, status bar)
└── package.json
```

### 6.2 Patrones de Angular 20

| Patrón | Uso en BoscoGest |
|--------|------------------|
| **Standalone components** | Todos los componentes usan `imports: [...]`, sin NgModules |
| **Signals** | Estado global (AuthService) y local (componentes) con `signal()` y `computed()` |
| **input/output API** | `input.required<T>()`, `output<T>()` en lugar de decoradores |
| **Control flow** | `@if`, `@for`, `@switch` en lugar de directivas estructurales |
| **Functional guards** | `authGuard`, `permissionGuard(resource, action)` como funciones |
| **Functional interceptors** | `authInterceptor` adjunta token JWT a peticiones |
| **Reactive forms** | `FormBuilder` + `FormGroup` para formularios |

### 6.3 Gestión de Estado con Signals

No se usa NgRx ni stores externos. Todo el estado se gestiona con Angular Signals:

```
AuthService (singleton)
├── isAuthenticated: signal<boolean>
├── currentUser: signal<UserResponse | null>
├── currentMembership: signal<MembershipDetails | null>
├── allMemberships: signal<MembershipDetails[]>
└── allUniquePermissions: computed<PermissionResponse[]>
        │
        ▼
    Componentes consumen con computed():
    canEditUsers = computed(() => this.authService.hasPermission('users', 'update'))
```

### 6.4 Sidebar Dinámico

El sidebar se genera dinámicamente por entidad usando `EntityViewConfig`:

```
1. Login → AuthService.currentMembership cambia
        │
        ▼
2. ViewConfigService.loadViewConfigs(entityId)
        │ GET /view-configs/entity/{id}/enabled
        ▼
3. _viewConfigs signal actualizado
        │
        ▼
4. enabledViews (computed) → filtra y ordena
        │
        ▼
5. getMenuItems() → convierte a MenuItem[]
        │ Mapeo: 'communications' → '/blog', 'users' → '/users', etc.
        ▼
6. Sidebar renderiza menuItems + admin items (filtrados por permisos)
```

Vistas disponibles: dashboard, users, entities, roles, activities, communications, magazines, resources, chat, shop, fees, payments, settings.

### 6.7 Aplicaciones Móviles (Capacitor)

El mismo código Angular se empaqueta como app nativa para Android e iOS usando **Capacitor 8**. Capacitor envuelve la web app compilada en un WebView nativo, sin necesidad de cambiar la UI (se mantiene Angular Material).

```
ng build → dist/boscoGest-front/browser/ → cap sync → android/ + ios/
```

#### Adaptaciones para móvil

| Adaptación | Fichero | Descripción |
|-----------|---------|-------------|
| CapacitorHttp | `capacitor.config.ts` | Parchea fetch/XHR para usar HTTP nativo, bypass CORS en móvil |
| Safe areas | `styles.css`, `layout.component.css`, `sidebar.component.css` | `env(safe-area-inset-*)` para notch y gesture bar |
| Back button Android | `app.ts` | `@capacitor/app` listener → `history.back()` o `exitApp()` |
| Status bar | `app.ts` | Color y estilo de la barra de estado en nativo |
| Descargas | `utils/file-download.util.ts` | Web: `<a download>`, Nativo: `@capacitor/filesystem` + `@capacitor/share` |
| Fuentes locales | `public/assets/fonts/` | Roboto + Material Icons bundleadas (sin CDN) |
| Viewport | `index.html` | `viewport-fit=cover` para pantallas con notch |

Todo el código condicional usa `Capacitor.isNativePlatform()` — en web no tiene impacto.

Para documentación detallada, ver [CAPACITOR.md](CAPACITOR.md).

### 6.5 Branding Dinámico

```
Login → BrandingService.loadAndApplyBranding(entityId)
        │
        ├── GET /branding/entity/{id}
        │
        ▼
    applyBrandingToDOM(branding)
        │
        ├── document.documentElement.style.setProperty('--primary-color', ...)
        ├── document.documentElement.style.setProperty('--secondary-color', ...)
        ├── document.documentElement.style.setProperty('--accent-color', ...)
        ├── Calcula variantes: --primary-light (+20%), --primary-dark (-20%)
        │
        ▼
    Todos los componentes con var(--primary-color) se actualizan
```

### 6.6 Flujo de Autenticación (Frontend)

```
LoginComponent
    │ POST /auth/token (email, password)
    ▼
AuthService.login() — usa switchMap para carga síncrona
    │ ← JWT token
    ├── localStorage.setItem('authToken', token)
    ├── GET /memberships/ → carga membresías (sincrónico vía switchMap)
    ├── si membresías vacías → router.navigate(['/pending'])   ← usuario pendiente de aprobación
    ├── si must_change_password → abre FirstTimePasswordDialog
    └── si membresías activas:
            ├── BrandingService.loadAndApplyBranding()
            ├── ViewConfigService.loadViewConfigs()
            └── router.navigate(['/dashboard'])

Registro de nuevo usuario:
    RegisterComponent (3 pasos)
        │ GET /entities/public → selección de entidad
        │ POST /auth/register → crea usuario + MembershipRequest
        ▼ → router.navigate(['/pending'])

PendingApprovalComponent:
    │ GET /membership-requests/mine → estado de solicitudes
    │ WS /notifications/ws → detecta membership_request_accepted
    └── auto-redirección a /dashboard al ser aceptado

Cada petición posterior:
    authInterceptor → adjunta "Authorization: Bearer {token}"

Navegación a ruta protegida:
    authGuard → verifica isAuthenticated (true aunque sin membresías, para /pending)
    permissionGuard(resource, action) → GET /auth/check-permission
```

---

## 7. Sistema de Chat en Tiempo Real

### 7.1 Arquitectura

El sistema de chat combina persistencia en PostgreSQL con entrega en tiempo real vía WebSocket, siguiendo el mismo patrón que el sistema de notificaciones pero con un `ChatManager` independiente:

```
Acción del usuario (enviar mensaje, unirse, etc.)
    │
    ▼
ChatService (sync, thread pool)
    │
    ├── 1. Persistencia: ChatRepository → INSERT en chat_messages
    │
    ├── 2. Re-fetch del mensaje (eager-load sender + reply_to)
    │
    ├── 3. Broadcast WebSocket: ChatManager.enqueue(conversation_id, payload)
    │       │   loop.call_soon_threadsafe(queue.put_nowait, ...)
    │       ▼
    │   ChatManager (singleton async)
    │       ├── asyncio.Queue recibe payloads
    │       ├── dispatch_loop() consume la cola
    │       └── Envía JSON a conexiones activas de la conversación
    │
    └── 4. Notificación in-app: NotificationService.notify(chat_message_received)
            └── Solo a usuarios offline (no conectados al WS del chat)
                que no hayan silenciado la conversación
```

### 7.2 Mensajes WebSocket

El cliente conecta a `WS /chat/ws/{conversation_id}?token=JWT`. El protocolo es bidireccional:

| Dirección | Tipo | Payload | Descripción |
|-----------|------|---------|-------------|
| Cliente → Servidor | `typing` | `{type, conversation_id}` | Indicador de escritura |
| Servidor → Cliente | `new_message` | `MessageResponse` completo | Nuevo mensaje en la conversación |
| Servidor → Cliente | `message_deleted` | `{message_id}` | Mensaje eliminado (soft delete) |
| Servidor → Cliente | `typing` | `{type, user_id, user_name, conversation_id}` | Reenvío del indicador de escritura a otros miembros |

### 7.3 Modelos de Chat

```
ChatConversation (1)
    ├──< ChatMember (N)           → user_id, role, is_muted, is_pinned
    ├──< ChatMessage (N)          → sender_id, content, message_type
    │       └── reply_to_id (FK auto-referencial)
    └──< ChatJoinRequest (N)      → user_id, status
```

**Tipos de mensaje (`message_type`):**
- `text` — mensaje de texto ordinario
- `file` — archivo adjunto (imagen, documento); campos: `file_url`, `file_name`, `file_type`
- `system` — evento del sistema (unión, salida, expulsión); `sender_id = NULL`, no cuenta como no leído

### 7.4 Paginación de Mensajes

Los mensajes se cargan mediante **paginación por cursor** con el parámetro `before_id`:

```
GET /chat/conversations/{id}/messages?before_id=500&limit=50
    → Devuelve los 50 mensajes anteriores al ID 500 (orden ascendente)
    → hasMore = true si existen mensajes más antiguos
```

Esto permite cargar hacia atrás sin saltos de posición al insertar nuevos mensajes.

### 7.5 Presencia Online

`ChatManager.is_online(user_id)` retorna `True` si el usuario tiene al menos una conexión WebSocket activa (en cualquier conversación). Se usa para:
- Mostrar el indicador de presencia en la lista de miembros del grupo
- Decidir si enviar notificación in-app (solo a usuarios offline)

---

## 8. Base de Datos

### 8.1 Configuración

| Entorno | Motor | Configuración |
|---------|-------|---------------|
| **Producción** | PostgreSQL 15 | `DATABASE_URL` env var |
| **Docker** | PostgreSQL 15 | `DATABASE_URL_DOCKER` env var |
| **Tests** | SQLite in-memory | `StaticPool`, conftest.py override |

### 8.2 Migraciones (Alembic)

```bash
# Local
make migrate-local                    # alembic upgrade head
make revision-local m="descripción"   # alembic revision --autogenerate

# Docker (auto-copia ficheros al host)
make migrate-docker
make revision-docker m="descripción"
```

### 8.3 Seeding

`app/database/seeds/initial_seeder.py` (auto-ejecutado al iniciar):

1. **3 Roles**: superadmin (todos los permisos), admin (todos los permisos), socio (solo read/list)
2. **~56 Permisos**: 7 recursos × 8 acciones (create, list, read, update, delete, assign, manage, manage_all)
3. **1 Usuario**: superadmin@boscogest.com / superadmin123
4. **1 Entidad**: "superentity" (nivel 1)
5. **1 Membresía**: superadmin → superadmin role → superentity

### 8.4 Estrategia de Borrado

- **Soft delete** (`is_active=False`): User, Role, Permission, Entity, Membership, Activity, Communication
- **Hard delete**: Comment, Magazine (+ eliminación del fichero PDF), Notification

---

## 9. Auditoría

Todas las acciones significativas se registran en `audit_logs` mediante `AuditService`, invocado desde cada servicio de negocio:

```python
# Dentro de un Service (ej: UserService)
self.audit_service.create_audit_log(
    user_id=current_user.id,
    action="create",              # create, update, delete, login, logout, etc.
    resource_type="users",        # Tipo de recurso
    resource_id=user.id,          # ID del recurso afectado
    details={"email": "..."},     # Metadatos adicionales (JSON)
    ip_address=ip_address
)
```

Acciones auditadas: login, logout, change_password, CRUD de todos los recursos.

---

## 9. Subida de Ficheros

| Tipo | Directorio | Formatos | Endpoint |
|------|-----------|----------|----------|
| Imágenes de actividades | `uploads/activities/` | JPG, PNG, GIF, WEBP | `POST /activities/{id}/upload-image` |
| Imágenes de comunicaciones | `uploads/communications/` | JPG, PNG, GIF, WEBP | `POST /communications/{id}/upload-image` |
| Revistas PDF | `uploads/magazines/` | PDF | `POST /magazines/` (multipart) |
| Logos de branding | `uploads/branding/` | JPG, PNG, GIF, WEBP | `POST /branding/entity/{id}/logo` |

Ficheros servidos estáticamente en `/uploads` via `StaticFiles` mount.

---

## 10. Despliegue

### 10.1 Docker Compose

```yaml
services:
  db:         # PostgreSQL 15, puerto 5432
  back:       # FastAPI, puerto 8000, depende de db
  front:      # Angular (nginx), puerto 80, depende de back

volumes:
  postgres_data   # Persistencia de datos
```

### 10.2 Entornos

| Entorno | Backend | Frontend | Base de datos |
|---------|---------|----------|---------------|
| **Desarrollo** | localhost:8000 | localhost:4200 | localhost:5432 |
| **Docker** | back:8000 | front:80 | db:5432 |
| **Producción** | EC2:8000 | EC2:80 | EC2:5432 |

### 10.3 Variables de Entorno

```env
DATABASE_URL=postgresql+psycopg2://admin:admin123@localhost:5432/boscogest
DATABASE_URL_DOCKER=postgresql+psycopg2://admin:admin123@db:5432/boscogest
SECRET_KEY=<mínimo 32 caracteres>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOAD_DIR=uploads
CORS_ORIGINS=http://localhost:4200,http://localhost
```

---

## 11. Testing

### 11.1 Backend (pytest)

- **Base de datos**: SQLite in-memory con `StaticPool` (conftest.py sobreescribe `get_sync_db`)
- **Fixtures**: `db_session`, `client`, `test_user`, `test_entity`, `test_membership`, `auth_headers`
- **Test de herencia jerárquica**: 14 tests dedicados en `test_hierarchical_permissions.py`
- **Tests por router**: `test_*_router.py` para cada recurso

```bash
pytest app/tests/ -v                    # Todos (~200 tests)
pytest app/tests/ -k "test_create"      # Filtrar por nombre
pytest app/tests/test_entity_router.py  # Fichero específico
```

### 11.2 Frontend (Karma + Jasmine)

```bash
npm test   # Ejecuta tests con Karma
```

---

## 12. Decisiones Arquitectónicas

| Decisión | Justificación |
|----------|---------------|
| **Derivación de entity_id desde el recurso** | Evita depender del frontend para contexto de seguridad; el backend siempre determina la entidad objetivo |
| **CTE recursiva para cadena de ancestros** | Query única independiente de la profundidad; funciona en PostgreSQL y SQLite |
| **Flag `inheritable` en Permission** | Permite control granular de qué permisos descienden por la jerarquía sin código especial por permiso |
| **Signals en lugar de NgRx** | Suficiente para la escala del proyecto; evita boilerplate; nativo de Angular 20 |
| **Sidebar dinámico (EntityViewConfig)** | Cada entidad puede personalizar qué vistas muestra, su orden y nombres, sin cambios de código |
| **Soft deletes** | Preserva datos para auditoría y recuperación; simplifica la trazabilidad |
| **JWT sin membership_id fijo** | El token no fija un contexto de membresía; el backend evalúa todas las membresías activas del usuario |
| **Standalone components** | Alineado con la dirección de Angular 20; menor acoplamiento, mejores tree-shaking y lazy loading |
| **Arquitectura 3 capas (Controller → Service → Repository)** | Separación de responsabilidades: routers delgados (HTTP), servicios (negocio + transacciones), repositorios (acceso a datos). Facilita testeo unitario y reutilización |
| **BaseRepository[T] por composición** | Los repositorios concretos usan `self.base = BaseRepository(db, Model)` en vez de herencia, permitiendo más flexibilidad y evitando problemas de herencia múltiple |
| **Services controlan transacciones** | Los services hacen `db.commit()`, los repositories solo `db.flush()`. Permite que un servicio orqueste múltiples operaciones en una transacción |
| **AuditService síncrono** | Invocado directamente desde los servicios dentro de la misma transacción, garantizando consistencia entre la acción y su registro |
| **Auto-creación de membresías padre** | `MembershipService.create_parent_memberships()` consolida la lógica duplicada: al crear membresía en una Local, se crean automáticamente membresías "socio" en Federación, Confederación y Superentidad |
| **Inyección de dependencias con factory functions** | Cada servicio tiene un `get_xxx_service(db=Depends(get_sync_db))` que FastAPI resuelve automáticamente en los routers |
| **PostgreSQL + WebSocket para notificaciones** | Persistencia en PostgreSQL (consulta de historial, paginación, contadores) + WebSocket para entrega en tiempo real. Evita dependencia externa (Redis, AWS SNS) manteniendo simplicidad |
| **NotificationManager singleton con asyncio.Queue** | Patrón productor-consumidor: servicios síncronos encolan vía `call_soon_threadsafe`, el dispatch loop async consume y envía por WebSocket. Desacopla la emisión del envío |
| **Preferencias de notificación opt-out** | Por defecto todo habilitado (sin registro = habilitado). El usuario deshabilita selectivamente por tipo de evento. Simplifica onboarding y evita crear registros innecesarios |
| **Dos estrategias de destinatarios** | Entity members (broadcast a miembros de la entidad) vs recipient_ids explícitos (notificación dirigida). Cubre tanto eventos generales como acciones individuales |
| **Capacitor sin Ionic** | Capacitor proporciona el runtime nativo (WebView + APIs del dispositivo). La UI sigue siendo Angular Material — no se usa Ionic como framework de UI. Un único codebase sirve web + móvil |
| **CapacitorHttp enabled** | Parchea fetch/XHR en nativo para usar HTTP del sistema operativo, eliminando problemas de CORS en el WebView sin cambios en el backend |
| **Fuentes locales** | Roboto y Material Icons bundleadas en `public/assets/fonts/` en lugar de CDN de Google Fonts. Necesario para apps nativas que no tienen acceso garantizado a internet al cargar |
