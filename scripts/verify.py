#!/usr/bin/env python3
"""Portable repository checks for ProofRank."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "proofrank"
SKILL = PLUGIN / "skills" / "audit-site-graph"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"


SECRET_PATTERNS = {
    "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def scan_secrets() -> list[str]:
    findings = []
    excluded = {".git", ".build", "demo-output", "demo-output-incomplete", "node_modules", "__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}: {path.relative_to(ROOT)}")
    return findings


def validate_manifest() -> None:
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "proofrank"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["skills"] == "./skills/"
    assert manifest["author"]["name"]
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        assert manifest["interface"][field]
    for field in ("composerIcon", "logo", "logoDark"):
        target = PLUGIN / manifest["interface"][field].removeprefix("./")
        assert target.is_file(), f"Missing manifest asset: {target}"


def validate_marketplace() -> None:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entries = [entry for entry in marketplace.get("plugins", []) if entry.get("name") == "proofrank"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["source"] == {"source": "local", "path": "./plugins/proofrank"}
    assert entry["policy"]["installation"] == "AVAILABLE"
    assert entry["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"}
    assert entry["category"] == "Productivity"


def validate_public_dashboard(path: Path) -> None:
    dashboard = path.read_text(encoding="utf-8")
    assert "ProofRank" in dashboard
    assert "C:\\Users\\" not in dashboard
    assert not re.search(r"<script[^>]+src=", dashboard, re.IGNORECASE)
    assert not re.search(r"https?://[^\"']+\.(?:js|css)", dashboard, re.IGNORECASE)


def main() -> int:
    validate_manifest()
    validate_marketplace()
    run([sys.executable, str(SKILL / "scripts" / "test_site_graph_audit.py")])
    with tempfile.TemporaryDirectory(prefix="proofrank-verify-") as temp:
        output = Path(temp) / "demo-output"
        run([
            sys.executable,
            str(SKILL / "scripts" / "run_demo.py"),
            "--scenario", "both",
            "--output-dir", str(output),
        ])
        complete = json.loads((output / "complete" / "audit.json").read_text(encoding="utf-8"))
        incomplete = json.loads((output / "incomplete" / "audit.json").read_text(encoding="utf-8"))
        assert complete["coverage"]["graph_complete"] is True
        assert complete["coverage"]["html_coverage"] == 1.0
        assert incomplete["coverage"]["graph_complete"] is False
        assert incomplete["coverage"]["html_pages"] == 7
        assert any(
            finding["type"] == "graph_claims_withheld" and finding["status"] == "withheld"
            for finding in incomplete["findings"]
        )
        for unsafe_type in ("orphan_candidate", "unreachable_from_home_candidate", "internal_link_opportunity"):
            assert unsafe_type not in incomplete["finding_counts"]
        validate_public_dashboard(output / "complete" / "dashboard.html")
        validate_public_dashboard(output / "incomplete" / "dashboard.html")
    secrets = scan_secrets()
    if secrets:
        raise RuntimeError("Potential secrets found:\n" + "\n".join(secrets))
    print(json.dumps({
        "status": "ok",
        "plugin": "proofrank",
        "checks": [
            "manifest",
            "marketplace",
            "unit_tests",
            "complete_demo",
            "incomplete_gate",
            "dashboard_boundary",
            "secret_scan",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
