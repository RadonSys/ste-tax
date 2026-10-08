#!/usr/bin/env python3
"""STE-tax eval harness: arms A0/A1/A2 on checkable tasks.

Design: docs/design.md and docs/intervention-pin.md.

Arms (run order default A0, A2, A1, per the pin):
- A0: free-form baseline. No STE instruction.
- A1: prompt instruction. System prompt states the STE rules and carries
  the approved word list from data/lexicon.json.
- A2: post-hoc rewrite. A0 draft first (reasoning frozen), then a rewrite
  pass that may change surface form only. Cost is draft + rewrite.

Metrics per task and arm:
- correct: answer check on the final text (after the think segment).
- reasoning_tokens: tokens inside <think>...</think>; the axis that tests
  "plans in native space, constrains surface only".
- generated_tokens: all new tokens (reasoning + final).
- output_tokens: final-text tokens only.
- latency_s: wall clock of the generate call(s).
- compliance: fraction of final-text word tokens in the approved
  vocabulary (scripts/validate.py trie). Numbers are not vocabulary and
  leave the denominator; task-declared technical terms are allowed.
- degenerate: empty/near-empty output or a refusal opening. Recorded as
  its own outcome, never folded into accuracy.

Backends: mock (plumbing test, no model), hf (transformers; CPU or GPU),
vllm (offline LLM; the DCS cluster path).

Watermark mode (--watermark): hf backend only. Generates watermarked text
(green-list, eval/watermark.py) under A0 and A1 on the writing tasks at
temperature 0.7 and reports detection z-scores truncated to matched
length per task.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate as ste_validate  # noqa: E402
import watermark as wm  # noqa: E402

REFUSAL_OPENERS = ("I cannot", "I can't", "I'm sorry", "I am sorry",
                   "I’m sorry", "I can’t")

STE_SYSTEM = """You write in ASD-STE100 Simplified Technical English.
Rules:
- Use only words from the approved word list below.
- One meaning per word. Keep sentences short.
- You may also use numbers, and these technical terms: {technical}
Approved words:
{approved}"""

REWRITE_USER = """Rewrite the text below in ASD-STE100 Simplified Technical English. Change the surface form only. Do not change facts, numbers, or the final answer line.

