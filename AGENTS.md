# ProofRank agent guidance

## Goal

Keep ProofRank a portable, read-only, evidence-first Codex plugin. Optimize for reproducible audits, clear uncertainty labels, safe demoability, and a reviewer-friendly product experience.

## Layout

- `plugins/proofrank/.codex-plugin/plugin.json`: plugin manifest.
- `plugins/proofrank/skills/audit-site-graph/`: reusable Codex skill.
- `plugins/proofrank/demo/`: synthetic, public-safe fixture.
- `scripts/verify.py`: repository verification.

## Commands

Run the demo:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py
```

Run unit tests:

```bash
python plugins/proofrank/skills/audit-site-graph/scripts/test_site_graph_audit.py
```

Run the full local verification:

```bash
python scripts/verify.py
```

## Safety and scope

- Never add real credentials, `.env` files, private analytics exports, medical data, customer data, or production backups.
- Keep network access disabled by default. A broad live crawl requires explicit scope approval.
- Do not add CMS writes, sitemap submission, indexing actions, redirects, deletion, `noindex`, or production mutation to the audit flow.
- Treat similarity, overlap, and zero-inbound signals as candidates unless the completeness and evidence gates pass.
- Keep all demo data synthetic.

## Done when

- Unit tests and `scripts/verify.py` pass.
- Plugin and skill validators pass.
- The demo generates a dependency-free dashboard with no local paths or secrets embedded.
- README commands work from the repository root.
- The diff contains no unrelated or generated private files.
