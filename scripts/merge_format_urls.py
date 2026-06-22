# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Merge per-system EPUB / HTML / PMC research results into manifest.yaml.

Reads `/tmp/manifest-format-urls-*.yaml` files produced by the research agents.

Each per-system file looks like:
    <system>:
      <topic>:
        - year: 2025
          society: AHA       # optional, disambiguates same-year entries
          html: https://...
          epub: https://...
          pmc: PMC1234567
          pmc_html: https://...   # or pmc_xml
          pmid: 12345678

For each matched manifest version, sets:
    source:
      html: {url: <html>}
      epub: {url: <epub>}
      pmc: {url: PMC HTML mirror}
      xml: {url: <pmc_xml>}     # if JATS XML URL provided
And on the version body:
    pmid: <pmid>                  # if not already present
"""

from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"
RESULT_DIR = Path("/tmp")

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def find_version(manifest, system, topic, year, society):
    sys_block = manifest.get("systems", {}).get(system) or {}
    topic_block = sys_block.get("topics", {}).get(topic) or {}
    topic_society = topic_block.get("society")
    matches = []
    for v in topic_block.get("versions", []):
        if v.get("year") != year:
            continue
        if society is not None:
            v_society = v.get("society") or topic_society
            if v_society != society:
                continue
        matches.append(v)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return "ambiguous"
    return None


def apply(version, entry):
    src = version.setdefault("source", {})
    changes = []

    if entry.get("html"):
        src.setdefault("html", {})["url"] = entry["html"]
        changes.append("html")
    if entry.get("epub"):
        src.setdefault("epub", {})["url"] = entry["epub"]
        changes.append("epub")

    pmc_id = entry.get("pmc")
    pmc_url = entry.get("pmc_html") or entry.get("pmc_url")
    if pmc_id or pmc_url:
        node = src.setdefault("pmc", {})
        if pmc_url:
            node["url"] = pmc_url
        elif pmc_id:
            node["url"] = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/"
        changes.append("pmc")

    if entry.get("pmc_xml"):
        src.setdefault("xml", {})["url"] = entry["pmc_xml"]
        changes.append("xml")

    if entry.get("pmid") and "pmid" not in version:
        version["pmid"] = str(entry["pmid"])
        changes.append("pmid")

    return changes


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    result_files = sorted(RESULT_DIR.glob("manifest-format-urls-*.yaml"))
    if not result_files:
        print("no /tmp/manifest-format-urls-*.yaml files found")
        return 1

    n_applied = 0
    n_ambiguous = 0
    n_unmatched = 0
    by_kind: dict[str, int] = {}

    for path in result_files:
        with path.open() as f:
            data = yaml.load(f) or {}
        for system, topics in data.items():
            for topic, entries in (topics or {}).items():
                for entry in entries or []:
                    year = entry.get("year")
                    society = entry.get("society")
                    version = find_version(manifest, system, topic, year, society)
                    if version == "ambiguous":
                        print(f"  AMBIGUOUS: {system}/{topic}/{year} — needs society")
                        n_ambiguous += 1
                        continue
                    if not version:
                        print(f"  UNMATCHED: {system}/{topic}/{year}/{society}")
                        n_unmatched += 1
                        continue
                    changes = apply(version, entry)
                    if changes:
                        n_applied += 1
                        for k in changes:
                            by_kind[k] = by_kind.get(k, 0) + 1

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)

    print(f"\napplied to {n_applied} versions; {n_ambiguous} ambiguous, {n_unmatched} unmatched")
    print(f"by kind: {by_kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
