# Brench

Brench evaluates whether an AI agent acted within its authority. It
runs scripted agents against task-defined mock tools, keeps a complete trace,
grades the decision with deterministic rules, and serves the evidence in a
local results UI. It does not use an LLM as a judge.

## Track B scope (candidate clarification)

This project is **Track B: full-stack harness**. The official clarification for
all candidates, kept here so future work stays in scope:

- **Tasks:** Two sample task YAML files are supplied in `starter/examples/`.
  Track B uses these to build the evaluation harness. (Track A creates six task
  pairs / 12 tasks; Track C builds an environment that generates reproducible
  task instances.)
- **Fixture agent (Track B):** a simple scripted agent that calls mock tools and
  produces an execution trace. It does not require an LLM.
- **Judge/grader (Track B):** separate from the agent; it evaluates the saved
  trace against the task rules. A deterministic grader is sufficient; you may
  adapt `starter/reference_grader.py` with attribution.
- **Required Track B flow:** Task → fixture agent → saved trace → grader →
  results UI. Demonstrate swapping the grader and re-grading **without rerunning
  the agent**.

How this repo maps to that flow:

| Required step | Where it lives |
|---|---|
| Task | `tasks/` — the two supplied samples `FIN-INV-0007` / `FIN-INV-0007b` (plus two extra self-authored pairs, `HR-0201-*` and `REF-0101-*`, built on the same contract to exercise the multi-domain results matrix) |
| Fixture agent | `harness/core/agents.py` — six scripted agents, no LLM |
| Saved trace | `runs/<run_id>/<task_id>/trajectory.jsonl` written by `harness/core/runner.py` |
| Grader | `harness/evaluation/graders/` — `strict` (ours) and `reference` (adapted from the supplied `reference_grader.py`, attribution in the module docstring) |
| Results UI | `harness/web/server.py` + `ui/` (built output committed in `ui/dist`) |
| Grader swap without rerunning the agent | `python -m harness replay <run> --grader reference` — copies the saved trace byte-for-byte, grades again, `kind: replay`, source untouched |

The step-by-step demo script with defence notes for each decision is in
`docs/plans/WALKTHROUGH.md`.

## Run the offline demo

Python 3.10+ and PyYAML are the only runtime requirements. The compiled React
UI is committed under `ui/dist`; Node is only needed when changing the UI.

```sh
python -m pip install -r requirements.txt
python -m harness demo
```

The command runs fixture agents over `tasks/`, writes saved evidence under
`runs/`, and serves the UI at `http://127.0.0.1:8765`. Use `--no-browser` to
keep it from opening a browser automatically. No API key or network access is
needed after PyYAML is installed. The current evidence store is local
file-backed JSON/YAML; PostgreSQL is not currently used by the harness.

### Run a task set from the UI

Open the workspace from the landing page and choose **New evaluation**. Add one
or more `.yaml` / `.yml` task files, validate them, choose a scripted fixture
agent and grader, then start the pipeline. The UI shows task loading and
validation, fixture dispatch, every trace record, grading and evidence saving.
On completion, open the run to inspect the saved verdict and full trace. The
workspace also offers **Re-grade saved trace**: choose another grader to create
a linked replay without calling the agent again. Fixture runs are deterministic
scripts, not live model results. `oracle` is a harness sanity check that can see
trusted task metadata and must not be treated as a model baseline.

Live pipeline status/events are held in the serving process while a job is
running. The job ID and run configuration are also recorded in run metadata;
after a server restart, the UI reconstructs the job view from saved evidence and
marks an unfinished run interrupted. Task snapshots, trajectories, verdicts and
run metadata are stored under `runs/` as each task completes; a failed batch
keeps its completed task evidence and records a failed run status. Keep the
server bound to loopback for local use.

Useful commands:

```sh
python -m harness validate-tasks tasks/
python -m harness run --agent oracle --run-id oracle-check
python -m harness replay always_escalate-seed0 --grader strict
python -m harness import-trace --help
python -m unittest discover -s tests -v
```

For UI development only, install the pinned JavaScript dependencies in `ui/`
and run `pnpm dev` or `pnpm build`. Rebuilds update the committed
`ui/dist/` that Python serves.

## Project layout

- `harness/core/` contains task loading, contract validation, mock tools, the
  runner and fixture agents.
- `harness/evaluation/` contains the grader registry, both graders, trace import
  and replay.
- `harness/persistence/` contains batch execution, run storage and summaries.
- `harness/web/` contains the local HTTP API and static UI server; `harness/`
  itself provides the CLI. The contract validator is vendored in the package,
  so runtime behavior does not depend on the archived candidate pack.
- `tasks/` contains editable example task YAML files. Pass hidden or custom
  task files with `--tasks PATH`.
- `tests/` contains the harness tests.
- `ui/` contains the React source and its built, self-contained distribution.
- `runs/` is generated by demo and run commands; each task stores the exact
  task snapshot, `trajectory.jsonl`, `verdict.json` and metadata.
- `reference/legacy-candidate-pack/` is an untouched copy of the supplied
  candidate pack for historical reference. The app does not read from it.

## Trace import and grading

External traces can be converted to the contract format and graded with
`python -m harness import-trace`. See `python -m harness import-trace --help`
for the task, trajectory, model, run ID and optional action-alias arguments.
The `reference` and `strict` graders implement the shared `grade(task,
trajectory, *, model, run_id, seed)` interface. `replay` grades saved traces
again without rerunning an agent and leaves the source trace untouched.

The UI reports counts and denominators by task category, domain and stakes;
empty matrix cells mean no cases were run. Unauthorised actions and
over-escalations are separate outcomes. Selecting a task opens its verdict and
full trace, including blocked attempts.

## Limits

The included agents are deterministic fixtures, not live model runs. Tool
effects are simulated and never call external services. Browser-triggered runs
are limited to one active pipeline per server process. After a process exits,
ordered live events are reconstructed from saved trajectories and verdicts;
events that were never persisted cannot be recovered.
Tripwire conditions
support only `amount_usd > N` and `payee not in vendor_master`; unsupported
conditions fail validation. An imported trace can be graded only to the extent
that it has been normalized to the published trajectory contract. Scores do
not establish general model safety or replace task-specific policy review.
