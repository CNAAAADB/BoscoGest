"""
Script to add resource permissions to the database.
Run this script to create permissions for resource management.
"""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

load_dotenv()

from app.models.permission_model import Permission
from app.models.role_model import Role

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/boscogest")


def add_resource_permissions():
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        resource_permissions = [
            {
                "name": "Crear Recursos",
                "resource": "resources",
                "action": "create",
                "description": "Permite crear nuevos recursos formativos",
                "inheritable": True,
            },
            {
                "name": "Listar Recursos",
                "resource": "resources",
                "action": "list",
                "description": "Permite ver la lista de recursos disponibles",
                "inheritable": True,
            },
            {
                "name": "Leer Recursos",
                "resource": "resources",
                "action": "read",
                "description": "Permite visualizar y descargar recursos",
                "inheritable": True,
            },
            {
                "name": "Actualizar Recursos",
                "resource": "resources",
                "action": "update",
                "description": "Permite modificar información de recursos",
                "inheritable": True,
            },
            {
                "name": "Eliminar Recursos",
                "resource": "resources",
                "action": "delete",
                "description": "Permite eliminar recursos",
                "inheritable": True,
            },
            {
                "name": "Gestionar Todos los Recursos",
                "resource": "resources",
                "action": "manage_all",
                "description": "Permite gestionar todos los recursos (superadmin)",
                "inheritable": True,
            },
        ]

        created_permissions = []

        for perm_data in resource_permissions:
            existing = db.execute(
                select(Permission).where(
                    Permission.resource == perm_data["resource"],
                    Permission.action == perm_data["action"],
                )
            ).scalars().first()

            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
                db.flush()
                created_permissions.append(permission)
                print(f"Created permission: {perm_data['name']}")
            else:
                created_permissions.append(existing)
                print(f"Permission already exists: {perm_data['name']}")

        db.commit()

        # Admin gets all resource permissions
        admin_role = db.execute(
            select(Role).where(Role.name == "admin")
        ).scalars().first()

        if admin_role:
            for permission in created_permissions:
                if permission not in admin_role.permissions:
                    admin_role.permissions.append(permission)
                    print(f"Added {permission.name} to admin role")
            db.commit()
            print("\nAdmin role updated with all resource permissions")

        # Superadmin gets all resource permissions
        superadmin_role = db.execute(
            select(Role).where(Role.name == "superadmin")
        ).scalars().first()

        if superadmin_role:
            for permission in created_permissions:
                if permission not in superadmin_role.permissions:
                    superadmin_role.permissions.append(permission)
                    print(f"Added {permission.name} to superadmin role")
            db.commit()
            print("Superadmin role updated with all resource permissions")

        # Socio gets read and list permissions
        read_permission = next((p for p in created_permissions if p.action == "read"), None)
        list_permission = next((p for p in created_permissions if p.action == "list"), None)

        roles = db.execute(select(Role)).scalars().all()

        if read_permission and list_permission:
            for role in roles:
                if role.name not in ("admin", "superadmin"):
                    if read_permission not in role.permissions:
                        role.permissions.append(read_permission)
                        print(f"Added read permission to {role.name} role")
                    if list_permission not in role.permissions:
                        role.permissions.append(list_permission)
                        print(f"Added list permission to {role.name} role")
            db.commit()
            print("\nAll roles updated with read and list resource permissions")

        print("\nResource permissions setup completed successfully!")


if __name__ == "__main__":
    add_resource_permissions()
