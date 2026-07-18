# Judge testing guide

ProofRank can be evaluated without rebuilding it, creating an account, or providing credentials.

## Fastest path: bundled interactive demo

1. Download `showcase/proofrank-demo.html`.
2. Open it in a modern desktop browser.
3. Confirm the headline values: 11 known URLs, 100% HTML coverage, 20 evidence items, and 5 high-priority items.
4. Open **Evidence**, filter severity to **high**, and select any row to inspect its source evidence and status.
5. Open **Method** to inspect the coverage gate and decision boundary.

The HTML is a self-contained static artifact. It performs no network request, loads no external script, and contains no local input paths.

## Reproduce the demo

Requirements: Python 3.10+ on Windows, macOS, or Linux. No package installation is required.

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

Open `plugins/proofrank/demo-output/dashboard.html`.

## Verify the repository

```bash
python scripts/verify.py
```

This runs the unit tests, regenerates the demo in a temporary directory, validates the dashboard's public-data boundary, checks required manifest fields and assets, and scans text files for common secret formats.

## Install in Codex

Add the repository as a plugin marketplace source:

```bash
codex plugin marketplace add OWNER/REPOSITORY
```

Install **ProofRank** from the Plugins Directory, start a new task, and invoke `$audit-site-graph`. The bundled demo remains the recommended zero-credential evaluation path.

## Supported input

- URL inventory: `.json`, `.csv`, `.txt`, `.xml`, or `.xml.gz`.
- Saved page cache: JSON records containing URL and HTML.
- Sitemap: local XML/XML.GZ files or approved network fetches.
- Optional analytics evidence: finalized page/query CSV or JSON exports.

Network crawling is disabled unless both `--crawl` and `--allow-network` are supplied. The Skill still requires explicit scope approval and never authorizes CMS or production writes.