{text}"""


# ---------------------------------------------------------------- lexicon

def load_lexicon():
    with open(REPO / "data" / "lexicon.json", encoding="utf-8") as f:
        return json.load(f)


def approved_phrases(lexicon):
    """Same inventory validate.py builds its trie from."""
    out = []
    for entry in lexicon["approved"]:
        out.extend(form.upper() for form in entry["forms"])
        if entry["plural"]:
            out.append(entry["plural"].upper())
    return out


def approved_id_list(lexicon):
    """Compact 'WORD (POS)' list for the A1/A2 system prompt."""
    return ", ".join(sorted(e["id"].upper() for e in lexicon["approved"]))


# ------------------------------------------------------------- compliance

def compliance(text, trie, technical_terms):
    toks = [t for t in ste_validate.tokenize(text) if not t.isdigit()]
    allowed = {t.upper() for t in technical_terms}
    toks = [t for t in toks if t not in allowed]
    if not toks:
        return 1.0, []
    conforming, nonconforming = ste_validate.validate(" ".join(toks), trie)
    good = sum(len(p.split()) for p in conforming)
    total = good + len(nonconforming)
    return good / total, sorted(set(nonconforming))


# --------------------------------------------------------------- checking

def final_answer_line(text):
    m = re.findall(r"Answer:\s*(.+)", text)
    return m[-1].strip() if m else text


def check(task, final_text):
    """True/False for scored tasks, None for unscored (writing)."""
    gold = task["answer"]
    if gold is None:
        return None
    line = final_answer_line(final_text)
    if task["kind"] == "math":
        nums = re.findall(r"-?\d+(?:\.\d+)?", line.replace(",", ""))
        if not nums:
            nums = re.findall(r"-?\d+(?:\.\d+)?",
                              final_text.replace(",", ""))
        if not nums:
            return False
        try:
            return abs(float(nums[-1]) - float(gold)) < 1e-6
        except ValueError:
            return False
    norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()  # noqa: E731
    return norm(str(gold)) == norm(line) or \
        " ".join(norm(str(gold))) in " ".join(norm(final_text))


def is_degenerate(final_text):
    if len(ste_validate.tokenize(final_text)) < 2:
        return True
    head = final_text.lstrip()[:60]
    return any(head.startswith(r) for r in REFUSAL_OPENERS)


# --------------------------------------------------------------- backends

class MockBackend:
    """Deterministic canned text. Tests plumbing only, never accuracy."""

    def __init__(self, model):
        self.model = model

    def generate(self, messages, max_new_tokens, temperature, seed,
                 processor=None):
        blob = " ".join(m["content"] for m in messages)
        if "Rewrite the text below" in blob:
            text = ("<think>Use approved words only.</think>"
                    "Open the cover. Remove the old part. "
                    "Install the new part. Answer: 200")
        elif "ASD-STE100" in blob:
            text = ("<think>Plan the answer with approved words.</think>"
                    "The pump removes the water. Answer: 200")
        else:
            text = ("<think>Compute: 480 - 35 * 8 = 200.</think>"
                    "After 8 minutes the tank holds less water. Answer: 200")
        return {"text": text, "token_ids": None, "latency_s": 0.0}


class HFBackend:
    def __init__(self, model, thinking=True):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype="auto", device_map="auto")
        self.model.eval()
        self.thinking = thinking
        self._torch = torch

    def _prompt(self, messages):
        try:
            return self.tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=self.thinking)
        except TypeError:
            return self.tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)

    def generate(self, messages, max_new_tokens, temperature, seed,
                 processor=None):
        torch = self._torch
        from transformers import LogitsProcessorList

        prompt = self._prompt(messages)
        inputs = self.tok(prompt, return_tensors="pt").to(self.model.device)
        n_prompt = inputs["input_ids"].shape[1]
        kwargs = {"max_new_tokens": max_new_tokens,
                  "do_sample": temperature > 0}
        if temperature > 0:
            kwargs["temperature"] = temperature
        if processor is not None:
            kwargs["logits_processor"] = LogitsProcessorList([processor])
        torch.manual_seed(seed)
        t0 = time.perf_counter()
        with torch.no_grad():
            out = self.model.generate(**inputs, **kwargs)
        latency = time.perf_counter() - t0
        new_ids = out[0][n_prompt:].tolist()
        return {"text": self.tok.decode(new_ids, skip_special_tokens=False),
                "token_ids": new_ids, "latency_s": latency}


class VLLMBackend:
    """Offline vLLM. The DCS cluster path (ROCm build of vLLM)."""

    def __init__(self, model, tp=1, thinking=True):
        from vllm import LLM

        self.llm = LLM(model=model, tensor_parallel_size=tp,
                       max_model_len=16384, gpu_memory_utilization=0.90,
                       seed=0)
        self.tok = self.llm.get_tokenizer()
        self.thinking = thinking

    def generate(self, messages, max_new_tokens, temperature, seed,
                 processor=None):
        from vllm import SamplingParams

        if processor is not None:
            raise NotImplementedError(
                "watermark logit bias needs the hf backend")
        params = SamplingParams(temperature=temperature,
                                max_tokens=max_new_tokens, seed=seed)
        t0 = time.perf_counter()
        outs = self.llm.chat(messages, params,
                             chat_template_kwargs={
                                 "enable_thinking": self.thinking})
        latency = time.perf_counter() - t0
        o = outs[0].outputs[0]
        return {"text": o.text, "token_ids": list(o.token_ids),
                "latency_s": latency}


# ------------------------------------------------------------ think spans

def split_reasoning(text, token_ids, tokenizer):
    """Return (reasoning_tokens, final_text, generated_tokens).

    Reasoning is the <think>...</think> segment. Token counts come from
    token ids when a backend supplies them, else whitespace words.
    """
    if tokenizer is not None and token_ids is not None:
        start = tokenizer.convert_tokens_to_ids("<think>")
        end = tokenizer.convert_tokens_to_ids("</think>")
        ids = list(token_ids)
        if start in ids:
            i = ids.index(start)
            if end in ids[i + 1:]:
                j = ids.index(end, i + 1)
                reasoning = j - i - 1
                final_ids = ids[:i] + ids[j + 1:]
            else:  # unclosed think: the rest is reasoning, no final text
                reasoning = len(ids) - i - 1
                final_ids = ids[:i]
            return reasoning, tokenizer.decode(
                final_ids, skip_special_tokens=True), len(ids)
    m = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    if m:
        final = (text[:m.start()] + text[m.end():]).strip()
        return len(m.group(1).split()), final, len(text.split())
    if "<think>" in text:  # unclosed
        return len(text.split("<think>", 1)[1].split()), "", len(text.split())
    return 0, text.strip(), (len(token_ids) if token_ids is not None
                             else len(text.split()))


# ------------------------------------------------------------------- arms

def ste_messages(task, lexicon, user_content):
    technical = ", ".join(task["technical_terms"]) or "none"
    system = STE_SYSTEM.format(
        technical=technical, approved=approved_id_list(lexicon))
    return [{"role": "system", "content": system},
            {"role": "user", "content": user_content}]


def run_arm(backend, task, arm, lexicon, trie, cfg):
    """Returns one result record for (task, arm)."""
    tok = getattr(backend, "tok", None)

    def gen(messages):
        return backend.generate(messages, cfg["max_new_tokens"],
                                cfg["temperature"], cfg["seed"])

    extra = {}
    if arm == "A0":
        res = gen([{"role": "user", "content": task["prompt"]}])
    elif arm == "A1":
        res = gen(ste_messages(task, lexicon, task["prompt"]))
    elif arm == "A2":
        draft = gen([{"role": "user", "content": task["prompt"]}])
        d_reason, d_final, d_gen = split_reasoning(
            draft["text"], draft["token_ids"], tok)
        res = gen(ste_messages(task, lexicon,
                               REWRITE_USER.format(text=d_final)))
        r_reason, r_final, r_gen = split_reasoning(
            res["text"], res["token_ids"], tok)
        extra = {"draft_generated_tokens": d_gen,
                 "draft_reasoning_tokens": d_reason,
                 "rewrite_generated_tokens": r_gen,
                 "rewrite_reasoning_tokens": r_reason,
                 "draft_text": d_final}
        res = {"text": res["text"], "token_ids": res["token_ids"],
               "latency_s": draft["latency_s"] + res["latency_s"],
               "_reasoning": d_reason + r_reason,
               "_generated": d_gen + r_gen,
               "_final": r_final}
    else:
        raise ValueError(f"unknown arm {arm}")

    if "_final" in res:
        reasoning, final, generated = (res["_reasoning"], res["_final"],
                                       res["_generated"])
    else:
        reasoning, final, generated = split_reasoning(
            res["text"], res["token_ids"], tok)
    rate, nonconf = compliance(final, trie, task["technical_terms"])
    record = {
        "task_id": task["id"], "kind": task["kind"], "arm": arm,
        "model": cfg["model"], "backend": cfg["backend"],
        "correct": check(task, final),
        "degenerate": is_degenerate(final),
        "reasoning_tokens": reasoning,
        "generated_tokens": generated,
        "output_tokens": (len(tok.encode(final)) if tok is not None
                          else len(final.split())),
        "latency_s": round(res["latency_s"], 3),
        "compliance": round(rate, 4),
        "nonconforming": nonconf[:50],
        "text": final,
    }
    record.update(extra)
    return record


# --------------------------------------------------------------- watermark

def run_watermark(backend, tasks, lexicon, cfg):
    """A0 vs A1 watermarked generation on writing tasks; z at matched len."""
    if not isinstance(backend, HFBackend):
        raise SystemExit("--watermark needs the hf backend")
    vocab = backend.model.config.vocab_size
    records = []
    writing = [t for t in tasks if t["kind"] == "writing"]
    for task in writing:
        per_arm = {}
        for arm in ("A0", "A1"):
            if arm == "A0":
                messages = [{"role": "user", "content": task["prompt"]}]
            else:
                messages = ste_messages(task, lexicon, task["prompt"])
            proc = wm.GreenListProcessor(vocab, cfg["gamma"], cfg["delta"],
                                         cfg["wm_key"])
            res = backend.generate(messages, cfg["wm_tokens"], 0.7,
                                   cfg["seed"], processor=proc)
            _, final_ids_text, _ = split_reasoning(
                res["text"], res["token_ids"], backend.tok)
            ids = res["token_ids"]
            per_arm[arm] = ids
            z, g, t = wm.z_score(ids, vocab, cfg["gamma"], cfg["wm_key"])
            records.append({"task_id": task["id"], "arm": arm,
                            "mode": "watermark", "tokens": len(ids),
                            "z_full": round(z, 3), "greens": g})
        matched = min(len(per_arm["A0"]), len(per_arm["A1"]))
        for rec in records[-2:]:
            z, _, _ = wm.z_score(per_arm[rec["arm"]][:matched], vocab,
                                 cfg["gamma"], cfg["wm_key"])
            rec["matched_len"] = matched
            rec["z_matched"] = round(z, 3)
    return records


# ---------------------------------------------------------------- summary

def summarize(records):
    arms = sorted({r["arm"] for r in records if r.get("mode") != "watermark"})
    lines = []
    stats = {}
    for arm in arms:
        rs = [r for r in records if r["arm"] == arm]
        scored = [r for r in rs if r["correct"] is not None]
        acc = (sum(r["correct"] for r in scored) / len(scored)
               if scored else float("nan"))
        mean = lambda k: sum(r[k] for r in rs) / len(rs)  # noqa: E731
        stats[arm] = {"n": len(rs), "accuracy": acc,
                      "generated": mean("generated_tokens"),
                      "reasoning": mean("reasoning_tokens"),
                      "latency": mean("latency_s"),
                      "compliance": mean("compliance"),
                      "degenerate": sum(r["degenerate"] for r in rs)}
        s = stats[arm]
        lines.append(
            f"{arm}: n={s['n']} acc={s['accuracy']:.3f} "
            f"gen_tok={s['generated']:.1f} reason_tok={s['reasoning']:.1f} "
            f"latency={s['latency']:.2f}s compliance={s['compliance']:.3f} "
            f"degenerate={s['degenerate']}")
    if "A0" in stats:
        base = stats["A0"]
        ratio = lambda a, b: (a / b) if b else float("nan")  # noqa: E731
        for arm in arms:
            if arm == "A0":
                continue
            s = stats[arm]
            lines.append(
                f"tax {arm}-A0: acc {s['accuracy'] - base['accuracy']:+.3f}, "
                f"gen_tok x{ratio(s['generated'], base['generated']):.2f}, "
                f"reason_tok {s['reasoning'] - base['reasoning']:+.1f}, "
                f"latency x{ratio(s['latency'], base['latency']):.2f}, "
                f"compliance {s['compliance'] - base['compliance']:+.3f}")
    return "\n".join(lines)


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", choices=["mock", "hf", "vllm"],
                    default="mock")
    ap.add_argument("--model", default="Qwen/Qwen3-32B")
    ap.add_argument("--tasks", default=str(REPO / "eval" / "tasks.jsonl"))
    ap.add_argument("--arms", nargs="+", default=["A0", "A2", "A1"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--no-thinking", action="store_true")
    ap.add_argument("--watermark", action="store_true")
    ap.add_argument("--gamma", type=float, default=0.25)
    ap.add_argument("--delta", type=float, default=2.0)
    ap.add_argument("--wm-key", type=int, default=42)
    ap.add_argument("--wm-tokens", type=int, default=200)
    args = ap.parse_args()

    cfg = vars(args)
    cfg["thinking"] = not args.no_thinking
    lexicon = load_lexicon()
    trie = ste_validate.build_trie(approved_phrases(lexicon))
    with open(args.tasks, encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    if args.limit:
        tasks = tasks[:args.limit]

    if args.backend == "mock":
        backend = MockBackend(args.model)
    elif args.backend == "hf":
        backend = HFBackend(args.model, thinking=cfg["thinking"])
    else:
        backend = VLLMBackend(args.model, tp=args.tp,
                              thinking=cfg["thinking"])

    out = args.out or str(
        REPO / "eval" / "results" /
        f"{args.backend}-{int(time.time())}.jsonl")
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    if args.watermark:
        records = run_watermark(backend, tasks, lexicon, cfg)
        with open(out, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        for r in records:
            print(f"{r['task_id']} {r['arm']}: z_full={r['z_full']} "
                  f"z_matched={r['z_matched']} (n={r['matched_len']})")
        print(f"wrote {out}")
        return

    records = []
    with open(out, "w", encoding="utf-8") as f:
        for task in tasks:
            for arm in args.arms:
                rec = run_arm(backend, task, arm, lexicon, trie, cfg)
                records.append(rec)
                f.write(json.dumps(rec) + "\n")
                f.flush()
                print(f"{task['id']} {arm}: correct={rec['correct']} "
                      f"gen={rec['generated_tokens']} "
                      f"reason={rec['reasoning_tokens']} "
                      f"compliance={rec['compliance']}")
    print("\n" + summarize(records))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
