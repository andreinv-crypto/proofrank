---
name: audit-site-graph
description: Run a read-only, evidence-first multilingual site-graph and content-overlap audit from offline GSC, GA4, WordPress, and crawler exports, URL inventories, saved sitemaps, and saved HTML caches. Use when Codex needs to reconcile source provenance; measure crawl coverage, internal links, or click depth; or identify cautious orphan, broken-link, schema, duplicate, and cannibalization candidates without changing a CMS or live site.
---

# Audit a site graph

Use the bundled deterministic scripts. Prefer saved inputs. Never convert incomplete crawl coverage into a whole-site claim.

## Safety boundary

- Read local inputs and write local reports only by default.
- Treat export adapters as offline file readers. They do not authorize OAuth or live Google, crawler, or CMS API access.
- Require explicit approval for the exact scope before any broad live crawl.
- Enable network reads only when both `--crawl` and `--allow-network` are present.
- Never edit a CMS, hosting, DNS, analytics, search-console settings, redirects, canonicals, schema, sitemaps, or content.
- Treat `WITHHOLD` and `READY_FOR_HUMAN_REVIEW` as read-only evidence states. Neither state authorizes, applies, or rolls back a live change.
- Treat merge, redirect, delete, archive, and `noindex` as separate follow-up decisions requiring stronger evidence and approval.
- Keep languages and distinct mechanisms such as articles, products, rentals, tours, and taxonomies in separate lanes.

## Explain the value

Start with the owner’s decision, not the graph vocabulary: ProofRank is a technical inspection before an old website is redesigned, moved, or cleaned up. Explain whether the evidence is sufficient to begin human review and what is still missing. Then give the technical SEO team the exact stages, counts, blockers, hashes, and next evidence step.

## Select inputs

Prefer the freshest complete artifacts with reproducible provenance:

1. Saved GSC, GA4, WordPress, crawler, or existing inventory exports in CSV or JSON.
2. A source manifest that identifies required, collected, invalid, empty, unavailable, and not-attempted sources; records the expected normalized identity count; and binds the exact inventory, supplied HTML cache, and resolved sitemap bodies by SHA-256.
3. Saved sitemap XML, including every saved child of a sitemap index.
4. Saved page-cache JSON containing URL, status, final URL, rendered HTML, and an explicit `html_complete=true` attestation for full documents used in topology coverage.

Read [references/input-formats.md](references/input-formats.md) when preparing inputs.

## Prepare and declare the source universe

Use the offline adapter when common exports have not already been normalized:

```bash
python scripts/prepare_sources.py \
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

Use `--declare-source-universe-complete` only after the selected source universe is explicitly scoped. The declaration remains false unless at least one required entry exists and every required entry was collected with at least one accepted same-site URL. Without `--require`, every supplied or declared entry is required. Record known gaps rather than omitting them:

```bash
python scripts/prepare_sources.py \
  --site "https://example.com/" \
  --require gsc --require wordpress \
  --unavailable "gsc=export not available for this property" \
  --not-attempted "wordpress=CMS export not requested" \
  --output-dir "prepared"
```

The direct source flags and `--source KIND=PATH` are repeatable. Inspect `prepared/source_manifest.json` and `prepared/prepare_report.json` before running the audit. Confirm that `expected_normalized_identities` represents the reconciled scoped union. Without a manifest, or when the expected and observed normalized counts differ, the source-universe gate fails and whole-site graph claims remain withheld. Never infer a complete universe merely because every supplied file parsed successfully.

## Choose a mode

### Local coverage

Use for inventories and metrics without HTML. Withhold orphan, click-depth, body-duplicate, link, and schema conclusions.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --output-dir "out"
```

### Saved HTML cache

Prefer this for complete audits because it creates no production load.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --page-cache "prepared/page_cache.json" \
  --sitemap "sitemap.xml" \
  --brand-term "Example" \
  --output-dir "out"
```

### Approved read-only crawl

Use only after explicit approval. Keep a finite `--max-pages`; zero means every seed.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --sitemap "https://example.com/sitemap.xml" \
  --crawl --allow-network --max-pages 100 --delay-ms 250 \
  --save-cache --output-dir "out"
```

## Run the audit

