#!/usr/bin/env python3
"""Run ProofRank against the bundled, synthetic Costa Demo fixture."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SITE = "https://costa-demo.example/"
INCOMPLETE_SOURCE_PATHS = (
    "/",
    "/about/",
    "/guides/hidden-coves/",
    "/guides/weekend-a/",
    "/guides/weekend-b/",
    "/rentals/",
    "/rentals/old/",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_fixture_source_manifest(
    inventory: Path,
    sitemap: Path,
    page_cache: Path,
    destination: Path,
    expected_normalized_identities: int,
) -> None:
    """Declare the synthetic fixture's authoritative URL sources without local paths."""
    with inventory.open("r", encoding="utf-8-sig", newline="") as handle:
        inventory_rows = sum(1 for _ in csv.DictReader(handle))
    manifest = {
        "version": 1,
        "site": SITE,
        "universe_complete": True,
        "expected_normalized_identities": expected_normalized_identities,
        "sources": [
            {
                "id": "synthetic-inventory",
                "kind": "inventory",
                "required": True,
                "status": "collected",
                "path": inventory.name,
                "sha256": file_sha256(inventory),
                "records": inventory_rows,
            },
            {
                "id": "synthetic-sitemap",
                "kind": "sitemap",
                "required": True,
                "status": "collected",
                "path": sitemap.name,
                "sha256": file_sha256(sitemap),
                "records": inventory_rows,
            },
        ],
        "outputs": {
            "inventory": {
                "path": inventory.name,
                "sha256": file_sha256(inventory),
                "records": inventory_rows,
            },
            "page_cache": {
                "path": page_cache.name,
                "sha256": file_sha256(page_cache),
            },
            "sitemaps": [
                {
                    "path": sitemap.name,
                    "sha256": file_sha256(sitemap),
                }
            ],
        },
    }
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_incomplete_cache(source: Path, destination: Path) -> tuple[list[str], int]:
    """Write a deterministic seven-page crawler view derived from the bundled fixture."""
    data = json.loads(source.read_text(encoding="utf-8"))
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, dict) or len(pages) < 2:
        raise ValueError("Bundled demo page cache must contain at least two keyed pages")

    selected_urls = [SITE.rstrip("/") + path for path in INCOMPLETE_SOURCE_PATHS]
    missing = [url for url in selected_urls if url not in pages]
    if missing:
        raise ValueError(f"Bundled demo cache is missing incomplete-scenario URLs: {missing}")
    selected_pages = {url: dict(pages[url]) for url in selected_urls}
    selected_pages[SITE]["html"] = selected_pages[SITE]["html"].replace(
        '<a href="/guides/beaches/">Beaches</a>',
        "",
    )
    partial = dict(data)
    partial["scenario"] = "incomplete-source-universe"
    partial["source_fixture"] = "bundled synthetic page_cache.json"
    partial["scenario_note"] = (
        "Synthetic source-limited view: homepage navigation is restricted to the observed "
        "seven-page set so source-universe and active-HTML gates are tested independently."
    )
    partial["pages"] = selected_pages
    destination.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    return selected_urls, len(pages)


def write_incomplete_inventory(source: Path, destination: Path, selected_urls: set[str]) -> None:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = [row for row in reader if row.get("url") in selected_urls]
    if len(rows) != len(selected_urls):
        raise ValueError("Incomplete inventory could not bind every selected synthetic URL")
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_incomplete_sitemap(destination: Path, selected_urls: set[str]) -> None:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    for url in sorted(selected_urls):
        entry = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(entry, f"{{{namespace}}}loc").text = url
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)


def run_scenario(scenario: str, output_dir: Path, script_dir: Path, demo_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = demo_dir / "inventory.csv"
    sitemap = demo_dir / "sitemap.xml"
    page_cache = demo_dir / "page_cache.json"
    source_manifest = output_dir / "source_manifest.json"
    coverage_note = ""
    with inventory.open("r", encoding="utf-8-sig", newline="") as handle:
        expected_normalized_identities = sum(1 for _ in csv.DictReader(handle))
    if scenario == "incomplete":
        page_cache = output_dir / "page_cache.incomplete.json"
        selected_urls, total = write_incomplete_cache(demo_dir / "page_cache.json", page_cache)
        selected_url_set = set(selected_urls)
        inventory = output_dir / "inventory.incomplete.csv"
        sitemap = output_dir / "sitemap.incomplete.xml"
        write_incomplete_inventory(demo_dir / "inventory.csv", inventory, selected_url_set)
        write_incomplete_sitemap(sitemap, selected_url_set)
        coverage_note = f" ({len(selected_urls)}/{total} source identities; {len(selected_urls)}/{len(selected_urls)} active HTML)"
    write_fixture_source_manifest(
        inventory,
        sitemap,
        page_cache,
        source_manifest,
        expected_normalized_identities,
    )

    audit_command = [
        sys.executable,
        str(script_dir / "site_graph_audit.py"),
        "--site", SITE,
        "--inventory", str(inventory),
        "--page-cache", str(page_cache),
        "--sitemap", str(sitemap),
        "--source-manifest", str(source_manifest),
        "--brand-term", "Costa Demo",
        "--output-dir", str(output_dir),
    ]
    subprocess.run(audit_command, check=True)
    subprocess.run([
        sys.executable,
        str(script_dir / "render_dashboard.py"),
        "--audit", str(output_dir / "audit.json"),
        "--output", str(output_dir / "dashboard.html"),
    ], check=True)
    print(f"ProofRank {scenario} demo ready{coverage_note}: {output_dir / 'dashboard.html'}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the bundled ProofRank demo")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--scenario",
        choices=("complete", "incomplete", "both"),
        default="complete",
        help="Coverage gate to demonstrate; the default preserves the original complete demo",
    )
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    demo_dir = repo_root / "demo"
    default_dir = repo_root / ("demo-output-incomplete" if args.scenario == "incomplete" else "demo-output")
    output_dir = (args.output_dir or default_dir).resolve()

    scenarios = ("complete", "incomplete") if args.scenario == "both" else (args.scenario,)
    for scenario in scenarios:
        scenario_dir = output_dir / scenario if args.scenario == "both" else output_dir
        run_scenario(scenario, scenario_dir, script_dir, demo_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
