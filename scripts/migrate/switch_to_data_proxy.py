#!/usr/bin/env python3
"""Switch partition:glob from the raw dotted S3 bucket to the Source
Cooperative data proxy, and declare it with the STAC storage extension.

Before: ``s3://us-west-2.opendata.source.coop/tge-labs/ftw-global-data/...``
  A real AWS bucket, but "tge-labs/ftw-global-data" is an internal key
  prefix that has nothing to do with the public ``ftw/global-data`` path, so
  a reader has to know that mapping to find anything.
After: ``s3://ftw/global-data/...``
  The Source Cooperative data proxy (https://docs.source.coop/data-proxy)
  presents each product as if it were its own bucket, named after the
  account (``ftw``), with the same key path as the public ``https://``
  URL. Anonymous ``ListObjectsV2`` against it was verified live (2026-11-20):

      curl 'https://data.source.coop/ftw?list-type=2&prefix=global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=FR/&max-keys=5'

  returned the 5 expected per-partition style/README keys, and a DuckDB
  ``glob()`` against the full wildcard pattern through the proxy
  (``ENDPOINT 'data.source.coop'``, ``URL_STYLE 'path'``) matched exactly
  598 partitions -- the same count this catalog's items already use.

This only changes the URI scheme/host in metadata. No data file moves: the
proxy serves the exact same bytes at the exact same key path, just reachable
through the `ftw` bucket name instead of the real one.

PORTO-FMT-066: a client assumes ``s3://`` means AWS by default, which is now
wrong (``s3://ftw`` is not really an AWS bucket), so every collection that
uses the proxy form also gains a ``storage:schemes`` entry (STAC storage
extension v2.0.0) describing it as ``custom-s3``.

Idempotent. Usage: python3 switch_to_data_proxy.py [--catalog catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

OLD_S3_BASE = "s3://us-west-2.opendata.source.coop/tge-labs/ftw-global-data"
NEW_S3_BASE = "s3://ftw/global-data"

STORAGE_EXT = "https://stac-extensions.github.io/storage/v2.0.0/schema.json"
STORAGE_SCHEME_KEY = "ftw-proxy"
STORAGE_SCHEME = {
    "type": "custom-s3",
    "title": "Source Cooperative data proxy (anonymous read)",
    "platform": "https://data.source.coop",
    "bucket": "ftw",
    "region": "us-west-2",
    "requester_pays": False,
}


def load(p: Path):
    with p.open() as f:
        return json.load(f)


def save(p: Path, obj) -> None:
    with p.open("w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def switch_glob(obj, stats: Counter) -> bool:
    glob = obj.get("partition:glob")
    if not isinstance(glob, str) or not glob.startswith(OLD_S3_BASE):
        return False
    obj["partition:glob"] = NEW_S3_BASE + glob[len(OLD_S3_BASE):]
    stats["glob_switched_to_proxy"] += 1

    exts = obj.setdefault("stac_extensions", [])
    if STORAGE_EXT not in exts:
        exts.append(STORAGE_EXT)
        stats["storage_extension_declared"] += 1
    schemes = obj.setdefault("storage:schemes", {})
    if schemes.get(STORAGE_SCHEME_KEY) != STORAGE_SCHEME:
        schemes[STORAGE_SCHEME_KEY] = dict(STORAGE_SCHEME)
        stats["storage_scheme_added"] += 1
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default="catalog", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.catalog.is_dir():
        print(f"no such directory: {a.catalog}", file=sys.stderr)
        return 1

    stats = Counter()
    targets = sorted([*a.catalog.rglob("collection.json"), *a.catalog.rglob("catalog.json")])
    for p in targets:
        obj = load(p)
        if switch_glob(obj, stats):
            stats["files_modified"] += 1
            if not a.dry_run:
                save(p, obj)

    label = "would change" if a.dry_run else "changed"
    print(f"Data-proxy glob switch ({label}):")
    for k in sorted(stats):
        print(f"  {k:<30} {stats[k]}")
    if not stats:
        print("  nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
