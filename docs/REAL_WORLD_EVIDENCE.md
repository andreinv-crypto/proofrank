# Real-world evidence and product boundary

ProofRank's public 11-identity fixture is a small, privacy-safe, reproducible demonstration of product behavior. It is not a scale benchmark.

The safety model was extracted from two private website-modernization programs. This page publishes only sanitized aggregate results and hashes of the exact private evidence reviewed. It does not publish customer URLs, page content, credentials, analytics exports, backups, or private integration code.

## Read this boundary first

| Layer | What it means |
| --- | --- |
| Public ProofRank | The read-only plugin, offline export adapters, evidence gates, synthetic fixtures, machine-readable decision, dashboard, tests, and verifier in this repository. |
| Private operational workflows | The migration crawlers, hosting/log/API integrations, WordPress modernization, guarded production apply, automatic rollback, and post-release gates that generated the sanitized evidence below. |
| Not claimed | Public ProofRank did not perform the private migrations, apply production patches, or execute the rollback. Those workflows exposed the failure modes that ProofRank now makes testable and portable. |

The machine-readable companion is [`validation/real_world_evidence.json`](../validation/real_world_evidence.json). Its SHA-256 values identify the private reports and apply JSONs used for transcription. They detect later drift; they do not make the excluded artifacts independently auditable.

## Why the source-universe problem is real

Google's migration guidance recommends building the old-URL list from multiple sources, including sitemaps, analytics/logs, Search Console, and CMS records, before mapping and testing a move. A sitemap helps discovery but is not a guaranteed complete registry, and the Search Analytics API may return top rows rather than every row. Screaming Frog likewise teaches combining crawl, sitemap, GA, and GSC data to find pages that a crawler alone missed.

