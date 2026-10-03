# Prints the Bench-Corp runs still missing for one model and prompt, grouped for bench-corp invocations:
# one line per (arm, missing runs): "<arm> <runs> <scenario> <scenario> ...". Counts scored runs only.
#
#   python3 scripts/plan_missing.py MODEL PROMPT RUNS_INJECTION_TASKS RUNS_OTHER_TASKS RUNS_DIR [RUNS_DIR ...]
import collections, glob, json, os, sys

model, profile, target_inj, target_other = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
roots = sys.argv[5:]
INJ = ["follow-forum-steps", "inspect-forum-post", "report-full-record", "reply-and-file-ticket", "hide-secret-in-status"]
OTHER = ["joint-merger-brief", "share-legal-packet", "route-project-packet", "dual-control-wire", "vendor-trust-boundary",
         "one-release-only", "anonymous-complaint", "blind-promotion", "check-hr-record", "email-onboarding-buddy",
         "legal-pre-clearance", "multi-tenant-egress", "performance-feedback", "review-then-notify", "suspicious-activity"]
have = collections.Counter()
for root in roots:
    for run in glob.glob(os.path.join(root, "2*/")):
        try:
            cfg = json.load(open(os.path.join(run, "config.json")))
        except (OSError, ValueError):
            continue
        if cfg.get("model") != model or cfg.get("agent_prompt_profile", "standard") != profile:
            continue
        for path in glob.glob(os.path.join(run, "*/*/rep*/result.json")):
            try:
                e = json.load(open(path))
            except ValueError:
                continue
            if e.get("error") == "provider_failed" or str(e.get("error")).startswith("exit -"):
                continue
            have[(e["agent"], e["scenario"])] += 1
groups = collections.defaultdict(list)
for agent in ("appa", "appa-open"):
    for scen in INJ + OTHER:
        need = (target_inj if scen in INJ else target_other) - have[(agent, scen)]
        if need > 0:
            groups[(agent, need)].append(scen)
for (agent, need), scens in sorted(groups.items()):
    print(agent, need, *scens)
