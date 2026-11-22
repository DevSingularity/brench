# CHANGE RESPONSE — Track B

## Impact on current work and claims

The scenario is already supported by the core design: the [runner records the blocked tool call and tripwire result before the terminal decision](harness/core/runner.py#L128-L153). The [strict grader recomputes tripwire hits from raw calls](harness/evaluation/graders/strict.py#L62-L80), while the [reference grader evaluates recorded hits](harness/evaluation/_reference_grader.py#L18-L44). Both should retain the unauthorised-action finding; a correct final declaration must not erase the earlier attempt. The [re-grade path reads the saved trajectory and calls the grader directly](harness/evaluation/replay.py#L35-L65), without invoking an agent/model. This harness uses scripted fixtures, so there is no model charge.

## Chosen response and rationale

Keep the original run immutable. The [replay implementation copies each task snapshot and trajectory into a linked run](harness/evaluation/replay.py#L35-L65), records SHA-256 hashes, and writes a new verdict and metadata; it does not overwrite source evidence. The [task report collects original and replay verdicts](harness/persistence/report.py#L82-L112), and the [evidence UI compares grader/version, outcome, decisions, tripwire hits, evidence count and notes with links to each run](ui/src/App.jsx#L284-L289). The [trace inspector renders the recorded action sequence](ui/src/App.jsx#L286-L289), including the blocked call and final escalation.

## Work deliberately deferred

Defer PostgreSQL migration, live-model billing integration, automatic grader-difference explanation, and changing the grader rules themselves. The current request is about comparing outputs for one saved trace; changing scoring policy during the comparison would confound the result. Keep the documented limitation that filesystem writes are not a transactional database and that replay copies task/trace evidence into another run directory.

## Acceptance test and remaining risk

Acceptance check: create a task whose fixture attempts a payment above a tripwire limit and then ends with `ESCALATE_HUMAN`. Snapshot source `trajectory.jsonl` and `verdict.json`, re-grade with the other grader, then verify the runner was not called, replay metadata links to the source, the [replay trajectory matches its source](harness/evaluation/replay.py#L35-L44), source files are unchanged, and both verdicts retain the blocked unauthorised attempt. In the UI, verify the [task grading history](ui/src/App.jsx#L285) shows both grader versions/outcomes and links, while the shared trace shows the blocked call and final escalation. Remaining risk: graders may agree on this case; comparison does not guarantee different scores.
