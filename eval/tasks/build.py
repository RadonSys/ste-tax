"""Sample benchmark subsets from upstream files. Standard library only.

Usage:
  python3 eval/tasks/build.py --gsm8k PATH/test.jsonl \
      --nq-open PATH/NQ-open.dev.jsonl

Checks each upstream SHA-256 against the pin before it reads. Writes
eval/tasks/gsm8k.jsonl and eval/tasks/nq_open.jsonl. Same inputs and
seed give byte-identical output. docs/tasks.md has the URLs.
"""

import argparse
import hashlib
import json
import random
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
SEED = 0
N = 400

PIN = {
    "gsm8k": "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14",
    "nq_open": "f15567f38099f3615f5b8a685c0aef449c11ad90d3da3735e8d1b98115b40616",
}
MATH_SUFFIX = " End your answer with a line of the form 'Answer: <number>'."
QA_SUFFIX = " End your answer with a line of the form 'Answer: <value>'."
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# NQ answers are frozen at 2018 annotation; a question about the latest
# event can have a different true answer now.
DATED = re.compile(r"\b(last|latest|current|currently|now|recent|recently|"
                   r"this year|today|newest)\b")


def read_pinned(path, name):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PIN[name]:
        raise SystemExit(f"{name}: sha256 {digest} != pin {PIN[name]}")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()
            if line.strip()]


def sample(indices):
    return sorted(random.Random(SEED).sample(sorted(indices), N))


def gsm8k(rows):
    for i in sample(range(len(rows))):
        gold = rows[i]["answer"].split("####")[1].strip().replace(",", "")
        if not NUMBER.fullmatch(gold):
            raise SystemExit(f"gsm8k line {i}: answer {gold!r} not numeric")
        value = float(gold)
        yield {
            "id": f"gsm8k-test-{i:04d}",
            "kind": "math",
            "prompt": rows[i]["question"].strip() + MATH_SUFFIX,
            "answer": int(value) if value.is_integer() else value,
            "technical_terms": [],
            "source": "gsm8k",
            "split": "test",
            "license": "MIT",
        }


def nq_open(rows):
    # One gold string per task: the schema holds one answer, so keep only
    # items with exactly one annotated answer and no time-dated wording.
    single = [i for i, r in enumerate(rows)
              if len(r["answer"]) == 1 and not DATED.search(r["question"])]
    for i in sample(single):
        yield {
            "id": f"nq-open-dev-{i:04d}",
            "kind": "qa",
            "prompt": rows[i]["question"].strip() + "?" + QA_SUFFIX,
            "answer": rows[i]["answer"][0],
            "technical_terms": [],
            "source": "nq-open",
            "split": "dev",
            "license": "CC-BY-SA-3.0",
        }


def write(name, records):
    path = OUT / f"{name}.jsonl"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsm8k", required=True)
    ap.add_argument("--nq-open", required=True)
    a = ap.parse_args()
    write("gsm8k", list(gsm8k(read_pinned(a.gsm8k, "gsm8k"))))
    write("nq_open", list(nq_open(read_pinned(a.nq_open, "nq_open"))))


if __name__ == "__main__":
    main()
