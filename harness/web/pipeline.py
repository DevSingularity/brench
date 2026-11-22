"""Local browser-run orchestration for the fixture harness."""
import math
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..core.tasks import load_tasks
from ..persistence import batch, report, store

MAX_FILES = 32
MAX_TOTAL_BYTES = 2_000_000
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]*\.ya?ml$", re.I)


def _validated_files(files):
    if not isinstance(files, list) or not files:
        raise ValueError("Choose at least one YAML task file.")
    if len(files) > MAX_FILES:
        raise ValueError(f"Upload at most {MAX_FILES} task files at a time.")
    normalized, names, total = [], set(), 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("content"), str):
            raise ValueError("Each file must include a name and text content.")
        name = Path(item["name"]).name
        if not SAFE_FILENAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a supported YAML filename.")
        if name.casefold() in names:
            raise ValueError(f"Duplicate filename: {name}")
        names.add(name.casefold())
        total += len(item["content"].encode("utf-8"))
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Combined task files exceed the 2 MB limit.")
        if "\ufffd" in item["content"]:
            raise ValueError(f"{name}: file is not valid UTF-8 text.")
        normalized.append({"name": name, "content": item["content"]})
    return normalized


def validate_files(files):
    from ..core.runner import initial_observation

    files = _validated_files(files)
    with tempfile.TemporaryDirectory(prefix="brench-tasks-") as tmp:
        for item in files:
            (Path(tmp) / item["name"]).write_text(item["content"], encoding="utf-8")
        result = load_tasks([tmp])
    issues = []
    for error in result.errors:
        file = Path(error.split(":", 1)[0]).name
        detail = error.split(": ", 1)[1] if ": " in error else error
        field, separator, message = detail.partition(": ")
        issues.append({"file": file, "field": field if separator and not field.startswith(("invalid YAML", "cannot read")) else None,
                       "message": message if separator else detail})
    pairs = {}
    for task in result.tasks:
        pair = pairs.setdefault(task.doc["pair_id"], {"pair_id": task.doc["pair_id"], "roles": [], "task_ids": []})
        pair["roles"].append(task.doc["pair_role"])
        pair["task_ids"].append(task.doc["id"])
    for warning in result.warnings:
        pair_id = warning.split("'", 2)[1] if "'" in warning else warning
        pairs.setdefault(pair_id, {"pair_id": pair_id, "roles": [], "task_ids": []})["warning"] = warning
    for pair in pairs.values():
        pair["complete"] = sorted(pair["roles"]) == ["act_case", "escalate_case"]
    return {"valid": not result.errors and bool(result.tasks),
            "files": [f["name"] for f in files],
            "tasks": [{"id": t.doc["id"], "domain": t.doc["domain"], "category": t.doc["category"],
                       "stakes_tier": t.doc["stakes_tier"], "pair_id": t.doc["pair_id"],
                       "pair_role": t.doc["pair_role"], "agent_observation": initial_observation(t.doc),
                       "grader_only": {"correct_action": t.doc["correct_action"], "rationale": t.doc["rationale"],
                                       "pair_id": t.doc["pair_id"], "pair_role": t.doc["pair_role"],
                                       "tripwires": t.doc["tripwires"],
                                       "escalation_requirements": t.doc["escalation_requirements"],
                                       "contamination_controls": t.doc["contamination_controls"]}}
                      for t in result.tasks],
            "errors": result.errors, "issues": issues, "warnings": result.warnings,
            "pair_coverage": list(pairs.values())}


