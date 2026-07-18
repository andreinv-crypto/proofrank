#!/usr/bin/env python3
"""Focused tests for the deterministic ProofRank site-graph audit."""

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("site_graph_audit.py")
SPEC = importlib.util.spec_from_file_location("site_graph_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

RUN_DEMO_SCRIPT = Path(__file__).with_name("run_demo.py")
RUN_DEMO_SPEC = importlib.util.spec_from_file_location("run_demo", RUN_DEMO_SCRIPT)
RUN_DEMO = importlib.util.module_from_spec(RUN_DEMO_SPEC)
RUN_DEMO_SPEC.loader.exec_module(RUN_DEMO)


class SiteGraphAuditTests(unittest.TestCase):
    def test_unicode_url_and_tokens(self):
        site = "https://proofrank.test/"
        plain = MODULE.normalize_url("/тест/", site)
        encoded = MODULE.normalize_url("/%D1%82%D0%B5%D1%81%D1%82/", site)
        self.assertEqual(plain, encoded)
        tokens = MODULE.tokenize("Пляжи города y las playas españolas")
        self.assertIn("пляжи", tokens)
        self.assertIn("españolas", tokens)

    def test_recursive_local_sitemap_and_full_fixture(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sitemap_index.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<sitemap><loc>https://proofrank.test/post-sitemap.xml</loc></sitemap>'
                '<sitemap><loc>https://proofrank.test/page-sitemap.xml</loc></sitemap>'
                '</sitemapindex>', encoding="utf-8")
            (root / "post-sitemap.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://proofrank.test/ru-a/</loc></url>'
                '<url><loc>https://proofrank.test/ru-b/</loc></url>'
                '</urlset>', encoding="utf-8")
            (root / "page-sitemap.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://proofrank.test/</loc></url>'
                '<url><loc>https://proofrank.test/es/playas/</loc></url>'
                '</urlset>', encoding="utf-8")

            inventory = root / "inventory.csv"
            with inventory.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["path", "title", "mechanismLane", "latestImpressions", "topQueries"])
                writer.writeheader()
                writer.writerows([
                    {"path": "/", "title": "Главная", "mechanismLane": "content", "latestImpressions": 10},
                    {"path": "/ru-a/", "title": "Пляжи города", "mechanismLane": "content", "latestImpressions": 100, "topQueries": "пляжи города"},
                    {"path": "/ru-b/", "title": "Лучшие пляжи города", "mechanismLane": "content", "latestImpressions": 50, "topQueries": "пляжи города"},
                    {"path": "/es/playas/", "title": "Playas de Costa Demo", "mechanismLane": "localized_content", "latestImpressions": 20},
                ])

            duplicated_text = " ".join(["Пляжи города подходят для семейного отдыха и прогулок у моря."] * 12)
            cache = root / "cache.json"
            cache.write_text(json.dumps({"pages": {
                f"{site}": {"status": 200, "html": '<html lang="ru"><head><title>Главная</title></head><body><a href="/ru-a/">Пляжи</a><a href="/es/playas/">Playas</a></body></html>'},
                f"{site}ru-a/": {"status": 200, "html": f'<html lang="ru"><head><title>Пляжи города</title><script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"Пляжи города"}}</script></head><body><main><h1>Пляжи города</h1><p>{duplicated_text}</p></main></body></html>'},
                f"{site}ru-b/": {"status": 200, "html": f'<html lang="ru"><head><title>Лучшие пляжи города</title></head><body><main><h1>Пляжи города</h1><p>{duplicated_text}</p></main></body></html>'},
                f"{site}es/playas/": {"status": 200, "html": '<html lang="es"><head><title>Playas de Costa Demo</title><script type="application/ld+json">{"@type":</script></head><body><main><h1>Playas de Costa Demo</h1><p>Información práctica sobre playas españolas para familias y visitantes.</p></main></body></html>'},
            }}, ensure_ascii=False), encoding="utf-8")

            output = root / "out"
            code = MODULE.main([
                "--site", site,
                "--inventory", str(inventory),
                "--page-cache", str(cache),
                "--sitemap", str(root / "sitemap_index.xml"),
                "--output-dir", str(output),
            ])
            self.assertEqual(code, 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["coverage"]["graph_complete"])
            self.assertEqual(audit["coverage"]["sitemap_urls"], 4)
            self.assertGreaterEqual(audit["finding_counts"].get("schema_parse_error", 0), 1)
            self.assertGreaterEqual(audit["finding_counts"].get("exact_duplicate_candidate", 0), 1)
            self.assertGreaterEqual(audit["finding_counts"].get("orphan_candidate", 0), 1)

    def test_inventory_only_withholds_graph_claims_and_separates_amp(self):
        site = "https://proofrank.test/"
        self.assertEqual(
            MODULE.infer_lane(f"{site}es/en/fishing/amp/", "localized_content"),
            "legacy_amp",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            with inventory.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["url", "title", "latestImpressions", "sitemap"])
                writer.writeheader()
                writer.writerows([
                    {"url": site, "title": "Главная", "latestImpressions": 10, "sitemap": "post-sitemap.xml"},
                    {"url": f"{site}example/", "title": "Пример", "latestImpressions": 5, "sitemap": "post-sitemap.xml"},
                ])

            output = root / "out"
            code = MODULE.main([
                "--site", site,
                "--inventory", str(inventory),
                "--output-dir", str(output),
            ])
            self.assertEqual(code, 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertEqual(audit["coverage"]["sitemap_urls"], 2)
            self.assertNotIn("orphan_candidate", audit["finding_counts"])
            self.assertNotIn("unreachable_from_home_candidate", audit["finding_counts"])
            self.assertNotIn("internal_link_opportunity", audit["finding_counts"])
            withheld = [item for item in audit["findings"] if item["type"] == "graph_claims_withheld"]
            self.assertEqual(len(withheld), 1)
            self.assertEqual(withheld[0]["status"], "withheld")
            self.assertIn("Whole-site orphan", withheld[0]["evidence"])

    def test_bundled_incomplete_demo_uses_same_fixture_and_withholds_graph_claims(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "incomplete"
            code = RUN_DEMO.main([
                "--scenario", "incomplete",
                "--output-dir", str(output),
            ])
            self.assertEqual(code, 0)

            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["coverage"]["known_urls"], 11)
            self.assertEqual(audit["coverage"]["html_pages"], 7)
            self.assertAlmostEqual(audit["coverage"]["html_coverage"], 7 / 11)
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertFalse(audit["inputs"]["network_enabled"])
            self.assertFalse(audit["inputs"]["crawl_enabled"])
            self.assertTrue((output / "dashboard.html").is_file())

            partial_cache = json.loads((output / "page_cache.incomplete.json").read_text(encoding="utf-8"))
            self.assertEqual(partial_cache["scenario"], "incomplete-coverage")
            self.assertEqual(len(partial_cache["pages"]), 7)
            self.assertIn("https://costa-demo.example/", partial_cache["pages"])

            withheld = [item for item in audit["findings"] if item["type"] == "graph_claims_withheld"]
            self.assertEqual(len(withheld), 1)
            self.assertEqual(withheld[0]["status"], "withheld")
            self.assertIn("63.64% (7/11)", withheld[0]["evidence"])
            self.assertNotIn("orphan_candidate", audit["finding_counts"])
            self.assertNotIn("unreachable_from_home_candidate", audit["finding_counts"])
            self.assertNotIn("internal_link_opportunity", audit["finding_counts"])


if __name__ == "__main__":
    unittest.main()
