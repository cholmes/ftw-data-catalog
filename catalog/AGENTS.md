# AGENTS.md — Fields of the World

Guidance for AI agents and automated clients working with this catalog.

**One rule survives every edit to this file.** Every claim here is either
quoted from a source or measured from the data. If you cannot point at where a
fact came from, it does not belong in this file. An agent acting on an
invented join key or an invented column name produces a confident wrong
answer, and nothing downstream catches it.

## What this catalog holds

Nothing you can query directly. This is the root catalog for the Fields of
the World datasets, at <https://data.source.coop/ftw/global-data/catalog.json>.
It is metadata only: no collections, no items, no assets of its own. It
exists so one URL reaches every FTW dataset.

Four `child` links leave it. Three are the roots of separately published
catalogs in their own Source Cooperative products; one — the 1st Edition of
Global Data — is a sub-catalog of this same repository and product, because
that is where it was already published before this root existed.

| Child catalog | Root | Its agent guide |
|---|---|---|
| Fields of the World — Global Data (1st Edition) | [`./first-edition/catalog.json`](./first-edition/catalog.json) | [`./first-edition/AGENTS.md`](./first-edition/AGENTS.md) |
| Fields of the World — Global Data | <https://data.source.coop/ftw/global-data-2e/catalog.json> | <https://data.source.coop/ftw/global-data-2e/AGENTS.md> |
| Fields of the World Benchmark Data | <https://data.source.coop/ftw/benchmark-data/catalog.json> | <https://data.source.coop/ftw/benchmark-data/AGENTS.md> |
| Harmonized Field Boundary Data | <https://data.source.coop/ftw/harmonized-field-data/catalog.json> | <https://data.source.coop/ftw/harmonized-field-data/AGENTS.md> |

**Read the child's own `AGENTS.md` before querying it.** The queries, the
column names, the partition globs and the traps are there, written and run
against those files. This file does not restate them, because a copy goes
stale and a stale query is worse than no query.

**Eventual plan, not yet done:** the 1st Edition's content is expected to
move into the 2nd Edition's own repository
([ftw-global-data-catalog](https://github.com/fieldsoftheworld/ftw-global-data-catalog)),
so the whole Global Data history lives in one repository. This table and the
`./first-edition/catalog.json` link are accurate as of this writing; if that
move has happened, the 1st Edition entry above is stale and the live root
catalog is the one to trust, not this file.

## How to read it

Walk the children, then follow one. Measured 2026-11-20:

```bash
for url in \
  https://data.source.coop/ftw/global-data/first-edition/catalog.json \
  https://data.source.coop/ftw/global-data-2e/catalog.json \
  https://data.source.coop/ftw/benchmark-data/catalog.json \
  https://data.source.coop/ftw/harmonized-field-data/catalog.json; do
  curl -s "$url" | python3 -c '
import json, sys
d = json.load(sys.stdin)
kids = sum(1 for l in d["links"] if l["rel"] == "child")
print(d["id"].ljust(22), "children=" + str(kids))'
done
```

```
ftw-global-data        children=4
ftw-global-data-2e      children=2
benchmark-data          children=37
harmonized-field-data   children=78
```

Those counts change as datasets are added. Measure them, do not cache them.

The 1st Edition's own children are two sub-catalogs (vector field boundaries,
field/boundary probability rasters) and a test sub-catalog, each a
collection-per-year tree. The 2nd Edition's two children are sub-catalogs
too, one for vectors and one for rasters, with a collection per year inside
each. The Benchmark children are sub-catalogs too, one per source group,
each holding the collections cut from that source. The Harmonized children
are collections directly, one per source dataset.

Each child catalog declares its own Portolan profile version in its root
`stac_extensions`, and they are not all the same version. Read the version
from the child's own root catalog rather than assuming this root's version
applies to it.

## Join keys

The datasets chain. The harmonized boundaries are the input the benchmark
chips are cut from; the benchmark is training and evaluation data for field
boundary delineation models; the Global Data boundaries are the output of such
a model. Only the first of those links is in the metadata.

**Benchmark collection → harmonized collection.** A benchmark collection
carries a `via` link to the Source Cooperative page of the harmonized
collection it was cut from. Measured on
`https://data.source.coop/ftw/benchmark-data/at/at_2021/collection.json`:

```bash
curl -s https://data.source.coop/ftw/benchmark-data/at/at_2021/collection.json \
  | python3 -c '
import json, sys
for l in json.load(sys.stdin)["links"]:
    if l["rel"] in ("via", "derived_from"):
        print(l["rel"], l.get("type"), l["href"])'
```

```
via text/html https://source.coop/ftw/harmonized-field-data/at
derived_from text/html https://source.coop/nlebovits/gaul-l2-admin
derived_from text/html https://source.coop/tge-labs/aef
derived_from text/html https://source.coop/olmoearth/olmoearth-v1-3-embeddings
```

The last path segment of that `via` href (`at`) is the harmonized collection
id. Its collection JSON is
`https://data.source.coop/ftw/harmonized-field-data/at/collection.json`. The
`derived_from` links name other inputs to the build and are not harmonized
collections.

**Global predictions → anything else.** There is no join key in the metadata.
The predictions are produced by a model, not cut from a specific harmonized
collection, so nothing ties a predicted field to a declared one. Joining them
is a spatial operation on the data, not a key lookup. This holds for both
editions.

**No column joins exist at this level.** This catalog has no tables. Column
names and types are in each child's `AGENTS.md` and in each collection's
`table:columns`.

## Quirks that produce silently wrong answers

- **The Global Data boundaries are predictions.** They describe
  remote-sensing field units inferred by a model from Sentinel-2 imagery.
  They are not cadastral or legal parcels, and they are not a land-tenure
  product. Treating a predicted boundary as a legal one is wrong in a way no
  query reports.
- **Do not add counts across the three data-origin catalogs.** The same
  field can appear as a declared boundary in Harmonized, as a label in
  Benchmark, and as a prediction in Global Data. Summing them counts one
  field up to three times.
- **Do not add counts across Global Data editions either.** The 1st and 2nd
  Editions are two independent full-world prediction runs, not a partition of
  one dataset. Adding their field counts double-counts the planet.
- **Licenses differ per collection, including within one child catalog.** The
  harmonized collections carry the license of their source provider, which is
  not one license. Read the `license` field of the collection you use; do not
  inherit a license from this root.
- **Two different ids for the same dataset.** A harmonized collection id
  (`at`) and a benchmark collection id (`at_2021`) are not the same object.
  The benchmark id carries the year of the source edition the chips were cut
  from.
- **`source.coop` and `data.source.coop` are different hosts.** The first
  serves the human-readable product pages, the second serves the bytes and
  the JSON. A `via` link points at the first; a catalog or data href points at
  the second.

## Structure

This root catalog carries an absolute `self` link, because it is served from
one fixed URL: <https://data.source.coop/ftw/global-data/catalog.json>. Its
`describedby`, `agents`, `llms` and `icon` links are relative, so a
downloaded copy keeps working. Its `child` link to the 1st Edition is
relative too, because that catalog is published from this same product; the
other three `child` links are absolute, because each of those is a separate
product on the same host and no relative path reaches it.

The catalog is maintained in git at
<https://github.com/fieldsoftheworld/ftw-data-catalog>, where the published
tree is the `catalog/` directory (this root catalog plus `catalog/first-edition/`,
the 1st Edition's own tree). Corrections are pull requests there. A
correction to a dataset belongs in that dataset's own repository, named in
[README.md](https://data.source.coop/ftw/global-data/README.md).
