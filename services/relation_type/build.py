#!/usr/bin/env python3
"""Build a single combined JSON-LD document from the DataCite relationType vocab.

Fetches every file in
  https://github.com/datacite/schema.datacite.org-linked-data/tree/main/vocab/relationType
and merges the individual SKOS Concept files, the ConceptScheme, and the shared
@context into one self-contained JSON-LD document (services/relation_type/relationType.jsonld).

Stdlib only. Set GITHUB_TOKEN in the environment to raise the API rate limit (used in CI).
Output is deterministic (sorted @graph, stable formatting) so the weekly diff only changes
when the upstream vocabulary actually changes.
"""
import json
import os
import sys
import urllib.request
from typing import Any, Dict, List

OWNER = "datacite"
REPO = "schema.datacite.org-linked-data"
REF = "main"
PATH = "vocab/relationType"
SOURCE_URL = f"https://github.com/{OWNER}/{REPO}/tree/{REF}/{PATH}"

CONTENTS_API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}?ref={REF}"

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relationType.jsonld")


def _get(url: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": "integrations-relationtype-builder",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_files() -> Dict[str, Any]:
    """Return {filename: parsed_json} for every .jsonld file in the folder."""
    listing = json.loads(_get(CONTENTS_API))
    files: Dict[str, Any] = {}
    for entry in listing:
        name = entry.get("name", "")
        if entry.get("type") != "file" or not name.endswith(".jsonld"):
            continue
        files[name] = json.loads(_get(entry["download_url"], accept="application/json"))
    return files


def build(files: Dict[str, Any]) -> Dict[str, Any]:
    if "context.jsonld" not in files:
        raise SystemExit("build: context.jsonld missing from upstream folder")
    if "relationType.jsonld" not in files:
        raise SystemExit("build: relationType.jsonld (ConceptScheme) missing from upstream folder")

    context = files["context.jsonld"]["@context"]

    # Pick the ConceptScheme by type, not by position, so upstream reordering
    # of relationType.jsonld's @graph can't select the wrong node.
    scheme_graph = files["relationType.jsonld"].get("@graph", [])
    scheme = next((n for n in scheme_graph if n.get("type") == "ConceptScheme"), None)
    if scheme is None:
        raise SystemExit("build: no ConceptScheme node found in relationType.jsonld")

    # Every other file is an individual Concept. Keep only type == Concept (so a
    # future non-concept file isn't silently emitted as one) and drop each node's
    # per-file @context (we inline a single shared one at the document level).
    concepts: List[Dict[str, Any]] = []
    for name, doc in files.items():
        if name in ("context.jsonld", "relationType.jsonld"):
            continue
        if doc.get("type") != "Concept":
            print(f"build: skipping {name} (type={doc.get('type')!r}, not a Concept)")
            continue
        concepts.append({k: v for k, v in doc.items() if k != "@context"})

    concepts.sort(key=lambda n: n.get("id", ""))

    return {
        "SPDX-License-Identifier": "Apache-2.0",
        "_source": SOURCE_URL,
        "_modifications": (
            "Individual *.jsonld concept files and context.jsonld combined into one "
            "JSON-LD document with an inlined @context. See services/relation_type/NOTICE."
        ),
        "@context": context,
        "@graph": [scheme] + concepts,
    }


def main() -> int:
    files = fetch_files()
    doc = build(files)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    n_concepts = sum(1 for n in doc["@graph"] if n.get("type") == "Concept")
    print(f"Wrote {OUT_FILE}: {len(doc['@graph'])} nodes ({n_concepts} concepts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
