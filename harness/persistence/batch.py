"""Run one agent over a task set, grade each trajectory, and save the evidence."""
import platform
import os
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..core.agents import make_agent
from ..core.runner import run_task_isolated
from ..evaluation import graders
from . import store


class BatchCancelled(Exception):
    pass

FIXTURE_NOTE = "Scripted fixture agent. Not a live model; results say nothing about any real model."


def run_batch(loaded_tasks, agent_name, *, runs_dir, run_id=None, seed=0, grader=graders.DEFAULT,
              max_steps=20, timeout_s=30.0, on_event=None, source_labels=None, job_id=None, should_cancel=None):
    grade = graders.get(grader)
    base_run_id = run_id or f"{agent_name}-seed{seed}"
    if run_id is not None:
        run_path = store.run_dir(runs_dir, run_id)
        if run_path.exists():
            raise ValueError(f"run {run_id!r} already exists; choose a new run id to preserve prior evidence")
    else:
        run_id = base_run_id
        run_path = store.run_dir(runs_dir, run_id)
        if run_path.exists():
            while run_path.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                run_id = f"{base_run_id}-{stamp}"
                run_path = store.run_dir(runs_dir, run_id)
    Path(runs_dir).mkdir(parents=True, exist_ok=True)
    run_path.mkdir(exist_ok=False)
    model = f"fixture/{agent_name}"
    ids = []
    meta = {
        "run_id": run_id, "model": model, "agent": agent_name, "kind": "fixture", "note": FIXTURE_NOTE,
        "grader": grader, "grader_version": graders.VERSIONS[grader], "seed": seed,
        "max_steps": max_steps, "timeout_s": timeout_s, "task_ids": ids,
        "expected_task_ids": [lt.doc["id"] for lt in loaded_tasks], "status": "running", "replay_of": None,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "harness_version": __version__, "python": platform.python_version(),
    }
    if job_id:
        meta["job_id"] = job_id
        meta["owner_pid"] = os.getpid()
    store.write_run_meta(runs_dir, run_id, meta)
    try:
        for lt in loaded_tasks:
            if should_cancel and should_cancel():
                raise BatchCancelled("Evaluation cancelled between tasks; completed task evidence was preserved.")
            task = lt.doc
            agent = make_agent(agent_name, task)
            if on_event:
                on_event({"type": "task_started", "stage": "running", "task_id": task["id"],
                          "message": "Fixture agent is running against mock tools."})
            result = run_task_isolated(task, agent, max_steps=max_steps, timeout_s=timeout_s,
                              on_record=(lambda record, tid=task["id"]: on_event({"type": "trace_record", "task_id": tid,
                                                                                 "record": record})) if on_event else None)
            if on_event:
                on_event({"type": "stage", "stage": "grading", "task_id": task["id"],
                          "message": "Applying the selected grader to the saved-format trace."})
            verdict = grade(task, result.trajectory, model=model, run_id=run_id, seed=seed)
            if on_event:
                on_event({"type": "stage", "stage": "persisting", "task_id": task["id"],
                          "records": len(result.trajectory), "message": "Persisting task snapshot, full trace, and verdict."})
            store.save_task_run(runs_dir, run_id, task["id"], lt.text, result.trajectory, verdict, {
                "task_id": task["id"], "run_id": run_id, "model": model, "agent": agent_name, "seed": seed,
                "records": len(result.trajectory), "simulator_effects": result.effects,
                "source_file": (source_labels or {}).get(task["id"], str(lt.path)),
            })
            ids.append(task["id"])
            meta["task_ids"] = list(ids)
            store.write_run_meta(runs_dir, run_id, meta)
            if on_event:
                on_event({"type": "task_graded", "task_id": task["id"], "outcome": verdict["outcome"],
                          "grader_version": verdict["grader_version"]})
    except BaseException as exc:
        meta.update(status="cancelled" if isinstance(exc, BatchCancelled) else "failed",
                    error=f"{type(exc).__name__}: {exc}", task_ids=list(ids),
                    finished=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        store.write_run_meta(runs_dir, run_id, meta)
        raise
    meta.update(status="completed", task_ids=list(ids),
                finished=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    store.write_run_meta(runs_dir, run_id, meta)
    return run_id
