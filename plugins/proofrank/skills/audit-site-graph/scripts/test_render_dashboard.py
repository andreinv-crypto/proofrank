#!/usr/bin/env python3
"""Regression tests for the dashboard's two-stage completeness display."""

from __future__ import annotations

import base64
import json
import re
import tempfile
import unittest
from pathlib import Path

import render_dashboard


def minimal_audit(*, source_universe: dict | None, content_complete: bool, graph_complete: bool) -> dict:
    audit = {
        "generated_at": "2026-07-20T12:00:00Z",
        "mode": "offline",
        "site": "https://example.test/",
        "coverage": {
            "known_urls": 10,
            "sitemap_urls": 10,
            "html_pages": 10 if content_complete else 7,
            "html_coverage": 1.0 if content_complete else 0.7,
            "homepage_parsed": True,
            "unresolved_sitemaps": 0,
            "complete_threshold": 1.0,
            "content_graph_complete": content_complete,
            "graph_complete": graph_complete,
        },
        "finding_counts": {},
        "findings": [],
        "pages": [],
        "decision_boundary": "Human review is still required before any URL action.",
    }
    if source_universe is not None:
        audit["inputs"] = {"source_universe": source_universe}
    return audit


def render_and_decode(audit: dict) -> tuple[str, dict]:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        audit_path = root / "audit.json"
        output_path = root / "dashboard.html"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        render_dashboard.render(audit_path, output_path)
        html = output_path.read_text(encoding="utf-8")
    match = re.search(r'atob\("([A-Za-z0-9+/=]+)"\)', html)
    if not match:
        raise AssertionError("Embedded dashboard payload was not found")
    payload = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
    return html, payload


class DashboardCompletenessTests(unittest.TestCase):
    def test_declared_complete_source_and_content_gates(self) -> None:
        source_universe = {
            "declared": True,
            "path": r"C:\Private\source_manifest.json",
            "universe_declared_complete": True,
            "required_sources_complete": True,
            "site_matches": True,
            "inventory_binding_complete": True,
            "page_cache_binding_complete": True,
            "sitemap_binding_complete": True,
            "input_binding_complete": True,
            "source_universe_complete": True,
            "required_source_count": 2,
            "sources": [
                {
                    "id": "gsc-pages",
                    "kind": "gsc",
                    "required": True,
                    "status": "collected",
                    "records": 1240,
                    "path": r"C:\Private\gsc.csv",
                },
                {
                    "id": "wordpress",
                    "kind": "cms",
                    "required": True,
                    "status": "loaded",
                    "records": "980",
                    "note": "private operator note",
                },
            ],
        }
        html, payload = render_and_decode(
            minimal_audit(source_universe=source_universe, content_complete=True, graph_complete=True)
        )

        self.assertEqual(payload["completeness"]["source_label"], "Declared scope bound")
        self.assertEqual(payload["completeness"]["content_label"], "Coverage passed")
        self.assertEqual(payload["completeness"]["final_label"], "Gate passed")
        self.assertTrue(payload["completeness"]["gate_passed"])
        self.assertEqual(payload["release_contract"]["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(payload["release_contract"]["release_gate_passed"])
        self.assertFalse(payload["release_contract"]["live_change_authorized"])
        self.assertEqual(payload["source_universe"]["sources"][0]["records"], 1240)
        self.assertEqual(payload["source_universe"]["sources"][1]["records"], 980)
        self.assertIn("Declared source scope → usable active HTML → final gate", html)
        self.assertIn("observed / expected", html)
        self.assertIn("usable / graph-eligible", html)
        self.assertIn("Owner / release view", html)
        self.assertIn("decision.json", html)
        self.assertNotIn(r"C:\Private", html)
        self.assertNotIn("private operator note", html)

    def test_incomplete_source_universe_withholds_whole_site_claims(self) -> None:
        source_universe = {
            "declared": True,
            "universe_declared_complete": True,
            "required_sources_complete": False,
            "site_matches": True,
            "inventory_binding_complete": True,
            "page_cache_binding_complete": True,
            "sitemap_binding_complete": True,
            "input_binding_complete": True,
            "source_universe_complete": False,
            "required_source_count": 2,
            "sources": [
                {"id": "gsc-pages", "kind": "gsc", "required": True, "status": "collected"},
                {"id": "cms", "kind": "wordpress", "required": True, "status": "attempted-unavailable"},
            ],
        }
        _, payload = render_and_decode(
            minimal_audit(source_universe=source_universe, content_complete=True, graph_complete=False)
        )

        completeness = payload["completeness"]
        self.assertEqual(completeness["source_label"], "Declared scope incomplete")
        self.assertEqual(completeness["content_label"], "Coverage passed")
        self.assertEqual(completeness["final_label"], "Withheld")
        self.assertEqual(completeness["headline"], "Declared source scope incomplete")
        self.assertIn("Whole-site graph claims are withheld", completeness["boundary"])
        self.assertFalse(completeness["gate_passed"])
        self.assertEqual(payload["release_contract"]["decision"], "WITHHOLD")
        self.assertFalse(payload["release_contract"]["live_change_authorized"])

    def test_release_contract_is_public_safe_and_preserved(self) -> None:
        source_universe = {
            "declared": True,
            "universe_declared_complete": True,
            "required_sources_complete": True,
            "site_matches": True,
            "inventory_binding_complete": True,
            "page_cache_binding_complete": True,
            "sitemap_binding_complete": True,
            "input_binding_complete": True,
            "source_universe_complete": False,
            "expected_normalized_identities": 11,
            "observed_normalized_identities": 7,
            "identity_count_matches": False,
            "required_source_count": 2,
            "sources": [],
        }
        audit = minimal_audit(source_universe=source_universe, content_complete=True, graph_complete=False)
        audit["release_contract"] = {
            "schema_version": "1.0",
            "decision": "WITHHOLD",
            "release_gate_passed": False,
            "live_change_authorized": False,
            "unclassified_count": 4,
            "blocker_codes": ["SOURCE_IDENTITY_COUNT_MISMATCH"],
            "stages": {"source_universe": {"passed": False}, "active_html": {"passed": True}},
            "decision_boundary": "Read-only evidence result.",
            "evidence_hashes": {"private_path": r"C:\\Private\\input.csv"},
        }
        html, payload = render_and_decode(audit)

        self.assertEqual(payload["source_universe"]["observed_normalized_identities"], 7)
        self.assertEqual(payload["source_universe"]["expected_normalized_identities"], 11)
        self.assertEqual(payload["source_universe"]["scope_assurance"], "DECLARED_SCOPE_INCOMPLETE")
        self.assertEqual(payload["release_contract"]["unclassified_count"], 4)
        self.assertEqual(payload["release_contract"]["blocker_codes"], ["SOURCE_IDENTITY_COUNT_MISMATCH"])
        self.assertNotIn("evidence_hashes", payload["release_contract"])
        self.assertNotIn(r"C:\\Private", html)

    def test_legacy_audit_is_not_presented_as_proven(self) -> None:
        _, payload = render_and_decode(
            minimal_audit(source_universe=None, content_complete=True, graph_complete=True)
        )

        completeness = payload["completeness"]
        self.assertEqual(completeness["source_label"], "Legacy / not declared")
        self.assertEqual(completeness["content_label"], "Coverage passed")
        self.assertEqual(completeness["final_label"], "Legacy / not proven")
        self.assertEqual(completeness["headline"], "Legacy audit — manifest not declared")
        self.assertIn("Whole-site graph completeness is not established", completeness["boundary"])
        self.assertFalse(completeness["gate_passed"])


if __name__ == "__main__":
    unittest.main()
