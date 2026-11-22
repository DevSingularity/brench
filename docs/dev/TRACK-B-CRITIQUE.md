# Track B implementation critique and product flow

**Reviewed:** 22 November 2026  
**Scope:** Current checkout against `reference/legacy-candidate-pack/TRACK-B-full-stack.md` v1.2 and `SHARED-CONTRACT.md` v1.1.  
**Purpose:** Record what is implemented, what is missing or misleading, and the product flow needed to make adding a task file and running the complete pipeline understandable in the UI.

> **Review baseline and follow-up:** The critique below records the gaps found before the browser pipeline was implemented. The “Implementation follow-up” section at the end records the work added in the current pass and remaining limitations.

## Summary

The core offline harness is substantially present: tasks are validated, a deterministic fixture agent is dispatched through mock tools, traces and verdicts are saved, graders can be swapped on saved traces, and the React results UI can inspect a saved run. This is a credible evidence viewer and CLI demo.

At the initial review baseline, the browser was a **read-only saved-run viewer**. The product changes made in this pass close the main journey gap: a guided file intake and validation flow now starts a fixture run, streams pipeline evidence, opens a dedicated page for each saved run, and offers grader replay. Historical findings below are labeled as baseline findings; remaining gaps are summarized at the end.

There is also a material persistence discrepancy: `docker-compose.yml` starts PostgreSQL and `README.md` tells users to start it, but the active store in `harness/persistence/store.py` persists runs as directories and JSON files. No database connection, schema, migration, or database repository appears in the run, report, import, replay, or HTTP paths. The running product should not imply PostgreSQL backs its evidence until that integration exists.

## Track B requirement assessment

| Track B requirement | Current implementation | Assessment |
|---|---|---|
| Load supplied YAML pair; validate with clear errors | `harness/core/tasks.py`, contract validator, and CLI `validate-tasks` / `_load` | **Mostly met in CLI.** No browser upload or validation flow. Validation feedback is not presented as a task-authoring experience. |
| Run scripted fixture against controlled mock tools | `harness/core/runner.py`, `harness/core/agents.py`, mock environment | **Met for offline fixture execution.** CLI is the only run entry point. |
| Check permissions and tripwires before execution; retain blocked attempts | Runner preflight and trajectory records; UI highlights blocked tool results | **Largely met.** Keep the distinction clear between tool calls blocked by the simulator and external side effects; no live adapter is part of this path. |
| Step budget, timeout, terminal `NONE` for unfinished runs | `run_task` handles timeout, step budget, model error and abort with terminal `NONE` | **Met with a boundary limitation.** A timed-out daemon thread cannot be killed and can keep computing; document this and do not run untrusted/live agents in-process. |
| Keep grading metadata out of agent observations | `initial_observation` exposes role/grant/brief/history and withholds grading fields | **Met by design.** Preserve this invariant as upload, run configuration and adapters are added. |
| One documented offline command saves evidence and starts UI | `python -m harness demo` runs, persists and serves the UI | **Met from CLI, with repeat-run behavior improved in `batch.py`.** It runs a preset collection of fixture agents/tasks, rather than letting a user build a run in the UI. |
| Persist task/run identity, full trace, verdict and model/seed metadata | File store writes snapshots, JSONL traces, verdicts and metadata | **Evidence exists on disk.** Persistence is filesystem-backed despite PostgreSQL setup claims. Atomicity is per-file; a multi-task run may be visible before all evidence and metadata are committed. |
| Redact secrets from raw requests/responses | Store redacts credential-like keys/patterns in trace and metadata writes | **Partial.** There is no live raw request/response integration; imported evidence is normalized. Task YAML snapshots are written byte-for-byte and can retain secrets placed in task context. |
| Pluggable `grade(...)` and replay without agent/model rerun | `harness/evaluation/graders/`, `replay.py`, replay CLI | **Met in core.** The UI offers no re-grade action, and replay creates another saved run rather than a visible pipeline operation. |
| Results UI run list, category × domain matrix, stakes breakdown, distinct outcomes | `report.py` and `ui/src/App.jsx` | **Mostly met for an individual selected run.** Run selector exists; matrix and stakes are shown; unauthorised and over-escalation are distinct. The UI does not give a useful run-management page or expose every outcome breakdown prominently. |
| Cell → task → full trace, verdict and notes | Matrix filters tasks; task panel shows expected/declared decision, rationale, grader notes and trace | **Mostly met.** Trace evidence is inspectable after a run. UI evidence context should be explicit about trusted task/oracle fields vs what the agent observed. |
| Tests, organiser fixtures, setup, known limits | `tests/`, vendored contract validation, README and walkthrough | **Partially evidenced.** The suite and documentation cover many requirements, but this review did not execute tests. Several audit findings remain open and the PostgreSQL statements are inaccurate for current code. |

