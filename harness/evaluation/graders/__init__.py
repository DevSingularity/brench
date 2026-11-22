"""Grader registry. Every grader implements the shared interface:

    grade(task, trajectory, *, model, run_id, seed) -> verdict dict

Add a grader by dropping a module here and registering it below.
"""
from . import reference, strict

GRADERS = {"strict": strict.grade, "reference": reference.grade}
VERSIONS = {"strict": strict.VERSION, "reference": reference.VERSION}
DEFAULT = "strict"


def get(name):
    if name not in GRADERS:
        raise KeyError(f"unknown grader {name!r}; choose from {sorted(GRADERS)}")
    return GRADERS[name]
