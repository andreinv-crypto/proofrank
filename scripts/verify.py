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
    excluded = {".git", "demo-output", "__pycache__"}
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


def main() -> int:
    validate_manifest()
    run([sys.executable, str(SKILL / "scripts" / "test_site_graph_audit.py")])
    with tempfile.TemporaryDirectory(prefix="proofrank-verify-") as temp:
        output = Path(temp) / "demo-output"
        run([sys.executable, str(SKILL / "scripts" / "run_demo.py"), "--output-dir", str(output)])
        dashboard = (output / "dashboard.html").read_text(encoding="utf-8")
        assert "ProofRank" in dashboard
        assert "C:\\Users\\" not in dashboard
        assert not re.search(r"<script[^>]+src=", dashboard, re.IGNORECASE)
        assert not re.search(r"https?://[^\"']+\.(?:js|css)", dashboard, re.IGNORECASE)
    secrets = scan_secrets()
    if secrets:
        raise RuntimeError("Potential secrets found:\n" + "\n".join(secrets))
    print(json.dumps({"status": "ok", "plugin": "proofrank", "checks": ["manifest", "unit_tests", "demo", "dashboard_boundary", "secret_scan"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
