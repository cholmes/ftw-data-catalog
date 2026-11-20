#!/usr/bin/env python3
"""Migrate the FTW catalog metadata from Portolan 0.2 to 0.3.

Runs *after* ``upgrade_to_0_1.py`` and ``upgrade_to_0_2.py`` — those scripts apply
the historical 0.1 and 0.2 sweeps and still run first:

    python3 scripts/migrate/upgrade_to_0_1.py
    python3 scripts/migrate/upgrade_to_0_2.py
    python3 scripts/migrate/upgrade_to_0_3.py
    python3 scripts/migrate/switch_to_data_proxy.py
    python3 scripts/migrate/backfill_file_meta.py --local-only

Idempotent: running it twice changes nothing the second time. Its S3_BASE
constant writes the raw dotted bucket (``us-west-2.opendata.source.coop/...``);
``switch_to_data_proxy.py`` is the later pass that rewrites it to the Source
Cooperative data proxy form (``s3://ftw/global-data/...``) and run after this
one, not a reason to change this constant retroactively.

What it does
------------

**Declares the 0.3.0 profile.** Swaps the schema URI in ``stac_extensions`` on
every catalog and collection (PORTO-CORE-006), including adding it fresh to
``predictions/zarr/collection.json``, which carried none. 0.3.0 is the current
release (2026-11-17).

**Fixes the breaking partition:glob rule** (PORTO-FMT-064, rashid ``PTL-PRT-002``).
v0.3 requires ``partition:glob`` to be an absolute bucket-native URL
(``s3://``, ``gs://``, ``az://``) because clients list the bucket to expand it;
an ``https://`` URL — what this catalog had — cannot be listed. The vectors
collection's glob is rewritten from the ``https://data.source.coop/...`` form to
the equivalent ``s3://us-west-2.opendata.source.coop/tge-labs/ftw-global-data/...``
form. Same bucket, same keys — this is a metadata-only rewrite, not a data move
(see ``scripts/catalog/publish_metadata.sh`` / ``scripts/catalog/publish.py`` for
the same bucket mapping).

**Gives the `fields-thinned` test collection its missing GeoParquet reference**
(PORTO-FMT-062, rashid ``PTL-AST-007``/``PTL-AST-009``). Its PMTiles file is
built directly from the same global field-boundary GeoParquet partitions the
``predictions/vectors`` collection publishes (see its own description: "every
2025 Fields of the World PRUE field polygon"). v0.3 requires a PMTiles asset's
collection to reference that GeoParquet with a ``data``-role asset or
``partition:glob``. This adds the identical glob (same bucket, same keys —
nothing new is produced) and declares the partition extension.

**Fills in missing asset ``description`` fields** (PORTO-CORE-088, a SHOULD since
0.3; rashid ``PTL-AST-010``). Every asset with a ``title`` and no ``description``
gets one, generated from its own role/type/title — nothing invented. The single
largest bucket (~4,190 of ~4,274 catalog-wide) is the per-partition and
per-country items under ``predictions/vectors/alpha/...``: each carries a
`data`, `pmtiles`, `README`, and up to four `style*` assets with a title but no
description. For the `data` asset specifically, the description also reports
the item's own already-known ``geoparquet:feature_count``.

Usage
-----
    python3 upgrade_to_0_3.py [--catalog catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

PORTOLAN_0_3 = "https://schemas.portolan-sdi.org/portolan/v0.3.0/schema.json"
PORTOLAN_PROFILE_RE = re.compile(
    r"^https://schemas\.portolan-sdi\.org/portolan/v[0-9.]+/schema\.json$")

# Matches the URI already declared by predictions/vectors/collection.json (the
# other partitioned collection in this catalog) and recognized by rashid, not
# the github.io form (which build_vector_items.py's own PARTITION_EXT constant
# predates and gets wrong -- see the generator fix in the same commit).
PARTITION_EXT = "https://schemas.portolan-sdi.org/incubating/partition/v1.0.0/schema.json"

# https base -> s3 base for the one bucket this catalog publishes to. Same bytes,
# same keys; only the URI scheme the partition:glob uses changes (PORTO-FMT-064
# requires a bucket-native, listable scheme). See scripts/catalog/publish_metadata.sh.
HTTPS_BASE = "https://data.source.coop/ftw/global-data"
S3_BASE = "s3://us-west-2.opendata.source.coop/tge-labs/ftw-global-data"


def load(p: Path):
    with p.open() as f:
        return json.load(f)


def save(p: Path, obj) -> None:
    with p.open("w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def bump_schema(obj, stats: Counter) -> bool:
    """Leave exactly one Portolan profile URI, at 0.3.0.

    Adds it fresh when the object (e.g. predictions/zarr/collection.json) carries
    none yet — PORTO-CORE-006 is a MUST on every catalog and collection.
    """
    exts = obj.get("stac_extensions")
    if not isinstance(exts, list):
        exts = []
    others = [e for e in exts if not PORTOLAN_PROFILE_RE.match(str(e))]
    had = [e for e in exts if PORTOLAN_PROFILE_RE.match(str(e))]
    rebuilt = [PORTOLAN_0_3, *others]
    if rebuilt == exts:
        return False
    obj["stac_extensions"] = rebuilt
    if not had:
        stats["schema_added"] += 1
    else:
        stats["schema_bumped"] += 1
        if len(had) > 1:
            stats["duplicate_profiles_collapsed"] += 1
    return True


def fix_vectors_partition_glob(obj, path: Path, stats: Counter) -> bool:
    """PORTO-FMT-064: partition:glob must be s3://, not https://."""
    if path.name != "collection.json" or path.parent.name != "vectors":
        return False
    glob = obj.get("partition:glob")
    if not isinstance(glob, str) or not glob.startswith(HTTPS_BASE):
        return False
    obj["partition:glob"] = S3_BASE + glob[len(HTTPS_BASE):]
    stats["partition_glob_rewritten_to_s3"] += 1
    return True


