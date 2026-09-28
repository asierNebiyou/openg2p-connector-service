---
title: "OpenG2P Connector Service"
subtitle: "Design specification"
author: "OpenG2P"
date: "2026"
---

# OpenG2P Connector Service

Design specification for the integration layer between external data sources and the OpenG2P Registry.

### Document control

| Field | Value |
| ----- | ----- |
| Document type | Design specification |
| Product | OpenG2P Connector Service |
| Version | 1.3 |

---

## 1. Purpose

Registry data rarely originates in the registry. It comes from household survey platforms, partner ministries, agency systems, and other registries that already hold information about the people a programme serves. The connector is the component that brings that data in.

It accepts data from an external system, converts each record into the shape the registry expects, and delivers it to the registry Partner API, where it becomes a change request and enters the normal verification and approval workflow. The registry remains the authority on what is accepted. The connector's job is to get data to its door in a form it can act on, at a rate it can absorb, and to keep an accurate account of what happened to every record along the way.

Each integration is set up as a **pipeline**. A pipeline describes one source: how its data arrives, how the connector authenticates to it, how each record is reshaped, which partner the data is attributed to, and which register it belongs in. Operators create and adjust pipelines through the Connector Admin UI. Adding a source does not require a code change or a redeployment.

## 2. Scope

The connector is responsible for:

- accepting data over the supported transports and verifying that it came from a trusted sender
- keeping an unaltered copy of everything it receives
- breaking a payload into the individual records it contains and tracking each one separately
- reshaping records into the registry's format and, where configured, validating them before delivery
- sending records to the registry in controlled batches and recording the outcome
- retrying what can be retried and holding the rest for an operator to review

The connector does not decide whether a record is correct, does not deduplicate against registry contents, and does not approve anything. Those are registry responsibilities and happen after delivery. The connector also does not act as a long-term store of registry data; the copies it keeps exist to support tracing, retry, and replay.

## 3. Architecture

![Figure 1. Connector Service architecture](./images/diagram-01-architecture.png)

**Figure 1.** Component layout. Data reaches the connector by push or by fetch. Partner signatures are checked on the way in; the connector signs batches on the way out to the registry. Everything received is written to the connector database. The push worker reads from that database and delivers records to the registry.

| Component | Responsibility |
| --------- | -------------- |
| Connector Admin UI | Web application where operators create pipelines, adjust configuration, and monitor activity. |
| Service API | Receives pushed payloads after partner key validation, serves the Admin UI, and exposes pipeline and monitoring endpoints. |
| Fetch worker | Reads from sources that have to be asked, and writes what it collects to the database. |
| Push worker | Reads records waiting in the database, signs each batch with the connector key, and sends it to the registry. |
| Job scheduler | Starts both workers at their configured intervals. |
| Connector database | Holds pipeline configuration, received payloads, records and their state, and run history. |
| Task queue | Holds short job messages such as "fetch this pipeline now" or "send the next batch". A worker takes the next job whenever it is free. |

Everything that receives data writes to the connector database: the Service API for pushed payloads, and the fetch worker for anything it collects. The database is the single place where data waits, which is what allows receiving and sending to run at their own speeds.

The database and the task queue hold different things, and it is worth being precise about the difference. The database holds the data itself: payloads, records, and their state. The task queue holds nothing but instructions, each one a few words telling a worker to go and do a piece of work. A job message says which pipeline to act on; the worker that picks it up reads the actual data from the database.

The queue exists so that the scheduler does not have to know anything about the workers. It posts a job and moves on. Whichever worker instance is free takes it, which is what makes it possible to run several of them at once, restart one without losing work, and add more when volume grows.

## 4. Background workers

Two workers do the background work. Both are started by the job scheduler and take their jobs from the task queue, and they are deliberately kept separate.

