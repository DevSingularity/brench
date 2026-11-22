"""Re-grade saved traces with a different grader. No agent or model is ever called.

The source run is left untouched. The trajectory and task snapshot are copied
byte-for-byte into a new run; only verdict.json and the run metadata differ.
"""
import shutil
from datetime import datetime, timezone

import yaml

from .. import __version__
from ..persistence import store
from . import graders


def regrade_run(src_run_id, grader_name, *, runs_dir, new_run_id=None):
    grade = graders.get(grader_name)
    src = store.run_dir(runs_dir, src_run_id)
    if not (src / "meta.json").is_file():
        raise FileNotFoundError(f"run {src_run_id!r} not found")
    meta = store.load_run_meta(runs_dir, src_run_id)
    explicit_new_id = new_run_id is not None
    new_run_id = new_run_id or f"{src_run_id}__{grader_name}"
    if new_run_id == src_run_id:
        raise ValueError("replay needs a different run id than its source")
    if explicit_new_id and store.run_dir(runs_dir, new_run_id).exists():
        raise ValueError(f"run {new_run_id!r} already exists; choose a new run id to preserve prior evidence")
    base_id = new_run_id
    if not explicit_new_id:
        suffix = 2
        while store.run_dir(runs_dir, new_run_id).exists():
            new_run_id = f"{base_id}-{suffix}"
            suffix += 1
    dst = store.run_dir(runs_dir, new_run_id)
    dst.mkdir(parents=True, exist_ok=False)
    ids = []
    for tid in store.task_ids(runs_dir, src_run_id):
        sdir, ddir = src / tid, dst / tid
        ddir.mkdir(parents=True)
        shutil.copyfile(sdir / "task.yaml", ddir / "task.yaml")
        shutil.copyfile(sdir / "trajectory.jsonl", ddir / "trajectory.jsonl")
        task = yaml.safe_load((sdir / "task.yaml").read_text(encoding="utf-8"))
        trajectory = store.read_jsonl(sdir / "trajectory.jsonl")
        verdict = grade(task, trajectory, model=meta["model"], run_id=new_run_id, seed=meta.get("seed"))
        store._write_json(ddir / "verdict.json", store.redact(verdict))
        tmeta = store.redact({**store.read_json(sdir / "meta.json"), "run_id": new_run_id})
        store._write_json(ddir / "meta.json", tmeta)
        ids.append(tid)
    new_meta = {**meta, "run_id": new_run_id, "kind": "replay", "grader": grader_name,
                "grader_version": graders.VERSIONS[grader_name], "task_ids": ids,
                "replay_of": src_run_id, "harness_version": __version__,
                "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "note": f"Saved traces of {src_run_id} re-graded with {grader_name}; no agent was run."}
    store.write_run_meta(runs_dir, new_run_id, new_meta)
    return new_run_id
