# Brench implementation plan and loophole register

This plan is a backlog snapshot; completed rows below are retained for history,
not asserted as open defects. Evidence storage is file-backed today. PostgreSQL
is a separate architecture decision, not a prerequisite for the local Track B
fixture flow.

The P0 database row (GAP-02, GAP-03, GAP-08) has a full design, schema, call-site
inventory, test strategy and time-boxed schedule in
`docs/plans/DB-PERSISTENCE.md`. This register stays the priority order; that
document is the implementation plan for it.

## Priority plan

| Order | Work | Acceptance |
|---|---|---|
| P0 | Decide whether PostgreSQL is required for the final deployment. Current Track B flow uses the local file store; do not describe the optional Compose database as the system of record. | Architecture and README agree; if PostgreSQL is selected, route all paths through it and add migrations/transactions before claiming completion. |
| P1 | Close remaining evidence and secret policy gaps: broaden credential detection to CLI/import inputs, document local file retention, and add adversarial regression coverage. Multi-task runs remain explicit partial runs, not transactions. | Browser uploads reject common secret fields/tokens; interrupted runs retain status and completed task evidence; risks are stated honestly. |
| P1 | Replace the home-grown UI primitive layer with standard shadcn/ui patterns and Radix-backed accessible controls; make the workspace calm, legible, responsive, and evidence-first. | Components follow shadcn conventions and keyboard/focus states; no novelty gradients, oversized display type, or decorative dashboard chrome. |
| P1 | Build a proper Brench landing page that explains the evaluation flow, evidence model, limits, and local workspace entry point. | Landing page is useful without a database/demo run and never presents fixture data as live model results. |
| P1 | Align README, walkthrough, phase plan, decision record, and dev audit with Brench, PostgreSQL, exact startup commands, current paths, and actual behavior. | A clean checkout can follow one canonical setup path; no stale “file store” or old product naming claims remain. |
| P2 | Continue HTTP/API hardening: content type, body limits, structured task diagnostics, upload caps, loopback trust and single-active-job concurrency are implemented; add regression coverage and request/read timeouts. | Malformed/oversized requests return controlled errors and concurrency does not corrupt evidence. |
| P2 | Expand coverage around grader invariants, import/replay fidelity, security redaction, task schemas, and persistence failure recovery. | Tests exercise adversarial inputs and data-store restart/failure cases. |

## Loophole register

| ID | Risk | Priority | Required resolution |
|---|---|---|---|
| GAP-01 | The UI primitives are custom CSS/React wrappers described as “shadcn-style”; they do not use the standard shadcn/Radix component implementation. | Medium | Adopt standard shadcn component patterns and accessible Radix primitives where interaction requires them. |
| GAP-02 | Runs are still persisted as directories and JSON files. There is no PostgreSQL configuration, schema, migration, or data access layer. | High | Implement PostgreSQL-backed run/task/evidence persistence and make every CLI/API path use it. |
| GAP-03 | Multi-task runs are not all-or-nothing transactions. Completed task evidence is intentionally retained and the run is marked partial/interrupted after failure. | Medium | Keep this contract explicit; use PostgreSQL transactions only if the product selects a database-backed all-or-nothing model. |
| GAP-04 | Common credential fields/tokens are rejected by the shared task loader on browser, CLI and importer paths, but novel secret formats are not comprehensively detected. | Low | Keep all task sources secret-free; broaden detection or offer a reviewed redaction policy without changing replay semantics. |
| GAP-05 | Fixture tasks are isolated in killable child processes; cancellation is cooperative between tasks. | Low | Keep live adapters out of scope until their side effects and cancellation semantics are defined. |
| GAP-06 | The task validator supports a deliberately narrow context/tool/tripwire vocabulary. Unsupported conditions are rejected, but unknown context types can be exposed as brief text. | Medium | Enforce explicit context handling and add fixtures for every accepted type and unknown-type behavior. |
| GAP-07 | API is unauthenticated and loopback-only by default. | Medium | Keep loopback binding; JSON content type and body bounds are enforced. Do not expose without authentication. |
| GAP-08 | Older docs implied PostgreSQL was required/active while the app uses files. | Medium | README and audit now identify the optional container and file-backed evidence accurately; choose a DB architecture only if the deployment requires it. |
| GAP-09 | Landing page preview currently mixes hard-coded sample rows with a live-selected run summary, so figures can look like actual run output. | Medium | Use fully labeled static sample data or render actual rows from the selected run, never a mixture. |
| GAP-10 | The five visual reference attachments were not available in the checkout/context provided to this pass. | Low | Revisit visual details when references can be inspected; current direction uses restrained, standard shadcn conventions. |

## Proposed delivery sequence

1. Database contract and schema: define run, task snapshot, verdict, metadata,
   and ordered trace records; add idempotent migration and Compose health check.
2. Store adapter: route batch, import, replay, report, and HTTP reads through one
   persistence interface; use transactions and uniqueness constraints.
3. Evidence/security: define secret-bearing task input policy, transaction/error
   behavior, and tests for duplicate IDs, retries, restarts, and partial writes.
4. UI foundation: install/use shadcn conventions, replace non-semantic controls,
   and restyle overview and trace review.
5. Landing page and content: explain product, process, limits, and local setup;
   remove mixed static/live preview data.
6. Documentation and release checklist: refresh README, walkthrough, decisions,
   audit, startup steps, and backup/reset instructions; verify from a clean DB.

## Current-pass decisions

- Product name: **Brench**.
- Database image: **`postgres:16-alpine`**.
- Docker Compose owns the database only. The Python API/UI runs as a host process.
- Current persisted evidence belongs in the local file store; the optional
  Compose PostgreSQL service is unused by the harness.
