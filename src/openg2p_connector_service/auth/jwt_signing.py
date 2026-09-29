import hashlib
import json
from typing import Any

import jwt

from ..config import get_settings


def sign_payload(payload: dict[str, Any]) -> str | None:
    settings = get_settings()
    private_key_pem = (settings.signing_private_key_pem or "").strip()
    if not private_key_pem or not settings.signing_enabled:
        return None

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    algorithm = settings.signing_algorithm or "RS256"
    issuer = settings.signing_issuer or "openg2p-connector"
    claims = {
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "iss": issuer,
    }
    token_headers = {"alg": algorithm, "typ": "JWT"}
    return jwt.encode(
        claims,
        private_key_pem,
        algorithm=algorithm,
        headers=token_headers,
    )


def signature_headers_for(payload: dict[str, Any]) -> dict[str, str]:
    token = sign_payload(payload)
    if not token:
        return {}
    header_name = get_settings().signing_header_name or "X-Signature"
    return {header_name: token}
