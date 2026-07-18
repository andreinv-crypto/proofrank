#!/usr/bin/env node
"use strict";

const path = require("path");
const fs = require("fs");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

async function main() {
  const dashboard = path.resolve(process.argv[2]);
  const desktopShot = path.resolve(process.argv[3]);
  const mobileShot = path.resolve(process.argv[4]);
  const browserCandidates = [
    process.env.PROOFRANK_BROWSER,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find(candidate => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const errors = [];

  try {
    const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    desktop.on("console", message => {
      if (message.type() === "error") errors.push(`console: ${message.text()}`);
    });
    desktop.on("pageerror", error => errors.push(`page: ${error.message}`));
    await desktop.goto(pathToFileURL(dashboard).href, { waitUntil: "load" });
    await desktop.waitForTimeout(500);
    if (errors.length) throw new Error(errors.join("\n"));
    const initialState = await desktop.evaluate(() => ({
      readyState: document.readyState,
      scriptCount: document.scripts.length,
      metricCount: document.querySelectorAll("#metrics .card").length,
      metricsHtml: document.querySelector("#metrics")?.innerHTML || "",
      bodyText: document.body.innerText.slice(0, 240),
    }));
    if (!initialState.metricCount) throw new Error(`Dashboard did not initialize: ${JSON.stringify(initialState)}`);
    await desktop.waitForSelector("#metrics .card");

    const title = await desktop.title();
    const metrics = await desktop.locator("#metrics .card").count();
    const tabs = await desktop.locator("[data-tab]").count();
    if (title !== "ProofRank — Evidence-first SEO audit") throw new Error(`Unexpected title: ${title}`);
    if (metrics < 4 || tabs !== 4) throw new Error(`Unexpected dashboard structure: ${metrics} metrics, ${tabs} tabs`);

    await desktop.locator('[data-tab="findings"]').click();
    const findings = await desktop.locator("#findingRows tr").count();
    if (findings < 1) throw new Error("Evidence table did not render");
    await desktop.locator("#severity").selectOption("high");
    const highFindings = await desktop.locator("#findingRows tr").count();
    if (highFindings < 1 || highFindings > findings) throw new Error("Severity filter failed");
    await desktop.locator("#severity").selectOption("");
    await desktop.locator("#findingRows tr").first().click();
    if (await desktop.locator("#drawer").getAttribute("hidden") !== null) throw new Error("Evidence drawer did not open");
    await desktop.locator("#closeDrawer").click();
    await desktop.locator('[data-tab="overview"]').click();
    await desktop.screenshot({ path: desktopShot, fullPage: true });

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    mobile.on("pageerror", error => errors.push(`mobile page: ${error.message}`));
    await mobile.goto(pathToFileURL(dashboard).href, { waitUntil: "load" });
    await mobile.waitForSelector("#metrics .card");
    await mobile.screenshot({ path: mobileShot, fullPage: true });

    if (errors.length) throw new Error(errors.join("\n"));
    process.stdout.write(JSON.stringify({
      status: "ok",
      title,
      metrics,
      tabs,
      findings,
      highFindings,
      desktopShot,
      mobileShot,
    }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error.stack || error.message);
  process.exit(1);
});
