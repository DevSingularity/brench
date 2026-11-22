# CHANGE RESPONSE — Track B

## Impact on current work and claims

The scenario is already supported by the core design: the runner records a blocked tool attempt and its tripwire result in the saved trajectory, even when the agent later declares `ESCALATE_HUMAN`. The strict grader recomputes tripwire hits from the raw call and the reference grader evaluates the recorded hit. Both should therefore retain the unauthorised-action finding; a correct final declaration must not erase the earlier attempt. Re-grading uses the saved trace and does not invoke an agent/model. This harness currently uses scripted fixtures, so there is no model charge.

## Chosen response and rationale

Keep the original run immutable. Persist each grader output as a separate replay run linked to its source, with the grader name/version and a copied task snapshot and trajectory; only the new verdict and replay metadata differ. This preserves the original verdict and exact evidence while allowing an auditable comparison. The run/task evidence UI should show the original and replay verdicts together as grading history, identify which grader produced each result, and link to each run. The blocked call must remain visible beside the final escalation so reviewers can see why the verdict stands. This matches the existing file-backed replay implementation and avoids rerunning or modifying the source run.

## Work deliberately deferred

Defer PostgreSQL migration, live-model billing integration, automatic grader-difference explanation, and changing the grader rules themselves. The current request is about comparing outputs for one saved trace; changing scoring policy during the comparison would confound the result. Keep the documented limitation that filesystem writes are not a transactional database and that replay copies task/trace evidence into another run directory.

## Acceptance test and remaining risk

Create a task whose fixture attempts a payment above a tripwire limit and then ends with `ESCALATE_HUMAN`. Save the run and snapshot the source `trajectory.jsonl` and `verdict.json`. Re-grade it with the other grader. Assert the agent runner is not called, the replay references the source run, the replay trajectory is byte-for-byte identical, the source files are unchanged, and both verdicts report the blocked unauthorised attempt even though the final declaration is correct. In the UI, verify the task’s grading history shows both grader names/versions and outcomes, links to both run pages, and retains the blocked call and final escalation in the same trace. Remaining risk: the two deterministic graders may agree on this case; that is expected if they apply the same rule to a complete, correctly recorded trace. Their known differences matter on other edge cases, and replay comparison must not be presented as a guarantee of different scores.
