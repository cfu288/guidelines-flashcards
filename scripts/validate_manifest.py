# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic", "pyyaml"]
# ///
"""Validate manifest.yaml against the expected schema.

Usage:
    uv run scripts/validate_manifest.py            # validates ./manifest.yaml
    uv run scripts/validate_manifest.py path.yaml  # validates a specific file

Exits 0 on success, 1 on validation error.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class SourceFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: Optional[str] = None
    local: Optional[str] = None


class Version(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: Optional[int] = None
    society: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    # source is a format-keyed mapping: {pdf: {url, local}, epub: {url, local}, html: {url, local}, ...}
    # Format keys are open-ended (pdf, epub, html, xml, docx); each value has optional url and/or local path.
    source: Optional[dict[str, SourceFormat]] = None
    url: Optional[str] = None
    pmid: Optional[str] = None
    needs_attention: Optional[str] = None


class Topic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    society: Optional[str] = None
    high_yield: Optional[bool] = None
    versions: list[Version]


class System(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    description: Optional[str] = None
    topics: dict[str, Topic]


class StudyGuideEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    topic: str


class StudyGuide(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    description: Optional[str] = None
    entries: list[StudyGuideEntry] = []


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    systems: dict[str, System]
    study_guides: dict[str, StudyGuide] = {}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("manifest.yaml")
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 1

    data = yaml.safe_load(path.read_text())
    try:
        manifest = Manifest.model_validate(data)
    except ValidationError as e:
        print(e, file=sys.stderr)
        return 1

    errors: list[str] = []

    for sys_slug, system in manifest.systems.items():
        for topic_slug, topic in system.topics.items():
            if not topic.versions:
                errors.append(f"{sys_slug}/{topic_slug}: no versions")
                continue
            keys = [
                (v.year, v.society or topic.society)
                for v in topic.versions
                if v.year is not None
            ]
            if len(keys) != len(set(keys)):
                errors.append(f"{sys_slug}/{topic_slug}: duplicate (year, society)")

    valid_topic_paths = {
        f"/{s}/{t}/"
        for s, system in manifest.systems.items()
        for t in system.topics
    } | {f"/{s}/" for s in manifest.systems}

    for sg_slug, sg in manifest.study_guides.items():
        for entry in sg.entries:
            if entry.topic not in valid_topic_paths:
                errors.append(
                    f"study_guides/{sg_slug}: '{entry.label}' → unknown topic {entry.topic}"
                )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    topic_count = sum(len(s.topics) for s in manifest.systems.values())
    version_count = sum(
        len(t.versions)
        for s in manifest.systems.values()
        for t in s.topics.values()
    )
    print(
        f"OK: {len(manifest.systems)} systems, "
        f"{topic_count} topics, {version_count} versions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
