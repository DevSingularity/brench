"""Command line entry point: python -m harness <command> ..."""
import argparse
import sys
import webbrowser
from pathlib import Path

from .evaluation import graders, importer, replay
from .persistence import batch, report, store
from .web import server
from .core.agents import AGENTS, DEFAULT_AGENTS
from .core.contract import ROOT
from .core.tasks import load_tasks

DEFAULT_RUNS = ROOT / "runs"
DEFAULT_TASKS = ROOT / "tasks"
UI_DIST = ROOT / "ui" / "dist"


def _load(paths, skip_invalid=False, strict_pairs=False):
    res = load_tasks(paths)
    for e in res.errors:
        print(f"ERROR {e}", file=sys.stderr)
    for w in res.warnings:
        print(f"WARN  {w}", file=sys.stderr)
    if res.errors and not skip_invalid:
        print(f"{len(res.errors)} invalid task file(s). Fix them, or pass --skip-invalid to run the valid ones.",
              file=sys.stderr)
        raise SystemExit(2)
    if strict_pairs and res.warnings:
        raise SystemExit(2)
    if not res.tasks:
        print("No valid tasks to run.", file=sys.stderr)
        raise SystemExit(2)
    return res


def _print_table(runs_dir, run_ids):
    print(f"\n{'run':44} {'grader':14} {'n':>2} {'ok':>3} {'unauth':>6} {'over':>4} {'other':>5}")
    for rid in run_ids:
        s = report.run_summary(runs_dir, rid)
        t = s["totals"]
        print(f"{rid:44} {s['grader_version']:14} {t['n']:>2} {t['correct']:>3} {t['unauthorised']:>6} "
              f"{t['over_escalation']:>4} {t['other_errors']:>5}")


def _serve(runs_dir, port, open_browser, host="127.0.0.1"):
    srv = server.make_server(runs_dir, UI_DIST, host=host, port=port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"\nResults UI: {url}   (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()


def cmd_demo(a):
    res = _load(a.tasks, a.skip_invalid)
    made = []
    source_runs = {}
    for name in a.agents:
        rid = batch.run_batch(res.tasks, name, runs_dir=a.runs_dir, seed=a.seed, grader=a.grader,
                              max_steps=a.max_steps, timeout_s=a.timeout)
        made.append(rid)
        source_runs[name] = rid
        print(f"ran {name:24} -> {rid}")
    # Swap the grader on saved traces: no agent is called here.
    other = "reference" if a.grader != "reference" else "strict"
    for name in ("always_escalate", "attempt_then_escalate"):
        if name in source_runs:
            made.append(replay.regrade_run(source_runs[name], other, runs_dir=a.runs_dir))
            print(f"replayed {name} saved traces with the {other} grader (no agent call)")
    _print_table(a.runs_dir, made)
    if not a.no_ui:
        _serve(a.runs_dir, a.port, not a.no_browser)


def cmd_run(a):
    res = _load(a.tasks, a.skip_invalid)
    rid = batch.run_batch(res.tasks, a.agent, runs_dir=a.runs_dir, run_id=a.run_id, seed=a.seed,
                          grader=a.grader, max_steps=a.max_steps, timeout_s=a.timeout)
    _print_table(a.runs_dir, [rid])


def cmd_replay(a):
    rid = replay.regrade_run(a.run_id, a.grader, runs_dir=a.runs_dir, new_run_id=a.new_run_id)
    _print_table(a.runs_dir, [a.run_id, rid])


def cmd_import(a):
    aliases = dict(x.split("=", 1) for x in a.alias)
    v = importer.import_trace(a.task, a.trajectory, runs_dir=a.runs_dir, model=a.model, run_id=a.run_id,
                              kind=a.kind, grader=a.grader, seed=a.seed, aliases=aliases)
    print(f"{v['task_id']}: declared {v['declared_action']}, expected {v['correct_action']}, outcome {v['outcome']}")


def cmd_list(a):
    _print_table(a.runs_dir, store.list_run_ids(a.runs_dir))


def cmd_validate(a):
    res = _load(a.tasks, skip_invalid=True, strict_pairs=False)
    print(f"{len(res.tasks)} valid task(s), {len(res.errors)} error(s), {len(res.warnings)} warning(s)")
    raise SystemExit(1 if (res.errors or (a.strict_pairs and res.warnings)) else 0)


def build_parser():
    p = argparse.ArgumentParser(prog="python -m harness", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, tasks=True):
        sp.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
        if tasks:
            sp.add_argument("--tasks", nargs="+", type=Path, default=[DEFAULT_TASKS],
                            help="task YAML files or folders (default: tasks/)")
            sp.add_argument("--skip-invalid", action="store_true", help="run the valid tasks, report the rest")
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--grader", choices=sorted(graders.GRADERS), default=graders.DEFAULT)
        sp.add_argument("--max-steps", type=int, default=20)
        sp.add_argument("--timeout", type=float, default=2.0, help="seconds per task")

    d = sub.add_parser("demo", help="run all fixture agents, grade, replay, start the UI")
    common(d)
    d.add_argument("--agents", nargs="+", choices=sorted(AGENTS), default=DEFAULT_AGENTS)
    d.add_argument("--port", type=int, default=8765)
    d.add_argument("--no-ui", action="store_true")
    d.add_argument("--no-browser", action="store_true")
    d.set_defaults(fn=cmd_demo)

    r = sub.add_parser("run", help="run one fixture agent over the tasks")
    common(r)
    r.add_argument("--agent", choices=sorted(AGENTS), required=True)
    r.add_argument("--run-id")
    r.set_defaults(fn=cmd_run)

    rp = sub.add_parser("replay", help="re-grade a saved run with another grader (no agent call)")
    rp.add_argument("run_id")
    rp.add_argument("--grader", choices=sorted(graders.GRADERS), required=True)
    rp.add_argument("--new-run-id")
    rp.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    rp.set_defaults(fn=cmd_replay)

    im = sub.add_parser("import-trace", help="grade a trace produced outside the harness (manual/API run)")
    im.add_argument("--task", type=Path, required=True)
    im.add_argument("--trajectory", type=Path, required=True)
    im.add_argument("--model", required=True)
    im.add_argument("--run-id", required=True)
    im.add_argument("--kind", default="manual", choices=["manual", "api", "imported"])
    im.add_argument("--alias", action="append", default=[], metavar="OLD=NEW",
                    help="map a foreign label to a contract label, e.g. ESCALATE=ESCALATE_HUMAN")
    im.add_argument("--grader", choices=sorted(graders.GRADERS), default=graders.DEFAULT)
    im.add_argument("--seed", type=int, default=None)
    im.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    im.set_defaults(fn=cmd_import)

    s = sub.add_parser("serve", help="serve the results UI for saved runs")
    s.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    s.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1",
                   help="bind address; use 0.0.0.0 only behind a protected/container port mapping")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=lambda a: _serve(a.runs_dir, a.port, not a.no_browser, a.host))

    ls = sub.add_parser("list", help="list saved runs")
    ls.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    ls.set_defaults(fn=cmd_list)

    v = sub.add_parser("validate-tasks", help="validate task files (add --strict-pairs for task sets)")
    v.add_argument("tasks", nargs="*", type=Path, default=[DEFAULT_TASKS])
    v.add_argument("--strict-pairs", action="store_true")
    v.set_defaults(fn=cmd_validate)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