def add_fields_thinned_geoparquet_ref(obj, path: Path, stats: Counter) -> bool:
    """PORTO-FMT-062: a PMTiles-only collection needs a GeoParquet reference.

    fields-thinned's PMTiles is built from the same global vectors GeoParquet
    partitions; add the identical glob rather than fabricating a new asset.
    """
    if path.name != "collection.json" or path.parent.name != "fields-thinned":
        return False
    if "partition:glob" in obj:
        return False
    obj["partition:glob"] = (
        f"{S3_BASE}/predictions/vectors/alpha/results-by-admin-conf/"
        "admin:country_code=*/*.parquet"
    )
    obj["partition:scheme"] = "hive"
    obj["partition:keys"] = [{"name": "admin:country_code", "type": "string"}]
    exts = obj.setdefault("stac_extensions", [])
    if PARTITION_EXT not in exts:
        exts.append(PARTITION_EXT)
    stats["fields_thinned_geoparquet_ref_added"] += 1
    return True


# Matches an underscore-joined human-name slug ("United_Arab_Emirates") but
# NOT a short administrative code ("BR_ZZ", "US_CA"): a code is pure
# uppercase/digits, where inserting spaces doesn't make it any more
# human-readable (see docs/conformance.md -- PORTO-CORE-040 explicitly expects
# this readability heuristic to misfire sometimes). Requiring a lowercase
# letter is what tells the two apart.
_SLUG_TITLE_RE = re.compile(r"^(?=.*[a-zà-ɏ])\w+(?:_\w+)+$", re.UNICODE)


def fix_slug_item_title(obj, stats: Counter) -> bool:
    """Same normalization as fix_slug_link_titles, for an item's own
    properties.title (e.g. a single-partition country item titled
    "United_Arab_Emirates" straight from its parquet filename stem).
    """
    if obj.get("type") != "Feature":
        return False
    props = obj.get("properties")
    if not isinstance(props, dict):
        return False
    title = props.get("title")
    if isinstance(title, str) and _SLUG_TITLE_RE.match(title):
        props["title"] = title.replace("_", " ")
        stats["slug_item_title_normalized"] += 1
        return True
    return False


def fix_slug_link_titles(obj, stats: Counter) -> bool:
    """rashid PTL-TTL-002: an `item`/`child` link titled with the raw
    underscore-joined filename stem (e.g. "Bosnia_and_Herzegovina") rather than
    a human-readable title. Normalizes the separator only -- "Foo_Bar" ->
    "Foo Bar" -- never adds or restores characters the stem doesn't have
    (e.g. "Cote_dIvoire" stays without its accent; that information isn't
    recoverable from the title string itself, so this doesn't invent it).
    Scoped to item/child links so an unrelated title with an underscore
    (e.g. a real asset or style name) is never touched.
    """
    links = obj.get("links")
    if not isinstance(links, list):
        return False
    changed = False
    for link in links:
        if link.get("rel") not in ("item", "child"):
            continue
        title = link.get("title")
        if isinstance(title, str) and _SLUG_TITLE_RE.match(title):
            link["title"] = title.replace("_", " ")
            stats["slug_link_title_normalized"] += 1
            changed = True
    return changed


_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")


def fix_nonascii_link_hrefs(obj, stats: Counter) -> bool:
    """rashid (PTL-LNK-006): a relative href with a literal non-ASCII character
    (e.g. ``./.../Åland_Islands.json``) is not a valid URI reference per RFC
    3986. Percent-encode the non-ASCII bytes only -- the files on disk keep
    their real (UTF-8) names; this only corrects the string a client parses as
    a URI. A browser/HTTP client resolves the percent-encoded form back to the
    exact same bytes, so this touches no data and changes no filename.

    Idempotent: once encoded the href is pure ASCII, so re-running is a no-op
    (and never double-encodes, since quote() is only invoked when a non-ASCII
    byte is still present).
    """
    links = obj.get("links")
    if not isinstance(links, list):
        return False
    changed = False
    for link in links:
        href = link.get("href")
        if isinstance(href, str) and "://" not in href and _NON_ASCII_RE.search(href):
            link["href"] = quote(href, safe="/:=")
            stats["nonascii_link_href_encoded"] += 1
            changed = True
    return changed


