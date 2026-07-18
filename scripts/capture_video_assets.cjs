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
    await page.waitForSelector("#metrics .card");
    await page.waitForTimeout(3200);

    if (scenario === "incomplete") {
      const metric = page.locator("#metrics .card").filter({ hasText: "Graph claims" });
      await metric.evaluate(el => { el.style.outline = "4px solid #ffc76a"; el.style.outlineOffset = "-4px"; });
      await page.waitForTimeout(3600);
      await page.locator('[data-tab="findings"]').click();
      await page.waitForTimeout(1300);
      await page.locator("#status").selectOption("withheld");
      await page.waitForTimeout(3200);
      const gateRow = page.locator("#findingRows tr").filter({ hasText: "graph claims withheld" }).first();
      if (await gateRow.count() !== 1) fail("Incomplete demo did not expose graph_claims_withheld");
      await gateRow.click();
      await page.waitForTimeout(6200);
      await page.locator("#closeDrawer").click();
      await page.locator('[data-tab="overview"]').click();
      await page.waitForTimeout(2600);
    } else if (scenario === "complete") {
      await page.waitForTimeout(1900);
      await page.locator('[data-tab="findings"]').click();
      await page.waitForTimeout(1200);
      await page.locator("#severity").selectOption("high");
      await page.waitForTimeout(2600);
      const broken = page.locator("#findingRows tr").filter({ hasText: "broken internal link" }).first();
      if (await broken.count() !== 1) fail("Complete demo did not expose the broken-link finding");
      await broken.click();
      await page.waitForTimeout(5700);
      await page.locator("#closeDrawer").click();
      await page.locator('[data-tab="overview"]').click();
      await page.waitForTimeout(2300);
    } else if (scenario === "safety") {
      await page.locator('[data-tab="method"]').click();
      await page.waitForTimeout(2200);
      const safety = page.locator(".method-grid .card").filter({ hasText: "No silent production writes" });
      await safety.evaluate(el => { el.style.outline = "4px solid #56d9d2"; el.style.outlineOffset = "-4px"; });
      await page.waitForTimeout(7200);
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
  const slides = ["founder", "disclosure", "risk", "promise", "codex", "architecture", "scale", "outro"];

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
