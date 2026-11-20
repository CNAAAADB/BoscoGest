import pytest
import httpx
from fastapi import HTTPException
import asyncio
from types import SimpleNamespace

from app.api.v1.magazine_router import archive_page
from app.services import archive_reader


def test_archive_requires_active_membership():
    with pytest.raises(HTTPException) as error:
        asyncio.run(archive_page(7, 1, SimpleNamespace(id=1, memberships=[SimpleNamespace(is_active=False)])))
    assert error.value.status_code == 403


def test_archive_reader_relays_only_the_requested_page(monkeypatch):
    original_client = httpx.AsyncClient

    def upstream(request):
        assert request.headers["X-BoscoGest-Page"].startswith("bg-page-v1:7:2:15:")
        assert "Authorization" not in request.headers
        return httpx.Response(200, headers={"content-type": "image/jpeg", "X-Next-Page": "3"},
                              content=b"\xff\xd8sample")

    monkeypatch.setattr(archive_reader.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(upstream), **kwargs))
    response = asyncio.run(archive_page(7, 2, SimpleNamespace(id=15, memberships=[SimpleNamespace(is_active=True)])))
    assert response.headers["x-next-page"] == "3"
    assert response.headers["cache-control"] == "private, no-store"
