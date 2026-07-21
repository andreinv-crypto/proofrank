# Offline export integrations

ProofRank includes deterministic adapters for already-exported GSC, GA4, WordPress, crawler, and generic inventory CSV/JSON files, plus saved sitemap XML. “Integration” here means local import, validation, normalization, provenance, and completeness accounting.

It does **not** mean live OAuth, API calls, CMS login, crawler control, scheduled synchronization, or production writes.

## Capability boundary

| Source | Public ProofRank can do | Public ProofRank does not do |
| --- | --- | --- |
| Google Search Console | Import page-level or page+query rows; aggregate clicks, impressions, query set, CTR, and position | Import query-only rows, authenticate, select properties, or call the Search Analytics API |
| Google Analytics 4 | Import landing-page rows and aggregate sessions, engaged sessions, and views | Authenticate or call `runReport` |
| WordPress | Import public post/page REST-style JSON or compatible CSV; exclude non-public statuses | Log in, enumerate a live CMS, or change content/settings |
| Crawlers | Import HTML-page rows and optionally prepare a status/final-URL/rendered-HTML cache | Launch, license, configure, or control a crawler |
| Sitemaps | Validate saved sitemap XML and bind every explicitly supplied index/child file by SHA-256 | Submit, modify, or fetch a sitemap during preparation |
| Generic inventory | Import compatible local CSV/JSON URL rows | Infer that an arbitrary file represents the whole website |

Private operational connectors and raw evidence are excluded. See [REAL_WORLD_EVIDENCE.md](REAL_WORLD_EVIDENCE.md) for sanitized aggregate validation and the exact public/private boundary.

## Prepare a source union

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/prepare_sources.py \
  --site "https://example.com/" \
  --gsc "gsc.csv" \
  --ga4 "ga4.csv" \
  --wordpress "wordpress.json" \
  --crawler "crawler.csv" \
  --sitemap "sitemap.xml" \
  --require gsc --require ga4 --require wordpress --require crawler --require sitemap \
  --declare-source-universe-complete \
  --output-dir "prepared"
```

The direct `--gsc`, `--ga4`, `--wordpress`, `--crawler`, `--inventory`, and `--sitemap` flags are repeatable. The generic repeatable form `--source KIND=PATH` is also available; use `auto` only for CSV/JSON exports that can be identified safely from their fields. For a saved sitemap index, also pass every local child XML separately so the manifest contains the same hash set the audit later resolves.

For GSC, every accepted row needs a page identity. Within each file, ProofRank removes exact duplicate rows, sums clicks and impressions by normalized page, recomputes CTR as clicks/impressions, and computes impression-weighted position. Separate files may overlap, so one per-URL file snapshot is selected atomically by greatest impressions instead of blending totals; queries and source provenance are still unioned. For GA4, metrics sum within a file and use maxima across potentially overlapping files.

The importer:

1. accepts CSV/JSON tabular exports or saved sitemap XML and validates the declared shape;
2. normalizes same-site URL identities and removes fragments/query strings from page identity;
3. excludes non-public WordPress rows and non-HTML crawler assets;
4. merges duplicate identities while retaining `sourceTypes` and generic `sourceIds`;
5. records each input filename, SHA-256, row count, accepted/rejected counts, and unique URLs added;
6. neutralizes spreadsheet-formula prefixes in text exported to CSV;
7. writes `prepared/inventory.csv`, `prepared/source_manifest.json`, `prepared/prepare_report.json`, and—when crawler rows are accepted—`prepared/page_cache.json`; sitemap hashes are stored in `outputs.sitemaps`;
8. records `expected_normalized_identities` from the reconciled inventory so the audit can detect a later partial copy instead of treating it as the whole declared universe.

The manifest does not expose absolute source paths, and source IDs do not include filenames. It does retain source basenames and hashes, so review it before publication. Do not publish raw exports unless their privacy and licensing have been reviewed separately. Generated dashboards can still contain URLs, titles, H1s, and findings; keep real audit outputs local unless they have been explicitly cleared for publication.

## Declare gaps explicitly

The complete declaration is not a guess and is not inferred merely because parsing succeeded. At least one required entry must exist; each must be collected with at least one accepted same-site URL. Without `--require`, every supplied or declared entry is required by default. List the kinds required for the chosen scope, then represent missing evidence:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/prepare_sources.py \
  --site "https://example.com/" \
  --source "gsc=gsc.csv" \
  --require gsc --require wordpress \
  --unavailable "wordpress=no CMS export was available" \
  --declare-source-universe-complete \
  --output-dir "prepared"
```

