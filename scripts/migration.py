#!/usr/bin/env python3
"""Migration tooling for transferring the encyclopedia entries to this Fern site.

Subcommands
-----------
  status              Summarize migration progress from the manifest.
  scaffold            Create stub MDX pages for every pending manifest entry.
  nav                 Regenerate the `encyclopedia` tab of fern/docs.yml.
  ingest FILE SLUG    Clean a raw fetched entry (saved as .md) into a normalized
                      working text under migration/raw/clean/ plus a metadata
                      JSON under migration/entries/.

Only stdlib is used. Run from anywhere; paths are resolved relative to the repo.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "migration" / "manifest.json"
PAGES_DIR = ROOT / "fern" / "docs" / "pages" / "encyclopedia"
DOCS_YML = ROOT / "fern" / "docs.yml"
RAW_DIR = ROOT / "migration" / "raw"
CLEAN_DIR = RAW_DIR / "clean"
ENTRIES_DIR = ROOT / "migration" / "entries"


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(data: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def split_dates(title: str) -> tuple[str, str]:
    """'Austin, J.L. (1911–1960)' -> ('Austin, J.L.', '1911–1960')."""
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", title)
    if m and re.search(r"\d", m.group(2)):
        return m.group(1).strip(), m.group(2).strip()
    return title.strip(), ""


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# --------------------------------------------------------------------------
# scaffold
# --------------------------------------------------------------------------

STUB_TEMPLATE = """---
title: {title_yaml}
{subtitle_line}---
<Lead>
*{title}* is part of the rhetoric reference collection on this site. The entry
has been inventoried and is queued for editorial migration.
</Lead>

<Note>
**Pending migration.** The entry will appear here once it has been rewritten in
contemporary academic English and set to the site editorial standard. See the
[Encyclopedia overview](/encyclopedia) for how entries are structured, and
`MIGRATION.md` in the repository for migration status.
</Note>
"""


def page_path(letter: str, slug: str) -> Path:
    return PAGES_DIR / letter.lower() / f"{slug}.mdx"


def cmd_scaffold(args: argparse.Namespace) -> None:
    data = load_manifest()
    created, skipped = 0, 0
    for entry in data["entries"]:
        if entry.get("skip") or entry["status"] != "pending":
            continue
        if entry.get("needs_review") and not args.include_review:
            skipped += 1
            continue
        path = page_path(entry["letter"], entry["slug"])
        if path.exists() and not args.force:
            skipped += 1
            continue
        title, subtitle = split_dates(entry["title"])
        subtitle_line = f"subtitle: {yaml_str(subtitle)}\n" if subtitle else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            STUB_TEMPLATE.format(
                title=title,
                title_yaml=yaml_str(title),
                subtitle_line=subtitle_line,
            ),
            encoding="utf-8",
        )
        created += 1
    print(f"scaffold: created {created} stub page(s), skipped {skipped}")


# --------------------------------------------------------------------------
# nav
# --------------------------------------------------------------------------

NAV_TEMPLATE = """\
# yaml-language-server: $schema=https://schema.buildwithfern.dev/docs-yml.json

instances:
  - url: us-fda-der.docs.buildwithfern.com
    edit-this-page:
      github:
        owner: fern-starter
        repo: family-323979
        branch: main
      launch: dashboard
title: US FDA DER | Documentation
layout:
  searchbar-placement: sidebar
  page-width: full
  tabs-placement: sidebar
tabs:
  home:
    display-name: Docs
    icon: home
  encyclopedia:
    display-name: Encyclopedia
    icon: fa-duotone fa-book-open
navigation:
  - tab: home
    layout:
      - section: Get started
        contents:
          - page: Welcome
            path: docs/pages/welcome.mdx
            icon: fa-duotone fa-house
          - page: Edit your docs
            path: docs/pages/editing-your-docs.mdx
            icon: fa-duotone fa-pen-to-square
          - page: Write content
            path: docs/pages/writing-content.mdx
            icon: fa-duotone fa-file-lines
          - page: Set up navigation
            path: docs/pages/navigation.mdx
            icon: fa-duotone fa-sitemap
          - page: Customize your docs
            path: docs/pages/customization.mdx
            icon: fa-duotone fa-palette
          - page: Support
            path: docs/pages/support.mdx
            icon: fa-duotone fa-headset
      - section: Changelog
        contents:
          - changelog: docs/changelog
  - tab: encyclopedia
    layout:
      - page: Encyclopedia Overview
        path: docs/pages/encyclopedia/overview.mdx
        slug: encyclopedia
        icon: fa-duotone fa-book-section
__SECTIONS__navbar-links:
  - type: filled
    text: Edit
    url: https://dashboard.buildwithfern.com
colors:
  accent-primary:
    light: "#1A1A2E"
    dark: "#1A1A2E"
  background:
    light: "#F8F8F9"
    dark: "#010102"
  card-background:
    dark: "#1a1a1c"
    light: "#FFFFFF"
  border:
    light: "#CACACB"
    dark: "#272728"
theme:
  page-actions: toolbar
  footer-nav: minimal
  body: canvas
  tabs: bubble
  sidebar: minimal
logo:
  dark: docs/assets/logo-dark.svg
  light: docs/assets/logo.svg
  height: 20
  href: https://buildwithfern.com
favicon: docs/assets/favicon.svg
css:
  - styles.css
  - docs/assets/onboarding-theme.css
typography:
  headingsFont:
    name: Inter
  bodyFont:
    name: Inter
