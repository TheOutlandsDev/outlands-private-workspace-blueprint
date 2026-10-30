#!/usr/bin/env python3
"""Tiny fictional metrics source; never reads host, container, or user data."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import time


MODES = {"fresh", "stale", "unavailable"}


def render(mode: str, now: int) -> tuple[int, bytes]:
    if mode not in MODES:
        raise ValueError("invalid fictional mode")
    if mode == "unavailable":
        return 503, b"synthetic source unavailable\n"
    observed_at = now - (600 if mode == "stale" else 0)
    body = (
        "# HELP outlands_demo_observed_at_seconds Fictional source observation time.\n"
        "# TYPE outlands_demo_observed_at_seconds gauge\n"
        f'outlands_demo_observed_at_seconds{{source="demo-01"}} {observed_at}\n'
        "# HELP outlands_demo_value Fictional sample value.\n"
        "# TYPE outlands_demo_value gauge\n"
        'outlands_demo_value{source="demo-01"} 7\n'
    )
    return 200, body.encode("ascii")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        code, body = render(os.environ["DEMO_MODE"], int(time.time()))
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    mode = os.environ.get("DEMO_MODE", "")
    if mode not in MODES:
        raise SystemExit("DEMO_MODE must be fresh, stale, or unavailable")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