Because required WordPress evidence is unavailable, `universe_complete` remains false even though the GSC file parsed successfully. `--not-attempted KIND=REASON` records a known source that has not yet been checked.

Invalid-shape and zero-accepted sources are recorded as `invalid` or `empty` and also block the gate when required. `expected_normalized_identities` must be a non-negative integer when present. At audit time, its exact equality with the observed normalized union is part of the source gate; any remainder is reported as `unclassified_count` rather than removed by evidence weighting. `prepare_sources.py` labels this basis as `expected_count_origin=AUTO_DERIVED_FROM_PREPARED_UNION`; it is a consistency count for the operator-declared scope, not an independent estimate of every URL that may exist.

## Run the two-stage audit

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --page-cache "prepared/page_cache.json" \
  --sitemap "sitemap.xml" \
  --brand-term "Example" \
  --output-dir "out" \
  --gate-exit-code

python plugins/proofrank/skills/audit-site-graph/scripts/render_dashboard.py \
  --audit "out/audit.json" \
  --output "out/dashboard.html"
```

ProofRank evaluates two independent stages:

1. **Declared-source-scope gate:** an explicit complete declaration, at least one required source, every required source collected, an absolute manifest origin equal to the audited origin, and exact SHA-256 multisets for every supplied inventory, the optional supplied HTML cache, and every recursively resolved sitemap body.
2. **Observed-content gate:** explicitly attested, conflict-free full HTML covers 100% of active graph-eligible URLs, the homepage is parsed, and every supplied sitemap child resolves. HTML must also be non-truncated, 2xx, and retain the requested identity on the audited origin. Confirmed 404s/410s and same-origin redirects with distinct destinations leave the active denominator; unresolved redirects, cross-origin finals, server errors, unattested snippets, conflicting snapshots, and other unusable 2xx records remain and block completeness. New page-like identities exposed by links, canonicals, or redirects contradict the declared universe. `--complete-threshold` is fixed at `1.0` because an unseen active page could change orphan, reachability, or link-opportunity results.

The final graph gate is the conjunction of both. `DECLARED_SCOPE_BOUND` means the declaration and supplied evidence agree; it is not independent proof that the operator remembered every source. When either gate fails, ProofRank emits withheld evidence and does not promote whole-site orphan, unreachable-page, click-depth, or internal-link-opportunity conclusions.

The false-green fixture shows why the count belongs in the first stage: declared-scope identities are only `7/11`, leaving four unclassified, even though usable full HTML covers every observed active identity (`7/7`). The active-HTML stage passes, but the final decision remains `WITHHOLD`. In the complete fixture, declared-scope identities are `11/11`; one confirmed 404 is outside the active denominator; usable full HTML is `10/10`; and the decision is `READY_FOR_HUMAN_REVIEW`.

## Consume the Guarded Release Contract

Every audit writes `decision.json` beside `audit.json`. The same object is also embedded at `audit.release_contract`. It contains:

- `decision`: `WITHHOLD` or `READY_FOR_HUMAN_REVIEW`;
- `release_gate_passed`;
- stage results for `source_universe`, `active_html`, and `final`;
- `scope_assurance`, `scope_warning`, and `expected_count_origin`;
- `unclassified_count` and stable `blocker_codes`;
- hashes that bind the decision to the evaluated evidence;
- `live_change_authorized=false` and the explicit read-only boundary.

The displayed fractions have different denominators: declared-scope identities are **observed / expected**, while active HTML is **usable / graph-eligible** after confirmed terminal identities are classified separately. Never combine them into one percentage.

By default the CLI can still generate a withheld report successfully. Add `--gate-exit-code` only when another read-only process needs deterministic control flow: exit `2` means `WITHHOLD`, and exit `0` means `READY_FOR_HUMAN_REVIEW`. Input and runtime failures remain normal errors. Neither exit code authorizes, applies, or rolls back a live change.

Public ProofRank contains no production apply or rollback implementation. Sanitized rollback evidence in the case-study documentation came from a separate private deployment workflow and only informed this contract design.

## Human review remains required

Source completeness and graph coverage make conclusions better supported; they do not turn cautious overlap heuristics into an automatic SEO diagnosis. Query intent, business role, language, page mechanism, and editorial context still determine whether pages should remain separate or whether any merge, redirect, canonical, noindex, or rewrite is appropriate.
