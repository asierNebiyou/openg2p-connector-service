from typing import Callable

from fastapi import HTTPException

verifier_registry: dict[str, Callable[..., None]] = {}


def _register(name: str):
    def decorator(fn: Callable[..., None]):
        verifier_registry[name] = fn
        return fn

    return decorator


from .hmac_sha256 import verify_hmac_sha256  # noqa: E402
from .jwt_signature import verify_jwt_signature  # noqa: E402
from .plain_shared_token import verify_plain_shared_token  # noqa: E402

verifier_registry["none"] = lambda secret, body, headers, source_config=None: None


def verify_webhook(
    verifier_name: str,
    secret: str,
    body: bytes,
    headers: dict[str, str],
    source_config: dict | None = None,
) -> None:
    if verifier_name == "none":
        return
    if verifier_name != "jwt_signature" and not secret:
        return
    fn = verifier_registry.get(verifier_name)
    if fn is None:
        raise HTTPException(500, f"Unknown webhook_verifier: {verifier_name!r}")
    try:
        fn(secret, body, headers, source_config=source_config)
    except TypeError:
        fn(secret, body, headers)
