"""Task loader: JSONL files to validated Tasks.

Default set: eval/tasks.jsonl plus every eval/tasks/*.jsonl, in that
order, files sorted by name. `--tasks GLOB` replaces the default set.
One record per line; blank lines skip. Every error in every file is
collected and reported at once; a duplicate id across files is an
error. `sample` takes N tasks by a seeded draw and keeps file order.
"""

from __future__ import annotations

import glob
import hashlib
import json
import random
from collections.abc import Iterable, Sequence
from pathlib import Path

from .records import SchemaError, Task, parse_task

EVAL = Path(__file__).resolve().parent


class TaskError(ValueError):
    def __init__(self, errors: Sequence[str]):
        super().__init__("\n".join(errors))
        self.errors = tuple(errors)


def default_paths() -> list[Path]:
    main = EVAL / "tasks.jsonl"
    rest = sorted((EVAL / "tasks").glob("*.jsonl"))
    return [main, *rest] if main.is_file() else rest


def expand(patterns: Iterable[str]) -> list[Path]:
    """Each glob must match at least one file. Order: pattern order,
    then name; a file matched twice loads once."""
    out: dict[Path, None] = {}
    for pattern in patterns:
        hits = sorted(glob.glob(pattern, recursive=True))
        if not hits:
            raise TaskError([f"--tasks {pattern}: no file matches"])
        out.update((Path(h).resolve(), None) for h in hits)
    return list(out)


def parse_lines(named_lines: Iterable[tuple[str, Iterable[str]]]) -> list[Task]:
    """Pure core of the loader: (file name, lines) pairs to Tasks."""
    tasks: list[Task] = []
    seen: dict[str, str] = {}
    errors: list[str] = []
    for name, lines in named_lines:
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            where = f"{name}:{n}"
            try:
                task = parse_task(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"{where}: bad JSON: {e.msg}")
                continue
            except SchemaError as e:
                errors.append(f"{where}: {e}")
                continue
            if task.id in seen:
                errors.append(
                    f"{where}: duplicate id {task.id!r} (first at {seen[task.id]})"
                )
                continue
            seen[task.id] = where
            tasks.append(task)
    if errors:
        raise TaskError(errors)
    return tasks


def load(paths: Sequence[Path]) -> list[Task]:
    if not paths:
        raise TaskError(["no task files"])

    def read(p: Path) -> tuple[str, list[str]]:
        return display(p), p.read_text(encoding="utf-8").splitlines()

    return parse_lines(map(read, paths))


def sample(tasks: Sequence[Task], limit: int | None, seed: int) -> list[Task]:
    """`limit` tasks by a seeded draw, in their original order. None or
    a limit at or above the count keeps all."""
    if limit is None or limit >= len(tasks):
        return list(tasks)
    keep = sorted(random.Random(seed).sample(range(len(tasks)), limit))
    return [tasks[i] for i in keep]


def display(p: Path) -> str:
    """Repo-relative when inside the repo, else absolute."""
    return str(p.relative_to(EVAL.parent)) if p.is_relative_to(EVAL.parent) else str(p)


def digests(paths: Iterable[Path]) -> dict[str, str]:
    return {display(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
