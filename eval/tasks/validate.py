"""Validate every task file against the task schema. Standard library only.

Usage: python3 eval/tasks/validate.py [FILE ...]
Default files: eval/tasks.jsonl and eval/tasks/*.jsonl. Exit 1 on any
error; every error prints. Ids must be unique across all files.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIELDS = ("id", "kind", "prompt", "answer", "technical_terms", "source",
          "split", "license")
ANSWER = {"math": (int, float), "qa": (str,), "writing": (type(None),)}


def errors(rec):
    if not isinstance(rec, dict):
        yield "not a JSON object"
        return
    if tuple(rec) != FIELDS:
        yield f"fields {list(rec)} != {list(FIELDS)}"
    for key in ("id", "prompt", "source", "split", "license"):
        if not (isinstance(rec.get(key), str) and rec[key].strip()):
            yield f"{key}: not a non-empty string"
    kind = rec.get("kind")
    if kind not in ANSWER:
        yield f"kind {kind!r} not in {sorted(ANSWER)}"
    else:
        ans = rec.get("answer")
        if isinstance(ans, bool) or not isinstance(ans, ANSWER[kind]):
            yield f"answer {ans!r}: wrong type for kind {kind}"
        elif isinstance(ans, str) and not ans.strip():
            yield "answer: empty string"
    terms = rec.get("technical_terms")
    if not (isinstance(terms, list)
            and all(isinstance(t, str) and t.strip() for t in terms)):
        yield "technical_terms: not a list of non-empty strings"


def main(argv):
    files = [Path(a) for a in argv] or [
        REPO / "eval" / "tasks.jsonl",
        *sorted((REPO / "eval" / "tasks").glob("*.jsonl"))]
    seen, bad, total = {}, 0, 0
    for path in files:
        for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
            where = f"{path.relative_to(REPO)}:{n}"
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"{where}: {e}")
                bad += 1
                continue
            total += 1
            for err in errors(rec):
                print(f"{where}: {err}")
                bad += 1
            rid = rec.get("id") if isinstance(rec, dict) else None
            if rid in seen:
                print(f"{where}: duplicate id {rid!r} (first {seen[rid]})")
                bad += 1
            seen.setdefault(rid, where)
    print(f"{total} tasks in {len(files)} files, {bad} errors")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
