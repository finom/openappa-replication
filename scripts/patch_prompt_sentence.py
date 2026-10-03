# The prompt-sentence test: copies the compiled Bench-Corp agent and replaces one sentence of its system prompt
# (bench/corp-agent/src/system_prompt.txt, compiled in with include_str!) in place, at the same length, so nothing
# else in the binary moves. macOS needs an ad hoc re-signature after the edit.
#
#   python3 scripts/patch_prompt_sentence.py OPENAPPA/bench/corp-agent/target/debug/appa-corp-agent OUT del|fix
import shutil, subprocess, sys

SHIPPED = (b"When a\ndelegated child finishes with no return data, its side effects have succeeded;\n"
           b"proceed with your remaining work or summarise without retrying the delegation.")
VARIANTS = {
    "del": b"",
    "fix": b"When a delegated child finishes with no return data, you cannot tell whether its side "
           b"effects succeeded. Do not retry it; tell the user what you could not confirm.",
}

src, out, variant = sys.argv[1], sys.argv[2], sys.argv[3]
new = VARIANTS[variant]
assert len(new) <= len(SHIPPED)
data = open(src, "rb").read()
if data.count(SHIPPED) != 1:
    sys.exit(f"expected the shipped sentence once in {src}, found it {data.count(SHIPPED)} times")
open(out, "wb").write(data.replace(SHIPPED, new + b" " * (len(SHIPPED) - len(new))))
shutil.copymode(src, out)
if sys.platform == "darwin":
    subprocess.run(["codesign", "-f", "-s", "-", out], check=True)
print(f"{out}: sentence {variant}")
