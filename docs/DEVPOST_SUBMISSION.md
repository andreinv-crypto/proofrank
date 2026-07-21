# OpenAI Build Week — Devpost submission

## Required fields

- **Project name:** ProofRank
- **Track:** Work & Productivity
- **Tagline:** Stop incomplete SEO evidence from becoming a confident migration plan.
- **Repository URL:** https://github.com/andreinv-crypto/proofrank
- **Complete interactive demo:** https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html
- **False-green interactive demo:** https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html
- **Public YouTube demo:** https://youtu.be/6vRI1otiv28
- **Codex `/feedback` Session ID:** Enter directly in the Devpost form; do not publish it in the repository.

## Project description

### Inspiration

I’m Andrei Zakharov, an SEO and digital project specialist and applied AI workflow builder with over thirteen years of experience. I’m fully paralysed. Codex doesn’t replace my expertise—it makes more of it executable, reducing physical repetition and freeing more of my capacity for strategy, judgment, and creative work.

That experience also makes correction work unusually visible to me. Unsafe automation does not remove work; it creates review, risk, and cleanup. In a website migration, redesign, or large cleanup, the most dangerous failure may happen before a redirect breaks: an incomplete set of URLs can look complete, and a confident recommendation can erase a page that still carries traffic, links, or business history.

ProofRank turns that problem into an enforceable product rule: **no whole-site graph conclusions until the declared starting scope is bound to evidence and every active in-scope page has usable HTML.**

### What it does

For a site owner, ProofRank is a technical inspection before renovating an old website. It helps the owner ask an SEO specialist, agency, or developer to prove that valuable pages have not disappeared from the plan.

For a technical team, ProofRank is a local, read-only Codex plugin that:

- imports already-exported GSC, GA4, WordPress, crawler, generic inventory, sitemap, and saved-HTML evidence;
- normalizes URL identities without discarding source provenance;
- verifies that the declared starting scope matches the exact inventory, cache, and sitemap bodies by SHA-256;
- verifies full HTML for every active graph-eligible identity inside that declared scope;
- reports broken, noindex, noncanonical, schema, duplicate, reachability, overlap, and link-opportunity evidence conservatively;
- emits a machine-readable `decision.json` contract with `WITHHOLD` or `READY_FOR_HUMAN_REVIEW`.

The public comparison demonstrates the false-green that motivated the product:

- **Incomplete case:** only 7 of 11 expected source identities are present, so the source gate fails and four identities remain unclassified. Yet all seven observed active pages have usable HTML (`7/7`, 100%), so the HTML gate passes. The final result is still `WITHHOLD`.
- **Complete case:** all 11 expected identities are present. One confirmed 404 is classified outside the active denominator, all 10 active pages have usable HTML (`10/10`, 100%), and the result becomes `READY_FOR_HUMAN_REVIEW`.

This is the product’s central value: **100% of what was observed is not proof that everything important was observed.**

`READY_FOR_HUMAN_REVIEW` never means “deploy.” The contract always contains `live_change_authorized=false`. With the optional `--gate-exit-code`, a separate workflow receives exit code `2` for `WITHHOLD` and `0` for ready-for-review; normal input or runtime failures remain ordinary errors.

### How we built it

ProofRank has four cooperating layers:

1. deterministic, standard-library Python tools for offline export validation, URL normalization, provenance, source bindings, HTML parsing, graph analysis, and portable JSON/CSV/Markdown output;
2. a Codex Skill that makes the safe workflow and decision boundaries reusable;
3. a Guarded Release Contract in `decision.json`, with stage results, blocker codes, unclassified counts, evidence hashes, and a deterministic optional CLI signal;
4. a dependency-free dashboard that starts with an owner/release explanation and then exposes the technical evidence ledger.

No API key or third-party Python package is required for the demo. The public adapters read files the user has already exported; they do not perform OAuth, call live Google or CMS APIs, control a crawler, or write to production.

### How Codex and GPT-5.6 were used

ProofRank grew from lessons in earlier private workflows built with previous Codex models. During Build Week, I used GPT-5.6 in Codex at the Ultra reasoning level to challenge the first design against sanitized migration evidence and turn those lessons into a portable public product.

That review exposed the false-completeness flaw: a perfect `7/7` observed-HTML result could hide four missing source identities. Codex then helped implement and test:

- separate declared-scope and active-HTML gates;
- `expected_normalized_identities` and an explicit unclassified count;
- terminal-URL handling, including the confirmed 404 outside the active denominator;
- offline GSC, GA4, WordPress, crawler, sitemap, and inventory adapters;
- `decision.json`, stable blocker codes, evidence hashes, and `--gate-exit-code`;
- the false-green comparison, owner/release dashboard, plugin documentation, regression tests, CI, secret scanning, and visual QA.

Deterministic Python calculates the facts. Codex follows the Skill, explains what the evidence supports, and never manufactures permission for a live change.

### Evidence beyond the synthetic fixture

The public fixture contains 11 synthetic identities so anyone can reproduce the behavior without exposing clients or credentials. It is intentionally small for inspection and is not presented as a scale benchmark. Sanitized aggregate evidence from two separate private projects shows where the rule matters at real operational scale:

Both projects began as long-lived WordPress estates with content history dating to 2013 and legacy PHP 5.6 / MySQL 5.7 stacks. Their separate platform modernization establishes the old-site-rescue use case; it is not presented as a capability of public ProofRank.

