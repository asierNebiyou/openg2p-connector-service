import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConnectorDefinition(Base):
    __tablename__ = "connector_definitions"

    connector_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transport_type: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)

    data_model_mnemonic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mapper_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapper_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    g2p_sender_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    g2p_register_mnemonic: Mapped[str | None] = mapped_column(String(128), nullable=True)

    source_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    auth_secret_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    webhook_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    webhook_path_slug: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    webhook_verifier: Mapped[str] = mapped_column(
        String(64), nullable=False, default="hmac_sha256"
    )

    last_poll_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    last_poll_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_poll_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_poll_fetched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_poll_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    max_in_flight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_schema_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    poll_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    poll_state_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def get_source_config(self) -> dict:
        import json

        merged_config: dict = {}
        if self.poll_config_json:
            merged_config.update(json.loads(self.poll_config_json))
        if self.source_config_json:
            merged_config.update(json.loads(self.source_config_json))
        if self.poll_state_json:
            merged_config.update(json.loads(self.poll_state_json))
        return merged_config

    def get_poll_state(self) -> dict:
        import json

        if not self.poll_state_json:
            return {}
        return json.loads(self.poll_state_json)

    def set_poll_state(self, state: dict) -> None:
        import json

        self.poll_state_json = json.dumps(state) if state else None

    def get_auth_secrets(self) -> dict:
        import json

        if not self.auth_secret_json:
            return {}
        return json.loads(self.auth_secret_json)

    @property
    def is_active(self) -> bool:
        return self.enabled and not self.paused
