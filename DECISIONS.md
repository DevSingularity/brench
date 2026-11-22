# Engineering decisions

This document records the reasoning behind the current Brench implementation,
including where the choice is deliberately narrow and what evidence would cause
us to revisit it. It describes the current main-worktree behavior; the optional
PostgreSQL Compose service is not yet connected to application persistence.

## 1. Keep the evaluation contract small and explicit

**Decision.** Use validated YAML tasks and a JSONL trajectory with explicit
terminal decisions, tool calls, tool results, and termination reasons.

**Why.** A reviewer can inspect the authority grant, what the agent could see,
what it did, and why the grader assigned an outcome. A narrow contract also
makes deterministic fixtures, imports, and re-grading possible without binding
the core to a particular model vendor.

**Tradeoff.** External traces need normalization before they can be compared.
The importer accepts the published trajectory shape and action aliases; it is
not a general schema-mapping or provenance system. Validation proves structural
conformance, not that an external recorder captured every event faithfully.

**Revisit when.** Multiple real integrations require incompatible source
schemas. Add explicit versioned mapping profiles and preservation tests rather
than weakening the core contract or silently dropping fields.

## 2. Separate the runner, environment, and grader

**Decision.** The runner mediates an agent protocol, the mock environment
executes tools, and graders consume a completed trajectory plus trusted task
rules. Tripwire checks happen before simulated side effects.

**Why.** This boundary makes it possible to distinguish an attempted action
from its effect. A blocked payment attempt remains evidence of an authority
violation even if the agent later escalates correctly. The simulator is offline
and cannot reach external systems.

**Tradeoff.** The environment only models the tools and conditions implemented
in this repository. Supported tripwire expressions are intentionally limited;
they are not a general policy language or proof that a production tool is safe.

**Revisit when.** New tool classes or policy conditions are required. Add
contract tests for parsing, preflight, blocking, and recorded effects before
expanding the expression language.

## 3. Keep the reference grader and strict grader side by side

**Decision.** Preserve the adapted reference grader and expose the project
strict grader behind the same `grade(task, trajectory, ...)` interface.

**Why.** A reviewer can run both against identical evidence. The strict grader
recomputes tripwire hits from raw calls rather than trusting only trace flags,
normalizes message requirements, and accepts a role or named person for target
matching. The reference grader remains a useful compatibility baseline.

**Tradeoff.** The strict grader is not independent ground truth: it shares the
contract and condition evaluator with the runner. Deterministic grader
agreement does not establish correctness for unseen policies. Differences must
be explained by concrete cases, not presented as a universal quality ranking.

**Revisit when.** Grading logic grows beyond auditable rules or requires
independent evaluation. Version grader behavior, preserve inputs and outputs,
and add adjudicated cases before changing default selection.

## 4. Preserve evidence and make re-grading append-only

**Decision.** Store a task snapshot, trajectory, verdict, and metadata for each
completed task. Re-grading writes a new run linked to its source and copies the
task and trajectory bytes unchanged; evidence hashes are recorded in replay
metadata.

**Why.** A reviewer can compare grader outputs without paying for or rerunning
a model, and can verify that the replay used the same saved evidence. The source
run remains available for audit.

**Tradeoff.** Replays duplicate trace files, and filesystem storage does not
provide database transactions or tamper-proof evidence. Run metadata is updated
as work progresses; a crash can leave a partial run, which is marked failed or
interrupted when recovered. File permissions and backups remain operational
responsibilities.

**Revisit when.** Concurrent writers, larger traces, multi-user access, or
stronger durability requirements arrive. Adopt a transactional store with
explicit migration and recovery semantics while retaining immutable source
records and evidence hashes.

## 5. Use a local single-process web service for the demo

**Decision.** Serve the static React UI and JSON API from Python's standard
library HTTP server, default to loopback binding, and allow one active browser
pipeline per server process. The container binds internally to all interfaces,
while Compose publishes its port only on host loopback. Execute each fixture task in a child process with a hard
parent-enforced deadline.

**Why.** This keeps setup small, avoids an external service dependency, and
allows a hung fixture process to be terminated. Job events and retry inputs are
stored with local run data; retry creates a new run rather than mutating old
evidence.

**Tradeoff.** The service has no authentication, multi-user isolation, or
multi-process job coordination. Loopback binding reduces exposure but is not an
authentication boundary against local processes. Job state is not a durable
queue and active work is not resumed after a restart.

**Revisit when.** The app is exposed beyond a trusted local machine or needs
multiple workers. Add authentication, authorization, request protections,
shared durable job state, and operational monitoring before network exposure.

## 6. Keep PostgreSQL optional until the application has a verified adapter

**Decision.** Keep `docker-compose.yml` limited to a local PostgreSQL 16
service, while the current main-worktree app continues to use filesystem
persistence.

**Why.** A running database container is not itself an integration. Keeping
runtime claims aligned with the active storage implementation avoids implying
transaction, consistency, migration, or recovery guarantees the app does not
currently provide.

**Tradeoff.** The Compose database is not used by the UI or CLI and therefore
adds no persistence capability to this branch. The filesystem remains the
source of truth.

**Revisit when.** The adapter, schema migration path, transaction boundaries,
restart behavior, backup expectations, and database-backed tests are reviewed
and integrated. Update the architecture and operational docs at the same time.

## 7. Containerize the local service without making its API public

**Decision.** Build the React bundle and Python server into one runtime image,
store run data in a named volume, and publish the VPS port on loopback only.
Remote review uses SSH forwarding. Compose can start the service with one
`docker compose up -d --build` command.

**Why.** The app has no authentication and its current API is designed for
trusted local use. A loopback-only host mapping gives a VPS deployment path
without silently making the API reachable from the internet. A named volume
keeps evidence outside the disposable container filesystem.

**Tradeoff.** Remote users need SSH access and a tunnel. This is not a public
multi-user deployment, and the named volume still needs a backup strategy.
The PostgreSQL profile is not connected to the app, so the container uses its
filesystem store.

**Revisit when.** Public browser access is required. Put an authenticated TLS
proxy in front of the service, review request/session protections, and integrate
and validate the database adapter before claiming database-backed persistence.

## 8. Keep scores decomposed and fixtures honestly labeled

**Decision.** Report counts, denominators, action match, unauthorized action,
over-escalation, other outcomes, pair consistency, and grader diagnostics
separately. Label fixture runs as scripted and `oracle` as a harness sanity
check.

**Why.** A single aggregate score can hide materially different failure modes.
Fixtures are useful for checking the pipeline and specific policy cases, but
they do not measure general model behavior.

**Tradeoff.** The UI presents more detail than a one-number leaderboard and
requires the reviewer to interpret each outcome in the context of its task.
Pair consistency is a narrow diagnostic, not a statistical measure.

**Revisit when.** A real evaluation set has calibrated labels and a stated
measurement objective. Add aggregate metrics only with explicit definitions,
uncertainty, coverage, and limits.

## Verification and least-trusted evidence

The repository test suite covers contract validation, simulated execution,
grading, persistence, replay, and API behavior. The most valuable manual
invariant is that a replay preserves the source task and trajectory bytes while
only grader output and replay metadata change.

Imported traces are the evidence I trust least. Their origin, completeness, and
normalization are controlled by the caller. Brench can validate and grade the
records it receives; it cannot establish that an external system logged every
relevant event or that imported observations are authentic.