1. Record input filenames, timestamps, hashes, row counts, mode, and network state without copying secrets or absolute local paths into public artifacts.
2. Normalize URL variants without discarding source provenance.
3. Require an explicit source-universe declaration; verify at least one required source exists, every required source is collected, the manifest site matches the audited origin, the expected normalized identity count equals the observed union, and exact SHA-256 sets match every supplied inventory, HTML cache, and resolved sitemap body. Report any identity-count remainder as unclassified; never remove it by evidence weighting.
4. Resolve every supplied sitemap-index child; record unresolved children.
5. Parse multilingual text with Unicode-aware tokens.
6. Build the graph only from saved or explicitly fetched HTML.
7. Count saved HTML as usable only when explicitly attested complete, non-truncated, conflict-free, 2xx, and still the same URL identity on the audited origin. Remove confirmed 404s/410s and same-origin redirects with distinct destinations from the active-page denominator, but keep unresolved redirects, cross-origin finals, server errors, and unusable 2xx records in it. Reconcile page-like identities discovered in links, canonicals, and redirect destinations before coverage; an identity outside the declared universe blocks both gates. Pass only at 100% usable active-page coverage, with the homepage parsed and every child sitemap resolved. Do not lower `--complete-threshold` for topology claims.
8. Enable whole-site graph claims only when both the source-universe and observed-content gates pass.
9. Inspect `decision.json`. Require `WITHHOLD` when either stage fails and `READY_FOR_HUMAN_REVIEW` only when both pass; require `live_change_authorized=false` in every state.
10. Use `--gate-exit-code` only when an external read-only workflow needs a deterministic signal: `2` means withheld and `0` means ready for human review. Treat normal input/runtime failures as errors.
11. Separate `confirmed`, `candidate`, and `withheld` findings.
12. Read [references/decision-rules.md](references/decision-rules.md) before interpreting URL-action candidates.
13. Render the static dashboard after generating `audit.json`:

```bash
python scripts/render_dashboard.py --audit "out/audit.json" --output "out/dashboard.html"
```

## Demonstrate the evidence gate

Change to this Skill directory, then run both bundled synthetic scenarios to compare an incomplete graph with a complete one:

```bash
python scripts/run_demo.py --scenario both --output-dir "demo-output"
```

Open `demo-output/incomplete/dashboard.html` before `demo-output/complete/dashboard.html`. Confirm that the incomplete result contains `graph_claims_withheld` and does not promote orphan, unreachable, or internal-link-opportunity conclusions. The bundled synthetic scenarios require no private exports.

Expect the incomplete result to report source identities `7/11`, `unclassified_count=4`, active HTML `7/7` (100%), `decision=WITHHOLD`, and `live_change_authorized=false`. This is the false green: the active-HTML stage passes while the source-universe stage fails. Expect the complete result to report source identities `11/11`, one confirmed 404, active HTML `10/10` (100%), `decision=READY_FOR_HUMAN_REVIEW`, and `live_change_authorized=false`. The final state is the conjunction of the source-universe gate and the active-HTML gate.

## Outputs

Source preparation can write:

- `inventory.csv`: normalized URL/metric evidence and merged source IDs;
- `page_cache.json`: conditional crawler status/final-URL records plus any supplied rendered HTML;
- `source_manifest.json`: source statuses, expected normalized identity count, basenames, hashes, declaration, and output bindings;
- `prepare_report.json`: offline boundary and source/output summary.

The audit writes:

- `audit.json`: provenance, coverage, findings, pages, and links.
- `decision.json`: compact Guarded Release Contract with stage results, blocker codes, unclassified count, evidence hashes, and the read-only authorization boundary.
- `pages.csv`: normalized page-level evidence.
- `links.csv`: observed internal links.
- `findings.csv`: sortable findings with status and evidence.
- `report.md`: concise evidence report.
- `dashboard.html`: local interactive viewer generated separately.

Lead with an owner-readable release decision, then source-universe limitations, then active-HTML limitations, and finally the smallest safe next step. Cannibalization and URL-action findings remain human-review candidates even when both gates pass. Never fill missing evidence with assumptions. Never attribute a separate private deployment apply or rollback to ProofRank.
