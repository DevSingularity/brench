"""Local results server: JSON API plus the built React UI (ui/dist). Stdlib only.

Binds to 127.0.0.1. If ui/dist is missing it serves a plain server-rendered
fallback page, so the evidence is always inspectable without Node.
"""
import html
import json
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ..evaluation import graders, replay
from ..persistence import report, store

ROUTES = [
    ("GET", re.compile(r"^/api/health$"), "health"),
    ("GET", re.compile(r"^/api/graders$"), "graders"),
    ("GET", re.compile(r"^/api/runs$"), "runs"),
    ("GET", re.compile(r"^/api/runs/([^/]+)$"), "run"),
    ("GET", re.compile(r"^/api/runs/([^/]+)/tasks/([^/]+)$"), "task"),
    ("POST", re.compile(r"^/api/runs/([^/]+)/regrade$"), "regrade"),
]


def fallback_page(runs_dir):
    rows = []
    for rid in store.list_run_ids(runs_dir):
        s = report.run_summary(runs_dir, rid)
        t = s["totals"]
        rows.append(f"<tr><td>{html.escape(rid)}</td><td>{html.escape(s.get('kind', ''))}</td>"
                    f"<td>{html.escape(s.get('grader_version', ''))}</td><td>{t['n']}</td>"
                    f"<td>{t['correct']}</td><td>{t['unauthorised']}</td><td>{t['over_escalation']}</td>"
                    f"<td>{t['other_errors']}</td></tr>")
    return ("<!doctype html><meta charset=utf-8><title>Brench runs</title>"
            "<body style='font-family:system-ui;margin:2rem'><h1>Brench runs</h1>"
            "<p>The Brench UI bundle is missing. Rebuild it with <code>cd ui &amp;&amp; pnpm install &amp;&amp; pnpm build</code>. "
            "The JSON API is available under <code>/api/runs</code>.</p>"
            "<table border=1 cellpadding=6><tr><th>run</th><th>kind</th><th>grader</th><th>tasks</th>"
            "<th>correct</th><th>unauthorised</th><th>over-escalation</th><th>other errors</th></tr>"
            + "".join(rows) + "</table></body>")


def make_handler(runs_dir, ui_dist):
    runs_dir, ui_dist = Path(runs_dir), Path(ui_dist)

    class Handler(BaseHTTPRequestHandler):
        server_version = "Brench/0.1"

        def log_message(self, fmt, *args):
            sys.stderr.write("[server] " + fmt % args + "\n")

        def _send(self, code, body, ctype):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, default=str), "application/json; charset=utf-8")

        def _api(self, method, path):
            for m, pat, name in ROUTES:
                match = pat.match(path)
                if m == method and match:
                    try:
                        return self._dispatch(name, *match.groups())
                    except (ValueError, KeyError) as exc:
                        return self._json(400, {"error": str(exc)})
                    except FileNotFoundError as exc:
                        return self._json(404, {"error": str(exc)})
            return self._json(404, {"error": f"no such endpoint: {method} {path}"})

        def _dispatch(self, name, *args):
            if name == "health":
                return self._json(200, {"ok": True})
            if name == "graders":
                return self._json(200, {"graders": [{"name": n, "version": v} for n, v in graders.VERSIONS.items()],
                                        "default": graders.DEFAULT})
            if name == "runs":
                return self._json(200, {"runs": [report.run_summary(runs_dir, r) for r in store.list_run_ids(runs_dir)]})
            if name == "run":
                store.safe(args[0])
                return self._json(200, report.run_detail(runs_dir, args[0]))
            if name == "task":
                return self._json(200, report.task_detail(runs_dir, args[0], args[1]))
            if name == "regrade":
                length = int(self.headers.get("Content-Length") or 0)
                if length < 0 or length > 4096:
                    raise ValueError("request body must be between 0 and 4096 bytes")
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("request body must be a JSON object")
                grader = body.get("grader", "")
                if grader not in graders.GRADERS:
                    raise ValueError(f"unknown grader {grader!r}; choose from {sorted(graders.GRADERS)}")
                new_id = replay.regrade_run(args[0], grader, runs_dir=runs_dir)
                return self._json(200, {"run_id": new_id})

        def _static(self, path):
            index = ui_dist / "index.html"
            if not index.is_file():
                return self._send(200, fallback_page(runs_dir), "text/html; charset=utf-8")
            target = (ui_dist / path.lstrip("/")).resolve()
            root = ui_dist.resolve()
            if target.is_file() and (root == target or root in target.parents):
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                return self._send(200, target.read_bytes(), ctype)
            if "." in Path(path).name:
                return self._send(404, "not found", "text/plain")
            return self._send(200, index.read_bytes(), "text/html; charset=utf-8")

        def do_GET(self):
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                return self._api("GET", path)
            return self._static(path)

        def do_POST(self):
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                return self._api("POST", path)
            return self._send(404, "not found", "text/plain")

    return Handler


def make_server(runs_dir, ui_dist, host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), make_handler(runs_dir, ui_dist))
