# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "llama-parse",
#   "python-dotenv",
#   "ebooklib",
#   "markdownify",
#   "beautifulsoup4",
#   "lxml",
# ]
# ///
"""Parse source documents under sources/ into sibling .md files.

One unified script — replaces the old parse_sources.py (PDF-only) and
parse_alt_formats.py. For each (topic_dir, basename) group, picks the highest-
preference format on disk and parses ONLY that one:

    epub > html > pdf

Local libraries do EPUB and HTML for free. PDF falls back to the LlamaParse
API (paid) when no better format is available.

Each parsed .md gets a one-line HTML-comment provenance marker at the top:

    <!-- parsed-from: 2025-aha-acc.epub sha256:abc123... -->

On re-runs, the marker drives idempotency:
- marker says EPUB+matching-hash and EPUB still on disk → SKIP
- marker says PDF but EPUB has been added → UPGRADE (re-parse from EPUB)
- no marker and a better format is available than the .md probably came from
  → UPGRADE
- no marker and only same/worse format on disk → SKIP (don't waste credits)

Usage:
    uv run scripts/parse_sources.py
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ebooklib import ITEM_DOCUMENT, epub
from markdownify import markdownify


SOURCES = Path("sources")
FORMATS = ("epub", "html", "pdf")  # most-preferred first
PROVENANCE_RE = re.compile(
    r"^<!-- parsed-from:\s+(\S+)\s+sha256:([a-f0-9]+)\s+-->$"
)


# ────────────────────────────────────────────────────────────────────────────
# Converters
# ────────────────────────────────────────────────────────────────────────────

def html_str_to_md(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return markdownify(str(soup), heading_style="ATX").strip() + "\n"


def parse_html(path: Path) -> str:
    return html_str_to_md(path.read_text(encoding="utf-8", errors="replace"))


def parse_epub(path: Path) -> str:
    try:
        book = epub.read_epub(str(path), options={"ignore_ncx": True})
        chunks: list[str] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            html = item.get_content().decode("utf-8", errors="replace")
            md = html_str_to_md(html)
            if md.strip():
                chunks.append(md)
        return "\n\n".join(chunks).strip() + "\n"
    except KeyError:
        # Publisher EPUBs (notably journals.lww.com) sometimes use Windows-
        # style backslashes in zip entry paths, which ebooklib can't follow.
        return _parse_epub_zip_fallback(path)


def _parse_epub_zip_fallback(path: Path) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = sorted(
            n for n in zf.namelist()
            if n.lower().endswith((".html", ".xhtml", ".htm"))
        )
        body = [n for n in names if "cover" not in n.lower()] or names
        for n in body:
            html = zf.read(n).decode("utf-8", errors="replace")
            md = html_str_to_md(html)
            if md.strip():
                chunks.append(md)
    return "\n\n".join(chunks).strip() + "\n"


def parse_pdf(path: Path, api_key: str) -> str:
    # Import lazily — only paid-API path needs it.
    from llama_parse import LlamaParse

    parser = LlamaParse(api_key=api_key, result_type="markdown")
    docs = parser.load_data(str(path))
    return "\n\n".join(d.text for d in docs).strip() + "\n"


# ────────────────────────────────────────────────────────────────────────────
# Provenance + idempotency
# ────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_marker(md_path: Path) -> Optional[tuple[str, str]]:
    """Return (source_filename, sha256) from the .md provenance marker, or None."""
    if not md_path.is_file():
        return None
    try:
        with md_path.open() as f:
            first = f.readline().rstrip("\n")
    except OSError:
        return None
    m = PROVENANCE_RE.match(first)
    if not m:
        return None
    return m.group(1), m.group(2)


def marker_line(source_filename: str, source_hash: str) -> str:
    return f"<!-- parsed-from: {source_filename} sha256:{source_hash} -->\n\n"


def best_available(group: dict[str, Path]) -> Optional[tuple[str, Path]]:
    """From {format: path}, return (format, path) for the highest-preference one."""
    for fmt in FORMATS:
        if fmt in group:
            return fmt, group[fmt]
    return None


def group_sources(root: Path) -> dict[tuple[Path, str], dict[str, Path]]:
    """Walk source files; group by (topic_dir, basename) → {format: path}."""
    out: dict[tuple[Path, str], dict[str, Path]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower().lstrip(".")
        if ext not in FORMATS:
            continue
        key = (path.parent, path.stem)
        out.setdefault(key, {})[ext] = path
    return out


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if not SOURCES.is_dir():
        print(f"no {SOURCES}/ directory", file=sys.stderr)
        return 1

    load_dotenv()
    api_key = os.environ.get("LLAMA_PARSE")

    groups = group_sources(SOURCES)
    if not groups:
        print(f"no source files under {SOURCES}/")
        return 0

    parsed: list[Path] = []
    upgraded: list[tuple[Path, str, str]] = []  # (md_path, from_fmt, to_fmt)
    skipped_current: list[Path] = []
    skipped_unknown: list[Path] = []
    pdf_calls = 0
    failed: list[tuple[Path, str]] = []

    for (topic_dir, basename), group in groups.items():
        chosen = best_available(group)
        if chosen is None:
            continue
        chosen_fmt, src_path = chosen
        md_path = topic_dir / f"{basename}.md"
        src_hash = sha256_file(src_path)

        marker = read_marker(md_path)
        if marker:
            marker_filename, marker_hash = marker
            marker_fmt = Path(marker_filename).suffix.lower().lstrip(".")
            if marker_fmt == chosen_fmt and marker_hash == src_hash:
                skipped_current.append(md_path)
                continue
            # Marker present but a better/different source is now chosen.
            if marker_fmt != chosen_fmt:
                action_label = f"upgrade {marker_fmt}→{chosen_fmt}"
            else:
                action_label = f"refresh ({chosen_fmt} content changed)"
        elif md_path.is_file():
            # No marker → existing .md is from before this script. Re-parse
            # ONLY if a strictly better format is available than what we'd
            # assume the .md came from. We assume the .md came from "best
            # available at time of last run." If that's the same as `chosen`,
            # leave it alone (don't burn LlamaParse credits relitigating).
            #
            # In practice this means unmarked .md files survive untouched on
            # the first migrated run. Future drops of better formats DO
            # trigger upgrades because, after the first parse, the marker
            # exists and the upgrade-detection branch above kicks in.
            skipped_unknown.append(md_path)
            continue
        else:
            action_label = f"parse ({chosen_fmt})"

        # Do the parse.
        try:
            if chosen_fmt == "epub":
                content = parse_epub(src_path)
            elif chosen_fmt == "html":
                content = parse_html(src_path)
            elif chosen_fmt == "pdf":
                if not api_key:
                    failed.append(
                        (src_path, "LLAMA_PARSE not set in .env (PDF requires API)")
                    )
                    continue
                content = parse_pdf(src_path, api_key)
                pdf_calls += 1
            else:
                continue
        except Exception as e:
            failed.append((src_path, f"{chosen_fmt}: {e}"))
            print(f"  {src_path}: failed ({e})", file=sys.stderr)
            continue

        if not content.strip():
            failed.append((src_path, f"{chosen_fmt}: empty output"))
            continue

        out = marker_line(src_path.name, src_hash) + content
        md_path.write_text(out)

        if marker and marker[0] != src_path.name:
            from_fmt = Path(marker[0]).suffix.lower().lstrip(".")
            upgraded.append((md_path, from_fmt, chosen_fmt))
        else:
            parsed.append(md_path)
        print(f"  {action_label}: {src_path} → {md_path}", flush=True)

    print(
        f"\ndone: parsed {len(parsed)}, "
        f"upgraded {len(upgraded)}, "
        f"current {len(skipped_current)}, "
        f"unknown-existing {len(skipped_unknown)}, "
        f"failed {len(failed)}, "
        f"LlamaParse API calls: {pdf_calls}"
    )
    if failed:
        print("\nfailures:", file=sys.stderr)
        for p, d in failed:
            print(f"  {p}: {d}", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
