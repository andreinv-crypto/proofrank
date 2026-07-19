# OpenAI Build Week — Devpost submission draft

## Required fields

- **Project name:** ProofRank
- **Track:** Work & Productivity
- **Tagline:** When evidence is incomplete, ProofRank refuses to guess.
- **Repository URL:** https://github.com/andreinv-crypto/proofrank
- **Live interactive demo:** https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html
- **Public YouTube demo:** `[ADD AFTER VIDEO UPLOAD]`
- **Codex /feedback Session ID:** `[ADD FROM THE CORE BUILD TASK]`

## Project description

### Inspiration

I’m Andrei Zakharov. For over 13 years, I have built and grown online projects across digital marketing, SEO, and automation. I’m fully paralysed, so every click and correction has a physical cost. Codex helps me turn experience and new ideas into working software with less physical effort and more creative freedom. That same constraint shaped ProofRank: bad automation does not remove work—it creates more review, more risk, and more cleanup. The most dangerous case is an AI turning an incomplete crawl into a confident live-site recommendation.

ProofRank grew from that constraint, but its value is universal: SEO and web operations teams need a fast way to see what the evidence supports, what is only a candidate, and what cannot yet be concluded.

### What it does

ProofRank is a read-only Codex plugin for SEO and web operations teams. It converts saved URL inventories, sitemaps, and HTML caches into a reproducible site graph audit. It detects coverage gaps, click depth, orphan and unreachable-page candidates, broken/noindex/noncanonical targets, schema problems, duplicate content, cautious topic conflicts, and contextual internal-link opportunities.

Every finding carries an evidence status: confirmed, candidate, or withheld. Graph-level conclusions are withheld until coverage clears an explicit completeness gate. A dependency-free interactive dashboard lets a reviewer filter the evidence, inspect individual findings, and understand the decision boundary before anyone changes a live site.

The bundled comparison makes the behaviour visible: the same 11-URL synthetic fixture produces a 63.64% incomplete result that withholds whole-site graph claims, then a 100% result that enables supported findings.

### How we built it

ProofRank has three layers:

1. a deterministic, standard-library Python engine for parsing, normalization, graph analysis, and portable JSON/CSV/Markdown artifacts;
2. a Codex Skill that defines the safe local workflow and evidence boundary for Codex to follow and explain, without authorizing live changes;
3. a single-file static dashboard that contains sanitized audit results and requires no server, account, analytics, or external JavaScript.

The public demo uses fully synthetic data. The design came from an earlier private, domain-specific workflow built with previous Codex models. That workflow processed 3,137 active pages returning HTTP 200 with 99.87% HTML coverage and informed ProofRank’s design. It is not part of this submission. No private URLs, content, credentials, analytics exports, backups, or local paths are included.

### How Codex and GPT-5.6 were used

During the Build Week submission period, Codex with GPT-5.6 helped turn those earlier lessons into a portable product: mapping the reusable architecture, refactoring the engine, authoring the Codex Skill and plugin manifests, generating a synthetic edge-case fixture, building the dashboard, writing tests, running official plugin/skill validators, scanning for secrets, and executing desktop/mobile browser QA.

For the final Build Week extension, Andrei used GPT-5.6 at the Ultra reasoning level while implementing and testing the reproducible incomplete-coverage scenario. Deterministic Python derives a 7-of-11 cache from the same public fixture, emits an explicit `graph_claims_withheld` evidence item, and verifies that orphan, unreachable, and internal-link-opportunity claims are not promoted when the gate fails.

The model does not manufacture graph facts. Deterministic Python calculates coverage and findings; Codex with GPT-5.6 follows the Skill’s safe local workflow, explains the result, and helps run validation.

### Challenges

- Generalizing a real workflow without leaking private operational data.
- Preventing partial input coverage from producing unsafe graph-level claims.
- Making a judgeable developer tool that works without rebuilding, credentials, or paid APIs.
- Keeping the interface useful on both desktop and mobile while remaining a portable static file.

### Accomplishments

- A working installable Codex plugin with a valid manifest and valid Skill.
- A deterministic demo that produces 20 evidence items across 11 synthetic pages.
- Explicit confirmed/candidate/withheld evidence states and a 95% graph-completeness gate.
- A one-command before/after proof: 63.64% coverage with graph claims withheld, then 100% coverage with the gate enabled.
- A dependency-free interactive dashboard with filters and evidence details.
- Automated unit, demo, boundary, secret-scan, and browser-interaction checks.

### What we learned

Agents become more trustworthy when uncertainty is part of the output contract. Separating deterministic measurements from model-guided interpretation makes the workflow easier to test, safer to operate, and more useful to experts.

### What's next

Next steps are read-only adapters for crawler exports and Search Console, comparison reports between audit snapshots, configurable evidence policies for larger teams, and an optional hosted viewer that preserves the same no-write safety boundary. The same evidence-gate pattern can also protect other AI workflows that act on incomplete data.

## Technologies

Codex, GPT-5.6, Codex Skills, Codex plugins, Python, HTML, CSS, JavaScript, JSON, CSV, XML, Playwright for QA.

## Testing instructions

The repository contains two pre-generated interactive demos. Open the [incomplete-coverage demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html) first, then the [complete demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html). No rebuilding, login, API key, or network request is required.

To regenerate the same result with Python 3.10+:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

To regenerate both evidence-gate states:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

To run the portable verification suite:

```bash
python scripts/verify.py
```

Expected complete-demo headline values: 11 known URLs, 100% HTML coverage, 20 evidence items, and graph claims enabled. Expected incomplete-demo values: 11 known URLs, 7 parsed pages, 63.64% HTML coverage, and graph claims withheld.
