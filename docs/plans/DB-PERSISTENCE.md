# DB persistence plan — PostgreSQL 16 via Docker Compose

**Status:** planned, not yet implemented. **Raised by:** `docs/dev/GAP-PLAN.md`
P0 row / GAP-02, GAP-03, GAP-08. **Baseline verified today:** 40 tests green on
the file store; Docker 29.9.0 + Compose v5.6.0 installed; `postgres:16-alpine`
image already present locally (no pull needed); `psycopg-binary==3.3.9` wheel
exists for macOS arm64 / Python 3.14; host port **5432 is already bound by
Docker**, so we default to host port **5433**.

---

## 1. Goal and non-goals

**Goal.** Runs, task snapshots, trajectories and verdicts are persisted in
PostgreSQL 16 (`postgres:16-alpine` via `docker compose`). Every CLI and API
path — `demo`, `run`, `replay`, `import-trace`, `list`, `serve`, report,
regrade endpoint — reads and writes through one store interface. The database
is the system of record; files become an **export format** for the frozen
snapshot and for humans who want to read evidence without a database.

**Non-goals (explicitly out of scope for this plan):**

- No ORM (SQLAlchemy), no Alembic. Three tables do not earn a dependency; plain
  SQL + a five-line idempotent migration runner keeps the code explainable in
  a defence.
- The Python app stays on the host. Compose runs **only** PostgreSQL (this is
  what GAP-PLAN P0 prescribes: "Keep only PostgreSQL in Compose").
- No SQL rewrite of `report.py` aggregation in phase 1 — the Python bucket
  logic is contract-tested; it just reads through the store instead of paths.
- No auth, pooling library, encryption at rest, or multi-user work. The API
  stays loopback-only (GAP-07 unchanged).
- GAP-04 (secret-bearing `task.yaml` snapshots) is **not** solved by moving to
  a database; it stays open and is noted in §13.

**What this buys us (honest scoring note):** persistence depth is not a line
item in the 60-point rubric — it is *engineering hygiene* (5 pts), it closes
three findings in our own audit (GAP-02/03/08), and it is a strong
production-ownership story for the showcase Q&A. It must never risk the
essential paths: trace, verdict, replay, tests, docs.

---

## 2. Constraints that shape the design

| Constraint | Source | Design consequence |
|---|---|---|
| Offline after deps installed; one documented command | Track B brief §1 | Image is local; `docker compose up -d --wait` needs no network. File store stays available as `--store file` escape hatch; unit tests run without any database. |
| Saved traces/verdicts in the 15:00 snapshot | Brief §"Submission" | `db export-files` command writes the exact `runs/` layout back out before packaging. |
| Replay = byte-for-byte copy of the source trajectory | WALKTHROUGH §5, replay.py:3-4 | Trajectory stored as **text** (the exact JSONL string), never `jsonb` — `jsonb` reorders object keys and would silently break the byte-for-byte claim. |
| 40 existing tests pass, most asserting on temp-dir paths | tests/test_harness.py:370-458 | Store seam accepts a *path or a store object*; zero test edits required. |
| No partial run ever visible | GAP-03, AUD-11 | Postgres: one transaction per run. File store: stage in `runs/.partial-*` then atomic `os.rename` (closes the same gap for files). |
| Duplicate run ids must raise the same errors | StoreTests:382-383, replay.py:24-33 | Keep `ValueError("... already exists ...")` message text identical; DB unique constraint is the backstop. |
| Loopback-only, credentials out of the package | Brief §AI tools, GAP-07 | Compose publishes `127.0.0.1:5433` only; `.env` gitignored, `.env.example` committed with a local-only placeholder password. |

---

## 3. Decision: architecture

**Recommended — one store interface, two backends, Postgres is primary when
configured.**

```
CLI / HTTP handler
      │  resolves once: --db-url > env BENCH_DB_URL > .env > (none)
      ▼
harness.persistence.backend.get_store(runs_dir, db_url)
      ├── db_url set  → PostgresStore(psycopg)   ← system of record
      └── db_url none → FileStore(runs_dir)      ← current behaviour, tests, escape hatch
      ▼
batch · report · replay · importer · server   (unchanged orchestration)
```

