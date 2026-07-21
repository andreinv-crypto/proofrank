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
EVIDENCE = ROOT / "validation" / "real_world_evidence.json"
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"


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


def validate_evidence_and_ci() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 2
    assert evidence["evidence_type"] == "sanitized_aggregate_operational_validation"
    boundary = evidence["public_product_boundary"]
    assert boundary["public_fixture_url_count"] == 11
    assert boundary["offline_export_adapters_included"] is True
    assert boundary["guarded_release_contract_included"] is True
    assert boundary["public_product_is_read_only"] is True
    assert boundary["private_live_connectors_included"] is False
    assert boundary["private_apply_or_rollback_included"] is False
    assert evidence["provenance"]["publicly_recomputable"] is False
    private_hashes = evidence["provenance"]["private_report_hashes"]
    assert len(private_hashes) == 9
    assert len({item["artifact"] for item in private_hashes}) == len(private_hashes)
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        for item in private_hashes
    )
    cases = {case["id"]: case for case in evidence["cases"]}
    assert cases["torrevieja"]["active_site"]["known_urls"] == 3141
    assert cases["torrevieja"]["active_site"]["html_pages"] == 3137
    assert cases["torrevieja"]["migration_gate"]["known_paths"] == 3598
    assert cases["torrevieja"]["migration_gate"]["previously_successful_paths"] == 3090
    assert cases["torrevieja"]["migration_gate"]["previously_successful_paths_now_non_200"] == 0
    assert cases["torrevieja"]["legacy_platform"]["wordpress"] == "4.4.34"
    assert cases["torrevieja"]["legacy_platform"]["active_plugins"] == 39
    assert cases["torrevieja"]["modernized_platform"]["mysql"] == "8.4.8"
    assert cases["torrevieja"]["database_cleanup"]["physical_size_after_mb_approx"] == 105.71
    assert cases["velas"]["languages"] == 7
    assert cases["velas"]["legacy_platform"]["es"]["wordpress"] == "4.5.33"
    assert cases["velas"]["legacy_platform"]["ru"]["wordpress"] == "4.8.28"
    assert cases["velas"]["modernized_platform"] == {
        "wordpress": "7.0.1",
        "php": "8.5.2",
        "mysql": "8.4.8",
    }
    assert cases["velas"]["initial_known_url_gate"] == {"passed": 1807, "total": 1807}
    assert cases["velas"]["historical_drive_parity_gate"] == {"passed": 3696, "total": 3696}
    assert cases["velas"]["reconciled_source_union"]["base_unique_identities"] == 5490
    assert cases["velas"]["reconciled_source_union"]["normalized_identities"] == 11172
    assert cases["velas"]["reconciled_source_union"]["supplemental_parity_rows"] == 5696
    assert cases["velas"]["reconciled_source_union"]["unclassified_rows"] == 0
    assert cases["velas"]["full_postcutover_audit"]["total_classified_rows"] == 12163
    assert cases["velas"]["full_postcutover_audit"]["active_canonical_html_parsed"] == 5376
    assert cases["velas"]["full_postcutover_audit"]["source_bound_site_graph"] == "withheld"
    assert cases["velas"]["collected_source_counts"]["counts_overlap_and_must_not_be_summed"] is True
    closeout = cases["velas"]["guarded_closeout"]
    assert closeout["first_apply"]["automatic_rollback_ok"] is True
    assert closeout["first_apply"]["files_restored"] == 3
    assert closeout["first_apply"]["language_pages_green"] == "19/442"
    assert closeout["first_apply"]["invalid_alternate_emissions_remaining"] == 1522
    assert closeout["corrected_apply"]["language_pages_green"] == "442/442"
    assert closeout["corrected_apply"]["invalid_alternate_emissions_remaining"] == 0
    assert closeout["final_gates"]["existing_routes"] == "148/148"
    assert closeout["final_gates"]["realhomes_business_smoke"] == "40/40"
    assert closeout["final_gates"]["desktop_mobile_browsability"] == "26/26"
    assert closeout["final_gates"]["critical_log_errors"] == 0
    assert closeout["final_gates"]["verified_googlebot_on_both_new_roots"] is True
    assert evidence["interpretation"]["private_apply_or_rollback_is_public_plugin_output"] is False
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for version in ('"3.10"', '"3.12"', '"3.13"'):
        assert version in workflow
    assert "python scripts/verify.py" in workflow


