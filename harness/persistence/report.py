"""Aggregate saved runs for the results UI. Counts and denominators only, never one score.

Unauthorised action, over-escalation and other errors are reported separately.
Cells with no task stay absent from the matrix so the UI can show them as unrun.
"""
import yaml

from ..core import contract, runner
from . import store

TASK_FIELDS = ("domain", "category", "stakes_tier", "pair_id", "pair_role")


def _bucket():
    return {"n": 0, "label_match": 0, "correct": 0, "unauthorised": 0, "over_escalation": 0,
            "other_errors": 0, "outcomes": {}}


def _add(b, row):
    b["n"] += 1
    b["label_match"] += int(row["action_match"])
    o = row["outcome"]
    b["outcomes"][o] = b["outcomes"].get(o, 0) + 1
    if o.startswith("correct_"):
        b["correct"] += 1
    elif o == contract.UNAUTHORISED:
        b["unauthorised"] += 1
    elif o == contract.OVER_ESCALATION:
        b["over_escalation"] += 1
    else:
        b["other_errors"] += 1


def _rows(runs_dir, run_id):
    rows = []
    base = store.run_dir(runs_dir, run_id)
    for tid in store.task_ids(runs_dir, run_id):
        task = yaml.safe_load((base / tid / "task.yaml").read_text(encoding="utf-8"))
        v = store.read_json(base / tid / "verdict.json")
        row = {k: task.get(k) for k in TASK_FIELDS}
        row.update(task_id=tid, declared_action=v["declared_action"], correct_action=v["correct_action"],
                   action_match=v["action_match"], outcome=v["outcome"], tripwires_hit=v["tripwires_hit"],
                   evidence_steps=v["evidence_steps"], escalation_quality=v["escalation_quality"],
                   reward=v["reward"], grader_version=v["grader_version"])
        rows.append(row)
    return rows


def run_summary(runs_dir, run_id):
    meta = store.load_run_meta(runs_dir, run_id)
    total = _bucket()
    for row in _rows(runs_dir, run_id):
        _add(total, row)
    return {**meta, "totals": total}


def run_detail(runs_dir, run_id):
    meta = store.load_run_meta(runs_dir, run_id)
    rows = _rows(runs_dir, run_id)
    totals, matrix, stakes = _bucket(), {}, {}
    for row in rows:
        _add(totals, row)
        _add(matrix.setdefault(row["category"], {}).setdefault(row["domain"], _bucket()), row)
        _add(stakes.setdefault(str(row["stakes_tier"]), _bucket()), row)
    pairs = {}
    for row in rows:
        pairs.setdefault(row["pair_id"], []).append(row)
    complete = [p for p in pairs.values() if sorted(r["pair_role"] for r in p) == ["act_case", "escalate_case"]]
    consistent = [p for p in complete if all(r["action_match"] and not r["tripwires_hit"] for r in p)]
    return {"meta": meta, "totals": totals, "matrix": matrix, "stakes": stakes, "rows": rows,
            "pairs": {"complete": len(complete), "consistent": len(consistent)},
            "categories": contract.CATEGORIES, "domains": contract.DOMAINS, "decisions": contract.DECISIONS}


def task_detail(runs_dir, run_id, task_id):
    from ..core.runner import initial_observation

    base = store.run_dir(runs_dir, run_id) / store.safe(task_id)
    if not (base / "verdict.json").is_file():
        raise FileNotFoundError(f"task {task_id!r} not found in run {run_id!r}")
    task = yaml.safe_load((base / "task.yaml").read_text(encoding="utf-8"))
    run = store.load_run_meta(runs_dir, run_id)
    source_id = run.get("replay_of") or run_id
    grade_history = []
    for candidate_id in store.list_run_ids(runs_dir):
        candidate = store.load_run_meta(runs_dir, candidate_id)
        if candidate_id != source_id and candidate.get("replay_of") != source_id:
            continue
        verdict_path = store.run_dir(runs_dir, candidate_id) / store.safe(task_id) / "verdict.json"
        if not verdict_path.is_file():
            continue
        grade = store.read_json(verdict_path)
        grade_history.append({"run_id": candidate_id, "grader": candidate.get("grader"),
                              "grader_version": grade.get("grader_version"),
                              "outcome": grade.get("outcome"), "action_match": grade.get("action_match"),
                              "grader_notes": grade.get("grader_notes"), "is_current": candidate_id == run_id,
                              "is_source": candidate_id == source_id})
    grade_history.sort(key=lambda item: (not item["is_source"], item["run_id"]))
    return {
        "task": task,
        "task_yaml": (base / "task.yaml").read_text(encoding="utf-8"),
        "agent_view": initial_observation(task),
        "trajectory": store.read_jsonl(base / "trajectory.jsonl"),
        "verdict": store.read_json(base / "verdict.json"),
        "meta": store.read_json(base / "meta.json"),
        "run": run,
        "grade_history": grade_history,
    }
