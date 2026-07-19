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
- Preserved separate evidence states: `confirmed`, `candidate`, and `withheld`.
- Andrei used GPT-5.6 at the Ultra reasoning level to help build and test a one-command comparison. Deterministic Python derives a 7-of-11 partial cache from the same synthetic fixture, emits `graph_claims_withheld`, and proves that unsupported graph conclusions are suppressed.
- In the demo, Codex with GPT-5.6 follows the Skill’s safe local workflow and explains the result; deterministic Python calculates the facts.

## Evidence

- The clean repository commit history records the competition-period implementation.
- The Devpost submission will include the Codex `/feedback` Session ID for the task where the core public product was assembled.
- The demo and unit tests run without private services or credentials.
