"""Load task YAML files from disk, validate them, and report clear errors.

Nothing here is specific to the example pair: hidden tasks are loaded the same way.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .contract import validate_task

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class LoadedTask:
    doc: dict
    path: Path
    text: str


@dataclass
class LoadResult:
    tasks: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _expand(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted([*p.glob("*.yaml"), *p.glob("*.yml")])
        else:
            files.append(p)
    return files


def load_tasks(paths):
    res = LoadResult()
    files = _expand(paths)
    if not files:
        res.errors.append("no task files found in: " + ", ".join(map(str, paths)))
        return res
    seen = {}
    pairs = {}
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            res.errors.append(f"{f}: cannot read file: {exc}")
            continue
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            res.errors.append(f"{f}: invalid YAML: {str(exc).splitlines()[0]}")
            continue
        errs = validate_task(doc)
        if errs:
            res.errors.append(f"{f}: " + "; ".join(errs))
            continue
        tid = doc["id"]
        if not SAFE_ID.match(tid):
            res.errors.append(f"{f}: id {tid!r} must match {SAFE_ID.pattern} (it is used as a folder name)")
            continue
        if tid in seen:
            res.errors.append(f"{f}: duplicate task id {tid!r} (first seen in {seen[tid]})")
            continue
        seen[tid] = f
        pairs.setdefault(doc["pair_id"], []).append(doc["pair_role"])
        res.tasks.append(LoadedTask(doc=doc, path=f, text=text))
    for pid, roles in pairs.items():
        if sorted(roles) != ["act_case", "escalate_case"]:
            res.warnings.append(f"pair {pid!r} is incomplete or duplicated: {roles}")
    return res
