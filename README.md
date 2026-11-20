# ftw-data-catalog

Git-backed [Portolan](https://portolan-sdi.org)/STAC catalog repo for **Fields of the World (FTW)**.

Since 2026-11-20 this repo publishes two things at once:

- **The FTW root catalog** (`catalog/catalog.json`, id `ftw`) — the single entry point that
  links out to all four FTW datasets: this repo's own 1st-Edition Global Data catalog, the
  2nd-Edition Global Data catalog (a separate repo/product), Benchmark Data, and Harmonized
  Field Boundary Data.
- **Fields of the World — Global Data, 1st Edition** (`catalog/first-edition/catalog.json`,
  id `ftw-global-data`) — the original global agricultural field-boundary predictions and
  prediction-quality layers at 10 m resolution. Superseded by the
  [2nd Edition](https://data.source.coop/ftw/global-data-2e/catalog.json)
  ([ftw-global-data-catalog](https://github.com/fieldsoftheworld/ftw-global-data-catalog) repo),
  which it links to with `rel: "latest-version"`; this 1st Edition remains published at its
  existing URLs and collection ids. **Eventual plan, not yet done:** this 1st-Edition content is
  expected to move into the `ftw-global-data-catalog` repo so the whole Global Data history
  lives in one place.

**This repository is the source of truth for catalog _metadata_ only.** The data itself — billions of field polygons, COGs, and Zarr stacks (hundreds of GB) — lives on [Source Cooperative](https://source.coop/ftw/global-data) and is never stored in or uploaded by this repo.

- 🌍 **Live root catalog:** <https://data.source.coop/ftw/global-data/catalog.json>
- 🌍 **1st-Edition Global Data:** <https://data.source.coop/ftw/global-data/first-edition/catalog.json>
- 🧭 **Browse the STAC catalog:** [Portolan browser](https://browser.portolan-sdi.org/#/external/data.source.coop/ftw/global-data/catalog.json)
- 🤖 **For AI agents:** [`llms.txt`](https://data.source.coop/ftw/global-data/llms.txt)
- 📄 **Paper:** Robinson et al. 2026, [arXiv:2605.11055](https://arxiv.org/abs/2605.11055)

## How this repo works

The [`catalog/`](./catalog/) directory **is** the published catalog: it is synced 1:1 to
`s3://us-west-2.opendata.source.coop/tge-labs/ftw-global-data/`, which Source Cooperative
serves at `https://data.source.coop/ftw/global-data/`. What you see in `catalog/` is exactly
what is live. Everything outside `catalog/` is never published.

```
catalog/                the published STAC/Portolan catalog (1:1 with Source Cooperative)
  catalog.json            the FTW root catalog (id "ftw") -- new entry point
  README.md, AGENTS.md,   root-level docs and the FTW logo
  llms.txt, _assets/
  first-edition/          Fields of the World -- Global Data, 1st Edition (id "ftw-global-data")
    catalog.json            was catalog/catalog.json before the 2026-11-20 restructure
    README.md, README_next.md, AGENTS.md, llms.txt
staging/        collections being prepared, not yet published
scripts/        publishing + build tooling
tests/          dependency-free catalog validation
docs/           design specs and plans
CLAUDE.md       developer / agent guide
```

## Editing & publishing

1. Edit metadata under `catalog/` (STAC JSON, `README.md`, `llms.txt`, `.portolan/metadata.yaml`).
2. Validate: `python3 tests/test_links.py && python3 tests/test_publish.py`
3. Commit.
4. Publish: `python3 scripts/catalog/publish.py` (dry run), then `python3 scripts/catalog/publish.py --confirm` (needs AWS credentials).

See [CLAUDE.md](./CLAUDE.md) for the full developer guide. Corrections and additions welcome via pull request.

## License

Catalog metadata and data are published under CC-BY-4.0 by Taylor Geospatial and collaborators.
