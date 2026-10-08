#!/usr/bin/env python3
"""Naive ASD-STE100 vocabulary check via trie + greedy longest match.

Run: uv run scripts/validate.py <text> | -f <file>  (reads data/lexicon.json)

The eval harness imports this module (`scripts.validate`) for its naive
compliance rate; keep the functions pure.

Builds a token-level trie from approved words. Walks the input text,
greedily taking the longest match at each position. Unmatched tokens
are reported as non-conforming.

This check is NECESSARY but NOT SUFFICIENT for ASD-STE100 compliance.
It verifies only that words come from the approved vocabulary. It does
NOT check:
- Part of speech (CLOSE as verb vs adjective)
- Approved meaning (dictionary definitions)
- Writing rules (grammar, sentence structure)

A text that passes this check may still violate ASD-STE100.
A text that fails this check definitely violates it (unknown word used).
"""

import json
import re
import sys
from pathlib import Path

LEXICON = Path(__file__).resolve().parent.parent / "data" / "lexicon.json"


def approved_phrases(lexicon):
    """Approved words with every form, and the derived noun plurals."""
    out = []
    for entry in lexicon["approved"]:
        out.extend(form.upper() for form in entry["forms"])
        if entry["plural"]:
            out.append(entry["plural"].upper())
    return out


def build_trie(phrases):
    """Token-level trie. phrases: list of strings like 'DOWNSTREAM OF'."""
    root = {}
    for phrase in phrases:
        # Skip templates like 'AS ... AS' (not literal)
        if "..." in phrase:
            continue
        tokens = phrase.split()
        node = root
        for tok in tokens:
            node = node.setdefault(tok, {})
        node["$"] = True
    return root


def tokenize(text):
    """Uppercase, split on whitespace, strip punctuation."""
    # STE words: letters, digits, hyphens, apostrophes
    return re.findall(r"[A-Z0-9][A-Z0-9\-']*", text.upper())


def validate(text, trie):
    """Greedy longest match. Returns (conforming_phrases, nonconforming_words).

    O(n) where n is token count: at each position, walk at most
    max_phrase_length steps (constant for STE).
    """
    tokens = tokenize(text)
    conforming = []
    nonconforming = []
    i = 0
    while i < len(tokens):
        node = trie
        longest = 0
        j = i
        # Walk trie, track longest match
        while j < len(tokens) and tokens[j] in node:
            node = node[tokens[j]]
            j += 1
            if "$" in node:
                longest = j - i
        if longest > 0:
            conforming.append(" ".join(tokens[i : i + longest]))
            i += longest
        else:
            # No match: single token is non-conforming, restart from head
            nonconforming.append(tokens[i])
            i += 1
    return conforming, nonconforming


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <text> | -f <file>", file=sys.stderr)
        sys.exit(1)

    with open(LEXICON, encoding="utf-8") as f:
        trie = build_trie(approved_phrases(json.load(f)))

    if sys.argv[1] == "-f":
        with open(sys.argv[2]) as f:
            text = f.read()
    else:
        text = " ".join(sys.argv[1:])

    conforming, nonconforming = validate(text, trie)

    print(f"Tokens: {len(tokenize(text))}")
    print(f"Conforming phrases: {len(conforming)}")
    print(f"Non-conforming words: {len(nonconforming)}")
    if nonconforming:
        print("\nNon-conforming:")
        for w in sorted(set(nonconforming)):
            print(f"  {w}")
    else:
        print("\nPASS: All words from approved vocabulary.")
        print("(Necessary but not sufficient for ASD-STE100 compliance.)")


if __name__ == "__main__":
    main()
