"""Run an agent against one task through mock tools and produce a trajectory.

The agent sees only: its role and grant, the visible brief, and the history of its
own actions and tool results. It never sees correct_action, rationale, pair info,
tripwire rules, escalation requirements or unrevealed context.
"""
import copy
import json
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .conditions import ConditionError
from .contract import ACTIONS
from .tools import Environment


@dataclass
class Say:
    content: str


@dataclass
class Call:
    tool: str
    args: dict = field(default_factory=dict)


@dataclass
class Decide:
    declared_action: str
    message: str = ""
    next_step: str = None


@dataclass
class RunResult:
    trajectory: list
    effects: list


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def initial_observation(task):
    """The only view of the task an agent is given. Allow-listed on purpose."""
    env = Environment(task)
    pg = task["principal_grant"]
    return {
        "role": pg["role"],
        "limits": copy.deepcopy(pg["limits"]),
        "allowed_tools": list(pg["allowed_tools"]),
        "escalation_target": pg["escalation_target"],
        "brief": copy.deepcopy(env.brief),
        "history": [],
    }


def _with_timeout(fn, timeout):
    """Run fn in a daemon thread. A hung agent cannot be killed, only abandoned."""
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - surfaced to the caller
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError
    if "error" in box:
        raise box["error"]
    return box["value"]


def run_task(task, agent, *, max_steps=20, timeout_s=30.0):
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be a positive finite number")
    env = Environment(task)
    obs = initial_observation(task)
    traj = []
    start = time.monotonic()

    def add(rec):
        rec = copy.deepcopy(rec)
        rec = {"step": len(traj), "ts": _now(), **rec}
        traj.append(rec)

    def finish(reason, message):
        add({"type": "terminal", "declared_action": "NONE", "message": message,
             "termination_reason": reason})
        return RunResult(traj, copy.deepcopy(env.effects))

    for _ in range(max_steps):
        remaining = timeout_s - (time.monotonic() - start)
        if remaining <= 0:
            return finish("timeout", f"Run exceeded the {timeout_s:g}s time limit.")
        snapshot = copy.deepcopy(obs)
        try:
            action = _with_timeout(lambda: agent.step(snapshot), remaining)
        except TimeoutError:
            return finish("timeout", f"Agent did not respond within the {timeout_s:g}s time limit.")
        except BaseException as exc:  # noqa: BLE001 - agent failures are evidence, not crashes
            return finish("model_error", f"Agent raised {type(exc).__name__}: {exc}")

        if isinstance(action, Say):
            add({"type": "model_message", "content": str(action.content)})
            obs["history"].append({"type": "say", "content": str(action.content)})
        elif isinstance(action, Call):
            if not isinstance(action.tool, str) or not action.tool.strip() or not isinstance(action.args, dict):
                return finish("model_error", "Agent returned a malformed tool call.")
            try:
                json.dumps(action.args, allow_nan=False)
            except (TypeError, ValueError):
                return finish("model_error", "Agent returned tool arguments that are not finite JSON data.")
            add({"type": "tool_call", "tool": action.tool, "args": action.args})
            try:
                ids, reasons = env.preflight(action.tool, action.args)
            except ConditionError as exc:
                add({"type": "tool_result", "tool": action.tool,
                     "result": f"HARNESS ERROR: {exc}", "tripwire_hit": None})
                return finish("aborted", f"Harness error while checking tripwires: {exc}")
            if ids:
                result = env.blocked_result(ids, reasons)
                add({"type": "tool_result", "tool": action.tool, "result": result,
                     "tripwire_hit": ids[0], "tripwires_hit": ids, "blocked": True})
            else:
                result = env.execute(action.tool, action.args)
                add({"type": "tool_result", "tool": action.tool, "result": result,
                     "tripwire_hit": None, "blocked": False})
            obs["history"].append({"type": "tool", "tool": action.tool,
                                   "args": copy.deepcopy(action.args), "result": result})
        elif isinstance(action, Decide):
            if not isinstance(action.declared_action, str) or action.declared_action not in ACTIONS:
                return finish("model_error", f"Invalid declared action {action.declared_action!r}.")
            rec = {"type": "terminal", "declared_action": action.declared_action,
                   "message": str(action.message or "")}
            if action.next_step:
                rec["next_step"] = str(action.next_step)
            add(rec)
            return RunResult(traj, copy.deepcopy(env.effects))
        else:
            return finish("model_error", f"Agent returned an unknown action type: {type(action).__name__}.")
    return finish("step_budget", f"Step budget of {max_steps} agent steps exhausted without a decision.")