ai-search: {}
"""


def cmd_nav(args: argparse.Namespace) -> None:
    data = load_manifest()
    letters: dict[str, list[dict]] = {}
    for entry in data["entries"]:
        if entry.get("skip"):
            continue
        if entry["status"] == "pending" and entry.get("needs_review"):
            continue  # do not surface broken artifacts in the sidebar
        letters.setdefault(entry["letter"], []).append(entry)

    blocks: list[str] = []
    for letter in sorted(letters):
        contents: list[str] = []
        for entry in letters[letter]:
            title, _ = split_dates(entry["title"])
            rel = page_path(entry["letter"], entry["slug"]).relative_to(
                ROOT / "fern"
            )
            contents.append(
                "          - page: {}\n"
                "            path: {}\n"
                "            slug: {}".format(
                    yaml_str(title),
                    rel.as_posix(),
                    yaml_str(f"{entry['letter'].lower()}/{entry['slug']}"),
                )
            )
        blocks.append(
            "      - section: {}\n"
            "        contents:\n{}".format(yaml_str(letter), "\n".join(contents))
        )
    sections = "\n".join(blocks) + "\n" if blocks else ""
    DOCS_YML.write_text(
        NAV_TEMPLATE.replace("__SECTIONS__", sections), encoding="utf-8"
    )
    total = sum(len(v) for v in letters.values())
    print(f"nav: wrote {DOCS_YML} with {total} entry pages in {len(letters)} letter sections")


# --------------------------------------------------------------------------
# ingest
# --------------------------------------------------------------------------

WRAPPER_MARKERS = ("\nReference: ", "\n## Response", "\n## Examples")


def cmd_ingest(args: argparse.Namespace) -> None:
    src = Path(args.file)
    text = src.read_text(encoding="utf-8")

    # 1. Cut away the API-wrapper documentation appended by the source site.
    for marker in WRAPPER_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]

    # 2. Drop the page chrome (blockquote banner, H1, GET line).
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">") or s.startswith("# ") or s.startswith("GET "):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()

    # 3. Rejoin words broken by hyphenation at hard line ends.
    text = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)

    # 4. Repair missing spaces before years ("Commission of1861").
    text = re.sub(r"([A-Za-z])(1[89]\d{2})\b", r"\1 \2", text)

    # 5. Reflow hard-wrapped lines into paragraphs (short last-line heuristic).
    lines = [ln.rstrip() for ln in text.splitlines()]
    lengths = [len(ln) for ln in lines if ln.strip()]
    wrapped = bool(lengths) and statistics.median(lengths) < 70
    paragraphs: list[str] = []
    if wrapped and lengths:
        threshold = 0.55 * statistics.median(lengths)
        buf: list[str] = []
        for ln in lines:
            if not ln.strip():
                paragraphs.append(" ".join(buf))
                buf = []
                continue
            buf.append(ln.strip())
            if len(ln) < threshold:
                paragraphs.append(" ".join(buf))
                buf = []
        if buf:
            paragraphs.append(" ".join(buf))
        paragraphs = [p for p in paragraphs if p.strip()]
    else:
        paragraphs = [ln.strip() for ln in lines if ln.strip()]

    # 6. Pull a bibliography out of the tail (runs of citation-like lines).
    def citation_like(p: str) -> bool:
        return bool(re.search(r"\b(19|20)\d{2}\b", p)) and (
            ". " in p or ", " in p
        )

    bib_start = None
    tail = paragraphs[max(0, len(paragraphs) - 12):]
    run = 0
    for i, p in enumerate(tail):
        run = run + 1 if citation_like(p) else 0
        if run >= 2:
            bib_start = len(paragraphs) - len(tail) + i - 1
            break

    bibliography = None
    author = None
    if bib_start is not None:
        bibliography = paragraphs[bib_start:]
        body = paragraphs[:bib_start]
        # signature: short lines right before the bibliography
        sig: list[str] = []
        while body and len(body[-1]) < 60 and len(sig) < 2:
            sig.insert(0, body.pop())
        if sig:
            author = ", ".join(sig)
    else:
        body = paragraphs
        sig: list[str] = []
        while body and len(body[-1]) < 60 and len(sig) < 2:
            sig.insert(0, body.pop())
        if sig and re.search(r"University|College|Institute|School", sig[-1]):
            author = ", ".join(sig)

    # 7. Persist: cleaned working text (git-ignored) + committed metadata only.
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    clean_path = CLEAN_DIR / f"{args.slug}.md"
    clean_path.write_text("\n\n".join(body) + "\n", encoding="utf-8")

    meta = {
        "slug": args.slug,
        "source_file": str(src),
        "words": sum(len(p.split()) for p in body),
        "paragraphs": len(body),
        "author_detected": author,
        "bibliography_items": len(bibliography or []),
        "clean_text": str(clean_path.relative_to(ROOT)),
    }
    out = ENTRIES_DIR / f"{args.slug}.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def cmd_status(_: argparse.Namespace) -> None:
    data = load_manifest()
    by_status: dict[str, int] = {}
    review = skip = 0
    for e in data["entries"]:
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
        review += 1 if e.get("needs_review") else 0
        skip += 1 if e.get("skip") else 0
    total = len(data["entries"])
    done = by_status.get("done", 0)
    print(f"total entries : {total}")
    print(f"migrated      : {done}")
    print(f"pending       : {by_status.get('pending', 0)}")
    print(f"needs review  : {review} (broken artifacts in the source export)")
    print(f"skipped       : {skip} (not real content)")
    print(f"progress      : {done}/{total - skip} ({100 * done / (total - skip):.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--include-review", action="store_true")
    p_scaffold.add_argument("--force", action="store_true")
    p_scaffold.set_defaults(func=cmd_scaffold)
    sub.add_parser("nav").set_defaults(func=cmd_nav)
    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("file")
    p_ingest.add_argument("slug")
    p_ingest.set_defaults(func=cmd_ingest)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
