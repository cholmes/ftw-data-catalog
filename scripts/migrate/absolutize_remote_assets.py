#!/usr/bin/env python3
"""Make every relative asset href that points at an uncommitted (data) file
absolute, ahead of moving the 1st-edition catalog tree under
``catalog/first-edition/``.

Why this has to run before the move
------------------------------------
Most of this catalog's own STAC/markdown files (collection.json, README.md,
AGENTS.md, styles/*.json, thumbnail.png) are committed to git and move
*together* with the metadata tree, so a relative reference between two of
them is unaffected by shifting the whole tree down one directory level.

Large data files (``*.parquet``, ``*.pmtiles``) are not committed -- they are
uploaded straight to the bucket -- and per this restructure they do **not**
move: they stay at their current published key,
``https://data.source.coop/ftw/global-data/<old relative path>``. An item
that references one of these by a *relative* href (e.g. ``./BR_ZZ.parquet``,
colocated with the item in the pre-move tree) would, after the item itself
moves one level deeper into ``first-edition/``, resolve to a path that is one
level too deep for a file that never moved. That is a silently broken link,
not a cosmetic one.

This script finds every asset whose href is relative and whose target is not
a file in this repo (i.e. it is one of exactly those uncommitted data files),
and rewrites it to the absolute, unmoved published URL. It must run while the
tree is still in its pre-move, flat layout, because the absolute URL it
computes is ``PUBLIC_BASE + <path relative to catalog/, right now>``.

Idempotent (an already-absolute href is left alone).
Usage: python3 absolutize_remote_assets.py [--catalog catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import posixpath
import sys
from collections import Counter
from pathlib import Path

PUBLIC_BASE = "https://data.source.coop/ftw/global-data"


def load(p: Path):
    with p.open() as f:
        return json.load(f)


def save(p: Path, obj) -> None:
    with p.open("w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def absolutize_assets(obj, p: Path, catalog_root: Path, stats: Counter) -> bool:
    assets = obj.get("assets")
    if not isinstance(assets, dict):
        return False
    changed = False
    for key, a in assets.items():
        if not isinstance(a, dict):
            continue
        href = a.get("href")
        if not isinstance(href, str) or "://" in href:
            continue
        target = (p.parent / href)
        if target.is_file():
            continue  # committed, moves with the tree -- leave relative
        # Not on disk: an uncommitted data file. Compute its absolute URL from
        # where it is published *right now*, before anything moves.
        rel_from_catalog = posixpath.normpath(
            (p.parent.relative_to(catalog_root) / href).as_posix())
        a["href"] = f"{PUBLIC_BASE}/{rel_from_catalog}"
        stats[f"absolutized{Path(href).suffix}"] += 1
        changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default="catalog", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    catalog_root = a.catalog.resolve()
    if not catalog_root.is_dir():
        print(f"no such directory: {catalog_root}", file=sys.stderr)
        return 1

    stats = Counter()
    for p in sorted(catalog_root.rglob("*.json")):
        if ".portolan" in p.parts:
            continue
        try:
            obj = load(p)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if absolutize_assets(obj, p, catalog_root, stats):
            stats["files_modified"] += 1
            if not a.dry_run:
                save(p, obj)

    label = "would change" if a.dry_run else "changed"
    print(f"Absolutize remote asset hrefs ({label}):")
    for k in sorted(stats):
        print(f"  {k:<30} {stats[k]}")
    if not stats:
        print("  nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
