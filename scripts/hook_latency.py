# Times the real Claude Code hook path: one `appa hook` process per event, posting to a running
# `appa runtime`, as Claude Code does for every tool call. Usage: hook_latency.py PORT CALLS OUT.json
import json, os, subprocess, sys, time, uuid, statistics

# The appa binary: APPA_BIN, or target/release/appa in the current OpenAPPA checkout.
APPA = os.environ.get("APPA_BIN", "target/release/appa")
PORT = sys.argv[1]
N = int(sys.argv[2])
OUT = sys.argv[3]
URL = f"http://127.0.0.1:{PORT}"
sid = str(uuid.uuid4())
base = {"session_id": sid, "transcript_path": f"/tmp/{sid}.jsonl", "cwd": "/work/app", "permission_mode": "default"}

def hook(payload):
    t = time.perf_counter()
    p = subprocess.run([APPA, "hook", "--deployment-url", URL], input=json.dumps(payload).encode(), capture_output=True)
    dt = time.perf_counter() - t
    return dt, p.returncode, p.stdout.decode(), p.stderr.decode()

dt, rc, out, err = hook({**base, "hook_event_name": "SessionStart", "source": "startup"})
print("SessionStart", round(dt*1000,1), "ms rc", rc, out[:200], err[:200])
pid = str(uuid.uuid4())
dt, rc, out, err = hook({**base, "prompt_id": pid, "hook_event_name": "UserPromptSubmit", "prompt": "Summarize the modules in src/."})
print("UserPromptSubmit", round(dt*1000,1), "ms rc", rc, out[:200], err[:200])

rows = []
for i in range(1, N + 1):
    tid = "toolu_" + uuid.uuid4().hex[:24]
    path = f"/work/app/src/mod_{i}.ts"
    tin = {"file_path": path}
    pre = {**base, "prompt_id": pid, "hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": tin, "tool_use_id": tid}
    d1, rc1, o1, e1 = hook(pre)
    content = f"export const value{i} = {i};\n"
    post = {**base, "prompt_id": pid, "hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": tin,
            "tool_response": {"type": "text", "file": {"filePath": path, "content": content, "numLines": 1, "startLine": 1, "totalLines": 1}},
            "tool_use_id": tid, "duration_ms": 3}
    d2, rc2, o2, e2 = hook(post)
    rows.append({"call": i, "pre_ms": d1 * 1000, "post_ms": d2 * 1000, "rc": [rc1, rc2]})
    if i % 100 == 0:
        json.dump(rows, open(OUT, "w"))
    if i <= 2 or i % 100 == 0:
        print(i, round(d1*1000,1), round(d2*1000,1), rc1, rc2, o1[:160].replace("\n"," "), e1[:160].replace("\n"," "), flush=True)

json.dump(rows, open(OUT, "w"))
for lo, hi in [(1, 10), (91, 110), (491, 510), (991, 1010), (1491, 1510), (1991, 2010), (2991, 3010), (3981, 4000)]:
    seg = [r["pre_ms"] + r["post_ms"] for r in rows if lo <= r["call"] <= hi]
    if seg:
        print(f"calls {lo}-{hi}: median per tool call (pre+post) {statistics.median(seg):.1f} ms")