## What is already working well

- **A real execution loop exists.** The runner gives an allow-listed observation, records tool calls/results, checks tripwires before mock execution and emits a terminal record.
- **Evidence is a first-class output.** Saved task snapshot, ordered trajectory, verdict and metadata are available to reports and the UI.
- **Grading is separable from the agent.** The grader registry and replay path support grading saved traces with another grader.
- **Correct final labels do not erase tripwires.** The reports count unauthorised actions separately from over-escalation and label matches.
- **Fixture labeling is explicit.** Runs use fixture metadata and the UI labels the selected fixture run.
- **Empty matrix cells are shown as unrun.** This avoids presenting missing task coverage as a zero score.
- **The UI can inspect full traces.** Blocked attempts are visibly marked, with arguments and results available for review.
- **The app has a documented offline route.** The React bundle is committed and the fixture run needs no model key.

## Major product and implementation gaps

### P0 — No user-facing pipeline entry point

The UI only calls `GET /api/runs`, `GET /api/runs/<id>`, `GET /api/runs/<id>/tasks/<tid>`, and `POST .../regrade`. The re-grade endpoint is not surfaced in `App.jsx`. There are no task discovery, upload, validation, run creation, run status, cancellation, or pipeline event APIs. The only way to execute is `python -m harness demo` or `python -m harness run` in a terminal.

**Impact:** A user cannot take the most natural product action—add a task file and run it—from the product. The UI does not demonstrate task loading, dispatch, tripwire detection, trace persistence, or grading as a live flow. New users must know the repository and CLI before they can produce the evidence the UI is designed to show.

### P0 — Pipeline lifecycle is invisible

Batch execution runs synchronously in the CLI. No persisted lifecycle status exists (`queued`, `validating`, `running`, `grading`, `completed`, `failed`, `cancelled`), and no incremental event stream or progress endpoint exists. There is no way to distinguish a long-running task from a frozen page or inspect partial traces before completion.

**Impact:** Adding a browser-triggered run without lifecycle design would produce an opaque request and risk blocking the HTTP handler. Product presentation needs a visible, honest pipeline, including failure and incomplete-run states.

### P0 — Persistence documentation is ahead of implementation

`docker-compose.yml` starts PostgreSQL, but `harness/persistence/store.py` uses `Path`, JSON, JSONL, and atomic file writes. `batch.py`, `report.py`, `importer.py`, and `replay.py` call this file store. There is no database driver or migration path in the inspected runtime. The README currently instructs users to start the database and configure `DATABASE_URL`, which the active store does not consume.

**Impact:** Operators may believe evidence is database-backed when it is not. Reset, backup, recovery, deployment, and data durability expectations are unclear. Resolve the implementation or documentation mismatch before presenting database-backed persistence as a product capability.

### P1 — No supported file intake or validation preview

There is no task upload control, drag/drop target, file picker, task preview, YAML parse feedback, duplicate-ID handling, or “ready to run” state. CLI validation errors do not translate to actionable UI errors. The expected input is YAML, but the product does not define accepted file count, size, encoding, or whether a pair is required for one run.

**Impact:** Users cannot supply custom evaluation tasks without manually placing files in the repo and running CLI commands. Validation feedback arrives too late or outside the UI.

### P1 — The visible “pipeline” is static marketing content

The landing page describes task → run → review, and the workspace preview uses illustrative rows. The actual workspace has a results matrix and trace inspector but does not show pipeline stages or let the user initiate them. The preview is labeled “Illustrative sample,” which helps, but should not be mistaken for a live execution view.

**Impact:** The product promise and available actions differ. The user sees what the system could do, not how their own input moves through it.

### P1 — Run creation and re-grading are CLI-only

At baseline, the UI had a run selector but no new-run flow, configuration, dedicated run page, or replay action. The current UI replaces the selector with a workspace dashboard and links each table row to its own `#/runs/<run_id>` page. The wizard now covers task intake, contract review, run configuration and live pipeline progress. Re-grade is available from a source run and creates a linked replay without calling the agent again.

### P1 — Run list and result semantics need stronger framing

