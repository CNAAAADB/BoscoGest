from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    ForeignKey,
    Index,
    JSON,
    desc,
    Integer,
    LargeBinary,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# PostgreSQL gets JSONB (indexable, no reparsing); the SQLite test-suite falls
# back to plain JSON, which it does support.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class BulkUploadJob(Base):
    __tablename__ = "bulk_upload_jobs"

    __table_args__ = (
        # Jobs are always listed newest-first, so the index is descending.
        Index("ix_bulk_upload_jobs_created_at", desc("created_at")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Entity (asociación) selected in the UI; applied to every row of the CSV.
    target_entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    # Role selected in the UI; assigned to every user created from the CSV.
    target_role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )

    csv_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable because it is discarded once the job finishes: the file holds
    # passwords in clear text along with the DNI, address and IBAN of everyone
    # in it, and is only needed while the rows are being processed.
    csv_content: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    total_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    errors: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONType, nullable=True)
    created_users: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONType, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