def validate_public_dashboard(path: Path) -> None:
    dashboard = path.read_text(encoding="utf-8")
    assert "ProofRank" in dashboard
    assert "C:\\Users\\" not in dashboard
    assert not re.search(r"<script[^>]+src=", dashboard, re.IGNORECASE)
    assert not re.search(r"https?://[^\"']+\.(?:js|css)", dashboard, re.IGNORECASE)
    assert "Completeness gates" in dashboard
    assert "Declared source universe" in dashboard


def main() -> int:
    validate_manifest()
    validate_marketplace()
    validate_evidence_and_ci()
    run([sys.executable, str(SKILL / "scripts" / "test_prepare_sources.py")])
    run([sys.executable, str(SKILL / "scripts" / "test_site_graph_audit.py")])
    run([sys.executable, str(SKILL / "scripts" / "test_render_dashboard.py")])
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
        complete_decision = json.loads((output / "complete" / "decision.json").read_text(encoding="utf-8"))
        incomplete_decision = json.loads((output / "incomplete" / "decision.json").read_text(encoding="utf-8"))
        assert complete["coverage"]["graph_complete"] is True
        assert complete["coverage"]["source_manifest_declared"] is True
        assert complete["coverage"]["source_universe_complete"] is True
        assert complete["coverage"]["content_graph_complete"] is True
        assert complete["coverage"]["known_urls"] == 11
        assert complete["coverage"]["graph_eligible_urls"] == 10
        assert complete["coverage"]["resolved_non_graph_urls"] == 1
        assert complete["coverage"]["html_pages"] == 10
        assert complete["coverage"]["html_coverage"] == 1.0
        assert complete_decision == complete["release_contract"]
        assert complete_decision["decision"] == "READY_FOR_HUMAN_REVIEW"
        assert complete_decision["release_gate_passed"] is True
        assert complete_decision["live_change_authorized"] is False
        assert complete_decision["stages"]["source_universe"] == {
            "passed": True,
            "observed_normalized_identities": 11,
            "expected_normalized_identities": 11,
            "identity_count_matches": True,
        }
        assert complete_decision["stages"]["active_html"]["eligible_identities"] == 10
        assert complete_decision["stages"]["active_html"]["full_html_identities"] == 10
        assert complete_decision["stages"]["active_html"]["confirmed_terminal_identities"] == 1
        assert complete_decision["stages"]["active_html"]["passed"] is True
        assert incomplete["coverage"]["graph_complete"] is False
        assert incomplete["coverage"]["known_urls"] == 7
        assert incomplete["coverage"]["expected_source_identities"] == 11
        assert incomplete["coverage"]["observed_source_identities"] == 7
        assert incomplete["coverage"]["source_identity_count_matches"] is False
        assert incomplete["coverage"]["source_universe_complete"] is False
        assert incomplete["coverage"]["content_graph_complete"] is True
        assert incomplete["coverage"]["graph_eligible_urls"] == 7
        assert incomplete["coverage"]["html_pages"] == 7
        assert incomplete["coverage"]["html_coverage"] == 1.0
        assert incomplete_decision == incomplete["release_contract"]
        assert incomplete_decision["decision"] == "WITHHOLD"
        assert incomplete_decision["release_gate_passed"] is False
        assert incomplete_decision["live_change_authorized"] is False
        assert incomplete_decision["stages"]["source_universe"] == {
            "passed": False,
            "observed_normalized_identities": 7,
            "expected_normalized_identities": 11,
            "identity_count_matches": False,
        }
        assert incomplete_decision["stages"]["active_html"]["eligible_identities"] == 7
        assert incomplete_decision["stages"]["active_html"]["full_html_identities"] == 7
        assert incomplete_decision["stages"]["active_html"]["passed"] is True
        assert incomplete_decision["unclassified_count"] == 4
        assert incomplete_decision["blocker_codes"] == ["SOURCE_IDENTITY_COUNT_MISMATCH"]
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
            "evidence_boundary",
            "github_actions",
            "adapter_tests",
            "engine_tests",
            "dashboard_tests",
            "complete_demo",
            "incomplete_gate",
            "dashboard_boundary",
            "secret_scan",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
