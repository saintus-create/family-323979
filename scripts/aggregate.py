#!/usr/bin/env python3
"""Small dependency-free continuous aggregation engine.

Reads configured RSS/Atom/JSON sources, fingerprints records, stores only new
records, and rebuilds a normalized aggregate index. The source URLs are
configured in data/sources.json so the workflow can be reused without code
changes.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "sources.json"
DATA = ROOT / "data" / "aggregate"
RECORDS = DATA / "records.jsonl"
INDEX = DATA / "index.json"
USER_AGENT = "family-323979-aggregator/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/json, text/xml;q=0.9, */*;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_json(payload: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    obj = json.loads(payload.decode("utf-8"))
    items = obj if isinstance(obj, list) else obj.get(source.get("items_path", "items"), [])
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = clean(item.get(source.get("title_field", "title")))
        url = clean(item.get(source.get("url_field", "url")))
        summary = clean(item.get(source.get("summary_field", "summary")))
        published = clean(item.get(source.get("date_field", "published")))
        if title or url:
            out.append({"title": title, "url": url, "summary": summary, "published": published})
    return out


def parse_xml(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall(".//a:entry", ns)
    out = []
    for entry in entries:
        def text(*paths: str) -> str:
            for path in paths:
                node = entry.find(path, ns) if ":" in path else entry.find(path)
                if node is not None and (node.text or "").strip():
                    return clean(node.text)
            return ""
        link = ""
        node = entry.find("a:link", ns)
        if node is not None:
            link = clean(node.attrib.get("href", ""))
        if not link:
            link = text("link")
        title = text("title", "a:title")
        summary = text("description", "summary", "a:summary", "content", "a:content")
        published = text("pubDate", "published", "updated", "a:published", "a:updated")
        if title or link:
            out.append({"title": title, "url": link, "summary": summary, "published": published})
    return out


def fingerprint(source_id: str, item: dict[str, Any]) -> str:
    canonical = "|".join([source_id, item.get("url", ""), item.get("title", ""), item.get("published", "")])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    existing: dict[str, dict[str, Any]] = {}
    if RECORDS.exists():
        for line in RECORDS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing[row["id"]] = row

    now = datetime.now(timezone.utc).isoformat()
    errors = []
    added = 0
    for source in config.get("sources", []):
        if source.get("enabled", True) is False:
            continue
        source_id = source["id"]
        try:
            payload = fetch(source["url"])
            kind = source.get("type", "rss").lower()
            items = parse_json(payload, source) if kind == "json" else parse_xml(payload)
            for item in items:
                item_id = fingerprint(source_id, item)
                if item_id not in existing:
                    existing[item_id] = {
                        "id": item_id,
                        "source_id": source_id,
                        "source_name": source.get("name", source_id),
                        "collected_at": now,
                        **item,
                    }
                    added += 1
        except Exception as exc:  # keep one broken source from stopping the run
            errors.append({"source_id": source_id, "error": str(exc)})

    rows = sorted(existing.values(), key=lambda r: r.get("collected_at", ""), reverse=True)
    RECORDS.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    index = {
        "generated_at": now,
        "source_count": len(config.get("sources", [])),
        "record_count": len(rows),
        "new_records": added,
        "errors": errors,
        "records": rows,
    }
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"new_records": added, "total_records": len(rows), "errors": len(errors)}))
    return 0 if not errors else 0


if __name__ == "__main__":
    sys.exit(main())
