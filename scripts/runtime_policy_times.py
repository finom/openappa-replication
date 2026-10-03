# Reads the runtime's own telemetry from an `appa runtime` log written during hook_latency.py: one "policy check
# completed ... appa.duration.seconds=X" line per PreToolUse, in call order. Shows how much of the hook time is the
# engine's decision. Usage: runtime_policy_times.py RUNTIME.log OUT.json
import json, re, sys

ansi = re.compile(r"\x1b\[[0-9;]*m")
times = []
for line in open(sys.argv[1], errors="replace"):
    line = ansi.sub("", line)
    if "policy check completed" in line:
        m = re.search(r"appa\.duration\.seconds=([0-9.eE+-]+)", line)
        if m:
            times.append(round(float(m.group(1)) * 1000, 3))
json.dump([{"call": i, "policy_ms": t} for i, t in enumerate(times, 1)], open(sys.argv[2], "w"))
print(len(times), "policy checks")
