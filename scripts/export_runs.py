# Turns raw benchmark run folders into the files in data/. Keeps outcomes, timings and token counts;
# drops transcripts, check specs and anything else that carries scenario text.
#
#   python3 scripts/export_runs.py --corp RUNS_DIR [--corp RUNS_DIR ...] --atb ATB_RUNS_DIR \
#       --august AUG_RUNS_DIR --ablation base=DIR --ablation del=DIR --ablation fix=DIR \
#       --openappa OPENAPPA_CHECKOUT --out data
import argparse, glob, json, os

# The one-episode smoke test of the Ollama patch; not part of the design.
EXCLUDED_RUNS = {"20261001-152915": "smoke test of the local-model patch"}
USAGE_KEYS = ("model_calls", "input_tokens", "output_tokens", "total_tokens", "reasoning_tokens", "cost_usd")
EPISODE_KEYS = ("agent", "scenario", "rep", "agent_prompt_profile", "utility", "security", "error", "terminal_status",
                "duration_s", "policy_events", "remedy_calls", "provider_retries")


def episode_row(e, source, run, model, version):
    row = {"source": source, "run": run, "model": model, "version": version}
    row.update({k: e.get(k) for k in EPISODE_KEYS})
    row["usage"] = {k: (e.get("model_usage") or {}).get(k) for k in USAGE_KEYS}
    # The provider never answered (HTTP 429), or the machine killed the agent mid-run: not model behavior.
    row["infra_failure"] = e.get("error") == "provider_failed" or str(e.get("error")).startswith("exit -")
    return row


def corp_runs(root, source, version):
    for run in sorted(glob.glob(os.path.join(root, "2*/"))):
        name = os.path.basename(run.rstrip("/"))
        if name in EXCLUDED_RUNS:
            print(f"skipped {name}: {EXCLUDED_RUNS[name]}")
            continue
        try:
            model = json.load(open(os.path.join(run, "config.json")))["model"]
        except (OSError, KeyError, ValueError):
            continue
        for path in sorted(glob.glob(os.path.join(run, "*/*/rep*/result.json"))):
            try:
                e = json.load(open(path))
            except ValueError:
                continue
            yield episode_row(e, source, name, model, version)


def authors_corp(openappa):
    for run in ("20260911-162255", "20260911-164615"):
        summary = json.load(open(os.path.join(openappa, "bench/corp/results", run, "summary.json")))
        for e in summary["episodes"]:
            if e["agent"] in ("appa", "appa-open"):
                yield episode_row(e, "authors", run, "anthropic/claude-sonnet-5", "50971988")


def atb_rows(summary_path, source, run, model, profile, seed):
    d = json.load(open(summary_path))
    samples, usage = [], []
    for arm, groups in d["groups"].items():
        for task_type, group in (groups or {}).items():
            results = group.get("sample_results") or {}
            for sample, r in sorted(results.items()):
                samples.append({"source": source, "run": run, "model": model, "profile": profile, "seed": seed, "arm": arm,
                                "type": task_type, "sample": sample, "utility": r.get("actual_utility"),
                                "security": r.get("actual_security")})
    for arm, u in (d.get("model_usage_by_arm") or {}).items():
        if u and u.get("samples"):
            usage.append({"source": source, "run": run, "model": model, "profile": profile, "seed": seed, "arm": arm,
                          **{k: u.get(k) for k in ("samples", "model_calls", "total_tokens", "reasoning_tokens", "cost_usd")}})
    return samples, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corp", action="append", default=[], help="Bench-Corp runs folder (repeatable)")
    ap.add_argument("--august", help="Bench-Corp runs of the August 26 build")
    ap.add_argument("--ablation", action="append", default=[], help="ARM=DIR: runs of the prompt-sentence ablation")
    ap.add_argument("--followup", action="append", default=[],
                    help="VERSION=DIR: targeted re-runs of one task, kept out of the per-model tables")
    ap.add_argument("--atb", help="AgentThreatBench runs folder")
    ap.add_argument("--openappa", required=True, help="OpenAPPA checkout at 53c3d8e (for the authors' committed results)")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows = [r for root in a.corp for r in corp_runs(root, "mine", "53c3d8e")] + list(authors_corp(a.openappa))
    with open(os.path.join(a.out, "bench-corp-episodes.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"bench-corp-episodes.jsonl: {len(rows)} episodes ({sum(r['infra_failure'] for r in rows)} infrastructure failures)")

    if a.august:
        # a1ccf3f's code with the scenario files of the next commit, bfa61d2, which a1ccf3f's .gitignore left out.
        rows = list(corp_runs(a.august, "mine", "bfa61d2"))
        with open(os.path.join(a.out, "bench-corp-august-build-episodes.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"bench-corp-august-build-episodes.jsonl: {len(rows)} episodes")

    if a.ablation:
        rows = []
        for spec in a.ablation:
            arm, root = spec.split("=", 1)
            for r in corp_runs(root, "mine", f"53c3d8e, prompt sentence: {arm}"):
                r["arm"] = arm
                rows.append(r)
        with open(os.path.join(a.out, "prompt-ablation-episodes.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"prompt-ablation-episodes.jsonl: {len(rows)} episodes")

    if a.followup:
        rows = []
        for spec in a.followup:
            version, root = spec.split("=", 1)
            rows += list(corp_runs(root, "mine", version))
        with open(os.path.join(a.out, "bench-corp-followup-episodes.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"bench-corp-followup-episodes.jsonl: {len(rows)} episodes")

    samples, usage = atb_rows(os.path.join(a.openappa, "bench/agentthreatbench/results/full-sonnet-5/summary.json"),
                              "authors", "full-sonnet-5", "anthropic/claude-sonnet-5", "standard", None)
    if a.atb:
        for path in sorted(glob.glob(os.path.join(a.atb, "*/summary.json"))):
            run = os.path.basename(os.path.dirname(path))
            cfg = json.load(open(os.path.join(os.path.dirname(path), "run-config.json")))["config"]
            # inspect names the route: openrouter/<model> for OpenRouter, openai/<model> for the local endpoint.
            model = cfg["model"].split("/", 1)[1]
            s, u = atb_rows(path, "mine", run, model, cfg.get("agent_prompt_profile", "standard"), cfg.get("seed"))
            samples += s; usage += u
    with open(os.path.join(a.out, "agentthreatbench-samples.jsonl"), "w") as f:
        for r in samples:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(a.out, "agentthreatbench-usage.jsonl"), "w") as f:
        for r in usage:
            f.write(json.dumps(r) + "\n")
    print(f"agentthreatbench-samples.jsonl: {len(samples)} samples; usage rows: {len(usage)}")


if __name__ == "__main__":
    main()
