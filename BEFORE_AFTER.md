# Build Week development boundary

ProofRank builds on lessons from an earlier private, domain-specific SEO workflow created with previous Codex models. This repository contains the new, portable extension created during the OpenAI Build Week submission period.

## Prior work

- A private TorreviejaTour workflow built with previous Codex models used local scripts and saved operational data to inspect one multilingual WordPress portal.
- The private project contained site-specific paths, vocabulary, analytics exports, credentials, backups, and production runbooks.
- That earlier private workflow processed 3,137 active pages returning HTTP 200 with 99.87% HTML coverage and informed ProofRank’s design. It is not included in this repository and is not the submitted artifact.

## Build Week extension

- Generalized the deterministic engine beyond one domain.
- Added configurable brand-term exclusion.
- Rewrote the report and Skill for portable English-language use.
- Created the installable `proofrank` plugin and GitHub marketplace structure.
- Added a fully synthetic public demo dataset.
- Added a dependency-free interactive evidence dashboard.
- Added portable verification, secret scanning, documentation, and an explicit safety boundary.
- Added credential-free offline import for saved GSC, GA4, WordPress, crawler, and generic inventory exports.
- Added per-source SHA-256 provenance and an explicit source-universe declaration instead of inferring completeness from the files that happened to be supplied.
- Split the final safety gate into source-universe completeness and observed HTML-graph completeness.
- Added an optional expected normalized-identity count, explicit unclassified count, and a false-green fixture in which all observed active HTML is present (`7/7`) while the known source universe is still incomplete (`7/11`).
- Added a machine-readable Guarded Release Contract: `WITHHOLD` / optional exit code `2`, or `READY_FOR_HUMAN_REVIEW` / exit code `0`. Both states keep `live_change_authorized=false`.
- Added an owner-facing release view that explains what is protected, what remains unknown, and the next safe action before exposing the technical evidence ledger.
- Corrected sitemap parsing so image, video, and news extension locations cannot become page identities.
- Added sanitized aggregate validation from two private operational programs, including the final 11,172-identity Velas source union, the 5,376/5,376 false-green graph result, and the separate guarded apply/automatic-rollback lesson; added a 10,000-row regression and GitHub Actions verification across Python 3.10, 3.12, and 3.13.
- Preserved separate evidence states: `confirmed`, `candidate`, and `withheld`.
- Andrei used GPT-5.6 at the Ultra reasoning level to challenge the first design against sanitized migration evidence. The key flaw it exposed was that `100%` of observed HTML can still hide an incomplete source universe. Codex then helped implement the separate identity-count gate, terminal-URL semantics, Guarded Release Contract, strict tests, false-green demo, and owner-facing decision.
- In the demo, deterministic Python calculates the facts and exit state; Codex with GPT-5.6 follows the Skill’s safe workflow, explains the evidence, and never authorizes a live change.

## Evidence

- The clean repository commit history records the competition-period implementation.
- [BUILD_LOG.md](BUILD_LOG.md) records dated milestones and the exact prior-work boundary.
- The Devpost submission will include the Codex `/feedback` Session ID for the task where the core public product was assembled.
- The demo and unit tests run without private services or credentials.
