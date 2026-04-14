from typing import Optional, Dict, Any
from fastapi import Depends
from sqlalchemy.orm import Session
from app.models.audit_log_model import AuditLog
from app.utils.auth import get_sync_db


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log


def get_audit_service(db: Session = Depends(get_sync_db)) -> AuditService:
    return AuditService(db)
