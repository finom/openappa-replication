# Logging pass-through in front of the pacing proxy: saves every request and response body, numbered,
# so the transcript each model call saw can be read back. Headers are never logged.
#   python3 scripts/request_log_proxy.py PORT UPSTREAM OUT_DIR
import json, os, sys, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, UPSTREAM, OUT = int(sys.argv[1]), sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
LOCK, N = threading.Lock(), [0]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        with LOCK:
            N[0] += 1
            rid = N[0]
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        t0 = time.time()
        up = urllib.request.Request(UPSTREAM + self.path, data=body, method="POST",
                                    headers={"Authorization": self.headers.get("Authorization", ""),
                                             "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(up, timeout=900) as r:
                status, data = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, data = e.code, e.read()
        except Exception as e:
            status, data = 599, json.dumps({"error": {"message": str(e)}}).encode()
        try:
            response = json.loads(data)
        except Exception:
            response = {"raw": data[:2000].decode(errors="replace")}
        with open(os.path.join(OUT, f"req-{rid:05d}.json"), "w") as f:
            json.dump({"id": rid, "t0": time.strftime("%H:%M:%S", time.localtime(t0)),
                       "elapsed_s": round(time.time() - t0, 1), "status": status,
                       "request": json.loads(body), "response": response}, f)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
