#!/usr/bin/env python3
"""Fix every `rel: "root"` link in the moved 1st-edition tree to point at the
new top-level FTW root catalog, and add `rel: "parent"` to the 1st-edition
root catalog.json.

Run *after* the pure move (catalog/* -> catalog/first-edition/*) and after
the new catalog/catalog.json has been written. See that commit's message for
why the transform below is correct.

The transform
-------------
The new root lives at exactly the filesystem path the OLD (1st-edition) root
used to occupy: catalog/catalog.json. The 1st-edition root itself moved one
level deeper, to catalog/first-edition/catalog.json. Every other file in the
tree moved down by that same one level. So for any file, in its new location,
the relative path to the (unmoved) new root is exactly one ".." deeper than
the relative path it used to have to the old root:

    new_root_href = normpath("../" + old_root_href)

This holds uniformly, including for the 1st-edition root's own self-pointing
"./catalog.json": normpath("../" + "./catalog.json") == "../catalog.json",
which is exactly the one level up needed to reach the new root from
first-edition/catalog.json.

Every rel:root link's title is also rewritten to the new root's title
("Fields of the World"), since the link's title is supposed to describe what
it points at, and what it points at changed.

Idempotent: a href already resolving correctly (i.e. already renormalized) is
left alone, detected by whether the computed new href equals the existing one.

Usage: python3 fix_root_links.py [--catalog catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import posixpath
import sys
from collections import Counter
from pathlib import Path

NEW_ROOT_TITLE = "Fields of the World"


def load(p: Path):
    with p.open() as f:
        return json.load(f)


def save(p: Path, obj) -> None:
    with p.open("w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fix_root_link(obj, stats: Counter) -> bool:
    links = obj.get("links")
    if not isinstance(links, list):
        return False
    changed = False
    for link in links:
        if link.get("rel") != "root":
            continue
        href = link.get("href")
        if not isinstance(href, str) or "://" in href:
            continue
        new_href = posixpath.normpath("../" + href)
        if link.get("href") != new_href:
            link["href"] = new_href
            changed = True
        if link.get("title") != NEW_ROOT_TITLE:
            link["title"] = NEW_ROOT_TITLE
            changed = True
    if changed:
        stats["root_link_fixed"] += 1
    return changed


def add_first_edition_parent(obj, p: Path, first_edition_root: Path, stats: Counter) -> bool:
    if p != first_edition_root:
        return False
    links = obj.setdefault("links", [])
    if any(l.get("rel") == "parent" for l in links):
        return False
    # Insert right after the (already-fixed) root link, for readability.
    idx = next((i for i, l in enumerate(links) if l.get("rel") == "root"), -1) + 1
    links.insert(idx, {
        "rel": "parent",
        "href": "../catalog.json",
        "type": "application/json",
        "title": "Fields of the World",
    })
    stats["parent_link_added"] += 1
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default="catalog", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    first_edition = a.catalog / "first-edition"
    if not first_edition.is_dir():
        print(f"no such directory: {first_edition}", file=sys.stderr)
        return 1
    first_edition_root = first_edition / "catalog.json"

    stats = Counter()
    for p in sorted(first_edition.rglob("*.json")):
        if ".portolan" in p.parts:
            continue
        try:
            obj = load(p)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        touched = fix_root_link(obj, stats)
        touched |= add_first_edition_parent(obj, p, first_edition_root, stats)
        if touched:
            stats["files_modified"] += 1
            if not a.dry_run:
                save(p, obj)

    label = "would change" if a.dry_run else "changed"
    print(f"Fix root links in catalog/first-edition/ ({label}):")
    for k in sorted(stats):
        print(f"  {k:<24} {stats[k]}")
    if not stats:
        print("  nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
