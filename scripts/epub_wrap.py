# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Prepare EPUB pending list (from manifest) and apply puppeteer results.

Usage:
    uv run scripts/epub_wrap.py prepare
    node scripts/puppeteer_epub.js                       # headless
    MODE=visible node scripts/puppeteer_epub.js          # browser visible, paused per URL
    uv run scripts/epub_wrap.py apply
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / "sources"
MANIFEST = REPO / "manifest.yaml"
PENDING = Path("/tmp/manifest-epub-pending.json")
RESULTS = Path("/tmp/manifest-epub-results.json")

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def slug(s):
    return (s or "").lower().replace("/", "-").replace(" ", "-").replace(".", "").replace("&", "and")


def filename_for(year, society):
    if year and society:
        return f"{year}-{slug(society)}.epub"
    if year:
        return f"{year}.epub"
    return f"{slug(society or 'guideline')}.epub"


def iter_versions(manifest):
    for system, sys_block in manifest.get("systems", {}).items():
        for topic, topic_block in sys_block.get("topics", {}).items():
            topic_society = topic_block.get("society")
            for v in topic_block.get("versions", []):
                yield system, topic, topic_society, v


def prepare():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)
    pending = []
    for system, topic, topic_society, v in iter_versions(manifest):
        src = v.get("source") or {}
        if not isinstance(src, dict):
            continue
        epub = src.get("epub") or {}
        if epub.get("local") or not epub.get("url"):
            continue
        year = v.get("year")
        society = v.get("society") or topic_society
        dest = SOURCES / system / topic / filename_for(year, society)
        pending.append({
            "ident": f"{system}/{topic}/{year or society}",
            "url": epub["url"],
            "dest": str(dest),
            "_system": system,
            "_topic": topic,
            "_year": year,
            "_society": society,
        })
    PENDING.write_text(json.dumps(pending, indent=2))
    print(f"wrote {PENDING} with {len(pending)} pending EPUB URLs")


def apply():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)
    results = json.loads(RESULTS.read_text())
    by_ident = {r["ident"]: r for r in results}

    ok = fail = 0
    for system, topic, topic_society, v in iter_versions(manifest):
        year = v.get("year")
        society = v.get("society") or topic_society
        ident = f"{system}/{topic}/{year or society}"
        r = by_ident.get(ident)
        if not r:
            continue
        if r["status"] == "downloaded":
            rel = Path(r["dest"]).relative_to(REPO)
            src = v.setdefault("source", {})
            src.setdefault("epub", {})["local"] = f"/{rel}"
            ok += 1
        elif r["status"] == "failed":
            # Don't mark on the manifest — keep the URL so a future retry can grab it.
            # The PDF is still usable as fallback for extraction.
            fail += 1

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)
    print(f"applied: {ok} downloaded, {fail} still failing")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("prepare", "apply"):
        print("usage: epub_wrap.py prepare|apply", file=sys.stderr)
        return 2
    if sys.argv[1] == "prepare":
        prepare()
    else:
        apply()
    return 0


if __name__ == "__main__":
    sys.exit(main())