class PipelineJobs:
    """In-process bounded-by-one local job registry; evidence itself stays in the run store."""
    def __init__(self, runs_dir):
        self.runs_dir = Path(runs_dir)
        self.jobs_dir = self.runs_dir / ".pipeline-jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._jobs = {}
        self._cancel = {}

    def _save(self, job):
        path = self.jobs_dir / f"{job['job_id']}.json"
        store._write_json(path, {k: v for k, v in job.items() if k != "input_files"})

    def create(self, payload):
        files = _validated_files(payload.get("files"))
        validation = validate_files(files)
        if not validation["valid"]:
            raise ValueError("Task validation failed: " + "; ".join(validation["errors"]))
        from ..core.agents import AGENTS
        from ..evaluation import graders
        agent = payload.get("agent", "oracle")
        grader = payload.get("grader", graders.DEFAULT)
        if agent not in AGENTS:
            raise ValueError(f"Unknown fixture agent {agent!r}.")
        if grader not in graders.GRADERS:
            raise ValueError(f"Unknown grader {grader!r}.")
        seed = payload.get("seed", 0)
        max_steps = payload.get("max_steps", 20)
        timeout_s = payload.get("timeout_s", 2.0)
        if type(seed) is not int:
            raise ValueError("seed must be an integer.")
        if type(max_steps) is not int or max_steps < 1 or max_steps > 500:
            raise ValueError("max_steps must be an integer between 1 and 500.")
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
            raise ValueError("timeout_s must be between 0 and 300 seconds.")
        try:
            timeout_s = float(timeout_s)
        except (OverflowError, ValueError) as exc:
            raise ValueError("timeout_s must be between 0 and 300 seconds.") from exc
        if not math.isfinite(timeout_s) or timeout_s <= 0 or timeout_s > 300:
            raise ValueError("timeout_s must be between 0 and 300 seconds.")
        run_id = "ui-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        job = {"job_id": uuid.uuid4().hex, "run_id": run_id, "status": "queued", "stage": "queued",
               "created": datetime.now(timezone.utc).isoformat(), "config": {"agent": agent, "grader": grader,
               "seed": seed, "max_steps": max_steps, "timeout_s": timeout_s, "task_ids": [x["id"] for x in validation["tasks"]]},
               "events": [], "error": None, "input_files": files}
        with self._lock:
            if any(existing["status"] in ("queued", "running", "cancelling") for existing in self._jobs.values()):
                raise ValueError("A pipeline is already running. Wait for it to finish before starting another.")
            self._jobs[job["job_id"]] = job
            self._cancel[job["job_id"]] = threading.Event()
            store._write_json(self.jobs_dir / f"{job['job_id']}.input.json", files)
            self._save(job)
        threading.Thread(target=self._run, args=(job["job_id"], files), daemon=True).start()
        return self.get(job["job_id"])

    def _emit(self, job_id, event):
        with self._lock:
            job = self._jobs[job_id]
            event = {"sequence": len(job["events"]), "at": datetime.now(timezone.utc).isoformat(), **event}
            job["events"].append(event)
            if event.get("stage"):
                job["stage"] = event["stage"]
            self._save(job)

    def _run(self, job_id, files):
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
        self._emit(job_id, {"stage": "loading", "message": "Loading the submitted task files."})
        try:
            with tempfile.TemporaryDirectory(prefix="brench-run-") as tmp:
                for item in files:
                    (Path(tmp) / item["name"]).write_text(item["content"], encoding="utf-8")
                loaded = load_tasks([tmp])
                if loaded.errors or not loaded.tasks:
                    raise ValueError("; ".join(loaded.errors) or "No valid tasks found.")
                self._emit(job_id, {"stage": "validated", "message": f"Validated {len(loaded.tasks)} task(s)."})
                self._emit(job_id, {"stage": "dispatching", "message": "Starting scripted fixture agent(s)."})
                config = job["config"]
                if self._cancel[job_id].is_set():
                    raise batch.BatchCancelled("Evaluation cancelled before the first task started.")
                self._emit(job_id, {"stage": "running", "message": "Running mock tools and recording the trace."})
                rid = batch.run_batch(loaded.tasks, config["agent"], runs_dir=self.runs_dir, run_id=job["run_id"],
                                      seed=config["seed"], grader=config["grader"], max_steps=config["max_steps"],
                                      timeout_s=config["timeout_s"], on_event=lambda e: self._emit(job_id, e),
                                      source_labels={t.doc["id"]: t.path.name for t in loaded.tasks}, job_id=job_id,
                                      should_cancel=self._cancel[job_id].is_set)
            summary = report.run_summary(self.runs_dir, rid)
            with self._lock:
                job["status"] = "completed"
                job["summary"] = summary
            self._emit(job_id, {"stage": "completed", "message": "Trace persisted and all tasks graded."})
        except BaseException as exc:  # preserve the job failure for UI inspection
            partial_summary = None
            try:
                if (store.run_dir(self.runs_dir, job["run_id"]) / "meta.json").is_file():
                    partial_summary = report.run_summary(self.runs_dir, job["run_id"])
            except (OSError, ValueError, KeyError):
                pass
            with self._lock:
                cancelled = self._cancel.get(job_id) and self._cancel[job_id].is_set()
                job["status"] = "cancelled" if cancelled else "failed"
                job["stage"] = job["status"]
                job["error"] = f"{type(exc).__name__}: {exc}"
                job["partial_summary"] = partial_summary
            self._emit(job_id, {"stage": job["stage"], "message": str(exc)})

    def get(self, job_id):
        with self._lock:
            import copy
            if job_id in self._jobs:
                public = copy.deepcopy(self._jobs[job_id])
                public.pop("input_files", None)
                return public
        saved = self.jobs_dir / f"{job_id}.json"
        if saved.is_file():
            job = store.read_json(saved)
            if job.get("status") in ("queued", "running"):
                job.update(status="interrupted", stage="interrupted",
                           error="Server stopped before this evaluation finished. Saved task evidence is available; retry creates a new run.")
                self._save(job)
                run_meta_path = store.run_dir(self.runs_dir, job["run_id"]) / "meta.json"
                if run_meta_path.is_file():
                    meta = store.read_json(run_meta_path)
                    meta.update(status="interrupted", error=job["error"])
                    store.write_run_meta(self.runs_dir, job["run_id"], meta)
            run_dir = store.run_dir(self.runs_dir, job["run_id"])
            if (run_dir / "meta.json").is_file() and job.get("status") in ("interrupted", "failed", "cancelled"):
                job["partial_summary"] = report.run_summary(self.runs_dir, job["run_id"])
            job.pop("input_files", None)
            return job
        return self._recover(job_id)

    def cancel(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError("Only jobs running in this server process can be cancelled.")
            if job["status"] not in ("queued", "running"):
                raise ValueError(f"Cannot cancel a {job['status']} job.")
            self._cancel[job_id].set()
            job["status"] = "cancelling"
            job["stage"] = "cancelling"
            self._save(job)
        self._emit(job_id, {"stage": "cancelling", "message": "Cancellation requested; the current task will finish or reach its timeout, then the batch stops."})
        return self.get(job_id)

    def retry(self, job_id):
        saved = self.jobs_dir / f"{job_id}.json"
        if not saved.is_file():
            raise FileNotFoundError(f"pipeline job {job_id!r} not found")
        job = store.read_json(saved)
        input_path = self.jobs_dir / f"{job_id}.input.json"
        if not input_path.is_file():
            raise ValueError("Original task files are unavailable for retry.")
        files = store.read_json(input_path)
        return self.create({**job["config"], "files": files})

    def _recover(self, job_id):
        meta = None
        run_id = None
        for candidate in store.list_run_ids(self.runs_dir):
            candidate_meta = store.load_run_meta(self.runs_dir, candidate)
            if candidate_meta.get("job_id") == job_id:
                meta, run_id = candidate_meta, candidate
                break
        if meta is None:
            raise FileNotFoundError(f"pipeline job {job_id!r} not found")

        status = meta.get("status", "completed")
        error = meta.get("error")
        if status == "interrupted":
            status = "failed"
        if status == "running" and not _process_alive(meta.get("owner_pid")):
            status = "failed"
            error = "The server stopped before this pipeline completed. Saved task evidence is available below."
            meta.update(status="interrupted", error=error,
                        finished=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            store.write_run_meta(self.runs_dir, run_id, meta)
            status = "failed"

        events = []
        def emit(event):
            events.append({"sequence": len(events), "at": event.pop("at", meta.get("created")), **event})

        emit({"stage": "loading", "message": "Task files were loaded for this run."})
        emit({"stage": "validated", "message": f"Validated {len(meta.get('expected_task_ids', []))} task(s)."})
        emit({"stage": "dispatching", "message": "Fixture agent configuration was recorded."})
        emit({"stage": "running", "message": "Reconstructed from saved task evidence; live progress events are no longer available."})
        saved_task_ids = meta.get("task_ids", [])
        for task_id in saved_task_ids:
            task_dir = store.run_dir(self.runs_dir, run_id) / store.safe(task_id)
            trajectory_path = task_dir / "trajectory.jsonl"
            if trajectory_path.is_file():
                emit({"type": "task_started", "stage": "running", "task_id": task_id,
                      "message": "Recovered task trace from saved evidence."})
                for record in store.read_jsonl(trajectory_path):
                    emit({"type": "trace_record", "task_id": task_id, "at": record.get("ts"), "record": record})
            verdict_path = task_dir / "verdict.json"
            if verdict_path.is_file():
                verdict = store.read_json(verdict_path)
                emit({"type": "stage", "stage": "grading", "task_id": task_id,
                      "message": "Saved verdict uses the recorded grader."})
                emit({"type": "stage", "stage": "persisting", "task_id": task_id,
                      "message": "Task snapshot, trajectory and verdict are saved."})
                emit({"type": "task_graded", "task_id": task_id, "outcome": verdict.get("outcome"),
                      "grader_version": verdict.get("grader_version")})
        if status == "completed":
            emit({"stage": "completed", "message": "Recovered completed run from saved evidence."})
        elif status == "failed":
            emit({"stage": "failed", "message": error or "Pipeline failed."})
        summary = report.run_summary(self.runs_dir, run_id)
        return {"job_id": job_id, "run_id": run_id, "status": status,
                "stage": "completed" if status == "completed" else "failed" if status == "failed" else "running",
                "created": meta.get("created"),
                "config": {"agent": meta.get("agent"), "grader": meta.get("grader"), "seed": meta.get("seed"),
                           "max_steps": meta.get("max_steps"), "timeout_s": meta.get("timeout_s"),
                           "task_ids": meta.get("expected_task_ids", [])},
                "events": events, "error": error,
                "summary": summary if status == "completed" else None,
                "partial_summary": summary if status == "failed" else None,
                "recovered": True}


def _process_alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
