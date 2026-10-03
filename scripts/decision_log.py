# One Bench-Corp run's agent log, as kept in data/decision-logs/: what the agent proposed, what OpenAPPA blocked and
# why, and what it released at which label. Tool arguments, child tasks, child output, the model's narration and
# its final answer are left out, the scenarios' secret values are replaced with [marker], and lines stop at 600
# characters.
#
#   python3 scripts/decision_log.py OPENAPPA_CHECKOUT RUN_DIR > data/decision-logs/NAME.txt
import os, re, sys

from scenario_secrets import redact, secret_values

SKIP = r"answers:|says:|dispatch ran|value admitted|forked from|ended with a void return|committed \[\]$"
secrets = secret_values(sys.argv[1])
for line in open(os.path.join(sys.argv[2], "stderr.txt"), errors="replace"):
    line = line.rstrip("\n")
    if not line.startswith(("appa: [", "appa: remedy")) or re.search(SKIP, line):
        continue
    line = re.sub(r"proposes ([\w/]+)\(.*\)$", r"proposes \1(…)", line)
    line = re.sub(r"(forked at depth \d+ to:) .*", r"\1 <task omitted>", line)
    line = re.sub(r"(the output crossed as:) .*", r"\1 <content omitted>", line)
    line = re.sub(r"offer_id: \"?[0-9a-f]+\"?", "offer_id: …", line)
    line = re.sub(r"\s*\\n\s*", " ", re.sub(r"\s*\\n\s*\\n\s*", " | ", line))
    print(redact(line, secrets)[:600])
