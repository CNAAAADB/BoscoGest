"""
Script to add magazine permissions to the database.
Run this script to create permissions for magazine management.
"""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from app.models.permission_model import Permission
from app.models.role_model import Role

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/boscogest")

def add_magazine_permissions():
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        # Define magazine permissions
        magazine_permissions = [
            {
                "name": "Crear Revistas",
                "resource": "magazines",
                "action": "create",
                "description": "Permite subir nuevas revistas en PDF"
            },
            {
                "name": "Listar Revistas",
                "resource": "magazines",
                "action": "list",
                "description": "Permite ver la lista de revistas disponibles"
            },
            {
                "name": "Leer Revistas",
                "resource": "magazines",
                "action": "read",
                "description": "Permite visualizar y descargar revistas"
            },
            {
                "name": "Actualizar Revistas",
                "resource": "magazines",
                "action": "update",
                "description": "Permite modificar información de revistas"
            },
            {
                "name": "Eliminar Revistas",
                "resource": "magazines",
                "action": "delete",
                "description": "Permite eliminar revistas"
            }
        ]

        created_permissions = []

        # Create permissions if they don't exist
        for perm_data in magazine_permissions:
            existing = db.execute(
                select(Permission).where(
                    Permission.resource == perm_data["resource"],
                    Permission.action == perm_data["action"]
                )
            ).scalars().first()

            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
                db.flush()
                created_permissions.append(permission)
                print(f"✓ Created permission: {perm_data['name']}")
            else:
                created_permissions.append(existing)
                print(f"- Permission already exists: {perm_data['name']}")

        db.commit()

        # Get all roles
        roles = db.execute(select(Role)).scalars().all()

        # Get admin role
        admin_role = db.execute(
            select(Role).where(Role.name == "admin")
        ).scalars().first()

        if admin_role:
            # Admin gets all magazine permissions
            for permission in created_permissions:
                if permission not in admin_role.permissions:
                    admin_role.permissions.append(permission)
                    print(f"✓ Added {permission.name} to admin role")

            db.commit()
            print("\n✓ Admin role updated with all magazine permissions")

        # All other roles get read and list permissions
        read_permission = next((p for p in created_permissions if p.action == "read"), None)
        list_permission = next((p for p in created_permissions if p.action == "list"), None)

        if read_permission and list_permission:
            for role in roles:
                if role.name != "admin":
                    if read_permission not in role.permissions:
                        role.permissions.append(read_permission)
                        print(f"✓ Added read permission to {role.name} role")

                    if list_permission not in role.permissions:
                        role.permissions.append(list_permission)
                        print(f"✓ Added list permission to {role.name} role")

            db.commit()
            print("\n✓ All roles updated with read and list magazine permissions")

        print("\n✅ Magazine permissions setup completed successfully!")

if __name__ == "__main__":
    add_magazine_permissions()