The results workspace is centered on one selected run; it has no searchable run history, creation timestamps in a table, source/type filters, status, comparison, or empty-state CTA to create a run. The outcome cells show only correctness plus one selected error count, although the report tracks `outcomes` and `other_errors`. Pair completeness is shown, but twin-pair consistency is not visibly reported.

**Impact:** Reviewers have to infer what is included and may miss wrong target, no decision, insufficient evidence, or other outcome classes. Small fixture samples also need an explicit exploratory-sample framing; counts should remain denominated and must not imply broad model performance.

### P1 — File-backed run writes can expose partial run state

The individual file writer is atomic, but `run_batch` creates the run directory before executing tasks and writes task evidence one item at a time. A crash can leave a partial run directory. The UI discovers a run by `meta.json`, which reduces visibility until metadata is written, but does not provide durable status or recovery for incomplete work. Treat incomplete runs as explicit evidence rather than silently absent or complete.

### P1 — Secret and trust boundary needs a product policy

`store.save_task_run` writes task snapshots without applying `redact`, unlike traces and metadata. A task context can therefore persist credentials supplied by an uploader. The future upload path must not execute arbitrary YAML constructs (the loader should remain safe), write user paths, or persist sensitive task content without explicit handling. Agent-visible content and grader-only fields should be visually distinguished in task inspection.

### P2 — Operational/audit risks remain

The existing `IMPLEMENTATION-AUDIT.md` and `GAP-PLAN.md` record unresolved items that matter for product reliability: timeout threads cannot be stopped; task snapshots can retain secrets; multi-task runs are not transactional; narrow tripwire/context vocabulary limits extension; the API is unauthenticated (so it should stay loopback-only); and custom UI primitives are not standard shadcn/Radix implementations. These do not invalidate the offline fixture flow, but should be reflected in implementation priorities and product claims.

### P2 — Documentation and assessment evidence need reconciliation

README, walkthrough, implementation audit, and gap plan must describe one actual storage path and one canonical startup sequence. This critique is a code/document review, not a test run; mark any contract behavior “verified” only after the corresponding tests or fixture validation have been run. Keep the missing 13:30 constraint-change card pending instead of inventing its contents.

## Proposed product flow: add a file, run, inspect everything

The primary action should be **New evaluation**. The flow below is the minimum product experience needed to turn the current evidence viewer into an end-to-end harness product.

### 1. Start from the workspace

Show a run history with clear statuses and a prominent **New evaluation** action. With no runs, show the same action beside a short explanation and an offline fixture option. Clearly label fixture runs, imported/manual traces, and any later live model runs.

### 2. Add task files

Provide a keyboard-accessible file picker and drag/drop zone for `.yaml` / `.yml`; allow multiple files to form a pair or suite. Show selected filenames, size, parse state, and remove/replace controls. Keep the supplied task set selectable without re-uploading. Document accepted encoding and file limits.

### 3. Validate before execution

Upload to a staging/validation endpoint and return structured diagnostics with file, task ID, field path, severity, and message. Show valid tasks and warnings; block run start for parse/schema errors. Surface duplicate IDs, incomplete pairs, unknown tripwire conditions, and unsupported context types. Let the user inspect the normalized task and make an explicit choice about whether warnings are acceptable.

The UI must not silently repair contract semantics. It should explain which task fields are agent-visible and which fields remain trusted grading metadata. Never use task ID/name to leak answer labels into the agent observation.

### 4. Configure the run

Offer only supported choices initially: fixture agent (with honest fixture labeling), grader, seed, maximum steps, timeout, and selected task set. Show the no-external-effects/offline guarantee for fixture execution. Display the run identity and immutable configuration before confirmation. Use a generated unique run ID by default and preserve prior evidence on retries.

### 5. Show the pipeline as it runs

Present an ordered stage rail with timestamps and status:

1. **Load tasks** — files accepted and task count.
2. **Validate contract** — pass/warning/failure count and diagnostics.
3. **Dispatch agent** — agent/model name and task currently running.
4. **Execute mock tools** — each call, permission result, tripwire check, mock result, and blocked-attempt badge.
5. **Persist trace** — saved trace identity and count; never imply it is saved before the durable write succeeds.
6. **Grade** — grader and version, verdict status.
7. **Complete** — summary counts and links to each task’s evidence.

