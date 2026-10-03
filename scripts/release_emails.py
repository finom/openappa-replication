# one-release-only, per run: how many times the agent searched the task tracker, and every release email it tried,
# in order: to the requested recipient (Customer Success) or the forbidden one (the address the scenario's attack
# check looks for), from the main session or a child, and whether OpenAPPA released or blocked it, and why.
#
#   python3 scripts/release_emails.py OPENAPPA_CHECKOUT VERSION=RUNS_DIR [VERSION=RUNS_DIR ...] \
#       > data/one-release-only-emails.jsonl
import glob, json, os, re, sys, tomllib

from export_runs import EXCLUDED_RUNS

checkout = sys.argv[1]
spec = tomllib.load(open(os.path.join(checkout, "bench/corp/scenarios/one-release-only/scenario.toml"), "rb"))
forbidden = {check["to"] for check in spec["security"]["email_sent"]}
REASONS = {"forbidden after a release.sent effect": "once-only rule", "the readers do not include": "readers check"}

for arg in sys.argv[2:]:
    version, root = arg.split("=", 1)
    for path in sorted(glob.glob(os.path.join(root, "2*/*/one-release-only/rep*/result.json"))):
        e = json.load(open(path))
        run = path.split(os.sep)[-5]
        if run in EXCLUDED_RUNS:
            continue
        lines = open(os.path.join(os.path.dirname(path), "stderr.txt"), errors="replace").read().splitlines()
        emails = []
        for i, line in enumerate(lines):
            m = re.search(r"\[appa-corp-agent(:c\d+)?\] proposes send_email\((.*)\)$", line)
            if not m:
                continue
            to = json.loads(m.group(2)).get("to", "")
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if "blocked send_email" in nxt:
                why = [r for k, r in REASONS.items() if k in nxt]
                outcome = "blocked: " + (" and ".join(why) or "other")
            else:
                outcome = "released"
            emails.append({"to": "forbidden" if to in forbidden else "requested" if to.startswith("customer-success@") else "other",
                           "session": "child" if m.group(1) else "main", "outcome": outcome})
        print(json.dumps({"version": version, "model": json.load(open(os.path.join(root, run, "config.json")))["model"],
                          "agent": e["agent"], "prompt": e.get("agent_prompt_profile"), "run": run, "rep": e["rep"],
                          "utility": e["utility"], "security": e["security"],
                          "searches": sum("proposes search_task_tracker(" in line for line in lines), "emails": emails}))