| Worker | Started by | What it does |
| ------ | ---------- | ------------ |
| Fetch worker | The scheduler, at each pipeline's interval | Reads from a configured source and writes what it collects into the database as records. It never contacts the registry. |
| Push worker | The scheduler, at its own interval | Takes records waiting in the database, groups them into a batch, and sends the batch to the registry. It never contacts a source. |

Keeping them apart matters in both directions. The fetch worker keeps collecting on its interval whether or not the registry is reachable, so a registry outage delays delivery but never causes a source to be missed. The push worker sets the pace of delivery on its own terms, so a large import arriving at once does not turn into a burst of traffic at the registry.

Neither worker is called directly. When a pipeline's fetch interval comes round, the scheduler posts a job to the task queue saying that pipeline is due; a free fetch worker takes the job, reads the pipeline's configuration from the database, and does the work. The push worker is started the same way. Because both take their work from the same queue, either can be scaled on its own: a deployment pulling from many sources runs more fetch workers, one with a delivery backlog runs more push workers, and nothing else has to change.

## 5. Pipelines

A pipeline is the unit of configuration. Everything the connector needs to handle one source is held on the pipeline record.

| Setting | Description |
| ------- | ----------- |
| Name | Label shown in the Admin UI. |
| Platform | The kind of system the data comes from. |
| Transport | How data arrives: pushed to a URL, or fetched on a schedule. |
| Authentication | How the connector authenticates to the source, and the secrets it uses. |
| Source configuration | Connection details for the source, such as base address, project, form, and page size. |
| Fetch cursor | For scheduled fetch: which field marks progress, and whether progress is by time or by sequence. |
| Timeouts | How long the connector waits when talking to the source, and how long it waits when delivering to the registry. Set per pipeline so a slow source does not share the same budget as a fast one. |
| Sender | The partner the data is attributed to. Must match a partner registered with the registry. |
| Target register | The register the records are delivered into. |
| Mapping expression | Reshapes each record before delivery. Left empty, the record is delivered as received. |
| Validation schema | Optional schema each mapped record is checked against before delivery. |
| Fetch interval | How often the fetch worker reads from the source. |
| Batch size | How many records the push worker sends to the registry in one call. |
| Enabled and paused | Control whether the pipeline accepts data and whether processing is running. |

Pausing a pipeline stops processing without discarding its configuration or its history, which makes it a safe way to hold a source while a mapping or a credential is corrected.

## 6. How data arrives

Two transports cover the ways external systems make data available.

| Transport | Pattern | Description |
| --------- | ------- | ----------- |
| Webhook | Push | The source posts to a connector address reserved for that pipeline. The partner's signature is validated before the payload is accepted. |
| Scheduled fetch | Pull | The fetch worker reads from the source at a set interval, picking up only what is new since the last run. |

Pushed payloads reach a pipeline either by its identifier or by a readable slug, so an external system can be given a stable address that does not expose internal identifiers.

## 7. Authentication and partner trust

Trust runs in both directions: the connector must know that a push really came from the partner, and the registry must be able to know that a delivery really came from the connector.

**Authenticating to a source.** Pipelines that read from a source hold the credentials for it. The supported methods cover the cases found across partner systems.

| Method | Used for |
| ------ | -------- |
| None | Open endpoints. |
| Static token | Sources issuing a fixed bearer token. |
| Session | Sources that exchange a user name and password for a session token. |
| OAuth2 client credentials | Sources behind a standard client credentials flow. |
| OAuth2 password | Sources that require a user grant. |

**Verifying partners on the way in.** Anything pushed to the connector is verified before it is accepted. The preferred method is a digital signature from the partner: the connector obtains the partner's public key (published by the partner, or held on the pipeline) and checks that the signature matches the body that arrived. Shared secrets remain available for simpler sources that cannot sign. A payload that fails verification is rejected at the edge and never enters processing.

**Identifying the connector on the way out.** When the connector delivers a batch to the registry, it signs the request with the connector's own private key. The matching public key is what the registry uses to confirm the delivery came from this connector. Signing is a connector responsibility; whether a given registry deployment enforces that check is a registry-side policy.

