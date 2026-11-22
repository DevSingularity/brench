"""Vendored reference grader implementation from the supplied contract pack.

Known limits, documented by the organiser: it trusts the tripwire hits recorded in
the trace, matches message tokens with a plain substring test and requires the full
escalation_target string, and counts distinct retrieval tools as 'evidence'.
It stays in the registry as the baseline that `strict` is compared against.
"""
from .. import _reference_grader as _ref

VERSION = "fixture-1.2.0"


def grade(task, trajectory, *, model="fixture/model", run_id="fixture", seed=0):
    return _ref.grade(task, trajectory, model=model, run_id=run_id, seed=seed)
