# Input formats

ProofRank reads local files by default. The export adapter supports CSV and JSON; it does not log in to Google, WordPress, a crawler, or any other service.

## Prepare common exports

Run `scripts/prepare_sources.py` before the graph audit when the inputs are raw exports:

```bash
python scripts/prepare_sources.py \
  --site "https://example.com/" \
  --gsc "gsc.csv" \
  --ga4 "ga4.csv" \
  --wordpress "wordpress.json" \
  --crawler "crawler.csv" \
  --require gsc --require ga4 --require wordpress --require crawler \
  --declare-source-universe-complete \
  --output-dir "prepared"
```

The direct `--gsc`, `--ga4`, `--wordpress`, `--crawler`, `--inventory`, and `--sitemap` flags are repeatable. The generic repeatable form `--source KIND=PATH` is also supported; `KIND` may be `auto`, `inventory`, `gsc`, `ga4`, `wordpress`, `crawler`, or `sitemap`. `auto` detects CSV/JSON tabular sources only. Sitemap XML is provenance-only in preparation; the audit engine performs the recursive URL parsing.

The adapter writes:

- `inventory.csv`: normalized same-site URLs, compatible fields, and merged `sourceTypes`/`sourceIds` provenance;
- `page_cache.json`: written when accepted crawler records exist; contains atomically selected status/final-URL/HTML snapshots, conflict metadata, and explicit full-HTML attestations;
- `source_manifest.json`: source kind, required status, collection status, source filename, SHA-256, input/accepted/rejected counts, `expected_normalized_identities`, output hashes, and the explicit universe declaration;
- `prepare_report.json`: network state, source and output summaries, page-cache/HTML counts, and the offline safety boundary.

Only filenames—not absolute source paths—are written to the manifest; source IDs are generic (`gsc-1`, `crawler-1`, and so on). Filenames can still be sensitive, so review the manifest before publication. The normalized inventory contains selected compatible fields and metrics, not a copy of every raw column. Credentials are never required or copied.

## Source-universe declaration

`--declare-source-universe-complete` is an explicit operator assertion about the selected scope. It is required for `universe_complete=true`; at least one required entry must exist, and every required entry must have status `collected`. A supplied file with zero accepted same-site URLs has status `empty` and cannot satisfy the gate. Without `--require`, every supplied or declared entry is required by default. The prepared manifest records the size of the reconciled scoped union as `expected_normalized_identities`; it must be a non-negative integer. It also writes `expected_count_origin=AUTO_DERIVED_FROM_PREPARED_UNION`, making clear that this count is not an independent census of the site.

Represent known gaps instead of silently omitting them:

```bash
--unavailable "gsc=property export was not available"
--not-attempted "wordpress=CMS export was not requested"
```

An unavailable, not-attempted, invalid-shape, or empty required source keeps `source_universe_complete=false`. During the audit, the manifest must also match the audited absolute HTTP(S) origin. Its expected normalized identity count must equal the observed normalized union; any shortfall is reported as `unclassified_count` and blocks the source gate. Its inventory hash set must exactly match all supplied `--inventory` files; its optional page-cache hash must match the supplied `--page-cache`; and its sitemap hash set must exactly match every body resolved from the supplied sitemap/index chain. A required collected sitemap source cannot pass without nonempty declared sitemap hashes. This binds the declaration to the actual audit inputs instead of accepting a related-looking manifest. `DECLARED_SCOPE_BOUND` remains separate from HTML coverage and is not an independent completeness oracle: a perfectly parsed crawl cannot prove that an undeclared CMS, analytics property, sitemap layer, or historical source contains no additional URLs.

## Recognized GSC exports

CSV rows must contain `Page`; `Query`, `Clicks`, `Impressions`, `CTR`, and `Position` are imported when present. JSON may contain Search Analytics-style `rows` with `keys` and the same fields, but each accepted row still needs a page URL. When a `keys` array contains both page and query dimensions, the URL-looking value becomes the page identity and query values become supporting text.

Within one GSC file, exact duplicate raw rows are removed before rows normalized to the same page are combined: clicks and impressions are summed, queries are deduplicated, CTR is recomputed as clicks/impressions, and position is weighted by positive impressions. Separate exports may overlap, so ProofRank never sums them together: per URL it atomically selects the file snapshot with the greatest impression evidence (stable content-hash tie-breaker), records its generic `gscMetricSource`, and still unions query/source provenance. Query-only exports cannot establish page identities.

This is an offline import format, not a live Google Search Console API integration.

## Recognized GA4 exports

Use a URL/path dimension such as:

- `landingPagePlusQueryString`;
- `landingPage`;
- `pagePathAndScreenClass`.

Imported metrics are `sessions`, `engagedSessions`, and `views`. Within one GA4 file, exact duplicate rows are removed and metrics for rows normalized to the same page are summed. Across separate files, overlapping totals use the maximum. An optional `hostname` helps resolve path-only rows, including double-slash landing paths. Query strings are removed during normalized URL identity matching.

This is an offline import format, not a live Google Analytics Data API integration.

## Recognized WordPress exports

Use `live_url`, `url`, `link`, or `permalink` for the public identity. Useful fields include `type`/`post_type`, `status`/`post_status`, `slug`, title/H1, language, and record ID; WordPress REST-style `{ "rendered": "..." }` text values are accepted. Rows marked `auto-draft`, `draft`, `future`, `pending`, `private`, or `trash` are excluded.

This is an offline import format, not a WordPress REST client or CMS connection.

## Recognized crawler exports

Common crawler columns include:

