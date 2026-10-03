# Pass-through to OpenRouter that keeps request starts under the new-account limit
# (20 per minute per model) and retries 429s instead of failing. Headers are never logged.
import json, sys, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://openrouter.ai"
PORT, LOG = int(sys.argv[1]), sys.argv[2]
SPACING = 3.4          # seconds between request starts: about 17.6 per minute
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
        model = json.loads(body).get("model")
        t0, retries = time.time(), 0
        while True:
            wait_turn()
            req = urllib.request.Request(UPSTREAM + self.path, data=body, method="POST",
                                         headers={"Authorization": self.headers.get("Authorization", ""),
                                                  "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    status, data = r.status, r.read()
            except urllib.error.HTTPError as e:
                status, data = e.code, e.read()
            except Exception as e:
                status, data = 599, json.dumps({"error": {"message": str(e)}}).encode()
            if status == 429 and retries < 8:
                retries += 1
                time.sleep(15)
                continue
            break
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "model": model, "status": status, "retries_429": retries,
                                "total_s": round(time.time() - t0, 1)}) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
