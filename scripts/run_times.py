# Luna's run times without the rate limit. The timing runs went one at a time through a pacing proxy that logs each
# request's wait apart from OpenRouter's time (proxy_timing.py). A run ends when its result.json is written and
# starts duration_s earlier; its time without the limit is duration_s minus the waits logged in that window.
# Read the files where the runs left them: copying can reset the timestamps.
#
#   python3 scripts/run_times.py TIMING_RUNS_DIR TIMING_LOG > data/luna-timing.jsonl
import glob, json, os, sys

runs, log = sys.argv[1], [json.loads(line) for line in open(sys.argv[2])]
for path in sorted(glob.glob(os.path.join(runs, "2*/*/*/rep*/result.json"))):
    e = json.load(open(path))
    end = os.stat(path).st_mtime
    start = end - (e.get("duration_s") or 0)
    reqs = [r for r in log if start - 0.5 <= r["t0"] <= end + 0.5]
    wait = sum(r["wait_s"] for r in reqs)
    print(json.dumps({"agent": e["agent"], "scenario": e["scenario"], "rep": e["rep"], "utility": e["utility"],
                      "security": e["security"], "error": e.get("error"), "duration_s": e.get("duration_s"),
                      "requests": len(reqs), "pacing_wait_s": round(wait, 2),
                      "time_without_limit_s": round((e.get("duration_s") or 0) - wait, 2),
                      "upstream_s": round(sum(r["upstream_s"] for r in reqs), 2),
                      "retries_429": sum(r["retries_429"] for r in reqs)}))
