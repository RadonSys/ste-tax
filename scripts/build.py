"""Build every artifact under data/ from the PDF, then the manifest.

Run: uv run scripts/build.py

Writes data/dictionary.json, data/lexicon.json, data/rules.json, and
data/manifest.json. All parsing finishes before the first write, so a
parse error leaves data/ as it was. The manifest lists each artifact with
its SHA-256 and byte size, so a downloader can verify what it fetched.
"""

import sys
from typing import Any

import pymupdf

import extract_dictionary
import extract_rules
import spec


def documents() -> dict[str, dict[str, Any]]:
    """Artifact name -> document. Pure over the PDF bytes."""
    pdf = pymupdf.open(spec.PDF)
    entries = extract_dictionary.extract(pdf)
    rules = extract_rules.rules_of(extract_rules.listed_rules(pdf))
    head = {"schema_version": spec.SCHEMA_VERSION, "source": spec.source()}
    return {
        "dictionary.json": {**head, "entries": entries},
        "lexicon.json": {**head, **extract_dictionary.lexicon_of(entries)},
        "rules.json": {**head, "rules": rules},
    }


def manifest(blobs: dict[str, bytes]) -> dict[str, Any]:
    return {
        "schema_version": spec.SCHEMA_VERSION,
        "source": spec.source(),
        "artifacts": [
            {"path": f"data/{name}", "sha256": spec.sha256(blob), "bytes": len(blob)}
            for name, blob in sorted(blobs.items())
        ],
    }


def main() -> int:
    try:
        docs = documents()
    except ValueError as err:  # ParseError and rule-set mismatch
        print(f"ERROR {err}", file=sys.stderr)
        return 1
    blobs = {name: spec.write_json(spec.DATA / name, doc) for name, doc in docs.items()}
    spec.write_json(spec.DATA / "manifest.json", manifest(blobs))
    entries = docs["dictionary.json"]["entries"]
    approved = sum(e["status"]["kind"] == "approved" for e in entries)
    print(
        f"{len(entries)} entries ({approved} approved), {len(docs['rules.json']['rules'])} rules",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
