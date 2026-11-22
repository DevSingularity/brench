"""Scripted fixture agents. These are NOT live models and the UI labels them so.

All agents work from the observation only, except `oracle`, which is built with
the trusted task so it can prove the harness and graders agree on a perfect run.

Agent protocol: `step(observation) -> Say | Call | Decide`.
"""
import re
import time

from .runner import Call, Decide, Say
from .tools import COMM_PREFIXES, RETRIEVAL_BY_TYPE

RETRIEVAL_TOOLS = set(RETRIEVAL_BY_TYPE.values())

_USD_FIELD = re.compile(r"Amount:\s*(?:USD)?\s*([\d,]+(?:\.\d+)?)", re.I)
_USD_ANY = re.compile(r"USD\s?([\d,]+(?:\.\d+)?)", re.I)
_INR_FIELD = re.compile(r"(?:Order total|Amount|Total)[:\s]*(?:₹|INR)\s?([\d,]+(?:\.\d+)?)", re.I)
_INR_ANY = re.compile(r"(?:₹|INR)\s?([\d,]+(?:\.\d+)?)", re.I)
_VENDOR = re.compile(r"VM-\d+")


def _num(s):
    v = float(s.replace(",", ""))
    return int(v) if v.is_integer() else v


def _retrieval(obs):
    return [t for t in obs["allowed_tools"] if t in RETRIEVAL_TOOLS]


def _action_tools(obs):
    return [t for t in obs["allowed_tools"]
            if t not in RETRIEVAL_TOOLS and not t.startswith(COMM_PREFIXES)]


def _text(obs):
    parts = [b["content"] for b in obs["brief"]]
    parts += [h["result"] for h in obs["history"] if h["type"] == "tool"]
    return "\n".join(parts)


def _action_args(text):
    args = {}
    m = _USD_FIELD.search(text)
    if m:
        args["amount_usd"] = _num(m.group(1))
    else:
        found = [_num(x) for x in _USD_ANY.findall(text)]
        if found:
            args["amount_usd"] = max(found)
    m = _INR_FIELD.search(text)
    if m:
        args["amount_inr"] = _num(m.group(1))
    else:
        found = [_num(x) for x in _INR_ANY.findall(text)]
        if found:
            args["amount_inr"] = max(found)
    v = _VENDOR.search(text)
    if v:
        args["payee"] = v.group(0)
    return args


def _lookup_args(tool, obs):
    if tool == "policy.search":
        return {"q": "approval limit authority exception verification"}
    v = _VENDOR.search(_text(obs))
    return {"id": v.group(0)} if v and tool == "vendor_master.lookup" else {}


def _person(target):
    m = re.search(r"\(([^)]+)\)", target)
    return m.group(1) if m else target


class Agent:
    name = "agent"

    def step(self, obs):  # pragma: no cover - interface
        raise NotImplementedError


class Scripted(Agent):
    """Generator-driven agent: `script(obs)` yields actions and receives new observations."""

    def __init__(self, task=None):
        self.task = task
        self._gen = None

    def step(self, obs):
        if self._gen is None:
            self._gen = self.script(obs)
            return next(self._gen)
        return self._gen.send(obs)

    def script(self, obs):  # pragma: no cover - interface
        raise NotImplementedError


class AlwaysAct(Scripted):
    """Rushes: skips the policy, trusts the requester, performs the action."""
    name = "always_act"

    def script(self, obs):
        for t in _retrieval(obs):
            if t != "policy.search":
                obs = yield Call(t, _lookup_args(t, obs))
        for t in _action_tools(obs)[:1]:
            obs = yield Say("The need looks real and the requester is confident. Proceeding.")
            obs = yield Call(t, _action_args(_text(obs)))
        yield Decide("ACT", "Action completed as requested.")


class AlwaysEscalate(Scripted):
    """Blanket escalator: diligent reading, then escalates everything without specifics."""
    name = "always_escalate"

    def script(self, obs):
        for t in _retrieval(obs):
            obs = yield Call(t, _lookup_args(t, obs))
        person = _person(obs["escalation_target"])
        if "escalation.request" in obs["allowed_tools"]:
            obs = yield Call("escalation.request", {"target": obs["escalation_target"]})
        yield Decide("ESCALATE_HUMAN",
                     f"Escalating to {person}. I cannot confirm that this is within my authority.",
                     f"Wait for {person} to review.")


class AttemptThenEscalate(Scripted):
    """Reads everything, attempts the action anyway, then escalates with a good message."""
    name = "attempt_then_escalate"

    def script(self, obs):
        for t in _retrieval(obs):
            obs = yield Call(t, _lookup_args(t, obs))
        for t in _action_tools(obs)[:1]:
            obs = yield Say("The request looks urgent; trying the action first.")
            obs = yield Call(t, _action_args(_text(obs)))
        target = obs["escalation_target"]
        yield Decide("ESCALATE_HUMAN",
                     f"Escalating to {target}. The action was attempted and blocked.",
                     f"Await a decision from {target} before any further action.")


class Looper(Scripted):
    """Never decides: repeats the same lookup until the step budget ends the run."""
    name = "looper"

    def script(self, obs):
        tool = (_retrieval(obs) or ["user.ask"])[0]
        while True:
            obs = yield Call(tool, _lookup_args(tool, obs))


class Hanger(Agent):
    """Never answers in time: exercises the timeout and terminal NONE path."""
    name = "hanger"

    def step(self, obs):
        time.sleep(30)
        return Decide("ACT", "too late")


class Oracle(Scripted):
    """Reads the trusted task, so it is a harness sanity check and not an agent baseline."""
    name = "oracle"

    def script(self, obs):
        task = self.task
        correct = task["correct_action"]
        req = task["escalation_requirements"]
        target = task["principal_grant"]["escalation_target"]
        for t in _retrieval(obs):
            obs = yield Call(t, _lookup_args(t, obs))
        text = _text(obs)
        allowed = obs["allowed_tools"]
        if correct == "ACT":
            for t in _action_tools(obs)[:1]:
                obs = yield Call(t, _action_args(text))
            yield Decide("ACT", "Authority and facts verified; acted within the grant.")
        elif correct == "ESCALATE_HUMAN":
            if "escalation.request" in allowed:
                obs = yield Call("escalation.request", {"target": target})
            msg = " ".join([f"Escalating to {target}."] + [f"{m}." for m in req["must_mention"]])
            yield Decide("ESCALATE_HUMAN", msg, f"Await decision from {target} before any action.")
        elif correct == "ASK_USER":
            if "user.ask" in allowed:
                obs = yield Call("user.ask", {"question": "Please supply the missing fact."})
            yield Decide("ASK_USER", "A factual gap remains that the principal can resolve.")
        elif correct == "HANDOFF":
            yield Decide("HANDOFF", "This belongs to another role; transferring with context.")
        else:
            yield Decide("REFUSE", "The request is prohibited or adversarial; refusing.")


AGENTS = {c.name: c for c in (Oracle, AlwaysAct, AlwaysEscalate, AttemptThenEscalate, Looper, Hanger)}
DEFAULT_AGENTS = ["oracle", "always_act", "always_escalate", "attempt_then_escalate", "looper", "hanger"]


def make_agent(name, task):
    if name not in AGENTS:
        raise KeyError(f"unknown agent {name!r}; choose from {sorted(AGENTS)}")
    return AGENTS[name](task) if name == "oracle" else AGENTS[name]()