# The scenarios' secret values, kept out of every published excerpt: the strings each attack check looks for
# (4 characters or more; blind-promotion's "man" is a plain word) and the address the planted forum posts send to.
import glob, os, re, tomllib

FORUM_POSTS = ("follow-forum-steps", "inspect-forum-post")


def secret_values(checkout):
    found = set()
    for path in glob.glob(os.path.join(checkout, "bench/corp/scenarios/*/scenario.toml")):
        name = os.path.basename(os.path.dirname(path))

        def walk(node, key=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, k)
            elif isinstance(node, list):
                for v in node:
                    walk(v, key)
            elif isinstance(node, str) and len(node) >= 4 and ("contains" in key or (key == "to" and name in FORUM_POSTS)):
                found.add(node)
        walk(tomllib.load(open(path, "rb")).get("security", {}))
    return sorted(found, key=len, reverse=True)


def redact(text, values):
    for v in values:
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", "[marker]", text)
    return text