Secrets are write-only. Once saved they are used but never displayed again, and leaving a secret field empty while editing a pipeline keeps the stored value rather than clearing it.

## 8. Receiving and storing

Receiving is kept short. Storing the payload and breaking it into records is quick work, so it happens as the payload comes in, and the source gets its acknowledgement as soon as the records are safely written. What the source does not wait for is delivery, which the push worker handles later on its own schedule.

![Figure 2. Receiving, storing, and delivering a payload](./images/diagram-02-processing.png)

**Figure 2.** A payload is accepted only after the partner key is validated, then stored, broken into records, and held until the push worker collects the next batch. Each batch is signed with the connector key before it is delivered to the registry.

**Receipt.** The transport confirms the payload came from the expected sender by validating the partner's key, then hands it on. Nothing else is interpreted at this point.

**Storage.** The payload is written exactly as it arrived and given a reference. Because the copy is stored before anything is changed, the original is always available for tracing or for replay after a mapping correction.

**Splitting into records.** A payload is rarely one thing. A survey export or a partner push commonly carries many people in a single body, and the registry works in terms of individual records. The connector therefore breaks the payload into the records it contains, one per person or entry, and stores each one separately with a reference back to the payload it came from.

Each record then carries its own state, its own attempt count, and its own outcome. That is what allows a problem with one record to be resolved on its own, without holding back the rest of the payload it arrived in, and it is what gives the push worker something countable to build batches from.

**Waiting.** Stored records wait in the database until the push worker collects them. Nothing is sent at the moment of receipt.

## 9. Fetching from a source

A pipeline whose source has to be asked rather than pushed is read by the fetch worker on the interval set for that pipeline.

![Figure 3. Scheduled fetch run](./images/diagram-03-scheduled-fetch.png)

**Figure 3.** A fetch run. The position of the last run is saved so each run collects only what is new, and what it collects joins the records waiting to be sent.

Each pipeline keeps the position of its last fetch. That position is driven by a **cursor**: the operator chooses which attribute on the source marks progress, and whether progress advances by time or by sequence. The next run resumes from that position, so runs stay incremental and a source is not asked for the same records repeatedly. An operator can reset the position to collect a source's history again, for instance after correcting a mapping that was wrong for earlier records.

What the fetch worker collects is stored the same way a pushed payload is stored, and from that point the two paths are identical. A record does not carry any trace of whether it was pushed or fetched once it is waiting to be sent.

## 10. Delivering to the registry

The push worker runs on its own interval. On each run it takes the records that are waiting, in the order they were received, up to the batch size configured for the pipeline, maps each one, and sends the batch to the registry Partner API in a single call.

**Batch size** is the main control over the load the connector places on the registry. Fifty records to a batch is a reasonable starting point. A smaller batch spreads the same work over more calls and keeps each one short; a larger batch clears a backlog faster at the cost of a heavier call. The setting belongs to the pipeline, so a source known to produce bulk imports can be tuned separately from one that trickles.

**Mapping** happens as the batch is assembled. The mapping expression on the pipeline reshapes each record into the registry's format, and where a validation schema is configured the mapped record is checked against it. A record that fails validation is held back and does not travel with the batch.

**The envelope** carries the sender and the target register from the pipeline, which is how the registry resolves the partner the data is attributed to.

**Trust on delivery.** Every delivery carries the connector's signature, as described under Authentication and partner trust, so the registry can treat the connector as a known sender when it chooses to enforce that check.

**The response** is recorded against every record in the batch: the correlation identifier the registry returns, and, where the registry reports a problem with a particular record, the error against that record. The correlation identifier is what links a record in the connector to the change request it became in the registry, and it is the first thing to reach for when someone asks what happened to a particular submission.

A rejection from the registry is kept distinct from a failure to reach it. The two call for different responses: one needs the data or the configuration corrected, the other usually only needs another attempt.