- **TorreviejaTour:** 3,598 migration paths were checked; zero of 3,090 previously successful paths became non-200. A separate active-site graph contained 3,141 known URLs and 3,137 usable HTML pages (`99.872652%`), which still does not satisfy ProofRank’s strict 100% topology gate.
- **Velas Purpuras / Alye Parusa:** a seven-language migration initially had an apparently complete `1,807/1,807` gate. Full reconciliation expanded the source union to 11,172 normalized identities. Even with usable HTML for all `5,376/5,376` active canonical pages, source readiness remained yellow and the crawl frontier remained open, so whole-site graph claims were withheld.

Across these two separate scopes, `8,513` usable HTML pages were analyzed (`3,137 + 5,376`). This derived aggregate is operational context, not a count of unique URLs across one combined site and not a public ProofRank benchmark. The `11,172` URL identities and `3,598` migration paths are different measures and are deliberately not added together.

In a **separate private deployment workflow**, not in public ProofRank, output validation later caught a static-cache-path defect: only `19/442` language pages were green and 1,522 invalid alternate emissions remained. That workflow automatically restored all three touched files. After the fix it passed `442/442` pages with zero invalid emissions. This incident shaped ProofRank’s read-only release contract, but ProofRank did not apply or roll back those live changes.

The public repository contains only synthetic fixtures and sanitized aggregates. It excludes raw URLs, credentials, analytics exports, backups, private connectors, and production write logic. The private artifacts are identified by hashes in `validation/real_world_evidence.json`; the aggregates are not claimed to be independently reproducible public benchmarks.

No controlled time benchmark exists yet, so the submission makes no quantified time-saving claim. The demonstrated automation is export joining, URL normalization, deduplication, provenance preservation, coverage checking, and evidence packaging. Access collection, crawling, expert URL decisions, implementation, and monitoring remain outside that claim.

### Challenges

- Distinguishing “every observed page has HTML” from “the declared starting scope is fully accounted for.”
- Generalizing private operational lessons without leaking private data.
- Classifying terminal URLs without hiding unresolved errors from the active denominator.
- Giving owners a plain-language stop/proceed explanation while preserving a rigorous technical evidence ledger.
- Making an installable, testable developer tool that judges can run without credentials or rebuilding.

### Accomplishments

- A working Codex plugin and reusable Skill.
- A one-command false-green comparison: source `7/11` fails while active HTML `7/7` passes, producing `WITHHOLD`; source `11/11` plus active HTML `10/10` and one confirmed 404 produces `READY_FOR_HUMAN_REVIEW`.
- A machine-readable Guarded Release Contract and deterministic optional exit codes `2/0`.
- Offline adapters that preserve provenance and bind exact inputs by SHA-256.
- Conservative evidence states: `confirmed`, `candidate`, and `withheld`.
- A self-contained owner/technical dashboard, reproducible fixtures, automated tests, multi-version CI, and secret checks.

### What we learned

Agents become more useful when uncertainty is part of the output contract. The right denominator is a product feature: 100% HTML coverage can be a false green if the declared starting scope is incomplete. A safe workflow must bind and reconcile the declared scope first, prove active content second, and keep human authorization outside both gates.

### What’s next

Next steps are additional export dialects, snapshot comparison, team policy profiles, and portable evidence packs. A controlled benchmark will compare analyst time on repeated audits; until then, time savings remain a planning model rather than a measured claim. Any future authenticated connector or production action would be a separately secured capability, not an implied feature of today’s offline, read-only plugin.

### Why it matters

- **Technical implementation:** deterministic tools, exact input bindings, two independent gates, a versioned decision contract, regression tests, and reproducible local artifacts.
- **Design:** an owner-first release explanation leads into the complete technical evidence ledger.
- **Potential impact:** fewer valuable pages lost and fewer correction cycles before a human approves migration or cleanup work.
- **Quality of idea:** ProofRank can refuse an unsupported site-wide claim even when the observed subset looks perfect.

Human review is deliberate. Cannibalization, merge, redirect, canonical, `noindex`, and content choices depend on intent, backlinks, business role, and history. ProofRank supplies auditable evidence; it does not make or authorize the live change.

## Technologies

Codex, GPT-5.6, Codex Skills, Codex Plugins, Python, JavaScript, HTML, CSS, JSON, CSV, XML, Playwright, GitHub Actions, SEO, Workflow Automation.

## Testing instructions

The fastest path requires no rebuild, login, API key, or network request:

1. Open the [false-green demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html). Confirm declared-scope identities `7/11` fail, usable active HTML `7/7` passes, four identities are unclassified, and the decision is `WITHHOLD`.
2. Open the [complete demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html). Confirm declared-scope identities `11/11`, one confirmed 404, usable active HTML `10/10`, and `READY_FOR_HUMAN_REVIEW`.
3. In both cases confirm `live_change_authorized=false`.

To regenerate both states with Python 3.10+:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

Open:

```text
plugins/proofrank/demo-output/incomplete/dashboard.html
plugins/proofrank/demo-output/complete/dashboard.html
```

Inspect the matching `decision.json` file in each directory. To make the result usable as a deterministic external read-only gate, rerun `site_graph_audit.py` with `--gate-exit-code`: the incomplete case returns `2`; the complete case returns `0`.

To run the full portable verification suite:

```bash
python scripts/verify.py
```

See [INTEGRATIONS.md](INTEGRATIONS.md) for accepted offline exports and [JUDGES.md](JUDGES.md) for the shortest evaluation path.
