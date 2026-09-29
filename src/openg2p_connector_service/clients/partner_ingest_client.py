import logging
import time
from typing import Any

import httpx

from .. import metrics as connector_metrics
from ..auth.jwt_signing import signature_headers_for
from ..config import get_settings

_logger = logging.getLogger("connector.client.partner_ingest")


def _status_class(code: int) -> str:
    return f"{code // 100}xx"


def _clamp_timeout(seconds: float | int | None, default: float) -> float:
    value = float(seconds if seconds is not None else default)
    return max(5.0, min(value, 300.0))


class PartnerIngestClient:
    async def send(
        self,
        payload: dict[str, Any],
        data_model: str | None = None,
        connector_id: str | None = None,
        timeout_seconds: float | int | None = None,
    ) -> str:
        settings = get_settings()
        ingest_url = (
            f"{settings.partner_ingest_base_url.rstrip('/')}/partner/ingest_data"
        )
        params: dict[str, str] = {}
        if data_model:
            params["data_model"] = data_model.strip().upper()

        headers = signature_headers_for(payload)
        timeout = _clamp_timeout(timeout_seconds, settings.partner_ingest_timeout)

        started_at = time.perf_counter()
        status_label = "error"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                _logger.info("POST %s data_model=%s", ingest_url, data_model)
                response = await client.post(
                    ingest_url, json=payload, params=params, headers=headers
                )
                status_label = _status_class(response.status_code)
                response.raise_for_status()
                body = response.json()
        finally:
            connector_metrics.partner_duration.labels(
                connector_id=connector_id or "unknown",
            ).observe(time.perf_counter() - started_at)
            connector_metrics.partner_requests_total.labels(
                connector_id=connector_id or "unknown",
                status_class=status_label,
            ).inc()

        response_header = body.get("response_header") or {}
        if response_header.get("response_status") == "ERROR":
            error_code = response_header.get("response_error_code", "")
            error_message = response_header.get("response_error_message", "unknown")
            raise ValueError(
                f"Partner API rejected payload: [{error_code}] {error_message}"
            )

        response_body = body.get("response_body") or {}
        response_payload = response_body.get("response_payload") or {}
        correlation_id = (
            response_payload.get("correlation_id")
            or body.get("correlation_id", "")
            or ""
        )
        _logger.info("Registry accepted payload, correlation_id=%s", correlation_id)
        return correlation_id