Use a run/job API that returns a run ID immediately and exposes status plus ordered events (polling is sufficient for an offline local product; SSE can come later). Do not hold an HTTP request open while a batch executes. Persist partial traces and terminal `NONE` records on timeout, step-budget exhaustion, and agent errors. Show failed/aborted stages with a retry action that creates a new run or clearly resumes from a defined checkpoint; never overwrite prior evidence. Cancellation must have defined semantics, especially given the current daemon-thread timeout limitation.

### 6. Review results and evidence

On completion, open a run summary with model/agent kind, seed, grader/version, task count, run time and status. Show category × domain counts/denominators, stakes counts, pair completeness and consistency, and distinct outcome counts. Keep unauthorised attempts and over-escalation separate. Empty combinations must say **Not run**. Label small samples exploratory and do not show a single blended score as a substitute for outcome breakdowns.

Selecting an outcome or matrix cell filters tasks; selecting a task opens a split evidence view with:

- declared action vs expected action and explicit outcome;
- grader notes, evidence steps, escalation quality, seed and grader version;
- complete ordered trajectory, with blocked tool calls and tripwire details highlighted;
- the agent-visible observation alongside trusted task/oracle fields clearly marked as grader-only;
- simulator effects and run metadata where relevant.

### 7. Re-grade a saved trace

Offer **Re-grade with…** on a completed run. Explain that the saved trajectory is reused and the agent is not called. Create a new immutable replay run linked to its source, preserve the source verdict and trace, and show grader/version differences. Do not permit destination ID collision or silently overwrite evidence.

## Suggested API and lifecycle contract

This is an implementation direction, not a claim about current endpoints.

| Capability | Proposed endpoint/behavior |
|---|---|
| Discover built-in tasks and supported agents/graders | `GET /api/tasks`, `GET /api/agents`, existing `GET /api/graders` |
| Validate uploaded task files | `POST /api/task-files/validate` with multipart upload or bounded JSON content; return structured task summaries and diagnostics; do not execute or persist as a run |
| Start a run | `POST /api/runs` with validated staged task references and explicit config; return `202` + immutable run ID/status |
| Read lifecycle and progress | `GET /api/runs/<id>` includes lifecycle/config; `GET /api/runs/<id>/events` returns ordered pipeline events (polling first, SSE optional) |
| Inspect task evidence | Keep `GET /api/runs/<id>/tasks/<task-id>`; include trace, verdict and visibility-safe agent observation |
| Re-grade | Keep re-grade behavior but return linked replay identity; expose it in UI and never alter source evidence |

For an initial local product, run jobs in a bounded worker owned by the local server, persist each stage transition, cap upload size and task count, and bind only to loopback. If PostgreSQL is chosen as the system of record, route every CLI/API/report/replay/import code path through the same repository and migrations; otherwise remove the unused Compose/database instructions and describe the file store accurately. Do not claim that starting PostgreSQL makes file-based runs durable in PostgreSQL.

## Delivery priorities

1. **Resolve storage truth:** implement and test PostgreSQL-backed persistence end to end, or correct README/Compose instructions to reflect the file store. Decide transaction, recovery, backup and migration behavior.
2. **Add task intake and validation UI/API:** safely parse files, return field-level diagnostics, preview task and pair coverage, and block invalid runs.
3. **Add run creation and lifecycle:** asynchronous bounded execution, immutable config, explicit statuses/events, partial evidence and non-destructive retry behavior.
4. **Build the pipeline view:** stage rail plus task-level live trace, blocked attempt visibility, error/timeout states, and direct navigation to final evidence.
5. **Complete result review and replay actions:** full outcome distribution, pair consistency, run history metadata, and grader swap that clearly reuses saved traces.
6. **Close evidence/security gaps:** define task secret policy, upload bounds, API content type/body validation, loopback trust boundary, timeout isolation strategy, and atomic/transactional run completion.
7. **Reconcile docs and acceptance criteria:** one canonical setup command, accurate persistence story, limitations, file workflow, and verification evidence. Update the dev audit as findings close.

## Acceptance criteria for the requested product flow

- A user can add one or more task YAML files in the browser, see parse/schema errors by file and field, and preview the valid task set before running.
- Invalid files cannot start a run; warnings and incomplete pairs are explicit.
- A user can configure a supported fixture run and start it without opening a terminal or supplying an API key.
- The UI immediately identifies the run and shows each pipeline stage, task progress, tool call/result, tripwire decision, persistence step, and grader result.
- Timeouts, step exhaustion, model errors and harness errors produce inspectable partial evidence and a terminal `NONE` where the contract requires it.
- The completed run appears in history with honest source/model kind, seed, grader/version, task denominators, distinct outcome counts and links to full evidence.
- Re-grading is initiated in the UI, creates a linked replay, preserves the original trace/verdict, and makes clear no agent/model call was made.
- A repeated run or retry cannot destroy earlier evidence; incomplete runs are represented honestly.
- README claims match the actual persistence backend and clean setup works offline after dependencies are installed.

