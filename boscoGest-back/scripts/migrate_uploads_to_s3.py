"""
One-time migration script: uploads local files to S3 and updates DB records.

Run from the project root on EC2 after deploying the new code:
    python -m scripts.migrate_uploads_to_s3

Requires:
    - DATABASE_URL env var pointing to the production database
    - S3_BUCKET_NAME env var with the target bucket
    - AWS credentials (via instance profile or env vars)
    - The local `uploads/` directory with the existing files
"""

import os
import sys
import mimetypes
from pathlib import Path

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

s3 = boto3.client("s3", region_name=AWS_REGION)


def upload_file(local_path: str, s3_key: str) -> bool:
    """Upload a local file to S3. Returns True on success."""
    full_path = Path(local_path)
    if not full_path.exists():
        print(f"  [SKIP] File not found: {full_path}")
        return False

    content_type, _ = mimetypes.guess_type(str(full_path))
    content_type = content_type or "application/octet-stream"

    with open(full_path, "rb") as f:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=f.read(),
            ContentType=content_type,
        )
    print(f"  [OK] {full_path} -> s3://{S3_BUCKET}/{s3_key}")
    return True


def strip_uploads_prefix(value: str) -> str:
    """Remove 'uploads/', '/uploads/' or leading '/' from a stored path to get the S3 key."""
    if value.startswith("/uploads/"):
        return value[len("/uploads/"):]
    if value.startswith("uploads/"):
        return value[len("uploads/"):]
    if value.startswith("/"):
        return value[1:]
    return value


def local_path_from_value(value: str) -> str:
    """Resolve the local filesystem path from the stored DB value."""
    cleaned = value.lstrip("/")
    if cleaned.startswith("uploads/"):
        return cleaned
    return os.path.join(UPLOAD_DIR, cleaned)


def migrate_table(table: str, id_col: str, file_col: str):
    """Migrate a single table: upload files to S3 and update DB column."""
    print(f"\n--- Migrating {table}.{file_col} ---")
    session = Session()
    try:
        rows = session.execute(
            text(f"SELECT {id_col}, {file_col} FROM {table} WHERE {file_col} IS NOT NULL")
        ).fetchall()

        migrated = 0
        skipped = 0
        already_done = 0

        for row in rows:
            row_id, file_value = row[0], row[1]

            if not file_value:
                skipped += 1
                continue

            # Already an S3 key (no uploads prefix, no http)
            if not file_value.startswith("/uploads") and not file_value.startswith("uploads/") and not file_value.startswith("http"):
                already_done += 1
                continue

            # Skip external URLs
            if file_value.startswith("http"):
                skipped += 1
                continue

            s3_key = strip_uploads_prefix(file_value)
            local_file = local_path_from_value(file_value)

            if upload_file(local_file, s3_key):
                session.execute(
                    text(f"UPDATE {table} SET {file_col} = :key WHERE {id_col} = :id"),
                    {"key": s3_key, "id": row_id},
                )
                migrated += 1
            else:
                skipped += 1

        session.commit()
        print(f"  Result: {migrated} migrated, {skipped} skipped, {already_done} already S3 keys")
    finally:
        session.close()


def main():
    print(f"Migration: local uploads -> s3://{S3_BUCKET}")
    print(f"Upload dir: {UPLOAD_DIR}")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else '***'}")

    migrate_table("magazines", "id", "file_path")
    migrate_table("resources", "id", "file_path")
    migrate_table("entity_branding", "id", "logo_url")
    migrate_table("activities", "id", "image_url")
    migrate_table("communications", "id", "image_url")

    print("\nMigration complete.")


if __name__ == "__main__":
    main()