Selection is **explicit, never auto-detected by probing**: if the config says
Postgres and the database is down, we fail fast with the remediation command
(`docker compose up -d --wait`). Silent fallback would serve the wrong
evidence source — worse than a clear error.

**Alternatives rejected:**

| Alternative | Why not |
|---|---|
| Files stay canonical, Postgres is a read index (dual-write) | Two sources of truth drift; GAP-02 asks for *the* store, not a cache. Export gives us files when needed without dual-write risk. |
| Replace file store outright, delete `FileStore` | Breaks "tests run with no dependencies beyond PyYAML", breaks the no-Docker escape hatch for judges, and makes the snapshot depend on a running database. |
| SQLite instead | Zero-dep and fine for local, but GAP-PLAN P0 names PostgreSQL 16, and PG gives us JSONB, transactional multi-writer safety under `ThreadingHTTPServer`, and a compose story that reads as production-shaped. |
| Trajectory as `jsonb` array | `jsonb` normalises key order → replay copies would no longer be byte-identical to the original JSONL. Text column, parsed on read (we already parse on read today: store.py:108-109). |
| SQLAlchemy / asyncpg | Dependency and cognitive cost for `INSERT`/`SELECT` on three tables; async buys nothing under the stdlib threaded server. |

---

## 4. Compose and configuration

### 4.1 `docker-compose.yml` (project root)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: brench
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-brench-local-only}
      POSTGRES_DB: brench
    ports:
      - "127.0.0.1:${BENCH_DB_PORT:-5433}:5432"   # 5432 is taken on this host
    volumes:
      - brench-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U brench -d brench"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 5s

volumes:
  brench-pgdata:
```

Notes:

- **Loopback bind only.** The database is never reachable off-machine.
- **Named volume** `brench-pgdata` → data survives `docker compose down` and
  Docker Desktop restarts (the GAP acceptance test: "restarting the DB
  preserves it"). `docker compose down -v` wipes it — documented as the reset
  button.
- **Port 5433 default** because `lsof` shows Docker already listening on
  `*:5432` on this machine. Overridable via `BENCH_DB_PORT`.
- Password default is a **local-only placeholder**, not a secret; real values
  go in `.env` (gitignored). Compose interpolates `${...}` from the environment
  or from `.env` in the project directory — the same file the Python app reads.

### 4.2 `.env.example` (committed) / `.env` (gitignored)

```ini
# Local development only. Do not reuse this password anywhere else.
POSTGRES_PASSWORD=brench-local-only
BENCH_DB_PORT=5433
# Read by the Python app; compose builds its connection from the values above.
BENCH_DB_URL=postgresql://brench:brench-local-only@127.0.0.1:5433/brench
```

`.gitignore` gains one line: `.env`.

### 4.3 Config resolution (new `harness/persistence/config.py`, ~30 lines)

Precedence: `--db-url` CLI flag → `BENCH_DB_URL` environment variable →
`BENCH_DB_URL` in `.env` (tiny `KEY=VALUE` parser, comments and blanks
skipped, no dependency) → **none → FileStore**.

`.env` is read by both compose and the app, so the whole workflow is:

```sh
cp .env.example .env
docker compose up -d --wait          # waits for healthcheck
python -m harness demo               # evidence lands in Postgres
```

---

## 5. Schema

Single idempotent migration `harness/persistence/migrations/001_init.sql`,
applied inside a transaction by a runner that records versions in
`schema_migrations`. Re-running is a no-op; no Alembic.

```sql
-- 001_init.sql
CREATE TABLE IF NOT EXISTS runs (
  run_id          text PRIMARY KEY,
  model           text NOT NULL,
  agent           text,                        -- null for imported/manual runs
  kind            text NOT NULL,               -- fixture | replay | manual | api | imported
  note            text,
  grader          text NOT NULL,
  grader_version  text NOT NULL,
  seed            integer,
  max_steps       integer,
  timeout_s       double precision,
  replay_of       text REFERENCES runs(run_id), -- lineage for grader-swap runs
  created         timestamptz NOT NULL,
  harness_version text,
  python          text,
  meta            jsonb NOT NULL DEFAULT '{}'::jsonb  -- full redacted meta.json
);

