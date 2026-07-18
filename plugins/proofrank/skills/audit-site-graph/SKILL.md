---
name: audit-site-graph
description: Run a read-only, evidence-first multilingual site-graph and content-overlap audit from URL inventories, saved sitemaps, and saved HTML caches. Use when Codex needs to measure crawl coverage, internal links, click depth, orphan candidates, broken or noncanonical links, JSON-LD syntax, exact/near duplicates, or cautious cannibalization candidates without changing a CMS or live site.
---

# Audit a site graph

Use the bundled deterministic scripts. Prefer saved inputs. Never convert incomplete crawl coverage into a whole-site claim.

## Safety boundary

- Read local inputs and write local reports only by default.
- Require explicit approval for the exact scope before any broad live crawl.
- Enable network reads only when both `--crawl` and `--allow-network` are present.
- Never edit a CMS, hosting, DNS, analytics, search-console settings, redirects, canonicals, schema, sitemaps, or content.
- Treat merge, redirect, delete, archive, and `noindex` as separate follow-up decisions requiring stronger evidence and approval.
- Keep languages and distinct mechanisms such as articles, products, rentals, tours, and taxonomies in separate lanes.

## Select inputs

Prefer the freshest complete artifacts with reproducible provenance:

1. URL inventory in CSV or JSON.
2. Saved sitemap XML, including every saved child of a sitemap index.
3. Saved page-cache JSON containing URL, status, final URL, and rendered HTML.

Read [references/input-formats.md](references/input-formats.md) when preparing inputs.

## Choose a mode

### Local coverage

Use for inventories and metrics without HTML. Withhold orphan, click-depth, body-duplicate, link, and schema conclusions.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "inventory.csv" \
  --output-dir "out"
```

### Saved HTML cache

Prefer this for complete audits because it creates no production load.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "inventory.csv" \
  --page-cache "page_cache.json" \
  --sitemap "sitemap.xml" \
  --brand-term "Example" \
  --output-dir "out"
```

### Approved read-only crawl

Use only after explicit approval. Keep a finite `--max-pages`; zero means every seed.

```bash
python scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --sitemap "https://example.com/sitemap.xml" \
  --crawl --allow-network --max-pages 100 --delay-ms 250 \
  --save-cache --output-dir "out"
```

## Run the audit

1. Record input paths, timestamps, counts, mode, and network state.
2. Normalize URL variants without discarding provenance.
3. Resolve every supplied sitemap-index child; record unresolved children.
4. Parse multilingual text with Unicode-aware tokens.
5. Build the graph only from saved or explicitly fetched HTML.
6. Declare completeness only when HTML coverage reaches the configured threshold, the homepage is parsed, and every child sitemap resolves.
7. Separate `confirmed`, `candidate`, and `withheld` findings.
8. Read [references/decision-rules.md](references/decision-rules.md) before interpreting URL-action candidates.
9. Render the static dashboard after generating `audit.json`:

```bash
python scripts/render_dashboard.py --audit "out/audit.json" --output "out/dashboard.html"
```

## Demonstrate the evidence gate

Change to this Skill directory, then run both bundled synthetic scenarios to compare an incomplete graph with a complete one:

```bash
python scripts/run_demo.py --scenario both --output-dir "demo-output"
```

Open `demo-output/incomplete/dashboard.html` before `demo-output/complete/dashboard.html`. Confirm that the incomplete result contains `graph_claims_withheld` and does not promote orphan, unreachable, or internal-link-opportunity conclusions.

Expect the incomplete result to report 11 known URLs, 7 parsed HTML pages, 63.64% coverage, and `graph_complete=false`. Expect the complete result to report 11 parsed pages, 100% coverage, and `graph_complete=true`.

## Outputs

- `audit.json`: provenance, coverage, findings, pages, and links.
- `pages.csv`: normalized page-level evidence.
- `links.csv`: observed internal links.
- `findings.csv`: sortable findings with status and evidence.
- `report.md`: concise evidence report.
- `dashboard.html`: local interactive viewer generated separately.

Lead with coverage limitations and the smallest safe next step. Never fill missing evidence with assumptions.
