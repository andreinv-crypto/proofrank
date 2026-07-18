# ProofRank demo script — final 2:49

English narration, approximately 338 words. Final local export: 2:49.

## 0:00–0:18 — Founder context

**Show:** A clean founder card. Use the ProofRank logo and Andrei’s name; no portrait or medical imagery.

**On screen:**

```text
Andrei Zakharov
SEO & web operations
Every click has a physical cost
```

**Narration:**

> I’m Andrei Zakharov. I’m fully paralysed, so every click and repetitive computer task has a physical cost. I’ve worked in SEO and web operations for years. Codex helps me turn that judgement into repeatable software with fewer manual steps.

## 0:18–0:24 — Narration disclosure

**Show:** The dashboard appears behind a small disclosure card.

**On screen:**

```text
AI-assisted English narration
Script reviewed and approved by Andrei Zakharov
```

**Narration:**

> This video uses AI-assisted English narration, reviewed and approved by me.

## 0:24–0:36 — The risk

**Show:** `11 known URLs → 7 parsed → 64% coverage`. A premature `ORPHAN` label is stopped by the coverage gate.

**On screen:**

```text
Partial crawl ≠ complete evidence
Confidence is not evidence
```

**Narration:**

> An AI can sound certain after seeing only part of a website. On a live site, a partial crawl can trigger risky redirect or noindex decisions. Confidence is not evidence.

## 0:36–0:48 — Product promise

**Show:** ProofRank dashboard, then the three evidence states.

**On screen:**

```text
CONFIRMED · CANDIDATE · WITHHELD
When evidence is incomplete, ProofRank refuses to guess.
```

**Narration:**

> ProofRank is a read-only Codex plugin that labels conclusions confirmed, candidate, or withheld. When evidence is incomplete, ProofRank refuses to guess.

## 0:48–1:08 — Meaningful Codex and GPT-5.6 use

**Show:** The exact Codex task, the Skill, the deterministic engine run, and the generated dashboard.

```text
Use $audit-site-graph to audit the bundled synthetic dataset.
Keep the run read-only.
```

**On screen:**

```text
Codex + GPT-5.6
$audit-site-graph
Synthetic data · Read-only
```

**Narration:**

> Inside Codex, I invoke the audit-site-graph skill on a synthetic eleven-page website. Using GPT-5.6, Codex chooses the safe local workflow, runs the deterministic Python engine, checks completeness, and explains the result. No API key or rebuild is required.

## 1:08–1:29 — Incomplete evidence

**Show:** Open the incomplete-cache result. Highlight `64%`, the failed gate, and a `WITHHELD` finding.

**On screen:**

```text
64% HTML coverage
COVERAGE GATE: FAILED

Orphan conclusion: WITHHELD
Graph-level opportunities: SUPPRESSED
```

**Narration:**

> First, the cache covers only sixty-four per cent of known URLs. The gate fails. A page with no observed inbound links may look orphaned, but the graph is incomplete. ProofRank marks that conclusion withheld and suppresses graph-level opportunities. It stops where the evidence stops.

## 1:29–1:51 — Complete evidence

**Show:** Switch to the complete-cache result. Coverage changes to `100%`; open Evidence, select High, and open the evidence drawer.

**On screen:**

```text
100% HTML coverage
COVERAGE GATE: PASSED

Evidence is now actionable for review
```

**Narration:**

> Now I load the complete cache. Coverage reaches one hundred per cent, the homepage is parsed, and the gate passes. ProofRank surfaces a confirmed broken link, a noindex target, malformed structured data, and cautious orphan candidates. I filter high-priority findings and open the evidence drawer.

## 1:51–2:05 — Safety boundary

**Show:** Method tab and safety panel. Highlight `READ-ONLY`, `LOCAL`, and `NO EXTERNAL REQUESTS`.

**On screen:**

```text
READ-ONLY
No live-site writes
No external scripts
Local paths removed
```

**Narration:**

> The dashboard is interactive and self-contained. It strips local paths, loads no external scripts, and authorises no CMS, redirect, content, or other live-site write.

## 2:05–2:29 — Build Week implementation

**Show:** Architecture, then short cuts of the Skill, plugin manifest, passing tests, validators, and mobile dashboard.

```text
Saved site data
↓
Deterministic Python engine
↓
Evidence policy
↓
Codex interpretation
↓
Interactive dashboard

Tests passed · Validators passed · Secret scan passed
```

**Narration:**

> During Build Week, Codex with GPT-5.6 helped generalise my private workflow into an installable plugin: refactoring the engine, designing the evidence policy, generating safe fixtures, building the interface, writing tests, running official validators, scanning for secrets, and checking desktop and mobile behaviour.

## 2:29–2:49 — Real scale and close

**Show:** Sanitised case card, then ProofRank logo and final dashboard frame.

**On screen:**

```text
PUBLIC DEMO
11 synthetic URLs

PRIVATE OPERATIONAL CASE
3,137 URLs
99.87% parsed coverage

When evidence is incomplete,
ProofRank refuses to guess.
```

**Narration:**

> The public demo is synthetic. The private case covered three thousand one hundred and thirty-seven URLs with ninety-nine point eight seven per cent parsed coverage. ProofRank gives teams inspectable evidence—and gives AI the discipline to stop. When evidence is incomplete, ProofRank refuses to guess.

## Recording checklist

- Keep the final video below 3:00 and target 1920×1080 at 30 fps.
- Use the approved first-person phrase `I’m fully paralysed`.
- Burn accurate English subtitles into the final export.
- Keep the AI-assisted narration disclosure visible and audible.
- Mention both Codex and GPT-5.6 in the audio.
- Show only synthetic public data; do not expose private paths, accounts, or case-study inputs.
- Upload as a public YouTube video only after Andrei approves the final local MP4.
