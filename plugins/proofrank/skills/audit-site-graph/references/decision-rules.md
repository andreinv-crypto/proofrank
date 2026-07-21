# Decision rules

## Evidence statuses

- `confirmed`: directly observed in a complete applicable input, such as invalid JSON-LD syntax in saved HTML or a cached 404 target.
- `candidate`: observed signal that requires another source, such as query/title overlap, near-duplicate text, or a weak internal-link target.
- `withheld`: current inputs cannot support the conclusion.

## Release decision

Return `READY_FOR_HUMAN_REVIEW` only when both stages pass:

1. **Declared source scope:** the scope is explicitly declared, required sources are collected, origin and SHA-256 bindings match, `expected_normalized_identities` equals the observed normalized union, and no new page-like identity contradicts the declaration.
2. **Active HTML:** usable parsed HTML covers 100% of active graph-eligible URLs; the normalized homepage is parsed; and every supplied sitemap-index child is resolved. The topology threshold cannot be lowered because one unseen active page can change inbound-link and reachability conclusions.

Return `WITHHOLD` when either stage fails. Report the expected/observed source counts, `unclassified_count`, blocker codes, and both stage results rather than collapsing them into one percentage. A `7/7` active-HTML pass cannot override a `7/11` source-universe failure.

Always expose `scope_assurance` and `expected_count_origin`. `DECLARED_SCOPE_BOUND` is a consistency and provenance assurance for the operator-declared inputs, not independent proof that every site source or historical URL was supplied. Label the fractions explicitly: source scope is observed / expected; active HTML is usable / graph-eligible.

When any condition fails:

- do not call a page orphaned;
- do not treat missing links as proof;
- report `zero_inbound_partial` only as a collection gap;
- do not calculate sitewide click-depth conclusions.

Every `decision.json` must retain `live_change_authorized=false`. `READY_FOR_HUMAN_REVIEW` is not approval to deploy. With `--gate-exit-code`, use exit `2` for `WITHHOLD` and `0` for ready-for-review; preserve ordinary error behavior for invalid inputs or runtime failures. Public ProofRank never applies or rolls back live changes.

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