# ---------------------------------------------------------------------------
# Asset description filler (PORTO-CORE-088 / PTL-AST-010)
# ---------------------------------------------------------------------------

def _describe_asset(key: str, asset: dict, item_props: dict | None) -> str | None:
    """Return a short, factual description for `asset`, derived only from data
    already in the object (title, roles, type, and — for a vectors/alpha `data`
    asset — the item's own geoparquet:feature_count). Never invents semantics.
    """
    title = (asset.get("title") or "").strip()
    if not title:
        return None  # nothing to derive from; leave it for a human
    roles = asset.get("roles") or []
    typ = asset.get("type") or ""

    if key == "data" and item_props and "geoparquet:feature_count" in item_props:
        n = item_props["geoparquet:feature_count"]
        n_fmt = f"{n:,}" if isinstance(n, int) else n
        return (f"GeoParquet field-boundary polygons for this partition "
                f"({n_fmt} feature{'s' if n != 1 else ''}). See the collection's "
                "`table:columns` for field definitions.")
    if "style" in roles:
        return f"MapLibre GL style (JSON) for rendering: {title}."
    if key == "documentation" or "documentation" in roles:
        return "Machine-readable usage guide for AI agents and automated tools (llms.txt)."
    if key == "README" or "metadata" in roles:
        return f"Human-readable documentation. {title}."
    if "thumbnail" in roles:
        return f"Static preview image. {title}."
    if "pmtiles" in typ or key.startswith("pmtiles"):
        return f"PMTiles vector tiles for rendering in MapLibre GL. {title}."
    if key in ("data", "parquet") or key.startswith("cells_"):
        return f"GeoParquet data asset underlying this collection's visualization. {title}."
    if "collection-mirror" in roles:
        return f"{title}."  # already has one in practice; fallback only
    if "visual" in roles and "cloud-optimized" in roles:
        return f"{title} — downsampled web-Mercator preview COG for fast rendering."
    if "data" in roles and "cloud-optimized" in roles:
        return f"{title} — cloud-optimized GeoTIFF (COG) data asset."
    return f"{title}."


def fill_asset_descriptions(obj, stats: Counter) -> bool:
    assets = obj.get("assets")
    if not isinstance(assets, dict):
        return False
    item_props = obj.get("properties") if obj.get("type") == "Feature" else None
    changed = False
    for key, asset in assets.items():
        if not isinstance(asset, dict):
            continue
        if asset.get("description"):
            continue
        desc = _describe_asset(key, asset, item_props)
        if desc:
            asset["description"] = desc
            stats["asset_descriptions_added"] += 1
            changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default="catalog", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--include-items", action="store_true", default=True,
                    help="also fill asset descriptions on item JSON (default: on)")
    a = ap.parse_args()

    if not a.catalog.is_dir():
        print(f"no such directory: {a.catalog}", file=sys.stderr)
        return 1

    stats = Counter()

    # Pass 1: catalog.json / collection.json only — schema + structural fixes.
    structural_targets = sorted(
        [*a.catalog.rglob("collection.json"), *a.catalog.rglob("catalog.json")]
    )
    for p in structural_targets:
        obj = load(p)
        touched = False
        touched |= bump_schema(obj, stats)
        touched |= fix_vectors_partition_glob(obj, p, stats)
        touched |= add_fields_thinned_geoparquet_ref(obj, p, stats)
        touched |= fix_nonascii_link_hrefs(obj, stats)
        touched |= fix_slug_link_titles(obj, stats)
        touched |= fill_asset_descriptions(obj, stats)
        if touched:
            stats["files_modified"] += 1
            if not a.dry_run:
                save(p, obj)

    # Pass 2: item JSON (STAC Features) — asset descriptions only. Skip files
    # already handled above (none overlap: those are catalog.json/collection.json).
    if a.include_items:
        seen = set(structural_targets)
        for p in sorted(a.catalog.rglob("*.json")):
            if p in seen or p.name in ("versions.json",) or ".portolan" in p.parts:
                continue
            try:
                obj = load(p)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(obj, dict) or obj.get("type") != "Feature":
                continue
            touched = fill_asset_descriptions(obj, stats)
            touched |= fix_nonascii_link_hrefs(obj, stats)
            touched |= fix_slug_item_title(obj, stats)
            if touched:
                stats["files_modified"] += 1
                if not a.dry_run:
                    save(p, obj)

    label = "would change" if a.dry_run else "changed"
    print(f"Portolan 0.2 -> 0.3 migration ({label}):")
    for k in sorted(stats):
        print(f"  {k:<36} {stats[k]}")
    if not stats:
        print("  nothing to do (already at 0.3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
