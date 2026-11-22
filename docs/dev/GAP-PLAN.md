# Brench implementation plan and loophole register

This plan records the remaining work after reviewing the current checkout. It
builds on `IMPLEMENTATION-AUDIT.md`; it does not replace the earlier findings.

## Priority plan

| Order | Work | Acceptance |
|---|---|---|
| P0 | Persist runs and trace evidence in PostgreSQL 16, with schema/migrations, health checks, and a documented local workflow. Keep only PostgreSQL in Compose; run the Python app on the host. | A fresh Compose database accepts a run; restarting the DB preserves it; API/report/replay/import all use the same store. |
| P0 | Close run lifecycle and evidence integrity gaps: atomic run creation, no partial visible run, non-destructive retries, secret-safe task snapshots, bounded resource use. | Duplicate IDs and interrupted runs cannot overwrite or masquerade as complete evidence; regression coverage pins behavior. |
| P1 | Replace the home-grown UI primitive layer with standard shadcn/ui patterns and Radix-backed accessible controls; make the workspace calm, legible, responsive, and evidence-first. | Components follow shadcn conventions and keyboard/focus states; no novelty gradients, oversized display type, or decorative dashboard chrome. |
| P1 | Build a proper Brench landing page that explains the evaluation flow, evidence model, limits, and local workspace entry point. | Landing page is useful without a database/demo run and never presents fixture data as live model results. |
| P1 | Align README, walkthrough, phase plan, decision record, and dev audit with Brench, PostgreSQL, exact startup commands, current paths, and actual behavior. | A clean checkout can follow one canonical setup path; no stale “file store” or old product naming claims remain. |
| P2 | Harden HTTP/API operational behavior: explicit content-type/body limits, structured errors, request timeouts, safe static paths, and concurrency behavior. | Malformed requests return controlled errors; concurrent writes do not corrupt or duplicate a run. |
| P2 | Expand coverage around grader invariants, import/replay fidelity, security redaction, task schemas, and persistence failure recovery. | Tests exercise adversarial inputs and data-store restart/failure cases. |

## Loophole register

| ID | Risk | Priority | Required resolution |
|---|---|---|---|
| GAP-01 | The UI primitives are custom CSS/React wrappers described as “shadcn-style”; they do not use the standard shadcn/Radix component implementation. | Medium | Adopt standard shadcn component patterns and accessible Radix primitives where interaction requires them. |
| GAP-02 | Runs are still persisted as directories and JSON files. There is no PostgreSQL configuration, schema, migration, or data access layer. | High | Implement PostgreSQL-backed run/task/evidence persistence and make every CLI/API path use it. |
| GAP-03 | The newly added atomic file writer protects individual files, but a multi-task run becomes visible before all tasks and metadata are committed. A crash can leave a partial run. | High | Use a database transaction for run creation and task evidence; define whether incomplete runs are retained as explicit incomplete records. |
| GAP-04 | `task.yaml` is deliberately copied byte-for-byte and bypasses redaction. Secrets included in caller-provided context can be persisted. | High | Preserve replay semantics while encrypting or excluding secret-bearing input fields; document the contract. |
| GAP-05 | Timeout abandons a daemon thread. An adapter may keep consuming resources or performing external work after the harness returns `NONE`. | Medium | Keep adapters local-only until killable process isolation exists; add resource and cancellation boundaries before live adapters. |
| GAP-06 | The task validator supports a deliberately narrow context/tool/tripwire vocabulary. Unsupported conditions are rejected, but unknown context types can be exposed as brief text. | Medium | Enforce explicit context handling and add fixtures for every accepted type and unknown-type behavior. |
| GAP-07 | API is unauthenticated and loopback-only by default. A caller can request regrading, which creates additional persisted evidence. | Medium | Keep loopback binding; add request-size/content-type validation and document local trust boundary. |
| GAP-08 | Documentation contains conflicting persistence claims: implementation audit says files, while the product requirement now calls for PostgreSQL. | High | Update all onboarding and demo docs after the database path is implemented; identify migration/backup behavior. |
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
- Persistent run evidence belongs in PostgreSQL; a Compose database alone does
  not satisfy the persistence requirement.
