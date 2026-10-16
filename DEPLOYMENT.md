# Connector Deployment

Layout matches other OpenG2P Gen2 services (see
[master-data-service](https://github.com/OpenG2P/master-data-service)):

| Path | Purpose |
|------|---------|
| `docker/connector-service/` | Image Dockerfile + entrypoint |
| `deployments/charts/openg2p-connector/` | Helm chart (api / worker / beat) |
| `.gitlab-ci.yml` | GitLab packaging (image + chart publish) |
| `deploy.env.example` | Env template for local / manual runs |

## Files

- `docker/connector-service/Dockerfile`: builds the Connector image
- `docker/connector-service/docker-entrypoint.sh`: selects the runtime role
- `Dockerfile`: thin root wrapper (`docker build .` still works)
- `deploy.env.example`: deployment-oriented env template

## Build

Build from the repo root:

```bash
docker build -f docker/connector-service/Dockerfile \
  -t your-registry/openg2p-connector-service:latest .
```

Optional extras (if declared in `pyproject.toml`):

```bash
docker build -f docker/connector-service/Dockerfile \
  --build-arg CONNECTOR_PIP_EXTRAS=dev \
  -t your-registry/openg2p-connector-service:latest .
```

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

## Kubernetes / Helm

Use the chart under `deployments/charts/openg2p-connector`:

```bash
helm dependency update deployments/charts/openg2p-connector
helm upgrade --install connector deployments/charts/openg2p-connector \
  --namespace <ns> \
  --set global.connectorHostname=connector.example.org \
  --set global.partnerApiService=registry-partner-api \
  --set global.redisHost=commons-redis-master \
  --set image.tag=<tag>
```

The chart creates:

- Deployment `…-api` with args `["api"]` (+ Service, probes, optional HPA)
- Deployment `…-worker` with args `["worker"]`
- Deployment `…-beat` with args `["beat"]`
- Optional `…-consumer` / `…-ui` when enabled in values
- `postgres-init` subchart for the connector database
- Istio VirtualService when `istio.enabled` is true

Expose only the API (and UI if enabled) via Service / VirtualService.

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
