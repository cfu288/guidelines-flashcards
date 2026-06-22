# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Generate /tmp/epub-launchpad.html with article URLs for every version that
lacks an EPUB locally. Grouped by publisher domain. Each row shows the URL,
the version's title, and the suggested save filename.

Open via `node scripts/open_browser.js` (loads this launchpad by default).
"""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlparse

from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"
OUT = Path("/tmp/epub-launchpad.html")

yaml = YAML()


def slug(s):
    return (s or "").lower().replace("/", "-").replace(" ", "-").replace(".", "").replace("&", "and")


def filename_for(year, society):
    if year and society:
        return f"{year}-{slug(society)}.epub"
    if year:
        return f"{year}.epub"
    return f"{slug(society or 'guideline')}.epub"


def iter_versions(manifest):
    for system, sb in manifest.get("systems", {}).items():
        for topic, tb in sb.get("topics", {}).items():
            ts = tb.get("society")
            for v in tb.get("versions", []):
                yield system, topic, ts, v


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    rows = []
    for system, topic, topic_society, v in iter_versions(manifest):
        src = v.get("source") or {}
        if isinstance(src, dict) and (src.get("epub") or {}).get("local"):
            continue
        # Prefer source.html.url (more specific, e.g. /doi/full/) over the bare canonical url
        html_url = (src.get("html") or {}).get("url") if isinstance(src, dict) else None
        article_url = html_url or v.get("url")
        if not article_url:
            continue
        year = v.get("year")
        society = v.get("society") or topic_society
        rows.append({
            "system": system,
            "topic": topic,
            "year": year,
            "society": society or "",
            "title": v.get("title", "(no title)"),
            "url": article_url,
            "suggested": filename_for(year, society),
            "host": urlparse(article_url).hostname or "?",
        })

    rows.sort(key=lambda r: (r["host"], r["system"], r["topic"], -(r["year"] or 0)))

    parts = ["<!doctype html><html><head><meta charset='utf-8'><title>EPUB launchpad</title>",
             "<style>",
             "body{font-family:-apple-system,sans-serif;max-width:1200px;margin:1em auto;padding:0 1em;font-size:14px}",
             "h2{margin-top:2em;border-bottom:1px solid #ccc;padding-bottom:.3em}",
             "table{width:100%;border-collapse:collapse}",
             "td{vertical-align:top;padding:.4em .6em;border-bottom:1px solid #eee}",
             "tr:hover{background:#fafafa}",
             ".topic{font-weight:600;color:#333}",
             ".meta{color:#666;font-size:.85em}",
             ".filename{font-family:ui-monospace,monospace;color:#446;font-size:.85em}",
             "a{color:#06c;text-decoration:none} a:hover{text-decoration:underline}",
             "</style></head><body>"]
    parts.append(f"<h1>EPUB launchpad — {len(rows)} entries without a local EPUB</h1>")
    parts.append("<p>Click an article URL → look for an EPUB download (Tools menu, "
                 "format toggle in the reader, etc.). Downloads land in "
                 "<code>tmp/</code>; run <code>import_manual_downloads.py</code> to move them.</p>")

    by_host = {}
    for r in rows:
        by_host.setdefault(r["host"], []).append(r)

    for host in sorted(by_host):
        parts.append(f"<h2>{html.escape(host)} <span class='meta'>({len(by_host[host])} entries)</span></h2>")
        parts.append("<table>")
        for r in by_host[host]:
            year_society = f"{r['year']} {r['society']}" if r['year'] else r['society']
            parts.append("<tr>")
            parts.append(f"<td><div class='topic'>{html.escape(r['system'])}/{html.escape(r['topic'])}</div>"
                         f"<div class='meta'>{html.escape(year_society)}</div></td>")
            parts.append(f"<td>{html.escape(r['title'])}</td>")
            parts.append(f"<td><a href='{html.escape(r['url'])}' target='_blank'>open</a></td>")
            parts.append(f"<td><span class='filename'>{html.escape(r['suggested'])}</span></td>")
            parts.append("</tr>")
        parts.append("</table>")

    parts.append("</body></html>")
    OUT.write_text("".join(parts))
    print(f"wrote {OUT} ({len(rows)} rows, {len(by_host)} hosts)")


if __name__ == "__main__":
    main()
