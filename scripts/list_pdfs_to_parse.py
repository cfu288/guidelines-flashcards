# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""List PDFs that need LlamaParse, in priority order.

Selection criteria for "needs LlamaParse":
  - version is CURRENT (highest `year` per topic, or a living/no-year entry)
  - source.pdf.local exists
  - source.epub.local is NOT set  (skip — EPUB extracts cheaper)
  - source.html.local is NOT set  (skip — HTML extracts cheaper)
  - sibling .md doesn't exist OR is empty (skip already-parsed)

Priority order:
  1. Topics flagged `high_yield: true` in manifest (priority block)
  2. Other current versions

Prints one absolute PDF path per line, suitable to pipe into `parse_sources.py`.
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"

yaml = YAML()


def is_current(version, all_versions, topic_society):
    """A version is 'current' if it's the highest year for its (topic, society) cohort,
    or has no year (living doc). Concurrent guidelines from DIFFERENT societies are all
    primary — only same-society same-topic older versions are superseded.
    """
    year = version.get("year")
    if year is None:
        return True
    society = version.get("society") or topic_society
    same_society_years = [
        v.get("year") for v in all_versions
        if v.get("year") is not None
        and (v.get("society") or topic_society) == society
    ]
    return year == max(same_society_years) if same_society_years else True


def needs_llamaparse(version) -> Path | None:
    """Return the PDF path if it needs LlamaParsing, else None."""
    src = version.get("source") or {}
    if not isinstance(src, dict):
        return None
    pdf_entry = src.get("pdf") or {}
    pdf_local = pdf_entry.get("local")
    if not pdf_local:
        return None
    # Skip if a cheaper text format is already local
    if (src.get("epub") or {}).get("local"):
        return None
    if (src.get("html") or {}).get("local"):
        return None
    pdf_path = REPO / pdf_local.lstrip("/")
    if not pdf_path.is_file():
        return None
    md_path = pdf_path.with_suffix(".md")
    if md_path.is_file() and md_path.stat().st_size > 0:
        return None
    return pdf_path


def priority_topics(manifest):
    """Return {(system_slug, topic_slug)} for every topic with high_yield: true.

    Single source of truth for the high-yield set is `topic.high_yield: true`
    in the manifest (see spec/conventions.md).
    """
    out: set[tuple[str, str]] = set()
    for sys_slug, sys_block in (manifest.get("systems") or {}).items():
        for topic_slug, topic_block in (sys_block.get("topics") or {}).items():
            if topic_block.get("high_yield"):
                out.add((sys_slug, topic_slug))
    return out


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)
    hy_topics = priority_topics(manifest)

    priority: list[Path] = []
    rest: list[Path] = []
    for system, sys_block in manifest.get("systems", {}).items():
        for topic, topic_block in sys_block.get("topics", {}).items():
            versions = topic_block.get("versions", [])
            topic_society = topic_block.get("society")
            is_hy = (system, topic) in hy_topics or (system, None) in hy_topics
            for v in versions:
                if not is_current(v, versions, topic_society):
                    continue
                p = needs_llamaparse(v)
                if p is None:
                    continue
                (priority if is_hy else rest).append(p)

    # Print: priority first (with a comment header line going to stderr), then rest
    import sys
    print(f"# {len(priority)} priority + {len(rest)} rest = {len(priority) + len(rest)} PDFs to parse", file=sys.stderr)
    for p in priority + rest:
        print(p.relative_to(REPO))


if __name__ == "__main__":
    main()
