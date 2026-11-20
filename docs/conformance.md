# Conformance notes — Portolan v0.3.0

This catalog declares `https://schemas.portolan-sdi.org/portolan/v0.3.0/schema.json`
on its root catalog and on every collection/sub-catalog (PORTO-CORE-006). Validated
with `rashid@0.4.0` (`rashid check catalog --no-data --json`); `tests/test_portolan_conformance.py`
runs the same check in CI and fails on any error finding not listed below.

`--no-data` means partitioned-collection data checks (`PTL-DAT-*`) do not run against
this local tree: `predictions/vectors/collection.json` and `predictions/vectors-test/fields-thinned/collection.json`
both use an absolute `s3://` `partition:glob` (required since v0.3, PORTO-FMT-064),
which a local run cannot list. A clean local run says nothing about the partitioned
files themselves; see `scripts/migrate/reference/validate_with_data.py`-style
symlink-tree validation (not run in this pass) for that.

## Accepted / deferred findings

| Rule | Where | Why | Tracking |
|---|---|---|---|
| `PTL-LNK-006` | `features/{2024,2025}/collection.json` → MGRS zone `child` links; `predictions/vectors/alpha/.../results-by-admin*` subdivision items' `collection` link | The ~22.7k per-tile features items and the MGRS zone catalogs are generated straight to S3 by `scripts/features/build_features_items.py` and never committed, so a git checkout can't resolve them; they resolve against the published catalog. The subdivision case is rashid treating an item's `collection` link as invalid when a catalog sits between the collection and the item — [portolan-sdi/rashid#61](https://github.com/portolan-sdi/rashid/issues/61), dormant since rashid 0.1.3. | rashid#61 (subdivision case); no fix available for the S3-only case without committing ~45k generated files |
| `PTL-COL-005` | `features/{2024,2025}/collection.json` | Same S3-only-items fact as above: the collection registers a `geoparquet-items` STAC-GeoParquet mirror but, locally, has no items to back it (they're on S3 only). | same as above |
| `PTL-AST-007` | `features/{2024,2025}/collection.json` | New in rashid 0.4.0 / Portolan v0.3: checks that a collection has primary-data reference via a `data`-role asset or `partition:glob`, on the collection *or its items*. The items (committed nowhere — S3-only) each carry a `data`-role COG asset per the collection's own `item_assets` template; a local-tree validator can't see them. Same root cause as `PTL-COL-005`. | same as above |
| `PTL-AST-008` | `predictions/vectors/alpha/results-by-admin-conf/admin:country_code={BR,US}/{BR,US}.json` | Genuine gap, not a validator artifact. These two items are country-wide PMTiles *overview* tiles built from many per-subdivision GeoParquet partitions (`BR_*`, `US_*`); there is no single consolidated file for a `data`-role asset to point at. Fixing it needs either a real consolidated country-level GeoParquet asset (new data) or remodeling these two items off item-classification (a restructuring change) — out of scope for a metadata-only migration. | [fieldsoftheworld/ftw-data-catalog#10](https://github.com/fieldsoftheworld/ftw-data-catalog/issues/10) |
| `PTL-BBX-001`, `PTL-FIL-001`, `PTL-FIL-002`, `PTL-FIL-003`, `PTL-CNF-004` (2 of 8) | `predictions/zarr/collection.json` | This collection is mid-regeneration (noted in `tests/test_portolan_conformance.py` before this migration too) and is out of scope here. | pre-existing, unrelated to v0.3 |
| `PTL-AST-003`/`PTL-AST-004` (`file:size`/`file:checksum`) | remote (not-in-repo) assets across the catalog | Filled by the in-region `scripts/migrate/backfill_file_meta.py --local-only` remote pass, not by this metadata migration. A missing checksum on a file actually committed to the repo is still a hard failure. | pre-existing |

## Known warnings not addressed in this pass

- `PTL-TTL-002` (300 findings / 158 files, all under `predictions/vectors/alpha/...`):
  the readable-title heuristic flags short administrative-subdivision codes
  (`BR_ZZ`, `US_CA`, `BR_13`, ...) as a "raw slug". This migration fixed every
  case where the identifier actually was a despaced human name
  (`United_Arab_Emirates` → "United Arab Emirates", 196 item titles + 196 link
  titles) but left the genuine short codes alone: replacing an underscore with
  a space in `BR_ZZ` does not make it any more human-readable, it only
  produces a different-looking opaque code. PORTO-CORE-040 anticipates exactly
  this: "because heuristics misfire, the finding is a warning, not an error."
  `scripts/migrate/upgrade_to_0_3.py`'s `_SLUG_TITLE_RE` requires a lowercase
  letter before normalizing a title, specifically so it doesn't mangle these.
- `PTL-CNF-004` (6 remaining, outside the zarr dirs above): `render` extension pinned
  at v1.0.0 vs. the registry's v2.0.0 on `predictions/confidence/**`, and `datacube`
  extension at v2.2.0 vs. v2.3.0 on `features/zarr`. Bumping either changes what that
  object's schema requires; left for a dedicated extension-version pass so it gets a
  real review rather than a drive-by edit in a conformance migration.
- `PTL-LNK-009` (root `icon` link is absolute, not relative): the only copy of
  `ftw-logo.svg` lives on the Source Cooperative bucket, not in this repo (`catalog/`
  has no `docs/` directory). Making the link relative means committing a new asset
  file, which this migration (metadata-only, no data-file changes) does not do.
- `PTL-MIR-001` (`predictions/confidence/collection.json` has 5 scene items but no
  `items.parquet` mirror): a SHOULD (PORTO-FMT-040/041), low value at 5 items;
  deferred as a small enhancement rather than a conformance gap.

## Requires data work (follow-up)

- **PORTO-FMT-067 – PORTO-FMT-072 (collection overview COG, new in v0.3):**
  `features/2024/collection.json` and `features/2025/collection.json` each model
  ~22.7k same-band, same-period Sentinel-2 composite tiles covering a far larger
  area than any one tile, and have no collection-level overview COG. Producing one
  means rendering an actual 8-bit RGB mosaic image — a real data-generation task,
  not a metadata edit.
- **PORTO-CORE-083 (`PTL-AST-008`):** see the table above — the `BR`/`US` country
  overview items need either a consolidated GeoParquet asset or a remodel.

Both tracked in [fieldsoftheworld/ftw-data-catalog#10](https://github.com/fieldsoftheworld/ftw-data-catalog/issues/10).

## Negative control

Before trusting the clean run above, `catalog/catalog.json`'s `stac_extensions` was
temporarily emptied (dropping the required Portolan schema URI) and `rashid` was
re-run: it reported `PTL-CNF-001` at `catalog.json` as expected. The file was then
restored and the suite re-run clean.
