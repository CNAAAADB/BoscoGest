"""Issue short-lived, page-specific proofs for the protected BoscoChat renderer."""
import base64
import hashlib
import hmac
import time

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException, Response

from app.config import SECRET_KEY

_seed = hmac.digest(SECRET_KEY.encode(), b"BoscoGest archive reader Ed25519 v1", hashlib.sha256)
_key = Ed25519PrivateKey.from_private_bytes(_seed)


def public_reader_key():
    key = _key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return {"public_key": key.decode("ascii")}


def page_proof(issue_id: int, page: int, user_id: int) -> str:
    claims = f"bg-page-v1:{issue_id}:{page}:{user_id}:{int(time.time()) + 60}"
    signature = base64.urlsafe_b64encode(_key.sign(claims.encode())).rstrip(b"=").decode()
    return f"{claims}.{signature}"


async def read_archive_page(issue_id: int, page: int, user_id: int):
    url = f"https://i40yd4xj1k.execute-api.us-east-1.amazonaws.com/api/archive/documents/{issue_id}/pages/{page}/image"
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            result = await client.get(url, headers={"X-BoscoGest-Page": page_proof(issue_id, page, user_id)})
            if result.status_code == 404:
                raise HTTPException(404, "Página no encontrada")
            if result.status_code == 429:
                raise HTTPException(429, "Espera unos segundos antes de pasar de página")
            result.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(503, "No se ha podido cargar la página de la revista") from exc
    if result.headers.get("content-type", "").split(";")[0] != "image/jpeg" or not result.content.startswith(b"\xff\xd8"):
        raise HTTPException(502, "Respuesta del archivo no válida")
    headers = {"Cache-Control": "private, no-store", "Access-Control-Expose-Headers": "X-Previous-Page, X-Next-Page"}
    for name in ("X-Previous-Page", "X-Next-Page"):
        value = result.headers.get(name, "")
        if value.isascii() and value.isdecimal():
            headers[name] = value
    return Response(result.content, media_type="image/jpeg", headers=headers)
