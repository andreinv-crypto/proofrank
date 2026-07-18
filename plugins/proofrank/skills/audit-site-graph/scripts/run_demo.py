#!/usr/bin/env python3
"""Run ProofRank against the bundled, synthetic Costa Demo fixture."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bundled ProofRank demo")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    demo_dir = repo_root / "demo"
    output_dir = (args.output_dir or (repo_root / "demo-output")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    audit_command = [
        sys.executable,
        str(script_dir / "site_graph_audit.py"),
        "--site", "https://costa-demo.example/",
        "--inventory", str(demo_dir / "inventory.csv"),
        "--page-cache", str(demo_dir / "page_cache.json"),
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
    print(f"ProofRank demo ready: {output_dir / 'dashboard.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
