# Brench implementation audit

This is the shared running record of correctness, safety, packaging and UX gaps
found while reviewing the implementation. Keep it current when a finding is
fixed or a new one is discovered.

## Findings

| ID | Priority | Finding | Status |
|---|---|---|---|
| AUD-01 | High | USD tripwire parsing accepted non-finite values such as `NaN` and `-Infinity`. A comparison against `NaN` is false, which could let a malformed amount avoid a threshold trip. Oversized finite thresholds could also parse as infinity. | Fixed in current pass; add regression coverage. |
| AUD-02 | High | PyYAML's default mapping loader silently keeps the last duplicate key. A task could therefore be read differently by a human and by the harness, including replacement of policy or expected-action fields. | Fixed in current pass; add regression coverage. |
| AUD-03 | Medium | Escalation target checking used substring matching. A short name could match as part of a longer unrelated word. The grader also gave a positive reward for the `wrong_target` outcome. | Fixed in current pass; add regression coverage. |
| AUD-04 | High | Credential-key redaction recursed into list or mapping values instead of masking the value. For example, `{"tokens": ["secret"]}` could be written unchanged. | Fixed in current pass; add regression coverage. |
| AUD-05 | High | Regrading a run reused its default destination ID and deleted that directory before copying evidence. Repeating a replay could destroy a previous replay result. | Fixed in current pass; add regression coverage. |
| AUD-06 | High | Importing into an existing run could overwrite a task's evidence or mix traces from different models, graders or run metadata under one run ID. | Fixed in current pass; add regression coverage. |
| AUD-07 | Medium | The regrade endpoint capped the read length by truncating oversized request bodies; a negative `Content-Length` could request an unbounded read, and a non-object JSON value could raise an uncaught attribute error. | Fixed in current pass; add regression coverage. |
| AUD-08 | Medium | Agent-supplied tool-call arguments were retained by reference in the trajectory and simulator ledger. A later mutation could change saved evidence after the call was recorded. Agent `SystemExit`/other `BaseException` failures could escape the runner. | Fixed in current pass; add regression coverage. |
| AUD-09 | Medium | Batch execution could reset an existing `agent-seed` run ID. | Fixed: collisions receive a unique suffix; explicit ID collisions fail without overwriting. Regression coverage remains desirable. |
| AUD-10 | Medium | Timeout handling could abandon a daemon thread that kept consuming resources. | Fixed for fixture execution: each task runs in a killable child process with an outer hard deadline. Live adapters remain out of scope. |
| AUD-11 | Medium | A process interruption could leave partially written evidence. | Partially addressed: atomic per-file writes, verdict-last task commit markers, explicit run statuses, and recoverable partial runs. There is no all-or-nothing transaction across a batch. |
| AUD-12 | Medium | Task YAML snapshots preserve exact input and could retain credentials. | The shared task loader now rejects common credential fields and recognizable tokens across browser, CLI, and importer paths. This is a heuristic, not a complete secret scanner; keep inputs synthetic and secret-free. |
| AUD-13 | Low | The built-in task set has a narrow tool/context vocabulary and supports only two tripwire condition forms. Unknown tripwire syntax fails visibly; unknown context types become visible brief text unless the task supplies a tool mapping. | Known contract limitation; keep documented and add extensions only with fixtures. |
| AUD-14 | Low | The demo is deterministic fixture data. It does not demonstrate a live API adapter, a general raw-dataset mapper, or an LLM judge. | Intentional scope; label fixture runs accurately and describe import normalization limits. |
| AUD-15 | Pending external input | Track B constraint-change response. | Closed: `CHANGE-RESPONSE.md` includes implementation links and the acceptance scenario. |

## Additional audit notes

- The contract validator is vendored under `harness/core/`; runtime code does not
  import from the archived candidate pack.
- The UI is served from committed `ui/dist/` and does not require Node at demo
  time. Node is used only to rebuild the UI.
- The local API binds to loopback. It has no user authentication; keep it local
  and do not expose the server on a public interface.
- Upload and re-grade JSON endpoints enforce `application/json`, bounded bodies
  and object payloads. Task validation reports file/field issues and pair
  coverage; recognized credential fields/tokens are rejected on browser intake.
- The HTTP handler applies a 10-second socket read timeout and refuses non-loopback
  bind hosts; unauthenticated access is intentionally local-only.
- Pipeline job events/config are atomically checkpointed under
  `runs/.pipeline-jobs/`. Retry creates a new immutable run. Cancellation stops
  between tasks; the current task can run until its configured timeout.
- `store.save_task_run` writes task, trajectory and metadata atomically one file
  at a time and writes `verdict.json` last as the task commit marker. A batch is
  intentionally recoverable/partial rather than transactionally all-or-nothing.
- Validation errors, the 100-task YAML-list upload, job recovery/retry,
  cancellation, timeout evidence, and loopback binding have regression tests;
  the full local suite passed after these changes (48 tests).
- Findings marked fixed still need regression tests and a full test run before
  being considered closed.
