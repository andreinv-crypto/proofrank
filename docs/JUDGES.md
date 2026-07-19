# Judge testing guide

ProofRank can be evaluated without rebuilding it, creating an account, or providing credentials.

## Fastest path: bundled evidence-gate comparison

1. Open the live [incomplete-coverage demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-incomplete-demo.html) in a modern desktop browser.
2. Confirm 11 known URLs, 7 parsed pages, 63.64% coverage, `Graph claims: Withheld`, and an explicit `graph claims withheld` evidence row.
3. Confirm that orphan, unreachable-from-home, and internal-link-opportunity conclusions are not promoted from the partial graph.
4. Open the live [complete demo](https://andreinv-crypto.github.io/proofrank/showcase/proofrank-demo.html) and confirm 11 known URLs, 100% coverage, and `Graph claims: Enabled`.
5. Open **Evidence**, filter severity to **high**, and select a row to inspect its source evidence and status.
6. Open **Method** to inspect the coverage gate and decision boundary.

Both HTML files are self-contained static artifacts. They perform no network request, load no external script, and contain no local input paths.

## Reproduce the demo

Requirements: Python 3.10+ on Windows, macOS, or Linux. No package installation is required.

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

Open `plugins/proofrank/demo-output/dashboard.html`.

To reproduce both states in one run:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py --scenario both
```

Open `plugins/proofrank/demo-output/incomplete/dashboard.html`, then `plugins/proofrank/demo-output/complete/dashboard.html`.

## Verify the repository

```bash
python scripts/verify.py
```

This runs the unit tests, regenerates the demo in a temporary directory, validates the dashboard's public-data boundary, checks required manifest fields and assets, and scans text files for common secret formats.

## Install in Codex

Add the repository as a plugin marketplace source:

```bash
codex plugin marketplace add OWNER/REPOSITORY
codex plugin add proofrank@proofrank-marketplace
```

Install **ProofRank** from the Plugins Directory, start a new task, and invoke `$audit-site-graph`. The bundled demo remains the recommended zero-credential evaluation path.

## Supported input

- URL inventory: `.json`, `.csv`, `.txt`, `.xml`, or `.xml.gz`.
- Saved page cache: JSON records containing URL and HTML.
- Sitemap: local XML/XML.GZ files or approved network fetches.
- Optional analytics evidence: finalized page/query CSV or JSON exports.

Network crawling is disabled unless both `--crawl` and `--allow-network` are supplied. The Skill still requires explicit scope approval and never authorizes CMS or production writes.
