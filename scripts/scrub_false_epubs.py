# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Remove the AHA `/doi/epub/<DOI>` URLs that the research agent inferred but
that don't actually serve EPUBs (Cloudflare-gated, return HTML challenge page).

Removes any `source.epub` entry whose URL matches the AHA epub pattern and has
no `local` file yet.
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def iter_versions(manifest):
    for s, sb in manifest.get("systems", {}).items():
        for t, tb in sb.get("topics", {}).items():
            for v in tb.get("versions", []):
                yield s, t, v


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    removed = 0
    for system, topic, v in iter_versions(manifest):
        src = v.get("source") or {}
        if not isinstance(src, dict):
            continue
        epub = src.get("epub")
        if not isinstance(epub, dict):
            continue
        url = epub.get("url", "")
        if "ahajournals.org/doi/epub/" in url and not epub.get("local"):
            del src["epub"]
            removed += 1
            print(f"  removed {system}/{topic} epub: {url}")

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)
    print(f"\nremoved {removed} false AHA EPUB entries")


if __name__ == "__main__":
    main()
