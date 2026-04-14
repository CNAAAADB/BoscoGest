"""
Centralized storage service abstracting file operations.
Supports S3 (production) and local filesystem (development/tests).
"""

import os
from abc import ABC, abstractmethod

import boto3
from botocore.config import Config


class StorageService(ABC):
    """Abstract storage interface."""

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload file data. Returns the storage key."""
        ...

    @abstractmethod
    def get_presigned_url(self, key: str, expires_in: int = 3600, filename: str | None = None) -> str:
        """Generate a URL to access the file. filename sets Content-Disposition for downloads."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a file by key."""
        ...


class S3StorageService(StorageService):
    def __init__(self):
        self.bucket_name = os.environ["S3_BUCKET_NAME"]
        self.region = os.getenv("AWS_REGION", "eu-west-1")
        self.client = boto3.client(
            "s3",
            region_name=self.region,
            config=Config(signature_version="s3v4"),
        )

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def get_presigned_url(self, key: str, expires_in: int = 3600, filename: str | None = None) -> str:
        params: dict = {"Bucket": self.bucket_name, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self.client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)


class LocalStorageService(StorageService):
    """For local development and tests. Stores files on local filesystem."""

    def __init__(self):
        self.upload_dir = os.getenv("UPLOAD_DIR", "uploads")

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = os.path.join(self.upload_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    def get_presigned_url(self, key: str, expires_in: int = 3600, filename: str | None = None) -> str:
        return f"/uploads/{key}"

    def delete(self, key: str) -> None:
        path = os.path.join(self.upload_dir, key)
        if os.path.exists(path):
            os.remove(path)


_storage_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    """Factory function returning a singleton StorageService."""
    global _storage_instance
    if _storage_instance is None:
        backend = os.getenv("STORAGE_BACKEND", "s3")
        if backend == "local":
            _storage_instance = LocalStorageService()
        else:
            _storage_instance = S3StorageService()
    return _storage_instance


def reset_storage_service() -> None:
    """Reset the singleton (used in tests)."""
    global _storage_instance
    _storage_instance = None
