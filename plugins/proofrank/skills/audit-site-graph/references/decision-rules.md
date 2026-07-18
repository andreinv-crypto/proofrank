# Decision rules

## Evidence statuses

- `confirmed`: directly observed in a complete applicable input, such as invalid JSON-LD syntax in saved HTML or a cached 404 target.
- `candidate`: observed signal that requires another source, such as query/title overlap, near-duplicate text, or a weak internal-link target.
- `withheld`: current inputs cannot support the conclusion.

## Graph completeness

Declare the graph complete only when:

1. parsed HTML coverage is at least the configured threshold (default 95% of known URLs);
2. the normalized homepage is parsed;
3. every supplied sitemap-index child is resolved.

When any condition fails:

- do not call a page orphaned;
- do not treat missing links as proof;
- report `zero_inbound_partial` only as a collection gap;
- do not calculate sitewide click-depth conclusions.

## URL actions

Never recommend merge, redirect, delete, archive, or `noindex` until all applicable gates pass:

1. confirm the CMS or publishing mechanism;
2. inspect current finalized page+query search-performance data;
3. check backlink/referring-domain evidence when available;
4. preserve legacy URL, comments, media, and voice where useful;
5. identify rollback and obtain explicit approval for a live change.

Exact duplicate HTML is evidence of duplication, not permission to remove a URL.

## Cannibalization

- Keep language and mechanism lanes separate.
- Treat title/H1/query overlap as a candidate, not a diagnosis.
- Confirm that multiple URLs receive impressions for the same queries in comparable dates.
- Distinguish healthy hub/spoke intent from competing same-intent pages.
- Name a primary URL only after search-performance evidence, URL history, backlinks, and business role agree.

## Schema

- JSON parse errors are confirmed syntax findings.
- Missing schema is not automatically an SEO error.
- Schema.org vocabulary support is not the same as Google rich-result eligibility.
- Verify current Google Search Central documentation for the exact feature before assigning required/recommended properties.
- Require markup to match visible page content.
- Do not insert or generate live markup automatically.

Current official starting points:

- https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://developers.google.com/search/docs/appearance/structured-data/article

## Internal-link opportunities

Prioritize contextual links that help users continue within a real cluster. Do not recommend footer spam, exact-match repetition, or cross-language links without a user purpose. Recently refreshed pages should normally act as anchors until their measurement checkpoint, not be rewritten again.