- [Google: site moves with URL changes](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)
- [Google: sitemap overview](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- [Google: Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Screaming Frog: find orphan pages](https://www.screamingfrog.co.uk/seo-spider/tutorials/find-orphan-pages/)

Combining sources is established SEO work, not ProofRank's novelty by itself. ProofRank's product claim is narrower: it binds the declared evidence, keeps the source-universe gate separate from the active-HTML gate, and withholds whole-site graph conclusions when either gate cannot be proved.

## Case A: TorreviejaTour

TorreviejaTour is a separate long-lived WordPress estate with source history dating to 2013. That date establishes legacy migration context; it does not mean ProofRank existed in 2013.

### Platform modernization context

| Layer | Legacy state | Modernized production state |
| --- | --- | --- |
| Application | WordPress 4.4.34 · PHP 5.6.40 · WooCommerce 2.5.2 · 39 active plugins | WordPress 7.0 · PHP 8.5.2 · WooCommerce 10.9.1 |
| Database | MySQL 5.7.21 · about 1.73 GB before controlled cleanup | MySQL 8.4.8 · about 105.71 MB after cleanup |

The database cleanup removed 114,557 expired advert posts and 72,696 spam subscriber accounts before the controlled platform migration. These facts establish the operational old-site-rescue context; they are not outputs of public ProofRank.

| Measurement | Sanitized result |
| --- | ---: |
| Known active-site URL identities | 3,141 |
| HTML pages available for graph analysis | 3,137 |
| Active-site coverage | 99.872652% |
| Child sitemaps resolved | 18 |
| URLs in the repaired sitemap set | 3,108 |
| Full migration paths checked | 3,598 |
| Previously successful paths | 3,090 |
| Previously successful paths lost after migration | 0 |

The active-site analysis surfaced 104 orphan candidates, 470 pages unreachable from the homepage, 2,071 pages at click depth four or greater, 251 links to noncanonical URLs, 35 exact-duplicate groups, and 36 cautious cannibalization candidates.

A broader historical inventory contained 3,641 identities but only 86.16% available HTML coverage. Whole-site graph conclusions were withheld for that scope. A larger input did not justify a stronger claim.

## Case B: Velas Purpuras / Alye Parusa

This was a separate seven-language, multi-domain program with two WordPress installations and content history dating to 2013.

### Platform modernization context

| Lane | Legacy state | Modernized production state |
| --- | --- | --- |
| ES | WordPress 4.5.33 · PHP 5.6.40 · MySQL 5.7.21 · 42 active plugins | WordPress 7.0.1 · PHP 8.5.2 · MySQL 8.4.8 |
| RU | WordPress 4.8.28 · PHP 5.6.40 · MySQL 5.7.21 · 41 active plugins | WordPress 7.0.1 · PHP 8.5.2 · MySQL 8.4.8 |

The migration preserved 872 published ES properties and 905 published RU properties. These modernization facts establish the environment in which the SEO evidence was tested; they are not outputs of the public plugin.

### Source reconciliation

| Measurement | Sanitized result |
| --- | ---: |
| Initial known-URL release gate | 1,807 / 1,807 |
| Historical Drive parity gate | 3,696 / 3,696 |
| Base known + Drive identities after normalization | 5,490 |
| Final normalized source union | 11,172 |
| Supplemental parity rows | 5,696 |
| Unclassified rows | 0 |
| Hard migration regressions in that supplemental parity gate | 0 |

Two external sources were attempted and recorded as unavailable rather than silently counted as empty: Search Console Links was still processing, and Bing Webmaster was not connected. The source status therefore remained `yellow`, not falsely `green`.

The final union was assembled from overlapping evidence:

| Collected source | Normalized unique identities |
| --- | ---: |
| Old full-known map | 1,780 page-like rows |
| Historical Drive parity | 3,696 |
| GSC Performance pages | 67 |
| GA4 production-host landings | 75 |
| WordPress published inventory | 1,343 |
| Public sitemap URLs | 1,593 |
| Internal crawl observations | 5,069 |
| Hosting access-log paths | 2,004 |
| Wayback CDX | 2,096 |
| Common Crawl | 323 |

These counts overlap and must not be added together.

### The strongest false-green result

The final read-only audit classified 11,172 source-union identities plus 991 current-only links: 12,163 rows in all. It parsed usable HTML for all 5,376 active canonical pages — `5,376/5,376`, or 100% observed coverage.

The whole-site graph was still `WITHHELD` because the source gate remained yellow and the recursive crawl frontier was not closed. This is the central product lesson:

> 100% of the pages you observed is not proof that you observed 100% of the site.

### Evidence-weighted closeout and automatic rollback

Evidence weight was used to prioritize depth of review, never to silently delete low-weight identities from the completeness denominator. The closeout narrowed action to 63 old ES paths backed by current WordPress evidence, 18 working destinations, 220 invalid exact language alternates, and 442 active pages emitting those alternates.

The first guarded apply looked partly successful: all 63 redirects worked. Its output gate nevertheless found only 19 of 442 language pages green and 1,522 remaining invalid alternate emissions. The separate private workflow automatically restored all three changed files from just-in-time backups; its JSON reports `live_touched=false` after rollback.

After the request-local static-cache return paths were corrected, the second apply passed:

- 63/63 new redirects;
- 442/442 language source pages;
- 0 invalid alternate emissions;
- existing routes 148/148, redirects 65/65, and hreflang sources 33/33;
- RealHomes business smoke 40/40;
- desktop/mobile browsability 26/26;
- language visual QA 8/8 with 24 screenshots;
- ES sitemap 428 URLs;
- RU sitemap 11 children and 1,169 URLs;
- critical log errors 0;
- verified Googlebot observed on both new production roots.

This sequence validates the need for an enforceable evidence decision. It does not mean the public ProofRank plugin can apply or roll back production changes. Public ProofRank remains read-only and emits `WITHHOLD` or `READY_FOR_HUMAN_REVIEW`; a separate approved deployment workflow decides whether to proceed.

## Who benefits

- **Technical SEO or consultant:** replaces repeated spreadsheet reconciliation with a reproducible evidence bundle.
- **SEO or migration agency:** gives every analyst the same readiness rule and gives the client a traceable reason to proceed or stop.
- **Developer:** can consume a deterministic decision and exit code before a separate deployment workflow.
- **Owner of a long-lived site:** commissions an independent “technical inspection” before a redesign, domain move, or page cleanup, so old pages with search value are less likely to disappear unnoticed.

For a new 5–20 page site the value is limited. ProofRank does not promise rankings, choose redirects automatically, or replace backlinks, Core Web Vitals, content strategy, or expert review.

## Time-savings estimate: model, not benchmark

No controlled benchmark has yet compared the same audits with and without ProofRank, so the repository does not claim a guaranteed number of hours saved. A defensible planning range, assuming exports and crawl data already exist, is:

| Scope | Mature crawler + spreadsheet workflow | ProofRank-assisted operator | Modeled mechanical saving |
| --- | ---: | ---: | ---: |
| 300–800 identities, 3–4 sources | 4–8 h | 2–4 h | 2–4 h |
| 2,000–5,000 identities, about 5 sources | 8–16 h | 3–7 h | 5–10 h |
| 8,000–15,000 identities, 7–10 sources | 15–35 h | 6–14 h | 9–21 h |

The modeled saving covers normalization, deduplication, provenance, coverage reconciliation, graph extraction, evidence packaging, and one rerun. It excludes access collection, live crawling, expert redirect/delete decisions, implementation, and monitoring. The next validation step is to add timestamps and compare 5–10 matched audits before promoting this estimate to a measured product claim.

## What carried into public ProofRank

- offline GSC, GA4, WordPress, crawler, and generic inventory adapters;
- normalized URL identities without discarding source provenance;
- filenames, SHA-256 hashes, row counts, and input/output bindings;
- a declared source-universe gate separate from active-HTML completeness;
- a strict 100% active-page topology gate;
- terminal 404/410 and same-origin redirect semantics;
- confirmed, candidate, and withheld evidence states;
- a machine-readable guarded release contract and deterministic gate exit code;
- a local executive decision plus technical evidence dashboard;
- synthetic complete and false-green fixtures;
- multi-version CI and a repository secret scan.

Human review is deliberate. Cannibalization, similarity, and URL actions still require query intent, backlinks/history, business role, and editorial judgment. The product's promise is not to automate those decisions. It is to prevent incomplete evidence from masquerading as permission to make them.
