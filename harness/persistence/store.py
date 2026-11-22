"""On-disk run store.

runs/<run_id>/meta.json                      run identity, model, grader, seed, kind
runs/<run_id>/<task_id>/task.yaml            trusted task snapshot (byte-for-byte)
runs/<run_id>/<task_id>/trajectory.jsonl     full trace, never rewritten by grading
runs/<run_id>/<task_id>/verdict.json         one verdict per grader pass
runs/<run_id>/<task_id>/meta.json            per-task details (steps, simulator effects)
"""
import json
import os
import re
import shutil
import tempfile
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
        return {k: ("[REDACTED]" if _KEY.search(str(k)) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, str):
        for p in _PATTERNS:
            obj = p.sub("[REDACTED]", obj)
    return obj


def run_dir(runs_dir, run_id):
    return Path(runs_dir) / safe(run_id)


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_json(path, obj):
    _atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")


def write_run_meta(runs_dir, run_id, meta):
    _write_json(run_dir(runs_dir, run_id) / "meta.json", redact(meta))


def reset_run(runs_dir, run_id):
    d = run_dir(runs_dir, run_id)
    if d.exists():
        shutil.rmtree(d)


def save_task_run(runs_dir, run_id, task_id, task_text, trajectory, verdict, meta):
    d = run_dir(runs_dir, run_id) / safe(task_id)
    d.mkdir(parents=True, exist_ok=True)
    _atomic_write(d / "task.yaml", task_text)
    lines = [json.dumps(redact(r), ensure_ascii=False) for r in trajectory]
    _atomic_write(d / "trajectory.jsonl", "\n".join(lines) + "\n")
    _write_json(d / "meta.json", redact(meta))
    # verdict.json is the task commit marker; reports only include tasks after it exists.
    _write_json(d / "verdict.json", redact(verdict))


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
