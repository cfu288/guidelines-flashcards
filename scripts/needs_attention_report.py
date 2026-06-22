# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Generate a human-readable report of manifest version entries still needing
manual download, with their URLs.

Also flips a final cleanup pass: any version that has a `source:` pointing to
a file that doesn't actually exist (or is < 1KB) gets `needs_attention:
download_failed` re-set and `source:` removed.

Writes spec/manifest-needs-attention.md (NOT /tmp — kept under spec/ because
it's a human-readable curation report, not a build artifact).
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"
REPORT = REPO / "spec" / "manifest-needs-attention.md"

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def iter_versions(manifest):
    for system, sys_block in manifest.get("systems", {}).items():
        for topic, topic_block in sys_block.get("topics", {}).items():
            topic_society = topic_block.get("society")
            for version in topic_block.get("versions", []):
                yield system, topic, topic_society, version


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    # 1. Verify on-disk files exist and have plausible size; remove dead local pointers.
    fixed = 0
    for _, _, _, v in iter_versions(manifest):
        src_map = v.get("source")
        if not isinstance(src_map, dict):
            continue
        for fmt in list(src_map.keys()):
            entry = src_map[fmt] or {}
            local = entry.get("local")
            if not local:
                continue
            p = REPO / local.lstrip("/")
            if not p.exists() or p.stat().st_size < 1024:
                entry.pop("local", None)
                if not entry:
                    del src_map[fmt]
                fixed += 1
        if not src_map:
            del v["source"]
            v.setdefault("needs_attention", "download_failed: tiny_or_missing_file")

    # 2. Clear ONLY stale `download_failed:` markers when the entry now has a local file.
    #    Other needs_attention reasons (downloaded_file_was_wrong, supplementary_appendix,
    #    pdf_local_was_misassigned, etc.) are deliberate flags and must be preserved.
    cleared = 0
    STALE_PREFIXES = ("download_failed",)
    for _, _, _, v in iter_versions(manifest):
        src_map = v.get("source") or {}
        if not isinstance(src_map, dict):
            continue
        has_any_local = any((src_map[k] or {}).get("local") for k in src_map)
        if has_any_local and "needs_attention" in v:
            if str(v["needs_attention"]).startswith(STALE_PREFIXES):
                del v["needs_attention"]
                cleared += 1

    if fixed or cleared:
        with MANIFEST.open("w") as f:
            yaml.dump(manifest, f)

    # Build the report
    def has_local(v):
        src = v.get("source") or {}
        return isinstance(src, dict) and any((src[k] or {}).get("local") for k in src)

    def filename_for(year, society, ext):
        s = (society or "").lower().replace("/", "-").replace(" ", "-").replace(".", "").replace("&", "and")
        if year and s:
            return f"{year}-{s}.{ext}"
        if year:
            return f"{year}.{ext}"
        return f"{s or 'guideline'}.{ext}"

    # --- Section 1: needs attention (no source at all OR explicitly flagged) ---
    no_source = []
    for system, topic, topic_society, v in iter_versions(manifest):
        # Include if no local OR if explicitly flagged needs_attention
        if has_local(v) and "needs_attention" not in v:
            continue
        url = v.get("url")
        if not url:
            continue
        no_source.append({
            "system": system, "topic": topic,
            "year": v.get("year"),
            "society": v.get("society") or topic_society,
            "url": url,
            "reason": v.get("needs_attention", "no_local_source"),
            "title": v.get("title", "(no title)"),
        })

    # --- Section 2: format URLs known but not downloaded (per format) ---
    # Excludes formats whose URL came from an unverified pattern (bot-blocked publisher direct).
    # Strategy: include any format where source.<fmt>.url is set and source.<fmt>.local is not,
    # regardless of whether other formats are downloaded.
    by_format: dict[str, list[dict]] = {}
    for system, topic, topic_society, v in iter_versions(manifest):
        src = v.get("source") or {}
        if not isinstance(src, dict):
            continue
        for fmt, entry in src.items():
            entry = entry or {}
            if entry.get("local") or not entry.get("url"):
                continue
            # skip pdf in this section — the "needs download" Section 1 already lists those, and
            # most PDF URLs we have are landing pages, not direct downloads
            if fmt == "pdf":
                continue
            year = v.get("year")
            society = v.get("society") or topic_society
            ext = "html" if fmt in ("html", "pmc") else fmt
            suggested = f"sources/{system}/{topic}/{filename_for(year, society, ext)}"
            by_format.setdefault(fmt, []).append({
                "system": system, "topic": topic,
                "year": year, "society": society,
                "title": v.get("title", "(no title)"),
                "url": entry["url"],
                "suggested_path": suggested,
            })

    # --- Build the report ---
    lines = ["# Manifest source-file gaps", ""]

    lines.append(f"**Section 1 — needs download (no source at all): {len(no_source)} entries**\n")
    if no_source:
        grouped = {}
        for e in no_source:
            grouped.setdefault(e["system"], []).append(e)
        for system in sorted(grouped):
            lines.append(f"### {system}")
            lines.append("")
            for e in grouped[system]:
                key = f"{e['year']} {e['society']}" if e['year'] else e['society']
                lines.append(f"- **{e['topic']}** ({key}) — {e['title']}")
                lines.append(f"  - url: {e['url']}")
                lines.append(f"  - reason: `{e['reason']}`")
            lines.append("")
    else:
        lines.append("_None — every version has at least one local source file._\n")

    fmt_total = sum(len(v) for v in by_format.values())
    lines.append(f"**Section 2 — alternate formats with URL but not yet downloaded: {fmt_total} entries**\n")
    lines.append("These are non-PDF formats (cheaper to extract) whose URLs are known. Download manually and drop into `tmp/`; the import script will move them to the suggested path.\n")

    for fmt in sorted(by_format.keys()):
        entries = by_format[fmt]
        lines.append(f"### {fmt.upper()} ({len(entries)})")
        lines.append("")
        grouped = {}
        for e in entries:
            grouped.setdefault(e["system"], []).append(e)
        for system in sorted(grouped):
            for e in grouped[system]:
                key = f"{e['year']} {e['society']}" if e['year'] else e['society']
                lines.append(f"- **{e['system']}/{e['topic']}** ({key}) — {e['title']}")
                lines.append(f"  - url: {e['url']}")
                lines.append(f"  - save to: `{e['suggested_path']}`")
            lines.append("")

    REPORT.write_text("\n".join(lines))
    print(f"wrote {REPORT}: {len(no_source)} needs-download, {fmt_total} alternate-format gaps")
    if fixed:
        print(f"  (also cleaned {fixed} entries with tiny/missing source files)")
    if cleared:
        print(f"  (also cleared {cleared} stale needs_attention markers on entries with a local file)")


if __name__ == "__main__":
    main()
