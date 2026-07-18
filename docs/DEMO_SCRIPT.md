# ProofRank demo script — target 2:35

## 0:00–0:20 — Problem

“SEO audits are full of plausible recommendations. The risk is acting on a partial crawl as if it were complete. ProofRank is an evidence-first Codex plugin that tells a team what the site graph proves, what is only a candidate, and what must be withheld.”

**Show:** repository README and one-line architecture.

## 0:20–0:45 — Run the project

“The demo uses eleven fully synthetic pages and requires no API key or third-party Python package.”

**Show:** run `python plugins/proofrank/skills/audit-site-graph/scripts/run_demo.py`, then open the generated dashboard.

## 0:45–1:20 — Working result

“ProofRank parsed every saved page, passed the 95-percent completeness gate, and produced twenty evidence items. It found a broken internal link, a noindex target, noncanonical links, orphan and unreachable candidates, malformed schema, a deep page, a cautious topic conflict, and internal-link opportunities.”

**Show:** overview metrics, finding bars, and coverage gate.

## 1:20–1:48 — Evidence interaction

“The dashboard is not a screenshot. I can filter to high-priority findings, search by URL or evidence, and open a row to inspect its exact basis and safety status.”

**Show:** Evidence tab, High filter, open one finding, close the drawer, then Pages tab.

## 1:48–2:08 — Safety boundary

“This audit authorizes no live change. If the crawl is incomplete, graph-level claims are withheld. The static report also strips local input paths and loads no analytics or external scripts.”

**Show:** decision-boundary panel and Method tab.

## 2:08–2:35 — Codex and GPT-5.6

“Using GPT-5.6 in Codex, I generalized a private, site-specific workflow into this portable plugin, refactored the engine, designed the evidence policy, generated the synthetic fixture, built the dashboard, wrote tests, ran OpenAI’s plugin and Skill validators, scanned for secrets, and tested desktop and mobile behavior. Deterministic Python computes the facts; Codex provides the safe workflow and expert interpretation around them.”

**Show:** plugin manifest, Skill, test success, then return to the final dashboard frame.

## Recording checklist

- Keep the final video below 3:00.
- Record at 1440p or 1080p with readable terminal text.
- Use English narration or add accurate English subtitles.
- Mention both Codex and GPT-5.6 in the audio.
- Upload as a public YouTube video, not unlisted or private.
- Do not show local private paths, browser accounts, credentials, or the private case-study data.
