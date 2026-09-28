from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = as_utc(value)
    assert aware is not None
    return aware.isoformat().replace("+00:00", "Z")
