# OpenG2P Connector

Multi-transport ingestion gateway: ODK Central, webhooks, and event buses into
the OpenG2P registry Partner API (`POST /partner/ingest_data`).

Typical install runs three Deployments from the same image: **api**, **worker**,
and **beat**. Redis is required for Celery. PostgreSQL holds connector config
and run history.
