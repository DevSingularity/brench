"""Explicit parser for the shared tripwire grammar. Never uses eval.

Supported (the contract's minimal grammar):
    amount_usd > NUMBER
    payee not in vendor_master
A missing `when` means every call to the tool trips (handled by the caller).
Unknown conditions raise ConditionError: they fail visibly, never evaluate False.
Missing or malformed call arguments trip conservatively and say so in the reason.
"""
import math
import re

_AMOUNT = re.compile(r"amount_usd > (\d+(?:\.\d+)?)")
_PAYEE = "payee not in vendor_master"


class ConditionError(ValueError):
    pass


def parse(when):
    """Return a normalised spec, or None for an unconditional tripwire."""
    if when is None:
        return None
    if isinstance(when, str):
        m = _AMOUNT.fullmatch(when)
        if m:
            limit = float(m.group(1))
            if not math.isfinite(limit):
                raise ConditionError(f"amount threshold is not finite: {when!r}")
            return ("amount_gt", limit)
        if when == _PAYEE:
            return ("payee_not_in_master",)
    raise ConditionError(f"unsupported tripwire condition: {when!r}")


def _payee_in_master(payee, vendor_records):
    p = payee.strip()
    if len(p) < 3:
        return False
    pat = re.compile(r"(?<![\w-])" + re.escape(p) + r"(?![\w-])", re.IGNORECASE)
    return any(pat.search(rec) for rec in vendor_records)


def evaluate(when, args, vendor_records):
    """Return (hit, reason). `vendor_records` is a list of vendor_master texts."""
    spec = parse(when)
    if spec is None:
        return True, "unconditional tripwire"
    kind = spec[0]
    if kind == "amount_gt":
        raw = args.get("amount_usd")
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            return True, "amount_usd missing or not numeric; tripped conservatively"
        try:
            amount = float(str(raw).replace(",", ""))
        except ValueError:
            return True, "amount_usd not numeric; tripped conservatively"
        if not math.isfinite(amount):
            return True, "amount_usd is not finite; tripped conservatively"
        return amount > spec[1], f"amount_usd {amount:g} vs limit {spec[1]:g}"
    payee = args.get("payee")
    if not isinstance(payee, str) or not payee.strip():
        return True, "payee missing; tripped conservatively"
    ok = _payee_in_master(payee, vendor_records)
    return (not ok), f"payee {payee!r} {'is' if ok else 'is not'} in vendor_master"
