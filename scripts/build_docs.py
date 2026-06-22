# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Generate Jekyll-rendered listing pages under docs/ from manifest.yaml.

Layout:
    docs/index.md          — root: list of systems with topic count each
    docs/<system>.md       — per system: topics with all versions inline

Source-file local paths are intentionally NOT linked from these pages — they
are copyrighted and gitignored. Only public publisher URLs are surfaced.
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"
DOCS = REPO / "docs"

yaml = YAML()


def fmt_year_society(year, society):
    if year and society:
        return f"{year} · {society}"
    if year:
        return str(year)
    return society or "(no year)"


def site_url(path: str) -> str:
    """Emit a Liquid expression that resolves to a baseurl-aware site URL.

    Jekyll processes Liquid before kramdown, so `[label]({{ '/x/' | relative_url }})`
    is rewritten to the correct href whether baseurl is `/guidelines-flashcards`
    or empty. Works on GH Pages project sites AND root-domain hosting.

    NOT suitable for `permalink:` frontmatter — Jekyll doesn't expand Liquid
    there; use `system_permalink()` for that.
    """
    return "{{ '" + path + "' | relative_url }}"


def system_permalink(slug: str) -> str:
    """Bare path for `permalink:` frontmatter. Jekyll prepends baseurl automatically
    for permalinks at render time."""
    return f"/{slug}/"


def system_link(slug: str) -> str:
    """Liquid-wrapped href for use inside markdown links."""
    return site_url(f"/{slug}/")


def render_version(v: dict, topic_society: str | None) -> list[str]:
    out: list[str] = []
    year = v.get("year")
    society = v.get("society") or topic_society
    title = v.get("title") or "(no title)"
    out.append(f"  - **{fmt_year_society(year, society)}** — {title}")

    badges: list[str] = []
    if v.get("needs_attention"):
        badges.append(f"⚠️ needs attention: `{v['needs_attention']}`")
    if badges:
        out.append(f"    - {' · '.join(badges)}")

    notes = v.get("notes")
    if notes:
        out.append(f"    - _{notes}_")

    src = v.get("source") or {}
    # Collect just the publisher URLs per format (no local paths — gitignored)
    url_links: list[str] = []
    if v.get("url"):
        url_links.append(f"[canonical]({v['url']})")
    if isinstance(src, dict):
        for fmt in ("html", "pdf", "epub", "pmc", "xml"):
            entry = src.get(fmt)
            if isinstance(entry, dict) and entry.get("url"):
                url_links.append(f"[{fmt}]({entry['url']})")
    if v.get("pmid"):
        url_links.append(f"[PubMed](https://pubmed.ncbi.nlm.nih.gov/{v['pmid']}/)")
    if url_links:
        out.append(f"    - {' · '.join(url_links)}")
    return out


def render_topic(topic_slug: str, topic_block: dict) -> list[str]:
    out: list[str] = []
    title = topic_block.get("title") or topic_slug
    society = topic_block.get("society")
    high_yield = topic_block.get("high_yield")
    header = f"### {title}"
    if high_yield:
        header += " ⭐"
    out.append(header)
    out.append("")
    meta_parts = [f"`{topic_slug}`"]
    if society:
        meta_parts.append(f"society: **{society}**")
    if high_yield:
        meta_parts.append("**high-yield**")
    out.append(" · ".join(meta_parts))
    out.append("")
    for v in topic_block.get("versions", []):
        out.extend(render_version(v, society))
    out.append("")
    return out


def render_system(system_slug: str, sys_block: dict) -> str:
    lines: list[str] = ["---"]
    lines.append(f'title: {sys_block.get("title", system_slug)}')
    lines.append(f"permalink: {system_permalink(system_slug)}")
    lines.append("---")
    lines.append("")
    if sys_block.get("description"):
        lines.append(f"> {sys_block['description']}")
        lines.append("")
    topics = sys_block.get("topics") or {}
    n_topics = len(topics)
    n_versions = sum(len(t.get("versions", [])) for t in topics.values())
    n_hy = sum(1 for t in topics.values() if t.get("high_yield"))
    lines.append(
        f"**{n_topics} topics** · **{n_versions} versions** · **{n_hy} high-yield**"
    )
    lines.append("")
    lines.append(f"[← back to all systems]({site_url('/')})")
    lines.append("")
    for topic_slug in sorted(topics):
        lines.extend(render_topic(topic_slug, topics[topic_slug]))
    return "\n".join(lines) + "\n"


def render_index(manifest: dict) -> str:
    lines = ["---", "title: Home", "---", ""]
    lines.append(
        f"# {manifest.get('title', 'Internal Medicine Guidelines') if isinstance(manifest, dict) else 'Internal Medicine Guidelines'}"
    )
    lines.append("")
    lines.append(
        "System-by-system index of current society guidelines for internal medicine "
        "practice. Click into a system to browse its "
        "topics and per-society / per-year versions, with links to publisher pages."
    )
    lines.append("")
    lines.append(
        "⭐ marks topics flagged as high-yield (an attending will expect these on rounds)."
    )
    lines.append("")
    lines.append("## Systems")
    lines.append("")
    systems = manifest.get("systems") or {}
    total_topics = total_versions = total_hy = 0
    for system_slug in sorted(systems):
        sb = systems[system_slug]
        topics = sb.get("topics") or {}
        n_topics = len(topics)
        n_versions = sum(len(t.get("versions", [])) for t in topics.values())
        n_hy = sum(1 for t in topics.values() if t.get("high_yield"))
        total_topics += n_topics
        total_versions += n_versions
        total_hy += n_hy
        desc = sb.get("description") or ""
        title = sb.get("title", system_slug)
        lines.append(
            f"- [{title}]({system_link(system_slug)}) — {desc} ({n_topics} topics, {n_hy} ⭐)"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"_Totals: {len(systems)} systems · {total_topics} topics · {total_versions} versions · {total_hy} high-yield_"
    )
    lines.append("")
    sg = manifest.get("study_guides") or {}
    if sg:
        lines.append("## Study guides")
        lines.append("")
        for slug, body in sg.items():
            lines.append(
                f"- **{body.get('title', slug)}**"
                + (f" — {body['description']}" if body.get("description") else "")
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.md").write_text(render_index(manifest))
    n_systems = 0
    for system_slug, sys_block in (manifest.get("systems") or {}).items():
        (DOCS / f"{system_slug}.md").write_text(render_system(system_slug, sys_block))
        n_systems += 1
    print(f"wrote docs/index.md and {n_systems} per-system pages")


if __name__ == "__main__":
    main()
