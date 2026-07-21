#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

function fail(message) {
  throw new Error(message);
}

async function captureSlide(browser, storyboard, scene, destination) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  try {
    const url = `${pathToFileURL(storyboard).href}?scene=${encodeURIComponent(scene)}`;
    await page.goto(url, { waitUntil: "load" });
    await page.waitForSelector(`[data-scene="${scene}"].active`);
    const size = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }));
    if (size.width !== 1920 || size.height !== 1080) fail(`Unexpected storyboard size for ${scene}: ${JSON.stringify(size)}`);
    await page.screenshot({ path: destination, type: "png" });
  } finally {
    await page.close();
  }
}

async function outline(locator, color) {
  if (await locator.count() !== 1) fail("Expected exactly one element to highlight");
  await locator.evaluate((element, outlineColor) => {
    element.style.outline = `4px solid ${outlineColor}`;
    element.style.outlineOffset = "-4px";
    element.style.transition = "outline-color 180ms ease";
  }, color);
}

async function clearOutline(locator) {
  await locator.evaluate(element => { element.style.outline = "none"; });
}

async function recordDashboard(browser, dashboard, destination, scenario) {
  const videoDir = path.join(path.dirname(destination), `.record-${scenario}`);
  fs.mkdirSync(videoDir, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: videoDir, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  const video = page.video();

  try {
    await page.goto(pathToFileURL(dashboard).href, { waitUntil: "load" });
    await page.waitForSelector("#releaseDecision");
    await page.waitForSelector("#metrics .card");
    await page.evaluate(() => {
      const label = document.createElement("div");
      label.textContent = "SMALL SYNTHETIC EXAMPLE · PUBLIC FIXTURE";
      label.style.cssText = [
        "position:fixed", "z-index:9999", "top:18px", "left:50%", "transform:translateX(-50%)",
        "padding:10px 18px", "border-radius:999px", "background:#10243b", "color:#ffc66c",
        "border:1px solid rgba(255,198,108,.48)", "font:800 14px Segoe UI,Arial,sans-serif",
        "letter-spacing:.08em", "box-shadow:0 12px 35px rgba(0,0,0,.3)"
      ].join(";");
      document.body.appendChild(label);
    });
    const sourceMetric = page.locator("#metrics .card").filter({ hasText: "Declared-scope identities" });
    const htmlMetric = page.locator("#metrics .card").filter({ hasText: "Usable active HTML" });
    const releaseCard = page.locator("#boundaryCard");
    const decision = (await page.locator("#releaseDecision").innerText()).trim();
    const sourceText = (await sourceMetric.innerText()).replace(/\s+/g, " ");
    const htmlText = (await htmlMetric.innerText()).replace(/\s+/g, " ");
    await page.waitForTimeout(1800);

    if (scenario === "incomplete") {
      if (!decision.includes("WITHHOLD")) fail(`Incomplete demo decision changed: ${decision}`);
      if (!sourceText.includes("7/11")) fail(`Incomplete source metric changed: ${sourceText}`);
      if (!htmlText.includes("7/7")) fail(`Incomplete HTML metric changed: ${htmlText}`);
      await outline(htmlMetric, "#73e2a7");
      await page.waitForTimeout(4200);
      await clearOutline(htmlMetric);
      await outline(sourceMetric, "#ffc76a");
      await page.waitForTimeout(4200);
      await clearOutline(sourceMetric);
      await outline(releaseCard, "#ffc76a");
      await page.waitForTimeout(7200);
    } else if (scenario === "complete") {
      if (!decision.includes("READY FOR HUMAN REVIEW")) fail(`Complete demo decision changed: ${decision}`);
      if (!sourceText.includes("11/11")) fail(`Complete source metric changed: ${sourceText}`);
      if (!htmlText.includes("10/10")) fail(`Complete HTML metric changed: ${htmlText}`);
      await outline(sourceMetric, "#73e2a7");
      await page.waitForTimeout(4000);
      await clearOutline(sourceMetric);
      await outline(htmlMetric, "#73e2a7");
      await page.waitForTimeout(4000);
      await clearOutline(htmlMetric);
      await outline(releaseCard, "#73e2a7");
      await page.waitForTimeout(6400);
    } else if (scenario === "safety") {
      await page.locator('[data-tab="method"]').click();
      await page.waitForTimeout(1800);
      const handoff = page.locator(".method-grid .card").filter({ hasText: "Stop or hand off deterministically" });
      await outline(handoff, "#56d9d2");
      await page.waitForTimeout(7200);
      await clearOutline(handoff);
      const safety = page.locator(".method-grid .card").filter({ hasText: "No silent production writes" });
      await outline(safety, "#ffc76a");
      await page.waitForTimeout(5200);
    }

    if (errors.length) fail(errors.join("\n"));
  } finally {
    await page.close();
    await context.close();
  }

  const recorded = await video.path();
  fs.copyFileSync(recorded, destination);
  fs.rmSync(videoDir, { recursive: true, force: true });
}

async function main() {
  const [storyboardArg, completeArg, incompleteArg, outputArg] = process.argv.slice(2);
  if (!storyboardArg || !completeArg || !incompleteArg || !outputArg) {
    fail("Usage: capture_video_assets.cjs <storyboard.html> <complete-dashboard.html> <incomplete-dashboard.html> <output-dir>");
  }

  const storyboard = path.resolve(storyboardArg);
  const complete = path.resolve(completeArg);
  const incomplete = path.resolve(incompleteArg);
  const output = path.resolve(outputArg);
  for (const required of [storyboard, complete, incomplete]) {
    if (!fs.existsSync(required)) fail(`Missing input: ${required}`);
  }
  fs.mkdirSync(output, { recursive: true });

  const candidates = [
    process.env.PROOFRANK_BROWSER,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find(candidate => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const slides = ["hook", "product", "founder", "codex", "proof", "rollback", "impact", "architecture", "outro"];

  try {
    for (const scene of slides) {
      await captureSlide(browser, storyboard, scene, path.join(output, `slide-${scene}.png`));
    }
    await recordDashboard(browser, incomplete, path.join(output, "clip-incomplete.webm"), "incomplete");
    await recordDashboard(browser, complete, path.join(output, "clip-complete.webm"), "complete");
    await recordDashboard(browser, complete, path.join(output, "clip-safety.webm"), "safety");
  } finally {
    await browser.close();
  }

  process.stdout.write(JSON.stringify({
    status: "ok",
    slides: slides.length,
    clips: 3,
    output,
  }, null, 2));
}

main().catch(error => {
  console.error(error.stack || error.message);
  process.exit(1);
});
