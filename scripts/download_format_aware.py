# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx", "ruamel.yaml"]
# ///
"""Fetch source files in cheapest-to-extract format order.

Walks `source` map per version. For each format we don't already have locally,
tries to GET the URL. Saves on success, records the local path in the manifest.

Priority (cheapest extraction first):
    html → pmc → xml → epub → pdf

Only persists files that look like the requested format (HTML for html/pmc,
PDF magic for pdf, ZIP-with-mimetype for epub, XML prolog for xml).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import httpx
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / "sources"
MANIFEST = REPO / "manifest.yaml"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
FORMAT_ORDER = ["html", "pmc", "xml", "epub", "pdf"]
EXT = {"html": "html", "pmc": "html", "xml": "xml", "epub": "epub", "pdf": "pdf"}

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def slug(s: str) -> str:
    return (s.lower().replace("/", "-").replace(" ", "-")
            .replace(".", "").replace("&", "and"))


def looks_valid(fmt: str, content: bytes, ct: str) -> bool:
    if fmt in ("html", "pmc"):
        if "text/html" in ct.lower() and len(content) > 1024:
            return True
        return content.lstrip().startswith(b"<!") or b"<html" in content[:2048].lower()
    if fmt == "pdf":
        return ct.lower().startswith("application/pdf") or content[:5] == b"%PDF-"
    if fmt == "epub":
        # EPUB = ZIP starting with PK\x03\x04 and a mimetype member
        return content[:4] == b"PK\x03\x04" and b"application/epub+zip" in content[:200]
    if fmt == "xml":
        return content.lstrip()[:5] in (b"<?xml", b"<arti", b"<root")
    return False


def fetch(url: str) -> tuple[Optional[bytes], Optional[str], int]:
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0,
                          headers={"User-Agent": UA, "Accept": "*/*"}) as c:
            r = c.get(url)
            return r.content, r.headers.get("content-type", ""), r.status_code
    except Exception:
        return None, None, 0


def iter_versions(manifest):
    for system, sys_block in manifest.get("systems", {}).items():
        for topic, topic_block in sys_block.get("topics", {}).items():
            topic_society = topic_block.get("society")
            for v in topic_block.get("versions", []):
                yield system, topic, topic_society, v


def main() -> int:
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    n_downloaded = 0
    n_skipped_have = 0
    n_tried = 0
    n_failed = 0

    for system, topic, topic_society, v in iter_versions(manifest):
        src = v.get("source") or {}
        if not isinstance(src, dict):
            continue
        year = v.get("year")
        society = v.get("society") or topic_society

        for fmt in FORMAT_ORDER:
            entry = src.get(fmt)
            if not entry:
                continue
            if entry.get("local"):
                n_skipped_have += 1
                continue
            url = entry.get("url")
            if not url:
                continue

            n_tried += 1
            content, ct, status = fetch(url)
            ident = f"{system}/{topic}/{year or society}/{fmt}"
            if not content or status >= 400:
                print(f"  ✗ {ident:<70} http_{status}")
                n_failed += 1
                continue
            if not looks_valid(fmt, content, ct or ""):
                print(f"  ✗ {ident:<70} not_{fmt} (ct={ct.split(';')[0] if ct else '?'})")
                n_failed += 1
                continue

            ext = EXT[fmt]
            fname_base = f"{year}-{slug(society)}" if year and society else (
                f"{year}" if year else slug(society or "guideline"))
            dest = SOURCES / system / topic / f"{fname_base}.{ext}"
            # avoid clobbering an existing pdf/etc.
            if dest.exists():
                dest = SOURCES / system / topic / f"{fname_base}.{fmt}.{ext}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            rel = dest.relative_to(REPO)
            entry["local"] = f"/{rel}"
            print(f"  ✓ {ident:<70} → {rel}")
            n_downloaded += 1
            time.sleep(0.3)

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)

    print(f"\ndownloaded {n_downloaded}, failed {n_failed}, skipped {n_skipped_have} already-local, tried {n_tried}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
