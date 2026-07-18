# OpenAI Build Week — Devpost submission draft

## Required fields

- **Project name:** ProofRank
- **Track:** Work and productivity
- **Tagline:** Evidence-first site graph intelligence for teams that need safer SEO decisions.
- **Repository URL:** `[ADD AFTER GITHUB PUBLICATION]`
- **Public YouTube demo:** `[ADD AFTER VIDEO UPLOAD]`
- **Codex /feedback Session ID:** `[ADD FROM THE CORE BUILD TASK]`

## Project description

### Inspiration

Large websites accumulate broken internal links, orphan pages, duplicate content, schema defects, and conflicting search intent. The dangerous part is not finding possible problems; it is turning incomplete crawl data into confident live-site actions. SEO teams need a fast way to see what the evidence supports, what is only a candidate, and what cannot yet be concluded.

### What it does

ProofRank is a read-only Codex plugin that converts saved URL inventories, sitemaps, and HTML caches into a reproducible site graph audit. It detects coverage gaps, click depth, orphan and unreachable-page candidates, broken/noindex/noncanonical targets, schema problems, duplicate content, cautious topic conflicts, and contextual internal-link opportunities.

Every finding carries an evidence status. Graph-level conclusions are withheld until coverage clears an explicit completeness gate. A dependency-free interactive dashboard lets a reviewer filter the evidence, inspect individual findings, and understand the decision boundary before anyone changes a live site.

### How we built it

ProofRank has three layers:

1. a deterministic, standard-library Python engine for parsing, normalization, graph analysis, and portable JSON/CSV/Markdown artifacts;
2. a Codex Skill that selects safe inputs, enforces coverage gates, and interprets the evidence without authorizing live changes;
3. a single-file static dashboard that contains sanitized audit results and requires no server, account, analytics, or external JavaScript.

The public demo uses fully synthetic data. The design came from a private, domain-specific workflow for a multilingual travel portal with more than 3,000 normalized URLs, but no private site data, credentials, analytics exports, or local paths are included.

### How Codex and GPT-5.6 were used

Codex with GPT-5.6 helped turn the original domain-specific workflow into a portable product: mapping the reusable architecture, refactoring the engine, authoring the Codex Skill and plugin manifests, generating a synthetic edge-case fixture, building the dashboard, writing tests, running official plugin/skill validators, scanning for secrets, and executing desktop/mobile browser QA.

The model does not manufacture graph facts. Deterministic code calculates coverage and findings; Codex supplies the workflow, safety policy, interpretation, and product experience around that evidence.

### Challenges

- Generalizing a real workflow without leaking private operational data.
- Preventing partial input coverage from producing unsafe graph-level claims.
- Making a judgeable developer tool that works without rebuilding, credentials, or paid APIs.
- Keeping the interface useful on both desktop and mobile while remaining a portable static file.

### Accomplishments

- A working installable Codex plugin with a valid manifest and valid Skill.
- A deterministic demo that produces 20 evidence items across 11 synthetic pages.
- Explicit confirmed/candidate/withheld evidence states and a 95% graph-completeness gate.
- A dependency-free interactive dashboard with filters and evidence details.
- Automated unit, demo, boundary, secret-scan, and browser-interaction checks.

### What we learned

Agents become more trustworthy when uncertainty is part of the output contract. Separating deterministic measurements from model-guided interpretation makes the workflow easier to test, safer to operate, and more useful to experts.

### What's next

Next steps are read-only adapters for crawler exports and Search Console, comparison reports between audit snapshots, configurable evidence policies for larger teams, and an optional hosted viewer that preserves the same no-write safety boundary.

## Technologies

Codex, GPT-5.6, Codex Skills, Codex plugins, Python, HTML, CSS, JavaScript, JSON, CSV, XML, Playwright for QA.

## Testing instructions

The repository contains a pre-generated interactive demo at `showcase/proofrank-demo.html`; download and open it in any modern browser. No rebuilding, login, API key, or network request is required.

To regenerate the same result with Python 3.10+:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

To run the portable verification suite:

```bash
python scripts/verify.py
```

Expected demo headline values: 11 known URLs, 100% HTML coverage, 20 evidence items, and 5 high-priority items.
