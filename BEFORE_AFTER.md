# Build Week development boundary

ProofRank builds on lessons from a private, domain-specific SEO workflow. This repository contains the new, portable extension created during the OpenAI Build Week submission period.

## Prior work

- A private TorreviejaTour workflow used local scripts and saved operational data to inspect one multilingual WordPress portal.
- The private project contained site-specific paths, vocabulary, analytics exports, credentials, backups, and production runbooks.
- That private project is not included in this repository and is not the submitted artifact.

## Build Week extension

- Generalized the deterministic engine beyond one domain.
- Added configurable brand-term exclusion.
- Rewrote the report and Skill for portable English-language use.
- Created the installable `proofrank` plugin and GitHub marketplace structure.
- Added a fully synthetic public demo dataset.
- Added a dependency-free interactive evidence dashboard.
- Added portable verification, secret scanning, documentation, and an explicit safety boundary.
- Preserved separate evidence states: `confirmed`, `candidate`, and `withheld`.

## Evidence

- The clean repository commit history records the competition-period implementation.
- The Devpost submission will include the Codex `/feedback` Session ID for the task where the core public product was assembled.
- The demo and unit tests run without private services or credentials.