## Files reviewed

- `reference/legacy-candidate-pack/TRACK-B-full-stack.md`
- `reference/legacy-candidate-pack/SHARED-CONTRACT.md`
- `harness/core/tasks.py`, `harness/core/runner.py`, `harness/core/agents.py`
- `harness/persistence/batch.py`, `harness/persistence/store.py`, `harness/persistence/report.py`
- `harness/evaluation/importer.py`, `harness/evaluation/replay.py`, `harness/evaluation/graders/`
- `harness/web/server.py`, `harness/__main__.py`
- `ui/src/App.jsx`, `ui/src/App.css`, `ui/src/components/ui.jsx`
- `README.md`, `docs/dev/IMPLEMENTATION-AUDIT.md`, `docs/dev/GAP-PLAN.md`, `docs/plans/WALKTHROUGH.md`, `docker-compose.yml`

## Implementation follow-up

The browser workflow described above is now implemented in this worktree:

- **Task intake and validation:** the workspace has a YAML file picker and drop zone, selected-file management, validation results, task summaries and pair warnings. The server reuses `load_tasks` and bounds file count and combined size.
- **Task visibility preview:** validated tasks can expand to show the exact starting observation sent to the fixture and a separate, labeled view of grader-only fields. The completed inspector also exposes the parsed trusted task and exact saved YAML snapshot.
- **Run configuration:** users choose a scripted fixture agent, grader, seed, step budget and per-task timeout. The UI calls `POST /api/runs`; the local server validates the input and starts the run in a background thread.
- **Pipeline view:** `GET /api/jobs/<id>` exposes in-process job status and ordered events. The UI shows stage status, per-task progress, each trace record, grading, persistence and completion. Blocked attempts and tripwire hits are highlighted. Run metadata is written before execution and updated after each saved task, so a failed run remains visible with its partial evidence and failure status.
- **Complete evidence inspection:** the selected run shows provenance, status, expected/saved task counts, all contract outcome counts and pair consistency. Task drill-down includes declared/expected action, grader notes and diagnostics, complete trajectory, initial agent observation, trusted task spec, exact YAML, simulator effects and full run/task metadata.
- **Re-grading:** the existing replay endpoint is now available from the selected run’s results view. It creates another run from saved traces without calling the fixture agent, and the UI prevents replaying with the same grader or re-grading a replay.
- **Documentation:** README now describes browser run creation and accurately identifies file-backed evidence storage rather than claiming PostgreSQL persistence.

### Current API behind the flow

| Endpoint | Current behavior |
|---|---|
| `GET /api/agents` | Lists supported scripted agents and labels them as fixtures. |
| `POST /api/task-files/validate` | Accepts bounded JSON file names/content, validates with the shared task loader, and returns task summaries, warnings/errors, starting agent observations and a separate grader-only preview. |
| `POST /api/runs` | Revalidates the supplied files, validates run settings, creates a unique run, and returns `202` with a job ID. One active browser pipeline is allowed per server process. |
| `GET /api/jobs/<id>` | Returns in-memory status and ordered stage/task/trace events for polling. |
| `GET /api/runs`, `GET /api/runs/<id>`, `GET /api/runs/<id>/tasks/<task-id>` | Lists saved runs, aggregates their evidence, and returns full trace plus task, observation, verdict, exact YAML, and metadata. |
| `POST /api/runs/<id>/regrade` | Grades saved trajectories with a selected grader and returns the new replay run ID. |

The file content is sent again when a run starts; the server validates it again rather than trusting a prior browser validation response. Job/event history is not durable across a server restart, while run/task evidence is written incrementally to the file store.

The React production bundle builds successfully; Python modules compile, and automated tests were not run in this pass. Remaining limitations include in-memory job status/events (lost when the server exits), no cancellation or durable resume, one active browser pipeline per server process, no PostgreSQL integration, task snapshot content being stored as submitted, and the runner’s non-killable daemon-thread timeout boundary. Validation errors are readable but not yet returned as structured field-path diagnostics. The local API should remain loopback-only. Treat the new UI path as fixture-only; it does not add a live model adapter or an LLM judge.

