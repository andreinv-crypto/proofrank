<p align="center"><img src="plugins/proofrank/assets/logo.svg" width="150" alt="ProofRank logo"></p>

# ProofRank

[![Verify ProofRank](https://github.com/andreinv-crypto/proofrank/actions/workflows/verify.yml/badge.svg)](https://github.com/andreinv-crypto/proofrank/actions/workflows/verify.yml)

**A technical inspection before an old website is redesigned, moved, or cleaned up.**

[Open the complete interactive demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html) · [Open the incomplete-coverage demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html) · [Watch the 2:41 demo video](https://youtu.be/x3pWJJJjKM8)

![ProofRank evidence-first dashboard](plugins/proofrank/assets/screenshot-dashboard.png)

ProofRank turns common offline SEO exports, CMS inventories, crawler data, saved sitemaps, and saved HTML into a reproducible pre-migration evidence gate. It answers one costly question first: **is the known page universe complete enough to trust site-wide conclusions?**

For a site owner, it is a technical inspection before renovation: do not throw away pages, traffic, links, or search history with the old design. For an SEO or migration team, it is a local, read-only QA layer: reconcile the evidence, prove coverage, then review findings — or stop.

The result is not another SEO content generator and not a crawler replacement. ProofRank emits a machine-readable `WITHHOLD` or `READY_FOR_HUMAN_REVIEW` decision, stable blocker codes, and a deterministic optional CLI exit state. Neither state authorizes a live change.

The same evidence-gate pattern can protect other AI workflows that act on incomplete data.

ProofRank grew from lessons in an earlier private workflow built with previous Codex models. Its creator, Andrei Zakharov, has over 13 years of experience building and growing online projects across marketing, SEO, and automation. He is fully paralysed. Codex lowers the physical cost of turning hard-won experience and new ideas into working systems, unlocking more of his professional and creative potential. That sharpened a universal product principle: automation should reduce correction work, not create more.

## What it detects

- whether the declared source universe is complete enough to support a whole-site claim;
- crawl and sitemap coverage;
- internal links and click depth;
- orphan and unreachable-page candidates;
- broken, noindex, and noncanonical internal-link targets;
- JSON-LD syntax and visible-content mismatches;
- exact and near-duplicate content candidates;
- cautious title/H1/query overlap candidates;
- contextual internal-link opportunities.

## Who it helps

| User | Practical value |
| --- | --- |
| Technical SEO / consultant | Reconcile GSC, GA4, CMS, crawler, sitemap, and saved HTML evidence without rebuilding the same spreadsheet workflow. |
| SEO or migration agency | Apply one auditable readiness rule across analysts and give the client a traceable stop/proceed explanation. |
| Developer | Consume `decision.json` or optional exit code `2/0` before a separate approved deployment workflow. |
| Owner of a long-lived site | Commission an independent check before a redesign, hosting move, domain move, or page cleanup. |

ProofRank is most useful on long-lived, multilingual, or migration-sensitive sites with hundreds or thousands of URL identities. It is deliberately less useful for a new 5–20 page brochure site, and it does not promise rankings or replace expert redirect, backlink, intent, and content decisions.

If you own an old website but do not work in SEO, the practical request is simple: ask the specialist handling the redesign or migration to run ProofRank before pages are deleted, merged, or redirected. The owner does not need to operate the tool; the owner receives a traceable stop/proceed explanation and a list of what remains unknown.

## Architecture

ProofRank combines four layers:

1. **Deterministic Python tools** for offline GSC, GA4, WordPress, and crawler-export validation and normalization; source provenance; optional crawler HTML-cache preparation; graph construction; evidence labels; and portable JSON/CSV/Markdown outputs.
2. **Codex Skill** for safe input selection, completeness gates, interpretation, and action boundaries.
3. **Guarded Release Contract** for a deterministic `WITHHOLD` / `READY_FOR_HUMAN_REVIEW` handoff, stable blocker codes, unclassified counts, evidence hashes, and optional gate exit codes.
4. **Dependency-free dashboard** with an owner/release view followed by the full technical evidence ledger, without uploading audit data to a third party.

No API key or third-party Python package is required. The adapters read already-exported CSV or JSON files; they do not perform OAuth or call live Google, CMS, or crawler APIs.

## Run the synthetic demo

From the repository root:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

Open:

```text
plugins/proofrank/demo-output/dashboard.html
```

The fixture is fully synthetic and intentionally contains a broken link, a noindex target, a noncanonical URL, an orphan candidate, malformed JSON-LD, and a conservative topic-overlap/cannibalization candidate. Exact and near-duplicate detection is covered separately by regression tests.

To reproduce the central evidence-gate comparison in one command:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

Open `plugins/proofrank/demo-output/incomplete/dashboard.html` first, then `plugins/proofrank/demo-output/complete/dashboard.html`.

- **False-green input:** the supplied seven-page view has usable HTML for every observed active page (`7/7`, 100%), but the manifest expects 11 normalized identities. ProofRank reports source `7/11`, `unclassified_count=4`, and `WITHHOLD`.
- **Complete input:** source identities reach `11/11`; one confirmed 404 is classified outside the active denominator; all `10/10` active pages have usable HTML; ProofRank reports `READY_FOR_HUMAN_REVIEW`.

Each output contains `audit.json`, `decision.json`, CSV evidence, a Markdown report, and a self-contained dashboard. This proves that observed-HTML completeness cannot override an incomplete source universe.

## Prepare common read-only exports

`prepare_sources.py` automatically recognizes and normalizes common saved GSC, GA4, WordPress, and crawler CSV/JSON exports. It validates declared shapes, deduplicates exact rows, merges URL identities without discarding source provenance, and writes `inventory.csv`, `source_manifest.json`, and `prepare_report.json`. An accepted crawler export also produces `page_cache.json` with status/final-URL records and any supplied rendered HTML.

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

The declaration flag is intentionally explicit. It can pass only when at least one required entry exists and every required entry was collected with at least one accepted same-site URL. Without `--require`, every supplied or declared entry is required by default. Record a missing source with `--unavailable KIND=REASON` or `--not-attempted KIND=REASON`; ProofRank will mark the source-universe gate incomplete instead of silently treating the available files as the whole site.

See [INTEGRATIONS.md](docs/INTEGRATIONS.md) for accepted export shapes, provenance rules, and the live-integration boundary.

## Run on saved site data

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "prepared/inventory.csv" \
  --source-manifest "prepared/source_manifest.json" \
  --page-cache "prepared/page_cache.json" \
  --sitemap "sitemap.xml" \
  --brand-term "Example" \
  --output-dir "out"

python plugins/proofrank/skills/audit-site-graph/scripts/render_dashboard.py \
  --audit "out/audit.json" \
  --output "out/dashboard.html"
```

Whole-site graph claims pass a two-stage gate. First, the source universe must be explicitly declared complete, contain at least one required collected source, match the audited origin, and exactly bind the supplied inventory, HTML cache, and every resolved sitemap body by SHA-256. Second, explicitly attested full HTML must cover 100% of active graph-eligible URLs, include the homepage, and resolve every supplied sitemap child. HTML is usable only when it is present, marked `html_complete=true`, non-truncated, conflict-free, 2xx, and the final URL is the same identity on the audited origin. A confirmed 404/410 or same-origin redirect with a distinct destination is reported and removed from the active-page denominator; unresolved redirects, cross-origin finals, server errors, and unusable 2xx responses remain and block completeness. Any new page-like identity discovered in links, canonicals, or redirect destinations contradicts the declared universe and also blocks the gate. The topology threshold cannot be lowered: one unseen active page could disprove an orphan claim. If the source manifest is missing or either stage fails, orphan, click-depth, unreachable-page, and link-opportunity conclusions are withheld.

When the manifest includes `expected_normalized_identities`, ProofRank also verifies the observed identity count and reports any remainder as unclassified. Evidence weight may prioritize deeper review, but it never silently removes a low-weight identity from the completeness denominator.

Add `--gate-exit-code` when an external read-only workflow needs a deterministic stop signal: `0` means ready for human review, `2` means evidence withheld, and normal input/runtime failures remain errors. The generated contract always says `live_change_authorized=false`.

See the bundled Skill references for accepted input shapes and evidence rules.

## Install as a Codex plugin

For local testing, add this repository as a marketplace source:

```bash
codex plugin marketplace add /absolute/path/to/proofrank
```

From the public GitHub repository:

```bash
codex plugin marketplace add andreinv-crypto/proofrank
codex plugin add proofrank@proofrank-marketplace
```

Then open the Plugins Directory in the ChatGPT desktop app or `/plugins` in Codex CLI, install **ProofRank**, and start a new task. Invoke the bundled skill explicitly with `$audit-site-graph` or describe the desired read-only site audit.

### Supported platforms

- Windows, macOS, or Linux with Python 3.10+ for the deterministic audit and demo generator.
- A modern desktop or mobile browser for the self-contained dashboard.
- Codex CLI or the ChatGPT desktop app for plugin use.

## Safety model

- Local reads and local report writes by default.
- Saved exports are imported offline; there is no live OAuth, Search Console API, GA4 API, crawler API, or CMS connection.
- Network crawling requires both `--crawl` and `--allow-network`.
- Live crawling still requires explicit scope approval.
- No CMS, hosting, analytics, Search Console, sitemap, redirect, canonical, or content writes.
- No URL deletion, merge, redirect, or noindex recommendation from similarity alone.
- The renderer strips local input paths and source notes, but a real dashboard still embeds audited URLs, titles, H1s, and findings. Treat it as potentially sensitive; only the bundled synthetic dashboards are publication-safe by default.

## Verify

```bash
python scripts/verify.py
```

The verification runs unit and adapter tests, including a 10,000-row no-truncation regression, generates the demo in a temporary folder, validates the public dashboard boundary, checks the manifest shape, and scans for common secret formats. The GitHub Actions workflow is configured to run the same command on Python 3.10, 3.12, and 3.13.

## OpenAI Build Week 2026

During the OpenAI Build Week submission period, Codex with GPT-5.6 helped generalize and package earlier private lessons as ProofRank. Andrei used GPT-5.6 at the Ultra reasoning level to challenge the first design against sanitized migration evidence. That reasoning exposed the central false-completeness flaw: 100% of observed HTML can still hide an incomplete source universe. Codex then helped implement the separate identity-count gate, offline adapters, terminal-URL semantics, strict 100% tests, Guarded Release Contract, false-green demo, dashboard, and repository verification. Deterministic Python calculates the audit facts; Codex follows the Skill, explains the evidence, and never manufactures permission for a live change.

**Track:** Work & Productivity.

The runnable public fixtures are synthetic. Sanitized Torrevieja evidence documents 3,598 migration paths checked with zero of 3,090 previously successful paths lost. Separate seven-language Velas evidence shows an apparently complete 1,807-row gate expanding to 11,172 normalized identities; even after all 5,376 active canonical pages had usable HTML, the whole-site graph remained withheld because source/frontier evidence was incomplete. A private guarded apply later failed at 19/442 language pages and automatically restored all three changed files; after the cache-path fix it passed 442/442 with zero invalid alternate emissions. These workflows informed the public safety model but are not public ProofRank outputs. See [REAL_WORLD_EVIDENCE.md](docs/REAL_WORLD_EVIDENCE.md) for exact scope, hashes, and boundary.

### Modeled analyst time, not a guarantee

No controlled benchmark exists yet. With exports and crawl data already available, the planning model estimates roughly 5–10 hours of mechanical reconciliation and evidence-packaging saved on a 2,000–5,000 identity project, and 9–21 hours on an 8,000–15,000 identity project. Access collection, live crawling, expert decisions, implementation, and monitoring are excluded. See the evidence document for assumptions and the planned benchmark method.

For the judging criteria, the technical implementation is deterministic and tested; the impact is fewer unsafe corrections before live SEO work; the novelty is a two-stage evidence contract that can refuse unsupported claims; and reproducibility comes from synthetic fixtures, local artifacts, one-command verification, and zero required credentials. Human review is intentional: cannibalization and URL-action candidates are decision support, not automatic diagnoses or production changes.

See [BEFORE_AFTER.md](BEFORE_AFTER.md) for the boundary between prior domain-specific work and the Build Week extension.

Submission materials: [Devpost draft](docs/DEVPOST_SUBMISSION.md) · [Build Week log](BUILD_LOG.md) · [public demo video](https://youtu.be/x3pWJJJjKM8) · [under-three-minute demo script](docs/DEMO_SCRIPT.md) · [judge testing guide](docs/JUDGES.md).

## License

MIT © 2026 Andrei Zakharov.
