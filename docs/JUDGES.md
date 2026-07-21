# Judge testing guide

ProofRank can be evaluated without rebuilding it, creating an account, or providing credentials.

## Fastest path: inspect the false green

1. Open the live [false-green demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html).
2. In the owner/release view confirm:
   - **source identities:** `7/11` — failed;
   - **unclassified:** `4`;
   - **active HTML:** `7/7` — passed;
   - **decision:** `WITHHOLD`;
   - **live change authorized:** `false`.
3. Confirm that whole-site orphan, unreachable-page, click-depth, and link-opportunity claims are not promoted. The HTML subset is 100% complete, but the known source universe is not.
4. Open the live [complete demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html).
5. Confirm:
   - **source identities:** `11/11` — passed;
   - **confirmed terminal identity:** `1` known 404;
   - **active HTML:** `10/10` — passed;
   - **decision:** `READY_FOR_HUMAN_REVIEW`;
   - **live change authorized:** `false`.
6. Open **Evidence**, filter to high priority, and inspect a finding’s status and sources. Open **Method** to inspect the two-stage boundary.

Both dashboards are self-contained synthetic artifacts. They load no external script, make no live-site write, and require no private data.

## Why this comparison matters

The incomplete state is intentionally not a conventional partial-crawl warning. It is a harder false green: every active page that the tool was given has full HTML (`7/7`), but only 7 of 11 expected source identities are present. ProofRank refuses to let a perfect observed-HTML percentage override the missing source identities.

The complete state classifies one confirmed 404 outside the active denominator, then requires usable HTML for all remaining active identities (`10/10`). `READY_FOR_HUMAN_REVIEW` means the evidence gate passed; it never authorizes deployment.

## Reproduce both states

Requirements: Python 3.10+ on Windows, macOS, or Linux. No package installation is required.

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

Open:

```text
plugins/proofrank/demo-output/incomplete/dashboard.html
plugins/proofrank/demo-output/complete/dashboard.html
```

Each directory contains:

- `audit.json` — complete audit evidence;
- `decision.json` — the compact Guarded Release Contract;
- `pages.csv`, `links.csv`, and `findings.csv`;
- `report.md`;
- `dashboard.html`.

Expected `decision.json` values:

| Scenario | Source stage | Active HTML stage | Final decision | Unclassified | Live change |
| --- | --- | --- | --- | ---: | --- |
| False green | `7/11`, fail | `7/7`, pass | `WITHHOLD` | 4 | never authorized |
| Complete | `11/11`, pass | `10/10`, pass; one confirmed 404 | `READY_FOR_HUMAN_REVIEW` | 0 | never authorized |

## Test the deterministic CLI gate

`site_graph_audit.py` writes reports normally. Add `--gate-exit-code` only when a separate read-only workflow needs a stop signal:

- exit `2`: evidence is withheld;
- exit `0`: ready for human review;
- normal input/runtime failures remain ordinary errors rather than being reclassified as a gate decision.

The generated contract always contains `live_change_authorized=false`. It does not apply, deploy, or roll back anything.

## Verify the repository

```bash
python scripts/verify.py
```

This runs unit and adapter tests, regenerates the demo in a temporary directory, validates the public dashboard boundary, checks the manifest and plugin shape, and scans for common secret formats. The GitHub Actions workflow runs the same verification on supported Python versions, including a 10,000-row no-truncation regression.

## Test offline source normalization

The adapters import already-exported page-identified GSC, GA4, WordPress, crawler, generic inventory, and saved sitemap evidence. They do not perform OAuth or call live Google, crawler, or CMS APIs.

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

python plugins/proofrank/skills/audit-site-graph/scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --page-cache "prepared/page_cache.json" \
  --sitemap "sitemap.xml" \
  --output-dir "out" \
  --gate-exit-code
```

The final gate passes only when:

1. the source universe is explicitly declared complete, all required sources are collected, the audited origin matches, exact SHA-256 bindings match the supplied inventory/cache/resolved sitemaps, and any declared `expected_normalized_identities` count matches the observed union; and
2. explicitly attested, conflict-free, non-truncated, same-identity 2xx full HTML covers 100% of active graph-eligible identities, the homepage is parsed, and every sitemap child resolves.

Confirmed 404/410 identities and resolved same-origin redirects with distinct destinations are reported and removed from the active denominator. Unresolved redirects, cross-origin finals, server errors, unusable 2xx records, new page-like identities, and count mismatches remain blockers.

## Install in Codex

```bash
codex plugin marketplace add andreinv-crypto/proofrank
codex plugin add proofrank@proofrank-marketplace
```

Install **ProofRank**, start a new task, and invoke `$audit-site-graph`. The bundled synthetic comparison remains the recommended zero-credential evaluation path.

## Evidence boundary

Sanitized private evidence explains the product’s origin but is not public ProofRank output:

- TorreviejaTour: 3,598 migration paths checked; zero of 3,090 previously successful paths lost.
- Velas Purpuras / Alye Parusa: the source union expanded from an apparently complete 1,807-row gate to 11,172 normalized identities; `5,376/5,376` active canonical pages had usable HTML, yet source/frontier evidence remained incomplete, so graph claims were withheld.
- A separate private deployment workflow caught a cache-path defect, rolled back three touched files, and later passed `442/442` pages with zero invalid emissions. Public ProofRank did not apply or roll back those changes.

See [REAL_WORLD_EVIDENCE.md](REAL_WORLD_EVIDENCE.md) and `validation/real_world_evidence.json` for exact aggregates, artifact hashes, and exclusions. Real dashboards can contain URLs, titles, H1s, and findings; only the bundled synthetic dashboards are publication-safe by default.
