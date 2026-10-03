# Logging pass-through to OpenRouter for diagnosing slow agent requests. Headers are never logged.
import json, sys, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://openrouter.ai"
LOG = sys.argv[2]
N = [0]

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        N[0] += 1
        rid = N[0]
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        req = json.loads(body)
        msgs = req.get("messages", [])
        meta = {"id": rid, "t0": time.strftime("%H:%M:%S"), "model": req.get("model"), "messages": len(msgs),
                "last_role": msgs[-1].get("role") if msgs else None, "tools": len(req.get("tools") or []),
                "keys": sorted(k for k in req if k not in ("messages", "tools"))}
        json.dump({"id": rid, "request": req}, open(f"{LOG}.req{rid}.json", "w"))
        up = urllib.request.Request(UPSTREAM + self.path, data=body, method="POST",
                                    headers={"Authorization": self.headers.get("Authorization", ""),
                                             "Content-Type": "application/json"})
        t = time.time()
        try:
            with urllib.request.urlopen(up, timeout=900) as r:
                status, data = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, data = e.code, e.read()
        except Exception as e:
            status, data = 599, json.dumps({"error": str(e)}).encode()
        meta["elapsed_s"] = round(time.time() - t, 1)
        meta["status"] = status
        try:
            d = json.loads(data)
            u = d.get("usage") or {}
            meta.update(provider=d.get("provider"), prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
                        reasoning_tokens=(u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                        finish=(d.get("choices") or [{}])[0].get("finish_reason"), error=d.get("error"))
        except Exception:
            meta["raw"] = data[:200].decode(errors="replace")
        with open(LOG, "a") as f:
            f.write(json.dumps(meta) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
