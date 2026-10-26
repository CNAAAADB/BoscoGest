"""Authoritative catalogue of permissions.

Every ``(resource, action)`` pair that the codebase ever checks lives here, so
seeding a fresh database produces exactly the permission set the application
expects. Previously the list was duplicated between the (orphaned) seeder and
the test fixtures, and had already drifted: branding, views and magazines were
enforced in the services but absent from the seed.

``inheritable=False`` marks a permission that applies **only** at the entity it
was granted on and does not cascade to descendants — see the authorisation
rules in CLAUDE.md.
"""

from typing import List, NamedTuple


class PermissionSpec(NamedTuple):
    resource: str
    action: str
    description: str
    inheritable: bool = True

    @property
    def name(self) -> str:
        return f"{self.resource}:{self.action}"


# Entity-specific by design: granting them on a parent must NOT let the holder
# reshape, re-staff or re-price every entity underneath.
NON_INHERITABLE = {
    ("entities", "create"), ("entities", "update"), ("entities", "delete"),
    ("memberships", "create"), ("memberships", "read"), ("memberships", "update"),
    ("memberships", "delete"), ("memberships", "list"), ("memberships", "manage"),
    ("memberships", "review"),
    # Holding it over a parent entity must not expose the personal data of
    # every member underneath.
    ("users", "read_sensitive"),
    ("roles", "create"), ("roles", "update"), ("roles", "delete"), ("roles", "assign"),
    ("branding", "read"), ("branding", "update"),
    ("views", "read"), ("views", "update"),
    # Platform-wide legal basis for processing: superadmin only, never
    # cascading from a parent entity.
    ("consent", "manage"),
    ("fees", "create"), ("fees", "maintenance"),
}

_RAW: List[tuple] = [
    # resource, action, description
    ("users", "create", "Crear usuarios"),
    ("users", "read", "Ver la ficha de un usuario"),
    ("users", "update", "Editar usuarios"),
    ("users", "delete", "Eliminar usuarios"),
    ("users", "list", "Ver el listado de usuarios"),
    ("users", "manage", "Gestionar usuarios"),
    ("users", "manage_all", "Gestionar todos los usuarios"),
    ("users", "read_sensitive", "Ver datos sensibles (DNI, IBAN, dirección, fecha de nacimiento)"),

    ("entities", "create", "Crear asociaciones"),
    ("entities", "read", "Ver una asociación"),
    ("entities", "update", "Editar asociaciones"),
    ("entities", "delete", "Eliminar asociaciones"),
    ("entities", "list", "Ver el listado de asociaciones"),
    ("entities", "manage_all", "Gestionar todas las asociaciones"),

    ("roles", "create", "Crear roles"),
    ("roles", "read", "Ver un rol"),
    ("roles", "update", "Editar roles"),
    ("roles", "delete", "Eliminar roles"),
    ("roles", "list", "Ver el listado de roles"),
    ("roles", "assign", "Asignar permisos a los roles"),
    ("roles", "manage", "Gestionar roles"),

    ("memberships", "create", "Dar de alta en una asociación"),
    ("memberships", "read", "Ver membresías"),
    ("memberships", "update", "Editar membresías"),
    ("memberships", "delete", "Dar de baja de una asociación"),
    ("memberships", "list", "Ver el listado de membresías"),
    ("memberships", "manage", "Gestionar membresías"),
    ("memberships", "review", "Revisar solicitudes de alta"),

    ("permissions", "create", "Crear permisos"),
    ("permissions", "read", "Ver un permiso"),
    ("permissions", "update", "Editar permisos"),
    ("permissions", "delete", "Eliminar permisos"),
    ("permissions", "list", "Ver el listado de permisos"),
    ("permissions", "assign", "Asignar permisos a los roles"),

    ("groups", "create", "Crear grupos"),
    ("groups", "read", "Ver un grupo"),
    ("groups", "update", "Editar grupos"),
    ("groups", "delete", "Eliminar grupos"),
    ("groups", "list", "Ver el listado de grupos"),
    ("groups", "assign", "Asignar usuarios y roles a grupos"),

    ("activities", "create", "Crear actividades"),
    ("activities", "read", "Ver una actividad"),
    ("activities", "update", "Editar actividades"),
    ("activities", "delete", "Eliminar actividades"),
    ("activities", "list", "Ver el listado de actividades"),
    ("activities", "manage", "Gestionar inscripciones a actividades"),

    ("communications", "create", "Crear noticias"),
    ("communications", "read", "Ver noticias"),
    ("communications", "edit", "Editar noticias"),
    ("communications", "delete", "Eliminar noticias"),
    ("communications", "publish", "Publicar noticias"),
    ("communications", "review", "Revisar noticias antes de publicarlas"),
    ("communications", "manage_all", "Gestionar todas las noticias"),

    ("comment", "create", "Comentar"),
    ("comment", "read", "Ver comentarios"),
    ("comment", "edit", "Editar comentarios propios"),
    ("comment", "delete", "Eliminar comentarios propios"),
    ("comment", "manage_all", "Moderar todos los comentarios"),

    ("resources", "create", "Crear recursos"),
    ("resources", "read", "Ver un recurso"),
    ("resources", "update", "Editar recursos"),
    ("resources", "delete", "Eliminar recursos"),
    ("resources", "list", "Ver el listado de recursos"),
    ("resources", "manage_all", "Gestionar todos los recursos"),

    ("magazines", "create", "Publicar un número de la revista"),
    ("magazines", "read", "Ver la revista"),
    ("magazines", "update", "Editar números de la revista"),
    ("magazines", "delete", "Eliminar números de la revista"),
    ("magazines", "list", "Ver el listado de la revista"),

    ("fees", "create", "Crear cuotas"),
    ("fees", "read", "Ver una cuota"),
    ("fees", "list", "Ver el listado de cuotas"),
    ("fees", "manage", "Gestionar cuotas y cobros"),
    ("fees", "maintenance", "Ejecutar y supervisar el mantenimiento de cuotas"),

    ("branding", "read", "Ver la personalización visual"),
    ("branding", "update", "Editar la personalización visual"),

    ("consent", "manage", "Editar y publicar la cláusula de protección de datos"),

    ("views", "read", "Ver la configuración del menú"),
    ("views", "update", "Editar la configuración del menú"),
]

ALL_PERMISSIONS: List[PermissionSpec] = [
    PermissionSpec(
        resource=resource,
        action=action,
        description=description,
        inheritable=(resource, action) not in NON_INHERITABLE,
    )
    for resource, action, description in _RAW
]

# Read-only subset handed to the default "socio" role.
READ_ONLY_ACTIONS = {"read", "list"}

READ_ONLY_PERMISSIONS: List[PermissionSpec] = [
    p for p in ALL_PERMISSIONS
    if p.action in READ_ONLY_ACTIONS and p.resource not in ("permissions", "memberships")
]
