#!/usr/bin/env python3
"""Run ProofRank against the bundled, synthetic Costa Demo fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SITE = "https://costa-demo.example/"
INCOMPLETE_COVERAGE_FRACTION = 0.64


def write_incomplete_cache(source: Path, destination: Path) -> tuple[int, int]:
    """Write a deterministic partial cache derived only from the bundled fixture."""
    data = json.loads(source.read_text(encoding="utf-8"))
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, dict) or len(pages) < 2:
        raise ValueError("Bundled demo page cache must contain at least two keyed pages")

    ordered_urls = sorted(pages, key=lambda url: (url.rstrip("/") != SITE.rstrip("/"), url))
    keep_count = round(len(ordered_urls) * INCOMPLETE_COVERAGE_FRACTION)
    keep_count = max(1, min(len(ordered_urls) - 1, keep_count))
    partial = dict(data)
    partial["scenario"] = "incomplete-coverage"
    partial["source_fixture"] = "bundled synthetic page_cache.json"
    partial["pages"] = {url: pages[url] for url in ordered_urls[:keep_count]}
    destination.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    return keep_count, len(ordered_urls)


def run_scenario(scenario: str, output_dir: Path, script_dir: Path, demo_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    page_cache = demo_dir / "page_cache.json"
    coverage_note = ""
    if scenario == "incomplete":
        page_cache = output_dir / "page_cache.incomplete.json"
        kept, total = write_incomplete_cache(demo_dir / "page_cache.json", page_cache)
        coverage_note = f" ({kept}/{total} synthetic HTML pages supplied)"

    audit_command = [
        sys.executable,
        str(script_dir / "site_graph_audit.py"),
        "--site", SITE,
        "--inventory", str(demo_dir / "inventory.csv"),
        "--page-cache", str(page_cache),
        "--sitemap", str(demo_dir / "sitemap.xml"),
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
