"""Sample benchmark subsets from upstream files. Standard library only.

Usage:
  python3 eval/tasks/build.py --gsm8k PATH/test.jsonl \
      --nq-open PATH/NQ-open.dev.jsonl --math500 PATH/math500.test.jsonl

Checks each upstream SHA-256 against the pin before it reads. Writes
eval/tasks/gsm8k_full.jsonl (all 1319 GSM8K test items, the cost axis),
eval/tasks/math500.jsonl (200 numeric-answer MATH-500 items, the
accuracy axis), and eval/tasks/nq_open.jsonl (400). Same inputs and
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
N_MATH500 = 200

PIN = {
    "gsm8k": "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14",
    "nq_open": "f15567f38099f3615f5b8a685c0aef449c11ad90d3da3735e8d1b98115b40616",
    "math500": "35dc41080a3680858b27fa7e0533d2d547825316fc5dafe5d316f4ccc5a06132",
}
MATH_SUFFIX = " End your answer with a line of the form 'Answer: <number>'."
QA_SUFFIX = " End your answer with a line of the form 'Answer: <value>'."
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# MATH-500 gold that the harness math check can compare: a plain number,
# or one with thousands commas. "1,-2" and "1,2" are tuples, not numbers.
PLAIN = re.compile(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")
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


def sample(indices, n=N):
    return sorted(random.Random(SEED).sample(sorted(indices), n))


def number(text):
    value = float(text.replace(",", ""))
    return int(value) if value.is_integer() else value


def gsm8k(rows):
    # The full test split: the cost axis needs n near 1,100 (docs/tasks.md).
    for i in range(len(rows)):
        gold = rows[i]["answer"].split("####")[1].strip().replace(",", "")
        if not NUMBER.fullmatch(gold):
            raise SystemExit(f"gsm8k line {i}: answer {gold!r} not numeric")
        yield {
            "id": f"gsm8k-test-{i:04d}",
            "kind": "math",
            "prompt": rows[i]["question"].strip() + MATH_SUFFIX,
            "answer": number(gold),
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


def math500(rows):
    # The harness compares numbers only, so keep items whose gold is a
    # plain number (318 of 500); symbolic answers leave the pool.
    numeric = [i for i, r in enumerate(rows) if PLAIN.fullmatch(r["answer"].strip())]
    for i in sample(numeric, N_MATH500):
        yield {
            "id": f"math500-test-{i:04d}",
            "kind": "math",
            "prompt": rows[i]["problem"].strip() + MATH_SUFFIX,
            "answer": number(rows[i]["answer"].strip()),
            "technical_terms": [],
            "source": "math-500",
            "split": "test",
            "license": "MIT",
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
    ap.add_argument("--math500", required=True)
    a = ap.parse_args()
    write("gsm8k_full", list(gsm8k(read_pinned(a.gsm8k, "gsm8k"))))
    write("nq_open", list(nq_open(read_pinned(a.nq_open, "nq_open"))))
    write("math500", list(math500(read_pinned(a.math500, "math500"))))


if __name__ == "__main__":
    main()
