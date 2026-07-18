# Input formats

## Inventory CSV

Accept a header row plus one URL identity field:

- `url`, `permalink`, `page`, `path`, `finalUrl`, or `final_url`.

Useful optional fields:

- `title`, `h1`;
- `mechanismLane`, `mechanism`, `lane`, `postType`;
- `strategicCluster`, `cluster`;
- `latestClicks`, `latestImpressions`, `sinceWorkClicks`, `sinceWorkImpressions`;
- `wordCount`, `linkCount`, `topQueries`.

Unknown columns remain provenance only and are not interpreted automatically.

## Inventory JSON

Accept an array or an object containing `pages`, `items`, or `rows`. `pages` may be an array or a URL-keyed object. URL aliases match the CSV format.

## Page cache JSON

Preferred URL-keyed form:

```json
{
  "site": "https://example.com/",
  "pages": {
    "https://example.com/example/": {
      "status": 200,
      "final_url": "https://example.com/example/",
      "html": "<!doctype html>..."
    }
  }
}
```

An array under `pages`, `rows`, or a top-level array is also accepted. HTML aliases are `html`, `body`, and `rendered_html`. Do not substitute plain article text for rendered HTML when auditing links or schema.

## Sitemap

- Accept a local XML file or, with `--allow-network`, an HTTP(S) URL.
- Resolve `<sitemapindex>` files recursively.
- For a saved local index whose children use public URLs, place saved child XML files beside the index using their URL basenames.
- Record missing children as unresolved and withhold completeness claims.

## Source selection

Prefer the freshest complete artifact with reproducible provenance. A small tracker, top-pages table, or capped crawl is not a replacement for a full URL universe.
