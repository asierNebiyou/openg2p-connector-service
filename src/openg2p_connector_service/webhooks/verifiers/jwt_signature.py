import hashlib
import json
from typing import Any

import httpx
import jwt
from fastapi import HTTPException

from . import verifier_registry

_SIGNATURE_HEADERS = (
    "x-signature",
    "X-Signature",
    "x-jws-signature",
    "X-JWS-Signature",
)


def _header_value(headers: dict[str, str], *names: str) -> str | None:
    lower_headers = {key.lower(): value for key, value in headers.items()}
    for name in names:
        value = lower_headers.get(name.lower())
        if value:
            return value
    return None


def _extract_token(headers: dict[str, str]) -> str:
    for name in _SIGNATURE_HEADERS:
        value = _header_value(headers, name)
        if value:
            return value.strip()
    authorization_header = _header_value(headers, "authorization", "Authorization")
    if authorization_header and authorization_header.lower().startswith("bearer "):
        return authorization_header[7:].strip()
    raise HTTPException(401, "Missing partner JWT signature header")


def _load_key_from_json_web_key_set(
    json_web_key_set: dict[str, Any], key_id: str | None = None
):
    keys = json_web_key_set.get("keys") or []
    if not keys:
        raise HTTPException(500, "Partner JSON Web Key Set has no keys")
    selected = None
    if key_id:
        selected = next(
            (entry for entry in keys if entry.get("kid") == key_id),
            None,
        )
    selected = selected or keys[0]
    if selected.get("kty") != "RSA":
        raise HTTPException(500, "Only RSA partner keys are supported")
    from jwt.algorithms import RSAAlgorithm

    return RSAAlgorithm.from_jwk(json.dumps(selected))


def _resolve_public_key(secret: str, source_config: dict | None, token: str):
    config = source_config or {}
    public_key_pem = (
        config.get("partner_public_key_pem") or secret or ""
    ).strip()
    json_web_key_set_url = (
        config.get("partner_json_web_key_set_url")
        or config.get("partner_jwks_url")
        or config.get("partner_public_key_url")
        or ""
    ).strip()

    if json_web_key_set_url:
        try:
            response = httpx.get(json_web_key_set_url, timeout=10.0)
            response.raise_for_status()
            json_web_key_set = response.json()
        except Exception as exc:
            raise HTTPException(
                502, f"Failed to fetch partner public key: {exc}"
            ) from exc
        try:
            token_header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise HTTPException(401, f"Invalid JWT header: {exc}") from exc
        return _load_key_from_json_web_key_set(
            json_web_key_set, token_header.get("kid")
        )

    if not public_key_pem:
        raise HTTPException(
            500,
            "jwt_signature requires partner_public_key_pem, "
            "partner_json_web_key_set_url, or webhook_secret PEM",
        )
    return public_key_pem


def verify_jwt_signature(
    secret: str,
    body: bytes,
    headers: dict[str, str],
    source_config: dict | None = None,
) -> None:
    token = _extract_token(headers)
    key = _resolve_public_key(secret, source_config, token)
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256", "ES256", "PS256"],
            options={"verify_aud": False},
        )
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(403, "Invalid partner JWT signature") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"Partner JWT verification failed: {exc}") from exc

    body_digest = claims.get("body_sha256") or claims.get("payload_sha256")
    if body_digest:
        import hmac

        expected = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(str(body_digest).lower(), expected.lower()):
            raise HTTPException(403, "Partner JWT body digest mismatch")


verifier_registry["jwt_signature"] = verify_jwt_signature
