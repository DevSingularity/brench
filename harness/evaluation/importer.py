"""Import a trace produced outside the harness (manual chat run, live API run) and grade it.

Use this for chat-only runs: save the exact prompts and responses separately, convert
the run to trajectory.jsonl, then import it here. It is labelled 'manual' (or whatever
--kind says), never 'fixture', so the UI does not present it as a scripted agent.
"""
import platform
from datetime import datetime, timezone

from .. import __version__
from ..core.contract import validate_trajectory
from ..core.tasks import load_tasks
from ..persistence import store
from . import graders


def import_trace(task_path, trajectory_path, *, runs_dir, model, run_id, kind="manual",
                 grader=graders.DEFAULT, seed=None, aliases=None, note=""):
    loaded = load_tasks([task_path])
    if loaded.errors:
        raise ValueError("; ".join(loaded.errors))
    lt = loaded.tasks[0]
    traj = store.read_jsonl(trajectory_path)
    aliases = aliases or {}
    for rec in traj:
        if rec.get("type") == "terminal" and rec.get("declared_action") in aliases:
            rec["declared_action"] = aliases[rec["declared_action"]]
    errs = validate_trajectory(traj)
    if errs:
        raise ValueError("trajectory is invalid: " + "; ".join(errs))
    verdict = graders.get(grader)(lt.doc, traj, model=model, run_id=run_id, seed=seed)
    store.save_task_run(runs_dir, run_id, lt.doc["id"], lt.text, traj, verdict, {
        "task_id": lt.doc["id"], "run_id": run_id, "model": model, "seed": seed,
        "records": len(traj), "source_file": str(trajectory_path),
    })
    meta_path = store.run_dir(runs_dir, run_id) / "meta.json"
    ids = [lt.doc["id"]]
    if meta_path.is_file():
        ids = sorted(set(store.load_run_meta(runs_dir, run_id)["task_ids"]) | set(ids))
    store.write_run_meta(runs_dir, run_id, {
        "run_id": run_id, "model": model, "agent": None, "kind": kind,
        "note": note or f"Imported {kind} trace. Prompts and outputs should be saved alongside it.",
        "grader": grader, "grader_version": graders.VERSIONS[grader], "seed": seed,
        "task_ids": ids, "replay_of": None, "harness_version": __version__,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
    })
    return verdict