- `Address`;
- `Status Code`;
- `Final URL` and `Content Type`;
- `Indexability`;
- `Title 1`;
- `H1-1`;
- `Crawl Depth`;
- `Canonical Link Element 1`;
- `Word Count` and `Link Count`;
- `Rendered HTML`, `rendered_html`, `html`, or `body`.
- `html_complete`, `htmlComplete`, `full_html`, `fullHtml`, `body_complete`, or `bodyComplete` as an explicit true/false full-document attestation.

Non-HTML assets are excluded by content type or known file suffix. Accepted crawler rows generate `page_cache.json`. Status, final URL, HTML, and attestation are selected as one atomic snapshot; conflicting snapshots are recorded, not blended. Cross-origin/cross-scheme finals cannot supply same-origin HTML. Unattested HTML remains available for human inspection but cannot satisfy topology coverage. The adapter does not start or control a crawler.

## Normalized inventory CSV

The audit engine accepts a header row plus one URL identity field:

- `url`, `permalink`, `page`, `path`, `finalUrl`, or `final_url`.

Useful optional fields:

- `title`, `h1`;
- `mechanismLane`, `mechanism`, `lane`, `postType`;
- `strategicCluster`, `cluster`;
- `latestClicks`, `latestImpressions`, `sinceWorkClicks`, `sinceWorkImpressions`;
- `wordCount`, `linkCount`, `topQueries`.

Unknown columns are ignored and are not copied into the normalized inventory. Preserve the original export separately when its full provenance is needed.

## Normalized inventory JSON

The audit engine accepts an array or an object containing `pages`, `items`, or `rows`. `pages` may be an array or a URL-keyed object. URL aliases match the normalized CSV format.

## Page cache JSON

Preferred URL-keyed form:

```json
{
  "site": "https://example.com/",
  "pages": {
    "https://example.com/example/": {
      "status": 200,
      "final_url": "https://example.com/example/",
      "html_complete": true,
      "html": "<!doctype html>..."
    }
  }
}
```

An array under `pages`, `rows`, or a top-level array is also accepted. HTML aliases are `html`, `body`, and `rendered_html`. Do not substitute plain article text for rendered HTML when auditing links or schema.

An HTML record is usable for the observed-content gate only when HTML is present, `html_complete=true` is explicit (per row or as a cache-wide default), the snapshot is conflict-free and non-truncated, the status is 2xx, and the final URL equals the requested normalized identity on the audited origin. Confirmed 404/410 records and same-origin redirects with distinct destinations are reported and removed from the active denominator. Unresolved redirects, cross-origin finals, server errors, unattested/snippet HTML, and other unusable 2xx records remain and block completeness. Status-only records remain useful evidence but do not increase usable HTML coverage.

## Sitemap

- Accept a local XML file or, with `--allow-network`, an HTTP(S) URL on the audited site.
- Resolve `<sitemapindex>` files recursively.
- Read only direct sitemap-namespace `<url><loc>` and `<sitemap><loc>` children; image, video, and news extension locations are not page identities.
- For a saved local index whose children use public URLs, place saved child XML files beside the index using their URL basenames.
- During preparation, pass the index and every local child separately with repeatable `--sitemap`; the manifest records all hashes. During audit, the exact manifest hash multiset must match every recursively resolved sitemap body.
- Record missing children as unresolved and withhold whole-site graph claims.

Compressed XML.GZ sitemap files are not currently accepted as local inputs; decompress them to XML first.

## Two-stage completeness gate

The final `graph_complete` state is true only when:

1. `source_universe_complete` is true: the universe was explicitly declared complete, at least one required source exists, every required source was collected, the manifest site matches the audited origin, `expected_normalized_identities` equals the observed normalized union, and exact inventory/cache/resolved-sitemap SHA-256 bindings pass; and
2. `content_graph_complete` is true: explicitly attested, conflict-free, non-truncated, same-identity 2xx full HTML covers 100% of active graph-eligible URLs, the homepage was parsed, and no supplied sitemap child remains unresolved. Confirmed 404s/410s and same-origin redirects with distinct destinations are excluded from the active denominator; unresolved redirects, cross-origin finals, server errors, and unusable 2xx records remain and block completeness.

Before either result is accepted, page-like identities exposed by parsed internal links, same-origin redirect destinations, or canonicals are reconciled into the known universe. Any identity absent from the declaration produces `source_universe_contradicted` and withholds whole-site topology claims.

Passing either gate alone is insufficient. In the bundled false-green fixture, source identities are `7/11` with four unclassified while active HTML is `7/7`; the final decision is therefore `WITHHOLD`. In the complete fixture, source identities are `11/11`, one confirmed 404 is classified outside the active denominator, active HTML is `10/10`, and the decision is `READY_FOR_HUMAN_REVIEW`.

## Decision contract

Every audit writes `decision.json` and embeds the same object at `audit.release_contract`. The contract records `WITHHOLD` or `READY_FOR_HUMAN_REVIEW`, all gate stages, `unclassified_count`, stable blocker codes, evidence hashes, `scope_assurance`, `scope_warning`, `expected_count_origin`, and `live_change_authorized=false`.

When `--gate-exit-code` is present, exit `2` means the read-only gate withheld and exit `0` means ready for human review. Input/runtime failures remain errors. The contract and exit code do not authorize, apply, or roll back a live change. Any private apply/rollback evidence referenced in project case studies belongs to a separate private deployment workflow, not public ProofRank.

Cannibalization, merge, redirect, canonical, and content decisions remain candidates for human review even when both gates pass.