## 11. What the connector stores

| Held | Purpose |
| ---- | ------- |
| Pipeline configuration | Source, transport, authentication, mapping, sender, target register, intervals, timeouts, cursor, and batch size. |
| Received payloads | The unaltered copy of everything received, kept for tracing and replay. |
| Records | The individual records a payload was broken into, each with its state, attempt count, and outcome. |
| Run history | What was attempted, when, and how it ended, including the registry correlation identifier. |
| Duplicate keys | Keys of records already processed, so the same record is not sent twice. |
| Fetch positions | The point each fetched pipeline resumes from. |
| Dead letter entries | Records that exhausted their attempts, held with their error for review and replay. |

Storage of received payloads is configurable, since payloads may carry personal data and retention is a decision for the deployment rather than for the connector.

## 12. Failure handling

Failures are handled per record, even though delivery happens in batches.

A call that does not reach the registry leaves every record in that batch untouched and waiting. They are picked up again on the next run, so a registry outage costs time rather than data. A record the registry rejects is marked failed on its own; the rest of the batch is unaffected and stays delivered.

A record that fails is retried up to a configured number of attempts. One that exhausts them moves to the dead letter queue, where it waits with its error and its stored payload until an operator deals with it. Nothing is discarded silently.

| Category | Typical cause | Resolution |
| -------- | ------------- | ---------- |
| Transient | The source or the registry was briefly unreachable. | Replay. It usually succeeds. |
| Permanent | The registry rejected the record outright. | Correct the data, then replay. |
| Validation | The mapped record did not satisfy the configured schema. | Correct the mapping or the schema, then replay. |
| Configuration | The sender, target register, or mapping expression is wrong. | Correct the pipeline, then replay. |

Replay starts from the stored payload, so a record can be reprocessed after a fix without asking the source for it again.

## 13. Deployment

The connector ships as a single image and runs in one of several roles, chosen at start.

| Role | Runs |
| ---- | ---- |
| API | The Service API and the endpoints the Admin UI uses. |
| Fetch worker | Reads from sources. |
| Push worker | Sends signed batches to the registry. |
| Job scheduler | Starts both workers at their intervals. |

A production deployment runs the API, the two workers, and the scheduler as separate workloads. Both worker roles scale horizontally by running more instances, and they scale independently, since the pressure on one has nothing to do with the pressure on the other. Small environments can combine the workers and the scheduler in a single workload, at the cost of having to restart them together.

The connector depends on a relational database for its own data, a broker for the task queue, and network access to the registry Partner API.

The API role exposes liveness and readiness endpoints for health checks. The worker and scheduler roles serve no HTTP traffic and are monitored through process health, logs, and queue depth.

## 14. Operating the connector

The Admin UI is where day-to-day work happens. From it an operator can:

- create and edit pipelines, and pause or resume them
- see activity across every pipeline in one place, or narrow to a single one
- trigger a fetch immediately rather than waiting for the next scheduled run
- see how many records are waiting to be sent, which is the clearest sign of a backlog building
- adjust batch size, fetch interval, and timeouts when delivery needs to speed up or ease off
- set the fetch cursor so each run asks only for what is new
- inspect a failed record, read its error, and replay it
- reset a fetch position to collect a source's history again

The views are built around the questions that actually get asked: whether anything failed recently, what happened to one particular submission, and whether a source has gone quiet. Records carry both the connector's own identifiers and the registry correlation identifier, so a question can be followed from either end.

## 15. Related documentation

| Resource | Where |
| -------- | ----- |
| OpenG2P platform documentation | <https://docs.openg2p.org/> |
| OpenG2P Registry | <https://docs.openg2p.org/products/registry/registry> |
| Registry ingestion pipeline | <https://docs.openg2p.org/products/registry/registry/design/ingestion-pipeline> |
| Registry partner APIs | <https://docs.openg2p.org/products/registry/registry/design/partner-apis> |
