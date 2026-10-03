# Counts tool calls per Claude Code session file in ~/.claude/projects (main thread only).
# Prints the distribution; reads no message content beyond the tool_use markers.
import glob, json, os, statistics

counts = []
for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    n = 0
    with open(path, errors="replace") as fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") != "assistant" or event.get("isSidechain"):
                continue
            content = (event.get("message") or {}).get("content") or []
            n += sum(1 for c in content if isinstance(c, dict) and c.get("type") == "tool_use")
    if n:
        counts.append(n)
counts.sort()
q = lambda p: counts[min(len(counts) - 1, int(p * len(counts)))]
print("sessions:", len(counts), "median:", statistics.median(counts), "p75:", q(0.75), "p90:", q(0.90), "max:", counts[-1])
for t in (500, 1000, 1500, 3000):
    print(f"sessions with >= {t} tool calls:", sum(c >= t for c in counts))
