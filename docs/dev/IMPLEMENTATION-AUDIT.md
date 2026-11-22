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
| AUD-09 | Medium | Batch execution reset an existing run directory for the default `agent-seed` ID. Re-running the demo could erase previously saved traces and verdicts. | Open; choose non-destructive repeat-run behavior and test it. |
| AUD-10 | Medium | Timeout handling abandons a daemon thread but cannot stop it. A timed-out adapter can continue computing or performing its own external work after the harness has recorded `NONE`. | Known limitation; document boundary, or isolate agents in a killable process if live adapters are introduced. |
| AUD-11 | Medium | Run files are written directly to their final paths. A process interruption during JSON or JSONL writes can leave partial evidence that later readers treat as a corrupt run. | Open; consider atomic temporary-file writes and recovery behavior. |
| AUD-12 | Medium | Task YAML snapshots are stored byte-for-byte to preserve replay fidelity. Credentials embedded by a caller in task context are not scrubbed from `task.yaml`, even though trace and metadata writes apply redaction. | Open; define a policy that preserves grading/replay semantics while preventing secrets in task inputs. |
| AUD-13 | Low | The built-in task set has a narrow tool/context vocabulary and supports only two tripwire condition forms. Unknown tripwire syntax fails visibly; unknown context types become visible brief text unless the task supplies a tool mapping. | Known contract limitation; keep documented and add extensions only with fixtures. |
| AUD-14 | Low | The demo is deterministic fixture data. It does not demonstrate a live API adapter, a general raw-dataset mapper, or an LLM judge. | Intentional scope; label fixture runs accurately and describe import normalization limits. |
| AUD-15 | Pending external input | `CHANGE-RESPONSE.md` requires the 13:30 constraint-change card, which is not present in this checkout. Writing a response without it would invent the change. | Pending card. |

## Additional audit notes

- The contract validator is vendored under `harness/core/`; runtime code does not
  import from the archived candidate pack.
- The UI is served from committed `ui/dist/` and does not require Node at demo
  time. Node is used only to rebuild the UI.
- The local API binds to loopback. It has no user authentication; keep it local
  and do not expose the server on a public interface.
- Findings marked fixed still need regression tests and a full test run before
  being considered closed.
