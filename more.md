Yes, this is a solid demo: the same 100 situations let you compare fixture behavior, then compare both graders against the exact same saved trace without rerunning the fixture.

I created demo-100.yaml. It contains 50 matched pairs: in one situation escalation is required; in the paired situation a signed exception authorizes action. The task loader now accepts a YAML list, so the file can be uploaded as one file. Both CLI validation and the upload API accepted all 100 tasks with no warnings.

Suggested order:

1. Run attempt_then_escalate first. Its trace shows an attempted action, whether the mock tool blocks it, and the agent’s final escalation.
2. Run always_escalate to contrast its cautious behavior on cases where action is authorized.
3. Run always_act to see the risk on cases requiring escalation.
4. On each run, use Re-grade saved trace to apply the other grader. The agent won’t run again.

These are intentionally simple scripted fixtures, not realistic AI models. They make behavior differences easy to demonstrate; they don’t guarantee the graders will disagree on every result. I added the demo guidance to the README, and the app is available at http://127.0.0.1:8765.