#!/usr/bin/env python3
"""Render a dependency-free, local-only ProofRank dashboard from audit.json."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>ProofRank — Evidence-first SEO audit</title>
  <style>
    :root {
      --bg: #07111f;
      --panel: rgba(16, 31, 51, .86);
      --panel-strong: #10233a;
      --line: rgba(163, 188, 217, .15);
      --text: #eef7ff;
      --muted: #9fb1c5;
      --cyan: #56d9d2;
      --cyan-soft: rgba(86, 217, 210, .12);
      --gold: #ffc76a;
      --red: #ff7f87;
      --green: #73e2a7;
      --blue: #77a8ff;
      --shadow: 0 24px 80px rgba(0, 0, 0, .28);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 12% 8%, rgba(60, 149, 192, .22), transparent 34rem),
        radial-gradient(circle at 86% 28%, rgba(86, 217, 210, .12), transparent 30rem),
        linear-gradient(150deg, #07111f 0%, #091827 48%, #07111f 100%);
      font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input, select { font: inherit; }
    button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible {
      outline: 3px solid rgba(86, 217, 210, .55);
      outline-offset: 2px;
    }
    .shell { max-width: 1440px; margin: 0 auto; padding: 20px; }
    .topbar {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      padding: 13px 16px; border: 1px solid var(--line); border-radius: 18px;
      background: rgba(7, 17, 31, .7); backdrop-filter: blur(18px); position: sticky; top: 12px; z-index: 20;
      box-shadow: var(--shadow);
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .mark {
      width: 38px; height: 38px; display: grid; place-items: center; flex: 0 0 auto;
      border-radius: 12px; color: #06151d; font-weight: 900; letter-spacing: -.06em;
      background: linear-gradient(135deg, var(--cyan), #b8fff3); box-shadow: 0 10px 30px rgba(86, 217, 210, .22);
    }
    .brand-name { font-weight: 780; letter-spacing: -.02em; }
    .brand-sub { color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .top-actions { display: flex; align-items: center; gap: 10px; }
    .chip, .ghost-button {
      border: 1px solid var(--line); border-radius: 999px; color: var(--muted); background: rgba(255,255,255,.035);
      padding: 8px 12px; white-space: nowrap;
    }
    .chip strong { color: var(--cyan); font-weight: 700; }
    .ghost-button { cursor: pointer; color: var(--text); }
    .ghost-button:hover { background: var(--cyan-soft); border-color: rgba(86,217,210,.35); }
    .hero {
      display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(300px, .7fr); gap: 20px;
      padding: 64px 6px 28px; align-items: end;
    }
    .eyebrow { color: var(--cyan); font-size: 12px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
    h1 { margin: 12px 0 14px; max-width: 860px; font-size: clamp(38px, 6vw, 76px); line-height: .98; letter-spacing: -.055em; }
    .hero p { max-width: 760px; margin: 0; color: var(--muted); font-size: clamp(16px, 2vw, 20px); }
    .boundary {
      border: 1px solid rgba(86,217,210,.26); border-radius: 18px; background: var(--cyan-soft); padding: 18px;
    }
    .boundary strong { display: block; color: var(--cyan); margin: 7px 0 4px; font-size: 28px; line-height: 1.05; letter-spacing: -.035em; }
    .boundary span { display: block; color: #d9e6f1; font-weight: 700; }
    .boundary p { color: #b8cada; margin: 8px 0 0; }
    .boundary small { display: block; color: var(--muted); margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(163,188,217,.16); }
    .boundary.withheld { border-color: rgba(255,199,106,.45); background: rgba(255,199,106,.1); }
    .boundary.withheld strong { color: var(--gold); }
    .tabs { display: flex; gap: 8px; margin: 22px 0 16px; overflow-x: auto; padding-bottom: 2px; }
    .tab {
      border: 1px solid var(--line); border-radius: 12px; background: rgba(255,255,255,.025); color: var(--muted);
      padding: 10px 14px; cursor: pointer; font-weight: 700;
    }
    .tab[aria-selected="true"] { color: #07111f; background: var(--cyan); border-color: transparent; }
    .panel-view[hidden] { display: none; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
    .card {
      border: 1px solid var(--line); border-radius: 18px; background: var(--panel); box-shadow: var(--shadow);
      padding: 18px; overflow: hidden;
    }
    .metric-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .metric-value { margin-top: 12px; font-size: clamp(28px, 4vw, 46px); font-weight: 790; letter-spacing: -.045em; }
    .metric-note { color: var(--muted); font-size: 13px; margin-top: 4px; }
    .metric-value.good { color: var(--green); }
    .metric-value.warn { color: var(--gold); }
    .grid-2 { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); gap: 14px; margin-top: 14px; }
    .section-title { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 16px; }
    .section-title h2 { margin: 0; font-size: 19px; letter-spacing: -.02em; }
    .section-title p { color: var(--muted); margin: 3px 0 0; font-size: 13px; }
    .coverage-ring {
      width: 160px; aspect-ratio: 1; border-radius: 50%; margin: 8px auto 18px; position: relative;
      display: grid; place-items: center; background: conic-gradient(var(--cyan) var(--coverage), rgba(255,255,255,.07) 0);
    }
    .coverage-ring::after { content: ""; position: absolute; inset: 13px; border-radius: 50%; background: var(--panel-strong); }
    .coverage-ring > div { position: relative; z-index: 1; text-align: center; }
    .coverage-ring strong { display: block; font-size: 32px; letter-spacing: -.04em; }
    .coverage-ring span { color: var(--muted); font-size: 12px; }
    .coverage-ring.withheld { background: conic-gradient(var(--gold) var(--coverage), rgba(255,255,255,.07) 0); }
    .bar-row { display: grid; grid-template-columns: minmax(120px, 1fr) 2fr 42px; gap: 10px; align-items: center; margin: 10px 0; }
    .bar-label { color: #ccdae8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
    .bar-track { height: 8px; background: rgba(255,255,255,.06); border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--blue), var(--cyan)); }
    .bar-count { color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; }
    .fact-row {
      display: grid; grid-template-columns: minmax(150px, 1fr) minmax(150px, .9fr); gap: 14px;
      align-items: start; margin: 10px 0;
    }
    .fact-label { color: #ccdae8; font-size: 13px; }
    .fact-value { color: var(--muted); text-align: right; font-size: 13px; overflow-wrap: anywhere; }
    .source-list { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--line); }
    .source-list h3 { margin: 0 0 3px; font-size: 14px; }
    .source-list > p { margin: 0 0 12px; color: var(--muted); font-size: 12px; }
    .source-row {
      display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center;
      padding: 10px 0; border-top: 1px solid rgba(163, 188, 217, .1);
    }
    .source-row:first-of-type { border-top: 0; }
    .source-name { color: #d8e4ee; overflow-wrap: anywhere; }
    .source-kind { display: block; color: var(--muted); font-size: 11px; }
    .source-state { color: var(--muted); font-size: 12px; text-align: right; }
    .source-state.ready { color: var(--green); }
    .source-state.missing { color: var(--gold); }
    .filters { display: grid; grid-template-columns: minmax(180px, 1fr) 160px 160px; gap: 10px; margin-bottom: 14px; }
    .control {
      width: 100%; border: 1px solid var(--line); border-radius: 12px; background: #0a1929; color: var(--text); padding: 11px 12px;
    }
    .table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 14px; }
    table { width: 100%; border-collapse: collapse; min-width: 820px; }
    th, td { text-align: left; padding: 12px 13px; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); background: #0b1a2a; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; position: sticky; top: 0; }
    tbody tr { cursor: pointer; }
    tbody tr:hover { background: rgba(86,217,210,.055); }
    td { color: #d8e4ee; font-size: 13px; }
    .url { max-width: 340px; overflow-wrap: anywhere; color: #b7cdf0; }
    .evidence { max-width: 460px; color: var(--muted); }
    .badge { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
    .badge-high { color: #ffd4d7; background: rgba(255,127,135,.16); }
    .badge-medium { color: #ffe0a7; background: rgba(255,199,106,.14); }
    .badge-low, .badge-info { color: #bed3ff; background: rgba(119,168,255,.14); }
    .status-confirmed { color: var(--green); }
    .status-candidate { color: var(--gold); }
    .status-withheld { color: var(--muted); }
    .method-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; }
    .step-num { color: var(--cyan); font-weight: 800; font-size: 12px; letter-spacing: .12em; }
    .method-grid h3 { margin: 10px 0 6px; }
    .method-grid p { color: var(--muted); margin: 0; }
    .drawer {
      position: fixed; inset: 0; z-index: 60; display: grid; grid-template-columns: 1fr minmax(320px, 540px);
      background: rgba(0,0,0,.48); backdrop-filter: blur(6px);
    }
    .drawer[hidden] { display: none; }
    .drawer-panel { grid-column: 2; height: 100%; overflow: auto; background: #0b1929; border-left: 1px solid var(--line); padding: 26px; box-shadow: -30px 0 80px rgba(0,0,0,.3); }
    .drawer-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .drawer h2 { margin: 10px 0 0; overflow-wrap: anywhere; }
    .close { width: 38px; height: 38px; border: 1px solid var(--line); border-radius: 12px; background: transparent; color: var(--text); cursor: pointer; }
    .detail-block { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--line); }
    .detail-block strong { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 7px; }
    .detail-block div { overflow-wrap: anywhere; }
    .empty { color: var(--muted); padding: 28px; text-align: center; }
    .footer { color: var(--muted); font-size: 12px; padding: 28px 4px 12px; display: flex; justify-content: space-between; gap: 20px; }
    @media (max-width: 920px) {
      .hero, .grid-2 { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      .method-grid { grid-template-columns: 1fr; }
      .filters { grid-template-columns: 1fr; }
      .hero { padding-top: 44px; }
    }
    @media (max-width: 560px) {
      .shell { padding: 10px; }
      .topbar { top: 6px; padding: 10px; }
      .brand-sub, .top-actions .chip { display: none; }
      .metrics { grid-template-columns: 1fr; }
      .drawer { grid-template-columns: 1fr; }
      .drawer-panel { grid-column: 1; }
      .footer { flex-direction: column; }
      .fact-row { grid-template-columns: minmax(0, 1fr) minmax(108px, .8fr); gap: 10px; }
    }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true">PR</div>
        <div>
          <div class="brand-name">ProofRank</div>
          <div class="brand-sub">Evidence-first site graph intelligence</div>
        </div>
      </div>
      <div class="top-actions">
        <span class="chip"><strong>Read-only</strong> by default</span>
        <button class="ghost-button" id="copySummary">Copy summary</button>
      </div>
    </header>

    <section class="hero">
      <div>
        <div class="eyebrow">Pre-migration evidence gate</div>
        <h1>Don't lose valuable pages when an old site moves.</h1>
        <p>ProofRank reconciles saved SEO and CMS evidence, proves what is actually known, and tells the team to stop when an apparently complete crawl is not enough.</p>
      </div>
      <div class="boundary" id="boundaryCard">
        <div class="eyebrow">Owner / release view</div>
        <strong id="releaseDecision">WITHHOLD</strong>
        <span id="gateHeadline">Decision boundary</span>
        <p id="decisionBoundary"></p>
        <small id="nextAction"></small>
      </div>
    </section>

    <nav class="tabs" aria-label="Dashboard sections">
      <button class="tab" aria-selected="true" data-tab="overview">Overview</button>
      <button class="tab" aria-selected="false" data-tab="findings">Evidence</button>
      <button class="tab" aria-selected="false" data-tab="pages">Pages</button>
      <button class="tab" aria-selected="false" data-tab="method">Method</button>
    </nav>

    <main>
      <section class="panel-view" id="overview">
        <div class="metrics" id="metrics"></div>
        <div class="grid-2">
          <article class="card">
            <div class="section-title"><div><h2>Finding profile</h2><p>Measured signals grouped by type</p></div><span class="chip" id="modeChip"></span></div>
            <div id="findingBars"></div>
          </article>
          <article class="card">
            <div class="section-title"><div><h2>Completeness gates</h2><p>Source universe → observed content graph → final graph</p></div></div>
            <div class="coverage-ring" id="coverageRing"><div><strong id="coverageValue"></strong><span>HTML coverage</span></div></div>
            <div id="coverageNotes"></div>
            <div class="source-list">
              <h3>Declared source universe</h3>
              <p id="sourceSummary"></p>
              <div id="sourceRows"></div>
            </div>
          </article>
        </div>
      </section>

      <section class="panel-view" id="findings" hidden>
        <article class="card">
          <div class="section-title"><div><h2>Evidence ledger</h2><p>Click any row to inspect its source evidence and safety status.</p></div><span class="chip" id="findingTotal"></span></div>
          <div class="filters">
            <label><span class="sr-only"></span><input class="control" id="search" placeholder="Search type, URL, or evidence"></label>
            <select class="control" id="severity" aria-label="Filter by severity"><option value="">All severities</option><option>high</option><option>medium</option><option>low</option><option>info</option></select>
            <select class="control" id="status" aria-label="Filter by status"><option value="">All statuses</option><option>confirmed</option><option>candidate</option><option>withheld</option></select>
          </div>
          <div class="table-wrap"><table><thead><tr><th>Severity</th><th>Status</th><th>Finding</th><th>URL / target</th><th>Evidence</th></tr></thead><tbody id="findingRows"></tbody></table></div>
        </article>
      </section>

      <section class="panel-view" id="pages" hidden>
        <article class="card">
          <div class="section-title"><div><h2>Page inventory</h2><p>Normalized pages with graph and indexability signals</p></div><span class="chip" id="pageTotal"></span></div>
          <div class="table-wrap"><table><thead><tr><th>Depth</th><th>Status</th><th>Lane</th><th>Page</th><th>Inbound</th><th>Impressions</th><th>Canonical</th></tr></thead><tbody id="pageRows"></tbody></table></div>
        </article>
      </section>

      <section class="panel-view" id="method" hidden>
        <div class="method-grid">
          <article class="card"><div class="step-num">01 / PROVENANCE</div><h3>Merge without erasing sources</h3><p>Inventory, sitemap, and cache URLs are normalized while their origin remains attached to every record.</p></article>
          <article class="card"><div class="step-num">02 / COMPLETENESS</div><h3>Pass both gates</h3><p>Whole-site claims require a declared, evidence-bound source universe and 100% usable HTML for active graph-eligible URLs, plus the homepage and every child sitemap.</p></article>
          <article class="card"><div class="step-num">03 / SEPARATION</div><h3>Keep mechanisms apart</h3><p>Languages, articles, products, rentals, tours, and taxonomies stay in separate lanes to reduce false consolidation advice.</p></article>
          <article class="card"><div class="step-num">04 / EVIDENCE</div><h3>Label certainty</h3><p>Every finding is marked confirmed, candidate, or withheld. Similarity alone never authorizes URL removal.</p></article>
          <article class="card"><div class="step-num">05 / SAFETY</div><h3>No silent production writes</h3><p>The audit is local-first and read-only. Network crawling and all live mutations require separate, explicit authorization.</p></article>
          <article class="card"><div class="step-num">06 / HANDOFF</div><h3>Stop or hand off deterministically</h3><p><code>decision.json</code> and the optional CLI gate return WITHHOLD / exit 2 or READY_FOR_HUMAN_REVIEW / exit 0. Neither state authorizes a live change.</p></article>
        </div>
      </section>
    </main>

    <footer class="footer"><span id="footerSite"></span><span>Generated locally · No analytics · No external scripts</span></footer>
  </div>

  <aside class="drawer" id="drawer" hidden aria-modal="true" role="dialog" aria-labelledby="drawerTitle">
    <div aria-hidden="true"></div>
    <div class="drawer-panel">
      <div class="drawer-head"><div><span class="badge" id="drawerBadge"></span><h2 id="drawerTitle"></h2></div><button class="close" id="closeDrawer" aria-label="Close evidence details">×</button></div>
      <div class="detail-block"><strong>Status</strong><div id="drawerStatus"></div></div>
      <div class="detail-block"><strong>URL / target</strong><div id="drawerUrl"></div></div>
      <div class="detail-block"><strong>Evidence</strong><div id="drawerEvidence"></div></div>
      <div class="detail-block"><strong>Interpretation</strong><div id="drawerInterpretation"></div></div>
    </div>
  </aside>

  <script>
    const payload = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob("__DATA_B64__"), c => c.charCodeAt(0))));
    const $ = (selector) => document.querySelector(selector);
    const escText = (value) => value == null || value === "" ? "—" : String(value);
    const pct = (value) => `${Math.round(Number(value || 0) * 100)}%`;
    const number = (value) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(Number(value || 0));
    const findingUrl = (f) => f.source && f.target ? `${f.source} ↔ ${f.target}` : (f.url || f.target || f.source || (f.urls || []).slice(0, 2).join(", ") || "—");
    const interpretation = {
      confirmed: "Directly observed in the applicable input. A live change still requires a separate decision and rollback plan.",
      candidate: "A measured signal that requires another evidence source or mechanism review before action.",
      withheld: "Current inputs cannot support this conclusion. Collect the missing evidence instead of guessing."
    };

    document.getElementById("modeChip").textContent = payload.mode.replaceAll("_", " ");
    document.getElementById("footerSite").textContent = `${payload.site} · ${payload.generated_at}`;

    const c = payload.coverage;
    const sourceUniverse = payload.source_universe || { declared: false, sources: [] };
    const completeness = payload.completeness;
    const release = payload.release_contract || {
      decision: completeness.gate_passed ? "READY_FOR_HUMAN_REVIEW" : "WITHHOLD",
      release_gate_passed: Boolean(completeness.gate_passed),
      live_change_authorized: false,
      unclassified_count: 0,
      blocker_codes: []
    };
    const sourceDeclared = Boolean(completeness.source_declared);
    const sourceComplete = Boolean(completeness.source_complete);
    const contentGraphComplete = Boolean(completeness.content_graph_complete);
    const gatePassed = Boolean(completeness.gate_passed);
    const sourceLabel = completeness.source_label;
    const contentLabel = completeness.content_label;
    const finalLabel = completeness.final_label;
    const boundaryCard = document.getElementById("boundaryCard");
    boundaryCard.classList.toggle("withheld", !gatePassed);
    document.getElementById("releaseDecision").textContent = release.decision.replaceAll("_", " ");
    document.getElementById("gateHeadline").textContent = completeness.headline;
    document.getElementById("decisionBoundary").textContent = completeness.boundary;
    document.getElementById("nextAction").textContent = gatePassed
      ? "Next: an SEO specialist reviews the evidence. A separate approval is still required before any live change."
      : release.unclassified_count > 0
        ? `Next: reconcile ${number(release.unclassified_count)} unclassified identities before planning a migration or cleanup.`
        : "Next: resolve the listed evidence blockers before planning a migration or cleanup.";
    const totalFindings = payload.findings.length;
    const high = payload.findings.filter(f => f.severity === "high").length;
    const observedSource = sourceUniverse.observed_normalized_identities ?? c.observed_source_identities ?? c.known_urls;
    const expectedSource = sourceUniverse.expected_normalized_identities ?? c.expected_source_identities;
    const sourceCountLabel = expectedSource == null ? number(observedSource) : `${number(observedSource)}/${number(expectedSource)}`;
    const metricData = [
      ["Source identities", sourceCountLabel, `${number(release.unclassified_count)} unclassified · ${number(sourceUniverse.required_source_count)} required sources`, sourceComplete ? "good" : "warn"],
      ["Active HTML", `${number(c.html_pages)}/${number(c.graph_eligible_urls ?? c.known_urls)}`, `${pct(c.html_coverage)} usable · ${number(c.resolved_non_graph_urls)} confirmed terminal`, contentGraphComplete ? "good" : "warn"],
      ["Release evidence", release.decision.replaceAll("_", " "), release.live_change_authorized ? "Live change authorized" : "Live changes never authorized here", gatePassed ? "good" : "warn"],
      ["Review queue", number(totalFindings), gatePassed ? `${number(high)} high-priority items` : `${number((release.blocker_codes || []).length)} blocker codes · graph claims withheld`, gatePassed ? "good" : "warn"]
    ];
    metricData.forEach(([label, value, note, cls]) => {
      const card = document.createElement("article"); card.className = "card";
      const labelEl = document.createElement("div"); labelEl.className = "metric-label"; labelEl.textContent = label;
      const valueEl = document.createElement("div"); valueEl.className = `metric-value ${cls}`; valueEl.textContent = value;
      const noteEl = document.createElement("div"); noteEl.className = "metric-note"; noteEl.textContent = note;
      card.append(labelEl, valueEl, noteEl); $("#metrics").append(card);
    });

    const findingCounts = Object.entries(payload.finding_counts).sort((a,b) => b[1] - a[1]).slice(0, 9);
    const maxCount = Math.max(1, ...findingCounts.map(([,count]) => count));
    findingCounts.forEach(([label, count]) => {
      const row = document.createElement("div"); row.className = "bar-row";
      const name = document.createElement("div"); name.className = "bar-label"; name.textContent = label.replaceAll("_", " "); name.title = label;
      const track = document.createElement("div"); track.className = "bar-track";
      const fill = document.createElement("div"); fill.className = "bar-fill"; fill.style.width = `${Math.max(3, count / maxCount * 100)}%`; track.append(fill);
      const value = document.createElement("div"); value.className = "bar-count"; value.textContent = number(count);
      row.append(name, track, value); $("#findingBars").append(row);
    });

    $("#coverageRing").style.setProperty("--coverage", pct(c.html_coverage));
    $("#coverageRing").classList.toggle("withheld", !gatePassed);
    $("#coverageValue").textContent = pct(c.html_coverage);
    const notes = [
      ["Source universe", `${sourceCountLabel} · ${sourceLabel}`],
      ["Unclassified identities", number(release.unclassified_count)],
      ["Required sources", sourceDeclared ? (sourceUniverse.required_sources_complete ? "Complete" : "Incomplete") : "Not declared"],
      ["Manifest site", sourceDeclared ? (sourceUniverse.site_matches ? "Matched" : "Mismatch") : "Not declared"],
      ["Inventory hash binding", sourceDeclared ? (sourceUniverse.inventory_binding_complete ? "Verified" : "Missing / mismatch") : "Not declared"],
      ["HTML-cache hash binding", sourceDeclared ? (sourceUniverse.page_cache_binding_complete ? "Verified / not used" : "Missing / mismatch") : "Not declared"],
      ["Sitemap hash binding", sourceDeclared ? (sourceUniverse.sitemap_binding_complete ? "Verified / not used" : "Missing / mismatch") : "Not declared"],
      ["Homepage parsed", c.homepage_parsed ? "Yes" : "No"],
      ["Graph-eligible URLs", number(c.graph_eligible_urls ?? c.known_urls)],
      ["Resolved redirects / gone", number(c.resolved_non_graph_urls)],
      ["Unresolved sitemaps", number(c.unresolved_sitemaps)],
      ["Required active HTML", pct(c.complete_threshold)],
      ["Observed content graph", contentLabel],
      ["Final graph", finalLabel],
      ["Release decision", release.decision.replaceAll("_", " ")],
      ["Live change authorized", release.live_change_authorized ? "Yes" : "No"]
    ];
    notes.forEach(([label, value]) => {
      const row = document.createElement("div"); row.className = "fact-row";
      const left = document.createElement("div"); left.className = "fact-label"; left.textContent = label;
      const right = document.createElement("div"); right.className = "fact-value"; right.textContent = value;
      row.append(left, right); $("#coverageNotes").append(row);
    });

    const readyStatuses = new Set(["collected", "complete", "included", "loaded", "resolved"]);
    const sourceRows = Array.isArray(sourceUniverse.sources) ? sourceUniverse.sources : [];
    if (!sourceDeclared) {
      $("#sourceSummary").textContent = "No source manifest was declared. This is a legacy audit; source-universe completeness is not proven.";
    } else if (!sourceComplete) {
      $("#sourceSummary").textContent = "Whole-site graph claims are withheld until every required source is ready and the declared universe is complete.";
    } else {
      $("#sourceSummary").textContent = "The operator declaration, required source rows, audited origin, and exact inventory / supplied HTML-cache / resolved-sitemap hash bindings passed the source gate.";
    }
    if (!sourceRows.length) {
      const empty = document.createElement("div"); empty.className = "empty";
      empty.textContent = sourceDeclared ? "No source rows are listed in this manifest." : "Legacy / not declared";
      $("#sourceRows").append(empty);
    } else {
      sourceRows.forEach(source => {
        const row = document.createElement("div"); row.className = "source-row";
        const name = document.createElement("div"); name.className = "source-name"; name.textContent = escText(source.id);
        const kind = document.createElement("span"); kind.className = "source-kind"; kind.textContent = escText(source.kind); name.append(kind);
        const state = document.createElement("div");
        const ready = readyStatuses.has(String(source.status || "").toLowerCase());
        state.className = `source-state ${ready ? "ready" : "missing"}`;
        const records = source.records == null ? "" : ` · ${number(source.records)} records`;
        state.textContent = `${source.required ? "required" : "optional"} · ${escText(source.status)}${records}`;
        row.append(name, state); $("#sourceRows").append(row);
      });
    }

    const rows = $("#findingRows");
    function showDrawer(finding) {
      $("#drawerBadge").className = `badge badge-${finding.severity || "info"}`;
      $("#drawerBadge").textContent = escText(finding.severity);
      $("#drawerTitle").textContent = escText(finding.type).replaceAll("_", " ");
      $("#drawerStatus").textContent = escText(finding.status);
      $("#drawerStatus").className = `status-${finding.status}`;
      $("#drawerUrl").textContent = findingUrl(finding);
      $("#drawerEvidence").textContent = escText(finding.evidence);
      $("#drawerInterpretation").textContent = interpretation[finding.status] || interpretation.candidate;
      $("#drawer").hidden = false; $("#closeDrawer").focus();
    }
    function renderFindings() {
      const query = $("#search").value.trim().toLowerCase();
      const severity = $("#severity").value;
      const status = $("#status").value;
      const filtered = payload.findings.filter(f => {
        const haystack = `${f.type} ${findingUrl(f)} ${f.evidence || ""}`.toLowerCase();
        return (!query || haystack.includes(query)) && (!severity || f.severity === severity) && (!status || f.status === status);
      });
      rows.replaceChildren();
      filtered.forEach((f) => {
        const tr = document.createElement("tr"); tr.tabIndex = 0; tr.setAttribute("role", "button");
        const sev = document.createElement("td"); const badge = document.createElement("span"); badge.className = `badge badge-${f.severity || "info"}`; badge.textContent = escText(f.severity); sev.append(badge);
        const stat = document.createElement("td"); stat.className = `status-${f.status}`; stat.textContent = escText(f.status);
        const type = document.createElement("td"); type.textContent = escText(f.type).replaceAll("_", " ");
        const url = document.createElement("td"); url.className = "url"; url.textContent = findingUrl(f);
        const evidence = document.createElement("td"); evidence.className = "evidence"; evidence.textContent = escText(f.evidence);
        tr.append(sev, stat, type, url, evidence);
        tr.addEventListener("click", () => showDrawer(f)); tr.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showDrawer(f); }});
        rows.append(tr);
      });
      $("#findingTotal").textContent = `${number(filtered.length)} of ${number(payload.findings.length)}`;
      if (!filtered.length) { const tr = document.createElement("tr"); const td = document.createElement("td"); td.colSpan = 5; td.className = "empty"; td.textContent = "No findings match these filters."; tr.append(td); rows.append(tr); }
    }
    ["#search", "#severity", "#status"].forEach(id => $(id).addEventListener("input", renderFindings));
    renderFindings();

    const pageRows = $("#pageRows");
    payload.pages.slice().sort((a,b) => (Number(b.latest_impressions || 0) - Number(a.latest_impressions || 0)) || String(a.url).localeCompare(String(b.url))).slice(0, 250).forEach(p => {
      const tr = document.createElement("tr");
      [p.depth, p.status, p.lane, p.url, p.inbound_total, number(p.latest_impressions), p.canonical].forEach((value, index) => {
        const td = document.createElement("td"); td.textContent = escText(value); if (index === 3 || index === 6) td.className = "url"; tr.append(td);
      });
      pageRows.append(tr);
    });
    $("#pageTotal").textContent = `${number(payload.pages.length)} pages`;

    $(".tabs").addEventListener("click", event => {
      const button = event.target.closest("[data-tab]"); if (!button) return;
      document.querySelectorAll(".tab").forEach(tab => tab.setAttribute("aria-selected", String(tab === button)));
      document.querySelectorAll(".panel-view").forEach(panel => panel.hidden = panel.id !== button.dataset.tab);
    });
    $("#closeDrawer").addEventListener("click", () => $("#drawer").hidden = true);
    $("#drawer").addEventListener("click", e => { if (e.target === $("#drawer")) $("#drawer").hidden = true; });
    document.addEventListener("keydown", e => { if (e.key === "Escape") $("#drawer").hidden = true; });
    $("#copySummary").addEventListener("click", async () => {
      const summary = `ProofRank audit for ${payload.site}: decision ${release.decision}, source identities ${sourceCountLabel}, active HTML ${c.html_pages}/${c.graph_eligible_urls ?? c.known_urls}, unclassified ${release.unclassified_count}, final graph ${finalLabel.toLowerCase()}, live change authorized no.`;
      try { await navigator.clipboard.writeText(summary); $("#copySummary").textContent = "Copied"; setTimeout(() => $("#copySummary").textContent = "Copy summary", 1400); }
      catch { $("#copySummary").textContent = "Copy unavailable"; }
    });
  </script>
</body>
</html>'''


def public_source_universe(audit: dict) -> dict:
    """Expose source-gate evidence without leaking manifest paths or free-form notes."""
    inputs = audit.get("inputs") if isinstance(audit.get("inputs"), dict) else {}
    raw = audit.get("source_universe") or inputs.get("source_universe") or {}
    if not isinstance(raw, dict):
        raw = {}

    declared = bool(raw.get("declared")) if "declared" in raw else bool(raw)
    safe_sources = []
    for index, source in enumerate(raw.get("sources", []), start=1):
        if not isinstance(source, dict):
            continue
        safe = {
            "id": str(source.get("id") or source.get("name") or f"source-{index}"),
            "kind": str(source.get("kind") or source.get("type") or "unspecified"),
            "required": bool(source.get("required")),
            "status": str(source.get("status") or "unspecified"),
        }
        records = source.get("records")
        if isinstance(records, (int, float)) and not isinstance(records, bool):
            safe["records"] = records
        elif isinstance(records, str) and records.strip().isdigit():
            safe["records"] = int(records.strip())
        safe_sources.append(safe)

    required_count = raw.get("required_source_count")
    if not isinstance(required_count, int) or isinstance(required_count, bool):
        required_count = sum(1 for source in safe_sources if source["required"])

    return {
        "declared": declared,
        "universe_declared_complete": bool(raw.get("universe_declared_complete")) if declared else False,
        "required_sources_complete": bool(raw.get("required_sources_complete")) if declared else False,
        "site_matches": bool(raw.get("site_matches")) if declared else False,
        "inventory_binding_complete": bool(raw.get("inventory_binding_complete")) if declared else False,
        "page_cache_binding_complete": bool(raw.get("page_cache_binding_complete")) if declared else False,
        "sitemap_binding_complete": bool(raw.get("sitemap_binding_complete")) if declared else False,
        "input_binding_complete": bool(raw.get("input_binding_complete")) if declared else False,
        "source_universe_complete": bool(raw.get("source_universe_complete")) if declared else False,
        "expected_normalized_identities": raw.get("expected_normalized_identities"),
        "observed_normalized_identities": raw.get("observed_normalized_identities", 0),
        "identity_count_matches": raw.get("identity_count_matches"),
        "required_source_count": required_count,
        "sources": safe_sources,
    }


def public_release_contract(audit: dict) -> dict:
    """Expose the machine decision without local paths or mutable-action authority."""
    raw = audit.get("release_contract") if isinstance(audit.get("release_contract"), dict) else {}
    coverage = audit.get("coverage") if isinstance(audit.get("coverage"), dict) else {}
    passed = bool(raw.get("release_gate_passed")) if raw else bool(coverage.get("graph_complete"))
    blockers = raw.get("blocker_codes") if isinstance(raw.get("blocker_codes"), list) else []
    stages = raw.get("stages") if isinstance(raw.get("stages"), dict) else {}
    return {
        "schema_version": str(raw.get("schema_version") or "1.0"),
        "decision": str(raw.get("decision") or ("READY_FOR_HUMAN_REVIEW" if passed else "WITHHOLD")),
        "release_gate_passed": passed,
        "live_change_authorized": False,
        "stages": stages,
        "unclassified_count": int(raw.get("unclassified_count") or 0),
        "blocker_codes": [str(value) for value in blockers],
        "decision_boundary": str(raw.get("decision_boundary") or "Read-only evidence result."),
    }


def completeness_view(audit: dict, source_universe: dict) -> dict:
    """Build the exact labels shown for the two gates and their final result."""
    coverage = audit.get("coverage") if isinstance(audit.get("coverage"), dict) else {}
    source_declared = bool(source_universe["declared"])
    source_complete = source_declared and bool(source_universe["source_universe_complete"])
    content_graph_complete = coverage.get("content_graph_complete")
    if not isinstance(content_graph_complete, bool):
        content_graph_complete = bool(coverage.get("graph_complete"))
    gate_passed = bool(
        source_declared
        and source_complete
        and content_graph_complete
        and coverage.get("graph_complete")
    )

    if not source_declared:
        source_label = "Legacy / not declared"
        final_label = "Legacy / not proven"
        headline = "Legacy audit — manifest not declared"
        boundary = (
            "The observed graph may pass the legacy HTML gate, but the source universe was not declared. "
            "Whole-site completeness is not proven; rerun with a source manifest."
        )
    elif not source_complete:
        source_label = "Declaration failed"
        final_label = "Withheld"
        headline = "Source universe incomplete"
        boundary = (
            "Required source evidence is missing or the declared universe is incomplete. "
            "Whole-site graph claims are withheld until the source gate passes."
        )
    elif not content_graph_complete:
        source_label = "Declared + bound"
        final_label = "Withheld"
        headline = "Observed graph incomplete"
        boundary = (
            "Observed HTML coverage, homepage parsing, or sitemap resolution is incomplete. "
            "Whole-site graph claims are withheld until the content gate passes."
        )
    elif gate_passed:
        source_label = "Declared + bound"
        final_label = "Gate passed"
        headline = "Both completeness gates passed"
        boundary = audit.get("decision_boundary", "No live changes are authorized by this audit.")
    else:
        source_label = "Declared + bound"
        final_label = "Withheld"
        headline = "Whole-site claims withheld"
        boundary = "The final graph gate did not pass. Whole-site graph claims remain withheld."

    return {
        "source_declared": source_declared,
        "source_complete": source_complete,
        "content_graph_complete": content_graph_complete,
        "gate_passed": gate_passed,
        "source_label": source_label,
        "content_label": "Coverage passed" if content_graph_complete else "Coverage failed",
        "final_label": final_label,
        "headline": headline,
        "boundary": boundary,
    }


def public_payload(audit: dict) -> dict:
    """Keep the static dashboard free of local input paths and secrets."""
    source_universe = public_source_universe(audit)
    return {
        "generated_at": audit.get("generated_at"),
        "mode": audit.get("mode"),
        "site": audit.get("site"),
        "coverage": audit.get("coverage", {}),
        "source_universe": source_universe,
        "completeness": completeness_view(audit, source_universe),
        "release_contract": public_release_contract(audit),
        "finding_counts": audit.get("finding_counts", {}),
        "findings": audit.get("findings", []),
        "pages": audit.get("pages", []),
        "decision_boundary": audit.get("decision_boundary", "No live changes are authorized by this audit."),
    }


def render(audit_path: Path, output_path: Path) -> None:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    packed = json.dumps(public_payload(audit), ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(packed.encode("utf-8")).decode("ascii")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(HTML_TEMPLATE.replace("__DATA_B64__", encoded), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a local ProofRank dashboard from audit.json")
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    render(args.audit, args.output)
    print(json.dumps({"dashboard": str(args.output.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
