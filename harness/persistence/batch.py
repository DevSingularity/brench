"""Run one agent over a task set, grade each trajectory, and save the evidence."""
import platform
from datetime import datetime, timezone

from .. import __version__
from ..core.agents import make_agent
from ..core.runner import run_task
from ..evaluation import graders
from . import store

FIXTURE_NOTE = "Scripted fixture agent. Not a live model; results say nothing about any real model."


def run_batch(loaded_tasks, agent_name, *, runs_dir, run_id=None, seed=0, grader=graders.DEFAULT,
              max_steps=20, timeout_s=30.0):
    grade = graders.get(grader)
    run_id = run_id or f"{agent_name}-seed{seed}"
    model = f"fixture/{agent_name}"
    store.reset_run(runs_dir, run_id)
    ids = []
    for lt in loaded_tasks:
        task = lt.doc
        agent = make_agent(agent_name, task)
        result = run_task(task, agent, max_steps=max_steps, timeout_s=timeout_s)
        verdict = grade(task, result.trajectory, model=model, run_id=run_id, seed=seed)
        store.save_task_run(runs_dir, run_id, task["id"], lt.text, result.trajectory, verdict, {
            "task_id": task["id"], "run_id": run_id, "model": model, "agent": agent_name, "seed": seed,
            "records": len(result.trajectory), "simulator_effects": result.effects,
            "source_file": str(lt.path),
        })
        ids.append(task["id"])
    store.write_run_meta(runs_dir, run_id, {
        "run_id": run_id, "model": model, "agent": agent_name, "kind": "fixture", "note": FIXTURE_NOTE,
        "grader": grader, "grader_version": graders.VERSIONS[grader], "seed": seed,
        "max_steps": max_steps, "timeout_s": timeout_s, "task_ids": ids, "replay_of": None,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "harness_version": __version__, "python": platform.python_version(),
    })
    return run_id
