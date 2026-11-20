# Fields of the World

The entry point to every [Fields of the World](https://fieldsofthe.world)
(FTW) dataset.

Fields of the World is an open collaboration on agricultural field boundaries.
It harmonizes the field boundary data that governments and research
institutions already publish, cuts machine-learning benchmark data from it,
and publishes global field boundary predictions made with field boundary
delineation models.

This catalog holds no data and no collections of its own. It is metadata: a
root that links to four published catalogs. Three are maintained in their own
repository and published as their own [Source Cooperative](https://source.coop)
product; the fourth — the 1st Edition of the global predictions — is kept as
a sub-catalog of this same repository and product, because that is where it
has always been published.

- Catalog root: <https://data.source.coop/ftw/global-data/catalog.json>
- Browse it: [Portolan data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/ftw/global-data/catalog.json)
- For agents: [AGENTS.md](https://data.source.coop/ftw/global-data/AGENTS.md)
- Catalog source and corrections: <https://github.com/fieldsoftheworld/ftw-data-catalog>

## What is here

| Catalog | What it holds |
|---|---|
| [Fields of the World — Global Data (1st Edition)](./first-edition/catalog.json) | The original global field boundary predictions and prediction-quality layers at 10 m resolution. Superseded by the 2nd Edition below; kept published and citable at its existing URLs. |
| [Fields of the World — Global Data](https://data.source.coop/ftw/global-data-2e/catalog.json) | The 2nd Edition of the global field boundary predictions and prediction-quality layers at 10 m resolution, as per-year vector and raster collections. The current release. |
| [Fields of the World Benchmark Data](https://data.source.coop/ftw/benchmark-data/catalog.json) | Training and evaluation chips for field boundary delineation models: Sentinel-2 imagery paired with instance and semantic label masks, in train, validation and test splits. One collection per country or region. |
| [Harmonized Field Boundary Data](https://data.source.coop/ftw/harmonized-field-data/catalog.json) | The source field boundary datasets, converted to one schema: boundaries published by government bodies from their agricultural subsidy registers (IACS/LPIS), cadastres, statistics and mapping programmes, and by research institutions, harmonized into the [fiboa](https://fiboa.org/) schema with [fiboa-cli](https://github.com/fiboa/cli) and republished as cloud-native GeoParquet and PMTiles. |

### Fields of the World — Global Data (1st Edition and 2nd Edition)

Model predictions of field boundaries, worldwide, from Sentinel-2 mosaics.
The 1st Edition is the original release, kept exactly where it was already
published — reachable from this root as [`./first-edition/catalog.json`](./first-edition/catalog.json),
and still linked with a `rel: "latest-version"` to the 2nd Edition catalog
below it in its own metadata. The 2nd Edition holds per-year vector
collections of predicted field boundaries and per-year raster collections of
field and boundary probability, and is the catalog to start from for current
work.

These are predictions of remote-sensing field units. They are not cadastral
or legal parcels, and they are not a land-tenure product. Read each edition's
and each year collection's own provenance, processing recipe and asset
inventory, because the recipe changed between editions and between years
within the 2nd Edition.

The 1st Edition's metadata is maintained in this repository
(<https://github.com/fieldsoftheworld/ftw-data-catalog>), at
[`catalog/first-edition/`](./first-edition/). **The eventual plan is to move
that 1st Edition content into the 2nd Edition's own repository,
[ftw-global-data-catalog](https://github.com/fieldsoftheworld/ftw-global-data-catalog),
so a reader has one repository for the whole Global Data history; that has
not happened yet, and this README will be updated when it does.** The 2nd
Edition's own metadata and processing pipeline already live there.

### Fields of the World Benchmark Data

Training and evaluation data for field boundary delineation models. Each
collection is one country or region, cut from a collection of the harmonized
field boundary data below, with Sentinel-2 image chips paired with instance
and semantic label masks and split into train, validation and test.
Collections are grouped by the harmonized source collection they were cut
from.

Metadata and the build recipes:
<https://github.com/fieldsoftheworld/benchmark-data-catalog>.

### Harmonized Field Boundary Data

One collection per source dataset, partitioned by the year the boundaries
represent, so every edition of one dataset can be queried at once and the
newest edition of every dataset can be queried together. Each collection
records how its boundaries came to exist — `declared` by farmers in a subsidy
application or the register built on those declarations, `mapped` by an
authority from imagery or survey, or `inferred` from imagery by a model — so a
reader can keep to one kind.

Metadata and the publication tooling:
<https://github.com/fieldsoftheworld/harmonized-field-data-catalog>.
This catalog supersedes <https://source.coop/fiboa/data>.

## License

This root catalog carries metadata only, published under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

**The license of the data is declared per collection, and that declaration is
authoritative.** The four child catalogs do not share one license:

- Global Data collections (both editions) are published under
  [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
- Benchmark Data collections carry a license per collection, inherited from
  the harmonized source they were cut from.
- Harmonized Field Boundary Data collections carry the license of their source
  data provider, which differs by provider — CC0-1.0, CC-BY-4.0 and others.

Check the `license` field of the collection you intend to use, and attribute
the providers it names.

## Provenance

This is the official publication of the Fields of the World datasets, not a
mirror. The harmonized collections are conversions of data published by the
responsible public bodies and research institutions, and each one links back
to its source with a `via` link and names that body in its `providers`.

Responsibility is declared per collection through STAC `providers`, and that
declaration is authoritative. The producers differ: the Global Data
predictions name [Taylor Geospatial](https://taylorgeospatial.org/) and the
[Microsoft AI for Good Research Lab](https://www.microsoft.com/en-us/research/group/ai-for-good-research-lab/);
harmonized and benchmark collections name the government body or research
institution that produced the source boundaries, with Fields of the World as
`processor`. Hosting is [Source Cooperative](https://source.coop/ftw).

## Access

Nothing in this root catalog is a data file, so there is nothing here to
query. Start from a child catalog. To walk this tree:

```bash
curl -s https://data.source.coop/ftw/global-data/catalog.json | python3 -c '
import json, sys
for link in json.load(sys.stdin)["links"]:
    if link["rel"] == "child":
        print(link["title"], "->", link["href"])'
```

Output, run 2026-11-20 against the catalog in this repository:

```
Fields of the World — Global Data (1st Edition) -> ./first-edition/catalog.json
Fields of the World — Global Data -> https://data.source.coop/ftw/global-data-2e/catalog.json
Fields of the World Benchmark Data -> https://data.source.coop/ftw/benchmark-data/catalog.json
Harmonized Field Boundary Data -> https://data.source.coop/ftw/harmonized-field-data/catalog.json
```

Each child catalog's own `AGENTS.md` carries the queries for its data. See
[AGENTS.md](https://data.source.coop/ftw/global-data/AGENTS.md) in this
catalog for where those are.

## Corrections

A wrong license, a broken link, or a dataset that should be listed here: open
an issue or a pull request at
<https://github.com/fieldsoftheworld/ftw-data-catalog>. A correction to a
dataset itself belongs in that dataset's own repository, linked above.
