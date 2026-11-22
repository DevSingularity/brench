"""On-disk run store.

runs/<run_id>/meta.json                      run identity, model, grader, seed, kind
runs/<run_id>/<task_id>/task.yaml            trusted task snapshot (byte-for-byte)
runs/<run_id>/<task_id>/trajectory.jsonl     full trace, never rewritten by grading
runs/<run_id>/<task_id>/verdict.json         one verdict per grader pass
runs/<run_id>/<task_id>/meta.json            per-task details (steps, simulator effects)
"""
import json
import re
import shutil
from pathlib import Path

SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_KEY = re.compile(r"(api[_-]?key|token|secret|authorization|password|passwd)", re.I)
_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}", re.I),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
]


def safe(name):
    if not isinstance(name, str) or not SAFE.match(name):
        raise ValueError(f"invalid name {name!r}: use letters, digits, '.', '_' or '-'")
    return name


def redact(obj):
    """Mask credentials in anything written to disk."""
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if _KEY.search(str(k)) and not isinstance(v, (dict, list)) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, str):
        for p in _PATTERNS:
            obj = p.sub("[REDACTED]", obj)
    return obj


def run_dir(runs_dir, run_id):
    return Path(runs_dir) / safe(run_id)


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_run_meta(runs_dir, run_id, meta):
    _write_json(run_dir(runs_dir, run_id) / "meta.json", redact(meta))


def reset_run(runs_dir, run_id):
    d = run_dir(runs_dir, run_id)
    if d.exists():
        shutil.rmtree(d)


def save_task_run(runs_dir, run_id, task_id, task_text, trajectory, verdict, meta):
    d = run_dir(runs_dir, run_id) / safe(task_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "task.yaml").write_text(task_text, encoding="utf-8")
    lines = [json.dumps(redact(r), ensure_ascii=False) for r in trajectory]
    (d / "trajectory.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_json(d / "verdict.json", redact(verdict))
    _write_json(d / "meta.json", redact(meta))


def list_run_ids(runs_dir):
    root = Path(runs_dir)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "meta.json").is_file())


def load_run_meta(runs_dir, run_id):
    return json.loads((run_dir(runs_dir, run_id) / "meta.json").read_text(encoding="utf-8"))


def task_ids(runs_dir, run_id):
    d = run_dir(runs_dir, run_id)
    return sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "verdict.json").is_file())


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
