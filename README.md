# Brench

Brench is a local harness for inspecting whether an AI agent stayed within its
stated authority. It runs scripted fixture agents against an isolated tool
simulator, records each interaction, grades the saved trajectory, and presents
the evidence in a browser UI. It does not call a live model or use an LLM as a
judge.

The intended evaluation path is:

```text
task contract → fixture agent → simulated tools → saved trajectory → grader → evidence UI
```

Brench is a Track B full-stack evaluation harness. Its fixtures make the
execution path reproducible and easy to inspect; they are not representative
model benchmarks. See [the technical overview](docs/TECHNICAL-OVERVIEW.md) for
module boundaries, data formats, API routes, failure behavior, and known
limitations. See [DECISIONS.md](DECISIONS.md) for the rationale and tradeoffs
behind the current design.

## Quick start

Requirements: Python 3.10 or newer and the dependencies in `requirements.txt`.
Node is only required when rebuilding the frontend.

```sh
python -m pip install -r requirements.txt
python -m harness demo --no-browser
```

The demo writes runs under `runs/` and starts the local UI at
`http://127.0.0.1:8765`. Open that address in a browser. To choose another port
or suppress the UI, run `python -m harness demo --help`.

To start the UI without launching fixture runs:

```sh
python -m harness serve --no-browser --port 8765
```

To run a focused, known grader-difference example:

```sh
python -m harness run --tasks examples/grader-difference.yaml \
  --agent always_escalate --grader strict --run-id grader-diff-demo
python -m harness replay grader-diff-demo --grader reference \
  --new-run-id grader-diff-demo-reference
```

The `GRADER-DIFF-001-E` task is designed so the fixture names the escalation
contact but not the full configured role string. The strict grader accepts the
person name; the reference grader expects the full target string. This should
produce `correct_escalation` and `wrong_target` on the same saved trajectory.
The paired authorized-action task also shows that blanket escalation can be an
over-escalation. This is a controlled behavior example, not a claim about model
performance.

For the larger synthetic comparison, upload `examples/demo-100.yaml` in the
UI. It contains 50 matched pairs of payment-authority tasks. Start with
`attempt_then_escalate` to inspect blocked attempts, then compare
`always_escalate` and `always_act`. Re-grade selected runs to compare graders
without executing the agent again. The fixtures use simple rules and generated
records; they do not reason like deployed agents.

## What gets saved

The default backend is the local filesystem. A run has a unique ID and stores
its run metadata plus, for each completed task, the exact task snapshot,
JSONL trajectory, verdict, and per-task metadata under `runs/<run_id>/`.
Pipeline job state, progress events, and retry inputs live under
`runs/.pipeline-jobs/`. Treat this directory as local evaluation data: uploaded
tasks and traces can contain sensitive information.

A re-grade creates a separate linked run. It copies the task snapshot and
trajectory byte-for-byte, records SHA-256 hashes for that evidence, and writes a
new verdict and run metadata. It does not invoke the fixture agent or overwrite
the source run. See [the replay implementation](harness/evaluation/replay.py)
and [the technical overview](docs/TECHNICAL-OVERVIEW.md#re-grading-and-evidence-identity).

`docker-compose.yml` defines a PostgreSQL 16 service for local development, but
**the current main-worktree application does not use PostgreSQL**. The harness
continues to read and write run evidence on disk. Starting Compose only starts
the database service; it does not migrate or connect the app to it.

## Task and grading model

A task is a YAML mapping (or a YAML list of mappings) validated against the
published task contract. It separates agent-visible information—role, grants,
allowed tools, brief, and tool-retrieved context—from grader-only fields such
as the expected action, rationale, tripwires, and escalation requirements.
The runner gives the agent only the allow-listed observation. Pair metadata is
used for coverage and reporting, not exposed to the agent.

Fixture agents implement a small `step(observation)` protocol and return a
message, tool call, or terminal decision. The simulator checks tool
permissions and tripwires before executing an action. A blocked attempt is
still recorded and counts as a violation; the simulator has no network or real
system side effects.

Two deterministic graders share the same interface:

- `reference` is the supplied contract grader adapted into the package. It is a
  comparison baseline with documented limitations.
- `strict` recomputes tripwire hits from trusted task rules and raw calls and
  applies stricter message and target matching. It is a project implementation,
  not an independent safety oracle.

Tasks may declare grader-only `evidence_requirements.must_use` tools. Both
graders then require successful, unblocked results from those tools before
awarding a correct outcome. In `examples/demo-100.yaml`, each of the 50
authorized payment cases requires `policy.search`, so `always_act` without a
policy lookup is graded `insufficient_evidence`. This checks that the trace
contains a required retrieval result; it cannot prove the agent understood or
used the returned content. Re-grade an old run against its saved task snapshot;
to apply changed task rules, create a new run from the updated YAML.

The result UI reports counts and denominators by outcome, category, domain,
stakes tier, and pair coverage. Selecting a task opens its verdict, task
snapshot, agent-visible observation, grader diagnostics, and trajectory.
Outcomes are not collapsed into one score: unauthorized actions,
over-escalations, and other errors remain distinct.

## CLI

```sh
python -m harness validate-tasks tasks/
python -m harness run --agent oracle --run-id oracle-check
python -m harness list
python -m harness replay oracle-check --grader reference
python -m harness import-trace --help
python -m harness serve --help
```

`oracle` can inspect trusted task metadata and is only a harness sanity check;
never interpret its results as an agent baseline. Use `python -m harness
--help` for all commands and options.

## Development

The Python server serves both the JSON API and the committed static React
bundle in `ui/dist/`. Rebuild the frontend only when changing UI source:

```sh
cd ui
pnpm install --frozen-lockfile
pnpm build
```

Run the Python test suite with:

```sh
python -m unittest discover -s tests -v
```

The API is intentionally unauthenticated and binds only to `127.0.0.1`. Keep it
on loopback. Upload validation limits requests to 32 YAML files and 2 MB total,
checks UTF-8 and file names, validates task contracts, rejects duplicate YAML
keys, and scans for common credential patterns. That scan is a guardrail, not a
complete secret detector; do not put credentials in task input.

## Repository map

- `harness/core/` — task loading, contract validation, fixture agents, runner,
  tripwire conditions, and mock tools.
- `harness/evaluation/` — grader registry, grader implementations, trace import,
  and re-grading.
- `harness/persistence/` — file-backed run storage and report aggregation.
- `harness/web/` — local HTTP API, static asset server, and browser-run jobs.
- `ui/` — React application source and committed build output.
- `tasks/`, `examples/` — contract tasks and synthetic demonstrations.
- `tests/` — Python contract, runner, persistence, grading, and API tests.
- `docs/` — implementation notes, plans, and [technical overview](docs/TECHNICAL-OVERVIEW.md).
- `reference/legacy-candidate-pack/` — retained source materials for reference;
  runtime code does not load from this directory.
