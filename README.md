<p align="center"><img src="plugins/proofrank/assets/logo.svg" width="150" alt="ProofRank logo"></p>

# ProofRank

**When evidence is incomplete, ProofRank refuses to guess.**

[Open the complete interactive demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html) · [Open the incomplete-coverage demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html)

![ProofRank evidence-first dashboard](plugins/proofrank/assets/screenshot-dashboard.png)

ProofRank turns URL inventories, saved sitemaps, and saved HTML caches into a reproducible graph audit. It separates directly observed facts, cautious candidates, and conclusions that the available coverage cannot support.

The result is not another generic SEO content generator. ProofRank is a read-only safety layer for SEO and web operations teams: it separates confirmed findings from candidates and withholds site-wide conclusions when crawl coverage is incomplete, before anyone touches a live site.

The same evidence-gate pattern can protect other AI workflows that act on incomplete data.

ProofRank grew from lessons in an earlier private workflow built with previous Codex models. Its creator, Andrei Zakharov, has over 13 years of experience building and growing online projects across marketing, SEO, and automation. He is fully paralysed, so every click and correction has a physical cost. Codex helps him turn experience and new ideas into working software with less physical effort and more creative freedom. That sharpened a universal product principle: automation should reduce correction work, not create more.

## What it detects

- crawl and sitemap coverage;
- internal links and click depth;
- orphan and unreachable-page candidates;
- broken, noindex, and noncanonical internal-link targets;
- JSON-LD syntax and visible-content mismatches;
- exact and near-duplicate content candidates;
- cautious title/H1/query overlap candidates;
- contextual internal-link opportunities.

## Architecture

ProofRank combines three layers:

1. **Deterministic Python engine** for normalization, parsing, graph construction, evidence labels, and portable JSON/CSV/Markdown outputs.
2. **Codex Skill** for safe input selection, completeness gates, interpretation, and action boundaries.
3. **Dependency-free dashboard** for fast human review without uploading audit data to a third party.

No API key or third-party Python package is required for the bundled demo.

## Run the synthetic demo

From the repository root:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

Open:

```text
plugins/proofrank/demo-output/dashboard.html
```

The fixture is fully synthetic and intentionally contains broken links, a noindex target, a noncanonical URL, an orphan candidate, malformed JSON-LD, and duplicate content.

To reproduce the central evidence-gate comparison in one command:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

Open `plugins/proofrank/demo-output/incomplete/dashboard.html` first, then `plugins/proofrank/demo-output/complete/dashboard.html`. The same 11-URL fixture moves from 63.64% coverage with graph claims withheld to 100% coverage with the gate enabled.

## Run on saved site data

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/site_graph_audit.py \
  --site "https://example.com/" \
  --inventory "inventory.csv" \
  --page-cache "page_cache.json" \
  --sitemap "sitemap.xml" \
  --brand-term "Example" \
  --output-dir "out"

python plugins/proofrank/skills/audit-site-graph/scripts/render_dashboard.py \
  --audit "out/audit.json" \
  --output "out/dashboard.html"
```

See the bundled Skill references for accepted input shapes and evidence rules.

## Install as a Codex plugin

For local testing, add this repository as a marketplace source:

```bash
codex plugin marketplace add /absolute/path/to/proofrank
```

After the GitHub repository is published, the equivalent command is:

```bash
codex plugin marketplace add OWNER/REPOSITORY
codex plugin add proofrank@proofrank-marketplace
```

Then open the Plugins Directory in the ChatGPT desktop app or `/plugins` in Codex CLI, install **ProofRank**, and start a new task. Invoke the bundled skill explicitly with `$audit-site-graph` or describe the desired read-only site audit.

## Safety model

- Local reads and local report writes by default.
- Network crawling requires both `--crawl` and `--allow-network`.
- Live crawling still requires explicit scope approval.
- No CMS, hosting, analytics, Search Console, sitemap, redirect, canonical, or content writes.
- No URL deletion, merge, redirect, or noindex recommendation from similarity alone.
- The static dashboard embeds only sanitized audit results, not local input paths.

## Verify

```bash
python scripts/verify.py
```

The verification runs unit tests, generates the demo in a temporary folder, validates the public dashboard boundary, checks the manifest shape, and scans for common secret formats.

## OpenAI Build Week 2026

During the OpenAI Build Week submission period, Codex with GPT-5.6 helped generalize and package those earlier lessons as ProofRank. Andrei used GPT-5.6 at the Ultra reasoning level while implementing and testing the reproducible incomplete-coverage extension shown in the demo. Deterministic Python calculates the audit facts; Codex follows the Skill’s safe local workflow, explains the result, and helps run validation. The project shows how an agent can combine deterministic tools, explicit uncertainty, and a coherent user experience on a real operational problem.

**Track:** Work & Productivity.

The public repository contains only synthetic demo data. An earlier private workflow processed 3,137 active pages returning HTTP 200 with 99.87% HTML coverage and informed ProofRank’s design. That private project is not part of this submission; credentials, analytics exports, backups, and customer data are excluded.

See [BEFORE_AFTER.md](BEFORE_AFTER.md) for the boundary between prior domain-specific work and the Build Week extension.

Submission materials: [Devpost draft](docs/DEVPOST_SUBMISSION.md) · [under-three-minute demo script](docs/DEMO_SCRIPT.md) · [judge testing guide](docs/JUDGES.md).

## License

MIT © 2026 Andrei Zakharov.
