# Connector Deployment

This directory now contains a container image definition for the Connector
Service that your DevOps team can deploy as one or more runtime roles from the
same image.

## Files

- `Dockerfile`: builds the Connector image
- `docker-entrypoint.sh`: selects the runtime role
- `deploy.env.example`: deployment-oriented env example

## Build

Build the base image:

```bash
docker build -t your-registry/openg2p-connector-service:latest ./openg2p-connector-service
```

Build with optional extras when needed:

```bash
docker build \
  --build-arg CONNECTOR_PIP_EXTRAS=metrics,kafka \
  -t your-registry/openg2p-connector-service:latest \
  ./openg2p-connector-service
```

Supported extras match `pyproject.toml`:

- `metrics`
- `kafka`
- `rabbit`
- `sqs`
- `otel`

## Runtime roles

One Docker image. Several processes. You choose which process to run by
passing a role name as the container command (first argument to the entrypoint).

If you pass nothing, it starts as `api`.

| Role | What it does | When you need it |
|------|----------------|------------------|
| `api` | HTTP API on port `8050` (config, webhooks, admin calls) | Always |
| `worker` | Celery worker: runs poll jobs, webhook handling, and Partner ingest | Always for polling / webhooks |
| `beat` | Celery beat: schedules periodic `poll_all` on a timer | Always if you use scheduled polling |
| `worker-beat` | Worker and beat in one process | Tiny demos only (not preferred in prod) |
| `consumer` | Reads Kafka / RabbitMQ / SQS event transports | Only if you use those transports |

Examples:

```bash
# API (default, same as omitting the role)
docker run ... your-registry/openg2p-connector-service:latest
docker run ... your-registry/openg2p-connector-service:latest api

# Background jobs
docker run ... your-registry/openg2p-connector-service:latest worker
docker run ... your-registry/openg2p-connector-service:latest beat
```

In Kubernetes, set the Deployment `args` to that role, for example
`args: ["worker"]`. Same image for every Deployment.

## Recommended production topology

For normal polling + webhook setups, run **three** Deployments / containers
from the same image:

| Workload name | Container args | Job |
|---------------|----------------|-----|
| `connector-api` | `["api"]` or omit | Serves HTTP |
| `connector-worker` | `["worker"]` | Executes the jobs |
| `connector-beat` | `["beat"]` | Fires the poll schedule |

Add a fourth only when you use event buses:

| Workload name | Container args | Job |
|---------------|----------------|-----|
| `connector-consumer` | `["consumer"]` | Kafka / RabbitMQ / SQS intake |

Do **not** run `consumer` for ODK / REST polling or WebSub webhooks alone.

Small environments: you may run one `worker-beat` instead of separate
`worker` + `beat`. Prefer separate `worker` and `beat` in production so you
can scale and restart them independently.

## Required infrastructure

The connector expects these external services:

- PostgreSQL for the connector's own metadata and run tables
- Redis for Celery broker/result backend
- OpenG2P Registry Partner API

Optional integrations:

- Master data DB and registry DB DSNs for UI dropdown metadata
- Kafka, RabbitMQ, or AWS SQS when event transports are enabled

## Required environment variables

Use `deploy.env.example` as the starting point.

The minimum required values in most deployments are:

```env
CONNECTOR_DB_DRIVER=postgresql+asyncpg
CONNECTOR_DB_HOSTNAME=postgres
CONNECTOR_DB_PORT=5432
CONNECTOR_DB_USERNAME=connector
CONNECTOR_DB_PASSWORD=change-me
CONNECTOR_DB_DBNAME=connector

CONNECTOR_PARTNER_INGEST_BASE_URL=http://registry-partner-api:8002

CONNECTOR_CELERY_BROKER_URL=redis://redis:6379/1
CONNECTOR_CELERY_RESULT_BACKEND=redis://redis:6379/1
```

Important note:

- `CONNECTOR_PARTNER_INGEST_BASE_URL` must be the Partner API base URL only.
  Do not append `/partner/ingest_data`; the connector appends that path itself.

Recommended production defaults:

```env
CONNECTOR_LOG_LEVEL=INFO
CONNECTOR_STORE_RUN_PAYLOADS=false
CONNECTOR_STRICT_INCREMENTAL=true
CONNECTOR_FULL_SCAN_ON_INCREMENTAL_UNSUPPORTED=false
```

## Docker run examples

API:

```bash
docker run -d \
  --name connector-api \
  --env-file deploy.env \
  -p 8050:8050 \
  your-registry/openg2p-connector-service:latest
```

Worker:

```bash
docker run -d \
  --name connector-worker \
  --env-file deploy.env \
  your-registry/openg2p-connector-service:latest \
  worker
```

Beat:

```bash
docker run -d \
  --name connector-beat \
  --env-file deploy.env \
  your-registry/openg2p-connector-service:latest \
  beat
```

Event consumer:

```bash
docker run -d \
  --name connector-consumer \
  --env-file deploy.env \
  your-registry/openg2p-connector-service:latest \
  consumer
```

## Kubernetes / platform mapping

Map the same image to separate workloads:

- Deployment `connector-api` with container args omitted or `["api"]`
- Deployment `connector-worker` with args `["worker"]`
- Deployment `connector-beat` with args `["beat"]`
- Deployment `connector-consumer` with args `["consumer"]` when needed

Expose only the API workload via a Service.

## Health checks

For the API container:

- liveness: `GET /health`
- readiness: `GET /health/ready`

Suggested probe target:

```text
http://<pod-or-service>:8050/health/ready
```

Worker, beat, and consumer roles do not expose HTTP endpoints. Treat them as
background workers and monitor process health plus logs / queue depth.

## Startup behavior

On API and worker startup, the connector automatically:

- creates missing connector tables
- applies the lightweight in-process DB migrations in `db_migrations.py`

No separate migration job is required for the current implementation.

## Notes for ODK polling

Per-connector ODK settings belong in connector records stored in the connector
database, usually in:

- `source_config_json`
- `auth_secret_json`

The deprecated global `CONNECTOR_ODK_CENTRAL_*` env vars are still supported as
fallbacks, but new deployments should leave them blank and use per-connector
configuration instead.
