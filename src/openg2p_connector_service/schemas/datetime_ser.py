from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

from ..timeutil import utc_iso

UtcDateTime = Annotated[
    datetime,
    PlainSerializer(lambda v: utc_iso(v) if isinstance(v, datetime) else v, return_type=str),
]

OptionalUtcDateTime = Annotated[
    datetime | None,
    PlainSerializer(lambda v: utc_iso(v) if isinstance(v, datetime) else v, return_type=str | None),
]
