"""Identity of the source specification and the artifact writer.

Every artifact carries `schema_version` and the `source` block below, so a
consumer can tell which issue of ASD-STE100 a file describes without the
PDF. `write_json` is the one place an artifact reaches disk: compact
UTF-8 JSON, one trailing newline, written to a temporary file and renamed,
so a failed run leaves the previous artifact in place.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "artifacts" / "ASD-STE100_ISSUE9.pdf"
DATA = ROOT / "data"

SCHEMA_VERSION = 1


def source() -> dict[str, Any]:
    """The `source` block. The PDF digest pins the exact bytes parsed."""
    return {
        "title": "ASD-STE100 Simplified Technical English",
        "issue": 9,
        "date": "2025-01-15",
        "url": "https://www.asd-ste100.org/",
        "pdf_sha256": sha256(PDF.read_bytes()),
    }


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def encode(doc: dict[str, Any]) -> bytes:
    """Artifact bytes: UTF-8, indent 1, keys in build order, final newline."""
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    return (text + "\n").encode("utf-8")


def write_json(path: Path, doc: dict[str, Any]) -> bytes:
    """Write `doc` atomically; return the bytes written."""
    blob = encode(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(blob)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    return blob
