"""Single entry point to the vendored task and trace contract validator."""
from pathlib import Path

from . import _contract_validator as _v

ROOT = Path(__file__).resolve().parents[2]

ACTIONS = set(_v.ACTIONS)
CATEGORIES = sorted(_v.CATEGORIES)
DOMAINS = sorted(_v.DOMAINS)
CORRECT = dict(_v.CORRECT)
OUTCOMES = set(_v.OUTCOMES)

_ORDER = ["ACT", "ASK_USER", "ESCALATE_HUMAN", "REFUSE", "HANDOFF"]
DECISIONS = [a for a in _ORDER if a in ACTIONS] + sorted(ACTIONS - set(_ORDER))

validate_task = _v.validate_task
validate_trajectory = _v.validate_trajectory
validate_verdict = _v.validate_verdict
read_and_validate = _v.read_and_validate

# Outcome groups used by reports. Unauthorised action and over-escalation are
# reported separately from everything else, as the shared contract requires.
UNAUTHORISED = "unauthorised_action"
OVER_ESCALATION = "over_escalation"
OTHER_ERRORS = ["wrong_decision", "wrong_target", "no_decision", "insufficient_evidence"]
