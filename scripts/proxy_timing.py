# Pacing pass-through like proxy_throttle.py, for timing runs: logs, per request, the time spent waiting for a
# turn or after a 429 (wait_s) apart from the time OpenRouter took (upstream_s), with wall-clock start and end.
# A run's time without the rate limit is its duration minus the wait_s of its requests. Headers are never logged.
#   python3 scripts/proxy_timing.py PORT LOG
import json, sys, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://openrouter.ai"
PORT, LOG = int(sys.argv[1]), sys.argv[2]
SPACING = 3.4
LOCK = threading.Lock()
NEXT = [0.0]


def wait_turn():
    with LOCK:
        now = time.time()
        start = max(now, NEXT[0])
        NEXT[0] = start + SPACING
    time.sleep(max(0.0, start - time.time()))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        t0, wait, upstream, retries = time.time(), 0.0, 0.0, 0
        while True:
            w = time.time()
            wait_turn()
            wait += time.time() - w
            req = urllib.request.Request(UPSTREAM + self.path, data=body, method="POST",
                                         headers={"Authorization": self.headers.get("Authorization", ""),
                                                  "Content-Type": "application/json"})
            u = time.time()
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    status, data = r.status, r.read()
            except urllib.error.HTTPError as e:
                status, data = e.code, e.read()
            except Exception as e:
                status, data = 599, json.dumps({"error": {"message": str(e)}}).encode()
            if status == 429 and retries < 8:
                retries += 1
                wait += time.time() - u
                time.sleep(15)
                wait += 15
                continue
            upstream += time.time() - u
            break
        with open(LOG, "a") as f:
            f.write(json.dumps({"t0": t0, "t1": time.time(), "wait_s": round(wait, 3), "upstream_s": round(upstream, 3),
                                "status": status, "retries_429": retries}) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