CREATE TABLE IF NOT EXISTS task_evidence (
  run_id           text NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  task_id          text NOT NULL,
  task_yaml        text NOT NULL,              -- byte-for-byte snapshot (see §13)
  trajectory_jsonl text NOT NULL,              -- exact JSONL bytes; replay copies this
  verdict          jsonb NOT NULL,
  task_meta        jsonb NOT NULL,
  -- Derived hot fields for SQL + the psql demo beat. STORED + immutable
  -- expressions only, so they cannot drift from `verdict`:
  outcome          text GENERATED ALWAYS AS (verdict ->> 'outcome') STORED,
  declared_action  text GENERATED ALWAYS AS (verdict ->> 'declared_action') STORED,
  correct_action   text GENERATED ALWAYS AS (verdict ->> 'correct_action') STORED,
  action_match     boolean GENERATED ALWAYS AS ((verdict ->> 'action_match') = 'true') STORED,
  PRIMARY KEY (run_id, task_id)
);

CREATE INDEX IF NOT EXISTS task_evidence_outcome_idx ON task_evidence (outcome);
CREATE INDEX IF NOT EXISTS runs_created_idx          ON runs (created DESC);

CREATE TABLE IF NOT EXISTS schema_migrations (
  version    text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
```

Design points, in the order a judge will ask:

- **Why `trajectory_jsonl text` and not `jsonb`?** Byte-for-byte replay. We
  parse to dicts on read exactly as `read_jsonl` does today (store.py:108-109).
- **Why generated columns instead of writing `outcome` twice?** They are
  computed from `verdict` by the database, so they *cannot* disagree with it;
  `(verdict ->> 'x') = 'true'` is immutable, so Postgres 16 accepts them.
  They give us `GROUP BY outcome` and a one-line psql demo without duplicating
  write logic.
- **Why no `status = running` column?** A run is inserted in **one
  transaction** (§7); readers either see all of it or none of it. A status
  column would only be needed if we streamed evidence during long live-model
  runs — out of scope, noted as future work.
- **`ON DELETE CASCADE`** so `DELETE FROM runs WHERE run_id = ...` is a complete
  cleanup; no orphan evidence rows.

**Migration runner** (`harness/persistence/migrate.py`, ~25 lines): connect,
`CREATE TABLE IF NOT EXISTS schema_migrations`, read applied versions, apply
each pending `.sql` file and `INSERT` its version — all inside one `with
conn.transaction():` block. A failed migration rolls back and records nothing.

---

## 6. Code changes, file by file

New modules:

| File | Contents |
|---|---|
| `harness/persistence/backend.py` | `get_store(runs_dir, db_url)`, `coerce_store(x)` (path → `FileStore`, store → itself), the `RunStore` surface documented as a protocol. |
| `harness/persistence/file_store.py` | The current `store.py` functions, wrapped as a class, **plus** atomic run creation (§7). `store.py` keeps `safe`, `redact`, `run_dir`, `_atomic_write` as shared helpers both backends use (redaction must happen before insert exactly as before: store.py:31-40). |
| `harness/persistence/postgres.py` | `PostgresStore` + `connect()` (lazy `import psycopg` so file-only users get a clean "pip install -r requirements.txt" message, not an ImportError traceback). |
| `harness/persistence/config.py` | Resolution order of §4.3. |
| `harness/persistence/migrate.py` + `migrations/001_init.sql` | §5. |
| `harness/persistence/export.py` | `import_files(store, runs_dir)` (backfill) and `export_files(store, out_dir)` (snapshot packaging). |

Modified call sites — the seam. Existing functions gain an optional
`store=None` first-class kwarg or accept *path-or-store*; signatures stay
backwards compatible so **not one line of the 40 tests changes**:

| File | Current coupling | Change |
|---|---|---|
| `harness/persistence/store.py` | file paths throughout (43-109) | becomes helpers + `FileStore`; gains `read_task_yaml / read_trajectory_lines / read_trajectory / read_verdict / read_task_meta / create_run` so callers stop reaching into paths. |
| `harness/persistence/batch.py` | `run_path.mkdir` then per-task writes, meta last (19-52) | collect all task evidence in memory, call **one** `store.create_run(run_id, meta, tasks)` → atomic on both backends. Existence checks go through `store.exists()` (keeps the auto-uniqueness loop at 25-30 and the "already exists" error at 22). |
| `harness/persistence/report.py` | reads files via `base / tid / ...` (36-46, 78-89) | every read becomes `store.read_*`; aggregation logic (14-72) untouched. First arg accepts path or store (`report.run_detail(out, rid)` keeps working). |
| `harness/evaluation/replay.py` | `shutil.copyfile` of `task.yaml` + `trajectory.jsonl` (40-41) | read source rows through the store, grade in Python (grader stays separate — Track B), pass `trajectory_jsonl` through **untouched**, write via one `create_run`. Source run never updated (the "source untouched" claim gets *stronger*: it is a different row, not a copied file). |
| `harness/evaluation/importer.py` | `save_task_run` + `write_run_meta` two-step (40-54) | one `store.add_task_run(...)` transaction that inserts the task row and updates run meta together. |
| `harness/web/server.py` | `make_handler(runs_dir, ...)` (46), `make_server(runs_dir, ...)` (133) | first parameter accepts path or store via `coerce_store`; handlers carry the store. `/api/health` gains a `db` block (§8). Everything else (routes 18-25, regrade 92-103, static 105-116) unchanged. |
| `harness/__main__.py` | `DEFAULT_RUNS` (14), per-subcommand `--runs-dir` (115, 143, 156, 160, 166) | `common()` and the standalone subcommands gain `--db-url`; resolve the store once in `main()` and pass it down. New `db` subcommand group (§8). |
| `requirements.txt` | `PyYAML==6.0.2` | add `psycopg[binary]==3.3.9` (wheel verified for cp314 arm64). |
| `.gitignore` | — | add `.env`. |

`harness/core/` (runner, agents, tools, conditions, tasks, contract) and
`harness/evaluation/graders/` — **untouched**. The database sits below the
grader, never between the agent and its trace.

### The `RunStore` surface (derived from actual call sites, not invented)

```python
class RunStore:
    def exists(self, run_id) -> bool: ...
    def list_run_ids(self) -> list[str]: ...
    def load_run_meta(self, run_id) -> dict: ...
    def write_run_meta(self, run_id, meta) -> None: ...      # upsert
    def task_ids(self, run_id) -> list[str]: ...
    def read_task_yaml(self, run_id, task_id) -> str: ...    # exact text
    def read_trajectory_lines(self, run_id, task_id) -> str: ...  # exact JSONL
    def read_trajectory(self, run_id, task_id) -> list[dict]: ... # parsed
    def read_verdict(self, run_id, task_id) -> dict: ...
    def read_task_meta(self, run_id, task_id) -> dict: ...
    def create_run(self, run_id, meta, tasks) -> None: ...   # atomic, all-or-nothing
    def add_task_run(self, run_id, task..., meta_update) -> None: ...  # import path
```

`PostgresStore.create_run` is one `with conn.transaction():` block inserting
`runs` + N `task_evidence` rows. `FileStore.create_run` stages into
`runs/.partial-<run_id>` and `os.rename`s into place — POSIX-atomic within a
filesystem, so GAP-03/AUD-11 are closed for files too, and a crash leaves only
a `.partial-*` directory that `list_run_ids` already ignores (it requires
`meta.json`: store.py:88-92).

---

## 7. Transactions, failures, and error compatibility

| Operation | Boundary | On failure |
|---|---|---|
| `demo` / `run` (batch) | one tx per run: run row + all task rows + meta | rollback → zero rows; no partial run ever listed. Grading happens before the tx (in memory), so a grader bug cannot half-write a run. |
| `replay` | one tx: new run row + copied trajectories + new verdicts | source rows are never in the tx's write set — structurally impossible to mutate the source. |
| `import-trace` | one tx: task row + run meta update | PK conflict on `(run_id, task_id)` → `ValueError` with the importer's existing "already present" wording (importer.py:38). |
| report / API reads | read-only, per-call connection | connection refused → 503 with `{"error": "database unavailable; run: docker compose up -d --wait"}`. |
| migration | one tx per version file | rollback, `schema_migrations` unchanged, non-zero exit. |

**Error-string compatibility (tests assert these):**

- `run ... already exists` — batch.py:22, replay.py:27 → keep exact wording,
  raise `ValueError` (both backends; PG unique-violation is caught and
  re-raised).
- `replay needs a different run id than its source` — replay.py:25.
- `task ... not found in run ...` — report.py:79.

**Connections:** one short-lived `psycopg.connect(dsn)` per store method via
`with` (commit/rollback managed by psycopg). Localhost round-trip is
sub-millisecond at this scale; `psycopg_pool` is listed as stretch work, not
phase-1 work. `row_factory=dict_row` so reads return the same dict shapes the
JSON file reads returned.

---

## 8. Commands, health, and demo beats

### New CLI

```sh
python -m harness db migrate        # apply pending migrations, print versions
python -m harness db status         # backend, DSN (password masked), migration, counts, ping ms
python -m harness db import-files   # backfill existing runs/ into Postgres
python -m harness db export-files   # Postgres → runs/ (snapshot packaging)
```

`db status` sample output:

```
backend    postgres  127.0.0.1:5433/brench  (password: ****)
migration  001_init applied 2026-11-22T12:41:07Z
runs       8        task_evidence 48
ping       1.9 ms
```

Global flag on every subcommand that touches evidence: `--db-url DSN`
(overrides env). `--store file` forces the file backend even when `BENCH_DB_URL`
is set — the documented escape hatch if a judge's Docker misbehaves.

### `/api/health` (server.py:80-81) grows a block

```json
{"ok": true,
 "db": {"ok": true, "backend": "postgres",
        "migrations": ["001_init"], "ping_ms": 2}}
```

File backend reports `{"backend": "file", "path": "runs/"}`. Health never
echoes the password.

### The three demo beats this buys (for the 7-minute showcase)

1. `docker compose up -d --wait && python -m harness demo` → evidence in UI.
2. `docker compose restart db` → `python -m harness list` still shows all 8
   runs. *"The evidence does not live in a directory that a cleanup can
   delete; it survives a database restart."*
3. `docker compose exec db psql -U brench -d brench -c \
   "SELECT run_id, outcome, count(*) FROM task_evidence GROUP BY 1,2 ORDER BY 1"``
   → the matrix as SQL, straight from the generated columns.

---

## 9. Data migration and the snapshot

Two paths, both provided because the snapshot is non-negotiable:

1. **Backfill (preserve current evidence as-is):** `python -m harness
   db import-files` walks `runs/` with the existing `FileStore` readers and
   inserts. Handles the 8 current runs including the two `__reference`
   replays, without re-running anything.
2. **Regenerate (clean slate):** fixtures are deterministic; `demo` into an
   empty database reproduces equivalent evidence in seconds.

**Before packaging the 15:00 snapshot:** `python -m harness db export-files`
writes `runs/<run_id>/meta.json` + `runs/<run_id>/<task_id>/{task.yaml,
trajectory.jsonl, verdict.json, meta.json}` byte-for-byte from the database —
the brief requires saved traces/verdicts in the snapshot, and `runs/` is
gitignored, so export is a mandatory packaging step either way. Round-trip
(test §10.6) proves export(import(x)) == x.

---

## 10. Testing strategy

**Rule: the existing 40 tests must stay green and unedited after every
phase.** They are the regression net for this refactor; any phase that breaks
them stops.

New file `tests/test_persistence_pg.py`, gated so the default suite still runs
with only PyYAML installed:

```python
@unittest.skipUnless(os.environ.get("BENCH_TEST_DB_URL"),
                     "set BENCH_TEST_DB_URL (docker compose up -d --wait)")
class PostgresStoreTests(unittest.TestCase): ...
```

Cases:

1. **Idempotent migrate** — `migrate()` twice, `schema_migrations` unchanged.
2. **Round-trip** — save → list → read; `read_trajectory_lines` is
   character-identical to what went in (the byte-for-byte claim).
3. **Duplicate run id** — `ValueError` matching `already exists` (parity with
   StoreTests:382-383).
4. **No partial run** — `create_run` with one invalid task (NOT NULL violation)
   → rollback; `list_run_ids` does not contain the run.
5. **Replay fidelity** — after `regrade_run`, source `trajectory_jsonl`
   unchanged, new run's copy identical, source verdict untouched
   (generalises ReplayTests:315-346 to the DB backend).
6. **Export/import round-trip** — `export(import(runs/))` byte-equal on
   `trajectory.jsonl` and `verdict.json`.
7. **Backend parity (the important one)** — run the same fixture batch through
   `FileStore` and `PostgresStore`, assert `report.run_detail(...)` outputs are
   deep-equal apart from run ids/timestamps. This is what lets us claim "every
   path uses the same store semantics" with evidence.

CLI check (manual, in the README): `BENCH_TEST_DB_URL=... python -m unittest
discover -s tests -v` → 40 + 7 green. Without the env var → 40 green, 7
skipped.

---

## 11. Documentation updates (with the implementation, not after)

| Doc | Change |
|---|---|
| `README.md` | Setup section: Docker requirement + versions (PyYAML 6.0.2, psycopg 3.3.9, postgres:16-alpine), `.env`, `compose up --wait`, `db` commands, `--store file` escape hatch, export-before-snapshot step. |
| `docs/plans/WALKTHROUGH.md` | New beat after P0: compose + health + restart-persistence; adjust the repo-layout section that describes `runs/` as the store to "export format". |
| `docs/plans/PHASES.md` | Stack line "Store: files under runs/..." → Postgres system of record, files as export. |
| `DECISIONS.md` | One line: Postgres as system of record, files as export; rejected dual-write for drift risk. |
| `docs/dev/GAP-PLAN.md` | GAP-02/03 → Fixed (with test ids); GAP-08 → Fixed once docs above are updated. |
| `docs/dev/IMPLEMENTATION-AUDIT.md` | AUD-11 → Fixed for both backends (rename/tx); note GAP-04 still open. |

---

## 12. Execution schedule against today's clock

Baseline: ~40 tests green now. Windows from the brief: lunch 12:30–13:00,
constraint card 13:30 (30 min for `CHANGE-RESPONSE.md`), stop features 14:40,
snapshot 15:00, showcase 15:15.

| Window | Phases | Est. | Ship criterion |
|---|---|---|---|
| **Now → 13:15** | **P0** Checkpoint commit of the current green tree (there are many uncommitted edits — this is the rollback anchor). **P1** compose + `.env*` + migrations + `db migrate/status` (zero behaviour change). **P2** store seam + `FileStore` + atomic rename; full suite green with no test edits. | ~45 min | 40 tests green, demo unchanged. |
| 13:30–14:00 | `CHANGE-RESPONSE.md` — DB work paused. | — | Card answered first; DB never eats this slot. |
| **14:00 → 14:15 hard cut** | **P3** `PostgresStore` + wire batch/report/replay/importer/server/CLI. **P4** PG tests, health block, export/import, README/WALKTHROUGH. | ~60 min (will not fully fit) | All of §14 acceptance. |
| 14:15–14:40 | If P4 acceptance passes: export-files, doc updates, final suite. If **any** item fails: `git reset` to the P0 checkpoint, delete the DB branch of work, keep only this plan document. | — | Honest state either way. |
| 14:40 | Feature freeze; 15:00 snapshot. | — | Snapshot contains DB work **only if acceptance is green**; otherwise file store exactly as today, plan doc records the direction. |

**Cut lines, in order:** (1) SQL aggregation / generated-column demo — never
needed for acceptance; (2) `db import-files` backfill — re-running `demo`
reproduces evidence; (3) the whole Postgres backend — revert to checkpoint;
**never cut** trace, verdict, replay, the 40 tests, or docs to buy time for
this. This is hygiene work; the essentials are already scored.

---

## 13. Risks and rollback

| Risk | Mitigation |
|---|---|
| Refactor breaks the 40-test net mid-flight | P0 checkpoint commit first; run the suite after P2 *before* writing any SQL store; path-or-store coercion means tests never change. |
| Half-wired store ships (files *and* DB disagree) | Single cut line at 14:15; acceptance checklist is all-or-nothing; no partial merge. |
| Judge machine has no Docker / port conflict | `--store file` documented escape hatch; host port overridable via `BENCH_DB_PORT`; unit tests need no database at all. |
| Byte-for-byte replay claim broken by a "helpful" `jsonb` column | Text column + test 10.2; the plan forbids `jsonb` for trajectories with the reason on the page. |
| Secrets: password in git | `.env` gitignored, `.env.example` placeholder only, `db status` masks the DSN, health never echoes it. Redaction (`store.redact`) still runs before every insert, identical to file writes. |
| GAP-04 unchanged | Honest note: moving evidence to Postgres does **not** redact `task.yaml`; the byte-for-byte snapshot contract still wins over scrubbing until we design hash-pinning. Listed as open in the audit. |
| Long transaction during batch | Fixture batches finish in seconds (6 tasks × ≤2 s timeout). If live-model adapters ever land, switch to staged rows + `status` — recorded as future work, not built now. |

**Rollback:** everything lands on one branch/commit series after the P0
checkpoint; reverting is `git reset --hard <checkpoint>` plus `docker compose
down`. No schema has been applied to anything a judge will run unless P4
passed.

---

## 14. Acceptance checklist (copy into the pre-snapshot run-through)

- [ ] `docker compose up -d --wait` → `db` healthy, no image pull.
- [ ] `python -m harness db status` → `postgres`, `001_init applied`, counts.
- [ ] `python -m harness demo --no-browser` → 8 runs (6 fixture + 2 replay)
      visible at `/api/runs`; `runs/` not written by the demo itself.
- [ ] `docker compose restart db` → `python -m harness list` still lists all
      runs; UI unchanged.
- [ ] `python -m harness replay <run> --grader reference` → source run's
      trajectory byte-identical (asserted by test), new run `kind: replay`,
      `replay_of` set, agent never called.
- [ ] `python -m harness db export-files` → `runs/` layout matches the file
      store's format byte-for-byte; this `runs/` goes into the snapshot.
- [ ] `python -m unittest discover -s tests -v` → **40 green with no database
      configured** (file backend).
- [ ] `BENCH_TEST_DB_URL=... python -m unittest discover -s tests -v` →
      **47 green** (40 + 7 PG, including backend parity).
- [ ] `/api/health` reports the backend honestly; password never appears in
      health, `db status`, logs or the snapshot.
- [ ] README documents dependency versions, compose workflow, `--store file`
      escape hatch, and export-before-snapshot.

---

## Appendix — defence crib sheet

**"Why Postgres and not just files?"**
Files were fine for six tasks and broke down where it matters: a crash
mid-batch left a partial run visible (our own GAP-03), a cleanup could delete
the evidence, and concurrent readers could see half-written JSON (AUD-11). One
transaction per run makes "no partial run" a database guarantee instead of a
hope, and the export command keeps every file-based workflow we already
documented.

**"Doesn't this break the offline requirement?"**
No — the image is already on the machine, `compose up` touches no network, and
the entire unit suite still runs with only PyYAML: the tests never configure a
database, so they exercise the file backend. Postgres is the *primary* path
when configured, the file store is the *documented escape hatch*, and both pass
the same parity test.

**"Where did the files go?"**
`runs/` is now an export format: `db export-files` reproduces the exact layout
for the snapshot and for anyone reading evidence without a database. The task
YAMLs, UI bundle and tests never moved.

**"Isn't two backends two codebases?"**
Two implementations of one 12-method interface, with a parity test asserting
they produce identical reports. The orchestration — runner, graders, replay,
report buckets, HTTP routes — is single-path and backend-agnostic.

**"Why is the trajectory a text column?"**
Because replay promises a byte-for-byte copy of the source trace. `jsonb`
silently reorders object keys; every replay would produce a file that differs
from its source at the byte level while claiming not to.

**"What is still weak?"**
`task.yaml` snapshots bypass redaction by contract (GAP-04) — a database does
not fix that; tripwire grammar remains two condition forms (AUD-13); and the
timeout path still abandons a daemon thread (AUD-10). We would fix GAP-04 next
by hashing the snapshot and storing the redacted copy for display.
