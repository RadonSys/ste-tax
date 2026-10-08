"""Shell: arguments, files, processes, clock. Run from the repo root:

    uv run python -m eval run --backend mock
    uv run python -m eval summarize eval/results/<run-id>
    uv run python -m eval rescore eval/results/<run-id>
    uv run python -m eval tasks

A run writes eval/results/<run-id>/manifest.json and records.jsonl. The
summary reads the records back, so analysis never needs the model.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from scripts import validate as ste_validate

from . import loader
from .compliance import CheckerCli, checker_off, default_trie, naive_compliance
from .harness import (
    Context,
    allowed_terms,
    approved_id_list,
    plain,
    run_arm,
    ste,
    summarize,
)
from .records import Arm, ArmRecord, Kind, Skipped, WatermarkRecord

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval" / "results"
SKILLS = REPO / ".github" / "skills"
WATERMARK_TEMPERATURE = 0.7


# ------------------------------------------------------------------ files


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, value: Any) -> None:
    write_atomic(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def jsonl(records: list[Any]) -> str:
    return "".join(json.dumps(r.to_json(), ensure_ascii=False) + "\n" for r in records)


def read_manifest(run: Path) -> dict[str, Any]:
    return json.loads((run / "manifest.json").read_text(encoding="utf-8"))


def read_records(run: Path) -> list[ArmRecord]:
    lines = (run / "records.jsonl").read_text(encoding="utf-8").splitlines()
    return [ArmRecord.from_json(json.loads(line)) for line in lines if line.strip()]


# ------------------------------------------------------------ environment


def command_output(argv: list[str], cwd: Path | None = None) -> str | None:
    """stdout of a command, or None when it is absent or fails."""
    if shutil.which(argv[0]) is None:
        return None
    try:
        proc = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def git_state(path: Path) -> dict[str, Any] | None:
    commit = command_output(["git", "-C", str(path), "rev-parse", "HEAD"])
    if commit is None:
        return None
    status = command_output(["git", "-C", str(path), "status", "--porcelain"])
    return {"commit": commit.strip(), "dirty": bool(status and status.strip())}


def version_of(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def environment() -> dict[str, Any]:
    """What docs/dcs-amd-hardware.md asks to keep with every result."""
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "host": platform.node(),
        "packages": {
            d: version_of(d) for d in ("torch", "vllm", "transformers", "accelerate")
        },
        "rocminfo": command_output(["rocminfo"]),
        "rocm-smi": command_output(["rocm-smi"]),
    }


def run_id(backend: str, model: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", Path(model).name).strip("-")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{backend}-{slug}-{stamp}"


# ---------------------------------------------------------------- scoring


def make_checker(args: argparse.Namespace):
    if args.checker == "off":
        return checker_off
    return CheckerCli.locate(Path(args.skills), args.checker_mode)


def score(records: list[ArmRecord], check, task_terms, workers: int) -> list[ArmRecord]:
    """Fill the checker outcome of every record that lacks one. Retries
    Skipped records except reason empty. Bounded thread pool; order kept."""

    def one(r: ArmRecord) -> ArmRecord:
        if not isinstance(r.checker, Skipped) or r.checker.reason == "empty":
            return r
        return replace(r, checker=check(r.text, task_terms.get(r.task_id, ())))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, records))


# --------------------------------------------------------------- commands


def backend_for(args: argparse.Namespace, sampling):
    from . import backends

    match args.backend:
        case "mock":
            return backends.MockBackend(args.model, sampling)
        case "hf":
            return backends.HFBackend(args.model, sampling, thinking=args.thinking)
        case "vllm":
            return backends.VLLMBackend(
                args.model,
                sampling,
                tp=args.tp,
                thinking=args.thinking,
                prefix_caching=args.prefix_caching,
            )
    raise SystemExit(f"unknown backend {args.backend}")


def task_paths(args: argparse.Namespace) -> list[Path]:
    return loader.expand(args.tasks) if args.tasks else loader.default_paths()


def cmd_tasks(args: argparse.Namespace) -> int:
    paths = task_paths(args)
    tasks = loader.load(paths)
    by = Counter((t.kind.value, t.source, t.split) for t in tasks)
    for (kind, source, split), n in sorted(by.items()):
        print(f"{n:6d}  {kind:8s} {source} [{split}]")
    print(f"{len(tasks)} tasks from {len(paths)} files: ok")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .backends import (
        VLLM_GPU_MEMORY_UTILIZATION,
        VLLM_MAX_MODEL_LEN,
        Sampling,
    )

    paths = task_paths(args)
    tasks = loader.sample(loader.load(paths), args.limit, args.sample_seed)
    check = make_checker(args)  # fail fast, before the model loads
    with open(ste_validate.LEXICON, encoding="utf-8") as f:
        lexicon = json.load(f)
    wordlist = approved_id_list(lexicon) if args.wordlist == "ids" else None

    rid = args.run_id or run_id(args.backend, args.model)
    out = Path(args.results) / rid
    out.mkdir(parents=True, exist_ok=False)

    config = {
        k: v
        for k, v in vars(args).items()
        if k not in ("func", "results", "run_id", "tasks", "skills")
    }
    if args.backend == "vllm":
        config["vllm"] = {
            "max_model_len": VLLM_MAX_MODEL_LEN,
            "gpu_memory_utilization": VLLM_GPU_MEMORY_UTILIZATION,
            "tensor_parallel_size": args.tp,
            "enable_prefix_caching": args.prefix_caching,
        }
    manifest: dict[str, Any] = {
        "run_id": rid,
        "mode": "watermark" if args.watermark else "arms",
        "model": args.model,
        "backend": args.backend,
        "arms": ["A0", "A1"] if args.watermark else args.arms,
        "seed": args.seed,
        "config": config,
        "tasks": {
            "files": loader.digests(paths),
            "lexicon": loader.digests([ste_validate.LEXICON]),
            "ids": [t.id for t in tasks],
        },
        "git": {
            "ste-tax": git_state(REPO),
            "skills": git_state(Path(args.skills)),
        },
        "environment": environment(),
        "started": datetime.now(UTC).isoformat(),
        "finished": None,
    }
    write_json(out / "manifest.json", manifest)

    sampling = Sampling(args.max_new_tokens, args.temperature, args.seed)
    backend = backend_for(args, sampling)

    if args.watermark:
        marks = run_watermark(backend, tasks, wordlist, args)
        write_atomic(out / "records.jsonl", jsonl(marks))
        for w in marks:
            print(
                f"{w.task_id} {w.arm}: z_full={w.z_full} "
                f"z_matched={w.z_matched} (n={w.matched_len})"
            )
    else:
        records = run_arms(backend, tasks, wordlist, args, out / "records.jsonl")
        terms = {t.id: allowed_terms(t) for t in tasks}
        records = score(records, check, terms, args.workers)
        write_atomic(out / "records.jsonl", jsonl(records))
        print("\n" + summarize(records))

    manifest["finished"] = datetime.now(UTC).isoformat()
    write_json(out / "manifest.json", manifest)
    print(f"wrote {out}")
    return 0


def run_arms(backend, tasks, wordlist, args, path: Path) -> list[ArmRecord]:
    """Task-major, arms in the given order. Streams each record to
    `path` as it lands, so a crash keeps the finished part."""
    trie = default_trie()
    ctx = Context(
        model=args.model,
        backend=args.backend,
        wordlist=wordlist,
        tokenizer=backend.tokenizer,
        naive=lambda text, terms: naive_compliance(text, terms, trie),
    )
    records = []
    with open(path, "w", encoding="utf-8") as f:
        for task in tasks:
            for arm in map(Arm, args.arms):
                rec = run_arm(backend.generate, task, arm, ctx)
                records.append(rec)
                f.write(json.dumps(rec.to_json(), ensure_ascii=False) + "\n")
                f.flush()
                print(
                    f"{task.id} {arm}: correct={rec.correct} "
                    f"gen={rec.generated_tokens} "
                    f"reason={rec.reasoning_tokens} "
                    f"compliance={rec.compliance}",
                    flush=True,
                )
    return records


def run_watermark(backend, tasks, wordlist, args) -> list[WatermarkRecord]:
    """A0 vs A1 watermarked generation on writing tasks; z at matched
    length. hf backend only."""
    from . import watermark as wm
    from .backends import HFBackend, Sampling

    if not isinstance(backend, HFBackend):
        raise SystemExit("--watermark needs the hf backend")
    backend.sampling = Sampling(args.wm_tokens, WATERMARK_TEMPERATURE, args.seed)
    vocab = backend.model.config.vocab_size
    records = []
    for task in (t for t in tasks if t.kind is Kind.WRITING):
        ids: dict[Arm, tuple[int, ...]] = {}
        for arm in (Arm.A0, Arm.A1):
            messages = (
                plain(task.prompt)
                if arm is Arm.A0
                else ste(task, wordlist, task.prompt)
            )
            proc = wm.GreenListProcessor(vocab, args.gamma, args.delta, args.wm_key)
            gen = backend.generate(messages, processor=proc)
            assert gen.token_ids is not None  # hf always returns ids
            ids[arm] = gen.token_ids
        matched = min(map(len, ids.values()))
        for arm, seq in ids.items():
            z, greens, _ = wm.z_score(seq, vocab, args.gamma, args.wm_key)
            zm, _, _ = wm.z_score(seq[:matched], vocab, args.gamma, args.wm_key)
            records.append(
                WatermarkRecord(
                    task_id=task.id,
                    arm=arm,
                    tokens=len(seq),
                    greens=greens,
                    z_full=round(z, 3),
                    matched_len=matched,
                    z_matched=round(zm, 3),
                )
            )
    return records


def cmd_summarize(args: argparse.Namespace) -> int:
    run = Path(args.run)
    if read_manifest(run)["mode"] == "watermark":
        for line in (run / "records.jsonl").read_text(encoding="utf-8").splitlines():
            r = WatermarkRecord.from_json(json.loads(line))
            print(f"{r.task_id} {r.arm}: z_full={r.z_full} z_matched={r.z_matched}")
        return 0
    print(summarize(read_records(run)))
    return 0


def cmd_rescore(args: argparse.Namespace) -> int:
    """Run the checker over a finished run. For a cluster run made with
    --checker off: copy the run directory to a machine with uv and
    network, then rescore."""
    run = Path(args.run)
    manifest = read_manifest(run)
    if manifest["mode"] != "arms":
        raise SystemExit("rescore: arms runs only")
    files = manifest["tasks"]["files"]
    paths = [REPO / p for p in files]
    if loader.digests(paths) != files:
        raise SystemExit("rescore: a task file changed since the run")
    tasks = loader.load(paths)
    terms = {t.id: allowed_terms(t) for t in tasks}
    check = CheckerCli.locate(Path(args.skills), args.checker_mode)
    records = score(read_records(run), check, terms, args.workers)
    write_atomic(run / "records.jsonl", jsonl(records))
    manifest["rescored"] = {
        "at": datetime.now(UTC).isoformat(),
        "skills": git_state(Path(args.skills)),
        "checker_mode": args.checker_mode,
    }
    write_json(run / "manifest.json", manifest)
    print(summarize(records))
    return 0


# ----------------------------------------------------------------- parser


def positive(text: str) -> int:
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("need an integer >= 1")
    return n


def checker_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--skills",
        default=str(SKILLS),
        help="SKILLs checkout with asd-ste100; default the submodule",
    )
    p.add_argument(
        "--checker-mode",
        choices=["description", "procedure"],
        default="description",
        help="asd-ste100 check --mode; default description",
    )
    p.add_argument("--workers", type=positive, default=os.cpu_count() or 1)


def task_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--tasks",
        action="append",
        metavar="GLOB",
        help="task files; repeat for more. Default eval/tasks.jsonl "
        "and eval/tasks/*.jsonl",
    )


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m eval",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(required=True)

    run = sub.add_parser("run", help="generate and score one run")
    run.set_defaults(func=cmd_run)
    run.add_argument("--backend", choices=["mock", "hf", "vllm"], default="mock")
    run.add_argument("--model", default="Qwen/Qwen3.8-27B")
    task_args(run)
    run.add_argument(
        "--limit",
        type=positive,
        default=None,
        help="sample N tasks, seeded by --sample-seed",
    )
    run.add_argument("--sample-seed", type=int, default=0)
    run.add_argument(
        "--arms", nargs="+", choices=[a.value for a in Arm], default=["A0", "A2", "A1"]
    )
    run.add_argument("--max-new-tokens", type=positive, default=1024)
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--tp", type=positive, default=1)
    run.add_argument("--no-thinking", dest="thinking", action="store_false")
    run.add_argument(
        "--wordlist",
        choices=["ids", "none"],
        default="ids",
        help="A1/A2 system prompt: ids attaches the 879 approved "
        "'WORD (POS)' ids; none states the rule only. Default ids",
    )
    run.add_argument(
        "--prefix-caching",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="vLLM prefix caching. Default off: cold-prompt cost",
    )
    run.add_argument(
        "--checker",
        choices=["cli", "off"],
        default="cli",
        help="cli: asd-ste100 check per record after generation; "
        "off: record Skipped(off), rescore later",
    )
    checker_args(run)
    run.add_argument("--results", default=str(RESULTS))
    run.add_argument("--run-id", default=None)
    run.add_argument("--watermark", action="store_true")
    run.add_argument("--gamma", type=float, default=0.25)
    run.add_argument("--delta", type=float, default=2.0)
    run.add_argument("--wm-key", type=int, default=42)
    run.add_argument("--wm-tokens", type=positive, default=200)

    summ = sub.add_parser("summarize", help="summary from a run directory")
    summ.set_defaults(func=cmd_summarize)
    summ.add_argument("run")

    resc = sub.add_parser("rescore", help="run the checker over a run")
    resc.set_defaults(func=cmd_rescore)
    resc.add_argument("run")
    checker_args(resc)

    tasks = sub.add_parser("tasks", help="validate task files")
    tasks.set_defaults(func=cmd_tasks)
    task_args(tasks)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except loader.TaskError as e:
        print(f"task error:\n{e}", file=sys.stderr)
        return 1
