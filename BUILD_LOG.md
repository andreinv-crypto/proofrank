# Build Week development log

This log separates earlier private operational work from the public ProofRank product built during the OpenAI Build Week submission period. Times use Europe/Madrid (UTC+02:00).

## Before the submission period

- Private, site-specific workflows existed for TorreviejaTour and Velas Purpuras. They contained production paths, credentials, private exports, and domain-specific scripts.
- Those workflows supplied design lessons and sanitized operational evidence. They are not the submitted plugin, and ProofRank is not claimed to have existed since 2013.
- The 2013 date describes the history of the TorreviejaTour site and its source estate, not the age of this public product.

## 2026-07-18

- `20:44` — commit `e979ae0`: created the portable, read-only ProofRank Codex plugin, deterministic audit engine, synthetic fixture, report, and dashboard.
- `20:45` — commit `19513f1`: finalized portable installation guidance.
- `23:30` — commit `a903379`: added the reproducible complete/incomplete evidence-gate demo and initial Build Week video materials.

## 2026-07-19

- Commits `2d6137d`, `d65fb92`, and `d52de80`: refined the truthful founder story, accessibility context, and under-three-minute demo without changing the deterministic evidence boundary.
- `20:04` — commit `8b452af`: linked the public complete and incomplete dashboards.

## 2026-07-20

- Corrected sitemap parsing so nested image, video, and news locations cannot be counted as page URLs or child sitemaps.
- Added a declared source-universe manifest with required-source statuses and SHA-256 provenance.
- Split completeness into two gates: source-universe completeness and observed HTML-graph completeness. Whole-site graph claims require both.
- Added credential-free import and normalization for Google Search Console, Google Analytics 4, WordPress, crawler, and generic inventory exports.
- Added sanitized real-world evidence from two private operational programs while preserving the public/private boundary.
- Expanded the regression suite with source reconciliation, unavailable/invalid inputs, crawler HTML evidence, WordPress draft and crawler-asset filtering, manifest binding, cross-origin/truncated HTML rejection, CSV formula safety, a 10,000-row export, and dashboard gate states.
- Added GitHub Actions verification on Python 3.10, 3.12, and 3.13.

## 2026-07-21 — current revision

- Reconciled the public evidence package with the final hashed Velas source-union, full-audit, failed-apply, rollback, corrected-apply, and closeout artifacts.
- Corrected the public aggregate from the earlier 10,168-identity snapshot to the final 11,172-identity union and recorded 991 separately discovered current-only links.
- Added the strongest real false-green result: 5,376/5,376 active canonical HTML pages parsed while whole-site graph conclusions remained withheld because source/frontier evidence was incomplete.
- Replaced the old incomplete-HTML comparison with an independent two-gate demo: source universe 7/11 fails while active HTML 7/7 passes.
- Added `decision.json`, stable blocker codes, unclassified counts, SHA-256 evidence bindings, and optional gate exit codes (`0` ready for human review, `2` withheld).
- Added an owner/release view and kept the public product read-only: neither decision state authorizes apply or rollback.
- Updated the competition narrative to explain the concrete GPT-5.6 reasoning contribution and to distinguish public ProofRank from the private production workflow.

## Reproducibility

Run:

```bash
python scripts/verify.py
```

The verifier checks plugin packaging, marketplace metadata, unit and regression tests, complete and incomplete demo behavior, dashboard privacy boundaries, and accidental secret exposure. The public fixture is synthetic; sanitized operational aggregates are documented separately in `docs/REAL_WORLD_EVIDENCE.md`.
