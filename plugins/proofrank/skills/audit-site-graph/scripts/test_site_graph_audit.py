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
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                f"{site}": {"status": 200, "html": '<html lang="ru"><head><title>Главная</title></head><body><a href="/ru-a/">Пляжи</a><a href="/es/playas/">Playas</a></body></html>'},
                f"{site}ru-a/": {"status": 200, "html": f'<html lang="ru"><head><title>Пляжи города</title><script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"Пляжи города"}}</script></head><body><main><h1>Пляжи города</h1><p>{duplicated_text}</p></main></body></html>'},
                f"{site}ru-b/": {"status": 200, "html": f'<html lang="ru"><head><title>Лучшие пляжи города</title></head><body><main><h1>Пляжи города</h1><p>{duplicated_text}</p></main></body></html>'},
                f"{site}es/playas/": {"status": 200, "html": '<html lang="es"><head><title>Playas de Costa Demo</title><script type="application/ld+json">{"@type":</script></head><body><main><h1>Playas de Costa Demo</h1><p>Información práctica sobre playas españolas para familias y visitantes.</p></main></body></html>'},
            }}, ensure_ascii=False), encoding="utf-8")

            manifest = root / "source_manifest.json"
            manifest.write_text(json.dumps({
                "version": 1,
                "site": site,
                "universe_complete": True,
                "sources": [
                    {"id": "fixture-inventory", "kind": "inventory", "required": True, "status": "collected"},
                    {"id": "fixture-sitemaps", "kind": "sitemap", "required": True, "status": "collected"},
                ],
                "outputs": {
                    "inventory": {"path": inventory.name, "sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"path": cache.name, "sha256": MODULE.file_sha256(cache)},
                    "sitemaps": [
                        {"path": "sitemap_index.xml", "sha256": MODULE.file_sha256(root / "sitemap_index.xml")},
                        {"path": "post-sitemap.xml", "sha256": MODULE.file_sha256(root / "post-sitemap.xml")},
                        {"path": "page-sitemap.xml", "sha256": MODULE.file_sha256(root / "page-sitemap.xml")},
                    ],
                },
            }), encoding="utf-8")

            output = root / "out"
            code = MODULE.main([
                "--site", site,
                "--inventory", str(inventory),
                "--page-cache", str(cache),
                "--sitemap", str(root / "sitemap_index.xml"),
                "--source-manifest", str(manifest),
                "--output-dir", str(output),
            ])
            self.assertEqual(code, 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["coverage"]["graph_complete"])
            self.assertTrue(audit["coverage"]["content_graph_complete"])
            self.assertTrue(audit["coverage"]["source_universe_complete"])
            self.assertTrue(audit["coverage"]["source_manifest_declared"])
            self.assertEqual(audit["coverage"]["sitemap_urls"], 4)
            self.assertGreaterEqual(audit["finding_counts"].get("schema_parse_error", 0), 1)
            self.assertGreaterEqual(audit["finding_counts"].get("exact_duplicate_candidate", 0), 1)
            self.assertGreaterEqual(audit["finding_counts"].get("orphan_candidate", 0), 1)

    def test_manifest_is_required_for_whole_site_claims(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://proofrank.test/</loc></url></urlset>',
                encoding="utf-8",
            )
            cache = root / "cache.json"
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                site: {"status": 200, "html": "<html><body><main>Complete page</main></body></html>"},
            }}), encoding="utf-8")
            output = root / "out"
            self.assertEqual(MODULE.main([
                "--site", site,
                "--page-cache", str(cache),
                "--sitemap", str(sitemap),
                "--output-dir", str(output),
            ]), 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["coverage"]["content_graph_complete"])
            self.assertFalse(audit["coverage"]["source_manifest_declared"])
            self.assertFalse(audit["coverage"]["source_universe_complete"])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertIn("source_universe_not_declared", audit["finding_counts"])
            self.assertNotIn("orphan_candidate", audit["finding_counts"])

    def test_sitemap_only_uses_direct_page_and_child_locs(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sitemap_index.xml").write_text(
                '<?xml version="1.0"?><sitemapindex '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                '<sitemap><loc>https://proofrank.test/pages.xml</loc>'
                '<image:loc>https://proofrank.test/also-not-a-child-sitemap.xml</image:loc>'
                '<image:image><image:loc>https://proofrank.test/not-a-child-sitemap.xml</image:loc></image:image>'
                '</sitemap></sitemapindex>',
                encoding="utf-8",
            )
            (root / "pages.xml").write_text(
                '<?xml version="1.0"?><urlset '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" '
                'xmlns:video="http://www.google.com/schemas/sitemap-video/1.1" '
                'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
                '<url><loc>https://proofrank.test/real-page/</loc>'
                '<image:loc>https://proofrank.test/media/direct-photo.jpg</image:loc>'
                '<image:image><image:loc>https://proofrank.test/media/photo.jpg</image:loc></image:image>'
                '<video:video><video:content_loc>https://proofrank.test/media/movie.mp4</video:content_loc>'
                '<video:player_loc>https://proofrank.test/player/</video:player_loc></video:video>'
                '<news:news><news:publication><news:name>ProofRank</news:name></news:publication></news:news>'
                '</url></urlset>',
                encoding="utf-8",
            )

            data = MODULE.load_sitemaps([str(root / "sitemap_index.xml")], site, allow_network=False)
            self.assertEqual(data["urls"], {f"{site}real-page/"})
            self.assertEqual(len(data["resolved"]), 2)
            self.assertEqual(data["unresolved"], [])

    def test_required_unavailable_source_blocks_whole_site_claims(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://proofrank.test/</loc></url>'
                '<url><loc>https://proofrank.test/child/</loc></url>'
                '</urlset>',
                encoding="utf-8",
            )
            cache = root / "cache.json"
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                site: {"status": 200, "html": '<html><body><a href="/child/">Child</a></body></html>'},
                f"{site}child/": {"status": 200, "html": '<html><body><main>Child page</main></body></html>'},
            }}), encoding="utf-8")
            inventory = root / "inventory.csv"
            with inventory.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["url"])
                writer.writeheader()
                writer.writerows([{"url": site}, {"url": f"{site}child/"}])
            manifest = root / "sources.json"
            manifest.write_text(json.dumps({
                "version": 1,
                "site": site,
                "universe_complete": True,
                "sources": [
                    {"id": "cms-inventory", "kind": "inventory", "required": True, "status": "collected"},
                    {"id": "gsc-export", "kind": "gsc", "required": True, "status": "unavailable", "reason": "export not provided"},
                ],
                "outputs": {
                    "inventory": {"path": inventory.name, "sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"path": cache.name, "sha256": MODULE.file_sha256(cache)},
                    "sitemaps": [{"path": sitemap.name, "sha256": MODULE.file_sha256(sitemap)}],
                },
            }), encoding="utf-8")

            output = root / "out"
            code = MODULE.main([
                "--site", site,
                "--inventory", str(inventory),
                "--page-cache", str(cache),
                "--sitemap", str(sitemap),
                "--source-manifest", str(manifest),
                "--output-dir", str(output),
            ])
            self.assertEqual(code, 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["coverage"]["content_graph_complete"])
            self.assertFalse(audit["coverage"]["required_sources_complete"])
            self.assertFalse(audit["coverage"]["source_universe_complete"])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertEqual(audit["inputs"]["source_universe"]["required_source_count"], 2)
            self.assertEqual(
                audit["inputs"]["source_universe"]["required_sources_incomplete"][0]["id"],
                "gsc-export",
            )
            self.assertIn("source_universe_incomplete", audit["finding_counts"])
            self.assertIn("graph_claims_withheld", audit["finding_counts"])
            self.assertNotIn("orphan_candidate", audit["finding_counts"])
            withheld = [item for item in audit["findings"] if item["type"] == "graph_claims_withheld"]
            self.assertIn("source universe complete=no", withheld[0]["evidence"])

    def test_manifest_requires_explicit_complete_declaration_and_a_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            implicit = root / "implicit.json"
            implicit.write_text(json.dumps({
                "version": 1,
                "sources": [
                    {"id": "inventory", "kind": "inventory", "required": True, "status": "collected"},
                ],
            }), encoding="utf-8")
            self.assertFalse(MODULE.load_source_manifest(str(implicit))["source_universe_complete"])

            empty = root / "empty.json"
            empty.write_text(json.dumps({
                "version": 1,
                "universe_complete": True,
                "sources": [],
            }), encoding="utf-8")
            self.assertFalse(MODULE.load_source_manifest(str(empty))["source_universe_complete"])

            invalid_count = root / "invalid-count.json"
            invalid_count.write_text(json.dumps({
                "expected_normalized_identities": "eleven",
                "sources": [],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected_normalized_identities"):
                MODULE.load_source_manifest(str(invalid_count))

    def test_manifest_requires_site_required_source_and_inventory_hash_binding(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            inventory.write_text("url\nhttps://proofrank.test/\n", encoding="utf-8")

            def evaluate(**overrides):
                data = {
                    "version": 1,
                    "site": site,
                    "universe_complete": True,
                    "sources": [{"id": "inventory", "kind": "inventory", "required": True, "status": "collected"}],
                    "outputs": {"inventory": {"path": inventory.name, "sha256": MODULE.file_sha256(inventory)}},
                }
                data.update(overrides)
                manifest = root / "manifest.json"
                manifest.write_text(json.dumps(data), encoding="utf-8")
                return MODULE.load_source_manifest(str(manifest), expected_site=site, inventory_paths=[str(inventory)])

            self.assertTrue(evaluate()["source_universe_complete"])
            self.assertFalse(evaluate(site="/")["source_universe_complete"])
            self.assertFalse(evaluate(site="https://other.test/")["source_universe_complete"])
            self.assertFalse(evaluate(sources=[{"id": "optional", "kind": "gsc", "required": False, "status": "collected"}])["source_universe_complete"])
            self.assertFalse(evaluate(sources=[{"id": "sitemap", "kind": "sitemap", "required": True, "status": "collected"}])["source_universe_complete"])
            self.assertFalse(evaluate(outputs={"inventory": {"path": inventory.name, "sha256": "0" * 64}})["source_universe_complete"])

            extra_inventory = root / "extra.csv"
            extra_inventory.write_text("url\nhttps://proofrank.test/extra/\n", encoding="utf-8")
            self.assertFalse(MODULE.load_source_manifest(
                str(root / "manifest.json"),
                expected_site=site,
                inventory_paths=[str(inventory), str(extra_inventory)],
            )["source_universe_complete"])

            cache = root / "cache.json"
            cache.write_text('{"pages": {}}', encoding="utf-8")
            other_cache = root / "other-cache.json"
            other_cache.write_text('{"pages": {"different": {}}}', encoding="utf-8")
            data = {
                "version": 1,
                "site": site,
                "universe_complete": True,
                "sources": [{"id": "inventory", "kind": "inventory", "required": True, "status": "collected"}],
                "outputs": {
                    "inventory": {"sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"sha256": MODULE.file_sha256(cache)},
                },
            }
            manifest = root / "cache-manifest.json"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(MODULE.load_source_manifest(
                str(manifest), expected_site=site, inventory_paths=[str(inventory)], page_cache_path=str(cache)
            )["source_universe_complete"])
            self.assertFalse(MODULE.load_source_manifest(
                str(manifest), expected_site=site, inventory_paths=[str(inventory)], page_cache_path=str(other_cache)
            )["source_universe_complete"])

    def test_non_2xx_cross_origin_and_truncated_html_do_not_pass_content_gate(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            urls = [site, f"{site}error/", f"{site}external/", f"{site}truncated/"]
            inventory = root / "inventory.csv"
            with inventory.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["url"])
                writer.writeheader()
                writer.writerows({"url": url} for url in urls)
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + "".join(f"<url><loc>{url}</loc></url>" for url in urls)
                + "</urlset>",
                encoding="utf-8",
            )
            cache = root / "cache.json"
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                site: {"status": 200, "final_url": site, "html": "<html><body>Home</body></html>"},
                f"{site}error/": {"status": 500, "final_url": f"{site}error/", "html": "<html><body>Error</body></html>"},
                f"{site}external/": {"status": 200, "final_url": "https://other.test/", "html": "<html><body>External</body></html>"},
                f"{site}truncated/": {"status": 200, "final_url": f"{site}truncated/", "html": "<html><body>Partial</body></html>", "truncated": True},
            }}), encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "version": 1,
                "site": site,
                "universe_complete": True,
                "sources": [{"id": "inventory", "kind": "inventory", "required": True, "status": "collected"}],
                "outputs": {
                    "inventory": {"path": inventory.name, "sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"path": cache.name, "sha256": MODULE.file_sha256(cache)},
                    "sitemaps": [{"path": sitemap.name, "sha256": MODULE.file_sha256(sitemap)}],
                },
            }), encoding="utf-8")
            output = root / "out"
            self.assertEqual(MODULE.main([
                "--site", site,
                "--inventory", str(inventory),
                "--page-cache", str(cache),
                "--sitemap", str(sitemap),
                "--source-manifest", str(manifest),
                "--output-dir", str(output),
            ]), 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue(audit["coverage"]["source_universe_complete"])
            self.assertEqual(audit["coverage"]["graph_eligible_urls"], 4)
            self.assertEqual(audit["coverage"]["resolved_non_graph_urls"], 0)
            self.assertEqual(audit["coverage"]["html_pages"], 1)
            self.assertFalse(audit["coverage"]["content_graph_complete"])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertEqual(audit["finding_counts"].get("html_evidence_excluded"), 1)

    def test_cross_origin_redirect_is_blocked_before_following(self):
        handler = MODULE.SameOriginRedirectHandler("https://proofrank.test/")
        request = MODULE.urllib.request.Request("https://proofrank.test/start/")
        with self.assertRaises(PermissionError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://other.test/")

    def test_unknown_cached_target_is_not_a_confirmed_broken_link(self):
        site = "https://proofrank.test/"
        target = f"{site}unknown/"
        analyses = {
            site: {"status": 200, "html_available": True, "noindex": False, "canonical": ""},
            target: {"status": 0, "html_available": False, "noindex": False, "canonical": ""},
        }
        findings = []
        MODULE.build_graph(
            {site: {}, target: {}},
            analyses,
            [{"source": site, "target": target, "anchor": "Unknown", "rel": "", "location": "content"}],
            site,
            False,
            findings,
        )
        self.assertNotIn("broken_internal_link", {item["type"] for item in findings})
        unverified = [item for item in findings if item["type"] == "link_target_unverified"]
        self.assertEqual(len(unverified), 1)
        self.assertEqual(unverified[0]["status"], "withheld")

    def test_saved_html_requires_explicit_completeness_and_row_false_overrides_default(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache.json"
            cache.write_text(json.dumps({
                "html_complete": True,
                "pages": {
                    site: {
                        "status": 200,
                        "final_url": site,
                        "html": "<html><body>Snippet</body></html>",
                        "html_complete": False,
                    },
                    f"{site}unknown/": {
                        "status": 200,
                        "final_url": f"{site}unknown/",
                        "html": "<html><body>Unattested</body></html>",
                        "html_complete": "false",
                    },
                },
            }), encoding="utf-8")
            loaded = MODULE.load_page_cache(str(cache), site)
            self.assertFalse(loaded[site]["html_complete"])
            self.assertFalse(loaded[f"{site}unknown/"]["html_complete"])
            analyses, _, _ = MODULE.parse_cached_pages(loaded, {}, site, [])
            self.assertFalse(analyses[site]["html_available"])
            self.assertFalse(analyses[f"{site}unknown/"]["html_available"])

    def test_conflicting_full_html_snapshots_cannot_pass_topology_gate(self):
        site = "https://proofrank.test/"
        cache = {
            site: {
                "url": site,
                "status": 200,
                "final_url": site,
                "html": '<html><body><a href="/possibly-hidden/">Hidden in other snapshot</a></body></html>',
                "html_complete": True,
                "truncated": False,
                "conflicting_snapshots": True,
            }
        }
        findings = []
        analyses, links, _ = MODULE.parse_cached_pages(cache, {site: {}}, site, findings)
        self.assertFalse(analyses[site]["html_available"])
        self.assertEqual(links, [])

    def test_undeclared_internal_link_contradicts_universe_and_blocks_gate(self):
        site = "https://proofrank.test/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            inventory.write_text(f"url\n{site}\n", encoding="utf-8")
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{site}</loc></url></urlset>", encoding="utf-8"
            )
            cache = root / "cache.json"
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                site: {"status": 200, "final_url": site, "html": '<html><body><a href="/undeclared/">New</a></body></html>'},
            }}), encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "site": site,
                "universe_complete": True,
                "sources": [{"id": "inventory", "kind": "inventory", "required": True, "status": "collected"}],
                "outputs": {
                    "inventory": {"sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"sha256": MODULE.file_sha256(cache)},
                    "sitemaps": [{"sha256": MODULE.file_sha256(sitemap)}],
                },
            }), encoding="utf-8")
            output = root / "out"
            self.assertEqual(MODULE.main([
                "--site", site, "--inventory", str(inventory), "--page-cache", str(cache),
                "--sitemap", str(sitemap), "--source-manifest", str(manifest),
                "--output-dir", str(output),
            ]), 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["coverage"]["known_urls"], 2)
            self.assertEqual(audit["coverage"]["html_pages"], 1)
            self.assertFalse(audit["coverage"]["source_universe_complete"])
            self.assertFalse(audit["coverage"]["content_graph_complete"])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertIn("source_universe_contradicted", audit["finding_counts"])

    def test_redirect_destination_is_a_distinct_uncovered_identity(self):
        site = "https://proofrank.test/"
        destination = f"{site}en/"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            inventory.write_text(f"url\n{site}\n", encoding="utf-8")
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{site}</loc></url></urlset>", encoding="utf-8"
            )
            cache = root / "cache.json"
            cache.write_text(json.dumps({"html_complete": True, "pages": {
                site: {"status": 200, "final_url": destination, "html": '<html><body><a href="/en/about/">About</a></body></html>'},
            }}), encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "site": site,
                "universe_complete": True,
                "sources": [{"id": "inventory", "kind": "inventory", "required": True, "status": "collected"}],
                "outputs": {
                    "inventory": {"sha256": MODULE.file_sha256(inventory)},
                    "page_cache": {"sha256": MODULE.file_sha256(cache)},
                    "sitemaps": [{"sha256": MODULE.file_sha256(sitemap)}],
                },
            }), encoding="utf-8")
            output = root / "out"
            self.assertEqual(MODULE.main([
                "--site", site, "--inventory", str(inventory), "--page-cache", str(cache),
                "--sitemap", str(sitemap), "--source-manifest", str(manifest),
                "--output-dir", str(output),
            ]), 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["coverage"]["known_urls"], 2)
            self.assertEqual(audit["coverage"]["resolved_non_graph_urls"], 1)
            self.assertEqual(audit["coverage"]["graph_eligible_urls"], 1)
            self.assertEqual(audit["coverage"]["html_pages"], 0)
            self.assertEqual(audit["links"], [])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertIn("source_universe_contradicted", audit["finding_counts"])

    def test_topology_completeness_threshold_cannot_be_lowered(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit):
                MODULE.main([
                    "--site", "https://proofrank.test/",
                    "--complete-threshold", "0.95",
                    "--output-dir", str(Path(temp) / "out"),
                ])

    def test_real_world_99_87_percent_is_not_complete(self):
        self.assertFalse(MODULE.content_gate_passes(3141, 3137, True, 0))
        self.assertTrue(MODULE.content_gate_passes(3141, 3141, True, 0))

    def test_csv_formula_text_is_neutralized(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "out.csv"
            MODULE.write_csv(path, [{"title": "=WEBSERVICE(\"https://evil.test\")", "count": -1}], ["title", "count"])
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertTrue(row["title"].startswith("'="))
            self.assertEqual(row["count"], "-1")

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
            self.assertEqual(audit["coverage"]["known_urls"], 7)
            self.assertEqual(audit["coverage"]["graph_eligible_urls"], 7)
            self.assertEqual(audit["coverage"]["html_pages"], 7)
            self.assertEqual(audit["coverage"]["html_coverage"], 1.0)
            self.assertTrue(audit["coverage"]["content_graph_complete"])
            self.assertEqual(audit["coverage"]["observed_source_identities"], 7)
            self.assertEqual(audit["coverage"]["expected_source_identities"], 11)
            self.assertFalse(audit["coverage"]["source_identity_count_matches"])
            self.assertFalse(audit["coverage"]["source_universe_complete"])
            self.assertFalse(audit["coverage"]["graph_complete"])
            self.assertFalse(audit["inputs"]["network_enabled"])
            self.assertFalse(audit["inputs"]["crawl_enabled"])
            self.assertTrue((output / "dashboard.html").is_file())

            partial_cache = json.loads((output / "page_cache.incomplete.json").read_text(encoding="utf-8"))
            self.assertEqual(partial_cache["scenario"], "incomplete-source-universe")
            self.assertEqual(len(partial_cache["pages"]), 7)
            self.assertIn("https://costa-demo.example/", partial_cache["pages"])

            decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
            self.assertEqual(decision, audit["release_contract"])
            self.assertEqual(decision["decision"], "WITHHOLD")
            self.assertFalse(decision["release_gate_passed"])
            self.assertFalse(decision["live_change_authorized"])
            self.assertEqual(decision["scope_assurance"], "DECLARED_SCOPE_INCOMPLETE")
            self.assertIn("operator-declared source scope", decision["scope_warning"])
            self.assertFalse(decision["stages"]["source_universe"]["passed"])
            self.assertEqual(
                decision["stages"]["source_universe"]["expected_count_origin"],
                "SYNTHETIC_CONTROL_FIXTURE",
            )
            self.assertTrue(decision["stages"]["active_html"]["passed"])
            self.assertEqual(decision["stages"]["active_html"]["eligible_identities"], 7)
            self.assertEqual(decision["stages"]["active_html"]["full_html_identities"], 7)
            self.assertEqual(decision["unclassified_count"], 4)
            self.assertIn("SOURCE_IDENTITY_COUNT_MISMATCH", decision["blocker_codes"])
            self.assertEqual(len(decision["evidence_hashes"]["page_cache"]), 64)

            withheld = [item for item in audit["findings"] if item["type"] == "graph_claims_withheld"]
            self.assertEqual(len(withheld), 1)
            self.assertEqual(withheld[0]["status"], "withheld")
            self.assertIn("100.00% (7/7)", withheld[0]["evidence"])
            self.assertIn("source universe complete=no", withheld[0]["evidence"])
            self.assertNotIn("orphan_candidate", audit["finding_counts"])
            self.assertNotIn("unreachable_from_home_candidate", audit["finding_counts"])
            self.assertNotIn("internal_link_opportunity", audit["finding_counts"])

            gated_output = Path(temp) / "gated-incomplete"
            self.assertEqual(MODULE.main([
                "--site", RUN_DEMO.SITE,
                "--inventory", str(output / "inventory.incomplete.csv"),
                "--page-cache", str(output / "page_cache.incomplete.json"),
                "--sitemap", str(output / "sitemap.incomplete.xml"),
                "--source-manifest", str(output / "source_manifest.json"),
                "--output-dir", str(gated_output),
                "--gate-exit-code",
            ]), 2)

    def test_bundled_complete_demo_classifies_terminal_url_and_is_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "complete"
            self.assertEqual(RUN_DEMO.main([
                "--scenario", "complete",
                "--output-dir", str(output),
            ]), 0)
            audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
            coverage = audit["coverage"]
            self.assertEqual(coverage["observed_source_identities"], 11)
            self.assertEqual(coverage["expected_source_identities"], 11)
            self.assertTrue(coverage["source_identity_count_matches"])
            self.assertEqual(coverage["known_urls"], 11)
            self.assertEqual(coverage["resolved_non_graph_urls"], 1)
            self.assertEqual(coverage["graph_eligible_urls"], 10)
            self.assertEqual(coverage["html_pages"], 10)
            self.assertTrue(coverage["content_graph_complete"])
            self.assertTrue(coverage["graph_complete"])

            decision = audit["release_contract"]
            self.assertEqual(decision["decision"], "READY_FOR_HUMAN_REVIEW")
            self.assertTrue(decision["release_gate_passed"])
            self.assertFalse(decision["live_change_authorized"])
            self.assertEqual(decision["scope_assurance"], "DECLARED_SCOPE_BOUND")
            self.assertEqual(audit["scope_assurance"], "DECLARED_SCOPE_BOUND")
            self.assertEqual(decision["stages"]["active_html"]["confirmed_terminal_identities"], 1)
            self.assertEqual(decision["unclassified_count"], 0)
            self.assertEqual(decision["blocker_codes"], [])
            self.assertEqual(
                json.loads((output / "decision.json").read_text(encoding="utf-8")),
                decision,
            )

            demo_dir = RUN_DEMO_SCRIPT.resolve().parent.parents[2] / "demo"
            self.assertEqual(MODULE.main([
                "--site", RUN_DEMO.SITE,
                "--inventory", str(demo_dir / "inventory.csv"),
                "--page-cache", str(demo_dir / "page_cache.json"),
                "--sitemap", str(demo_dir / "sitemap.xml"),
                "--source-manifest", str(output / "source_manifest.json"),
                "--output-dir", str(Path(temp) / "gated-complete"),
                "--gate-exit-code",
            ]), 0)


if __name__ == "__main__":
    unittest.main()
