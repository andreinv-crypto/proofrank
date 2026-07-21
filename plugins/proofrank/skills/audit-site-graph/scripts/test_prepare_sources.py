#!/usr/bin/env python3
"""Regression tests for ProofRank's credential-free export adapters."""

from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_sources.py")
SPEC = importlib.util.spec_from_file_location("prepare_sources", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class PrepareSourcesTests(unittest.TestCase):
    site = "https://proofrank.test/"

    def run_prepare(self, root: Path, *args: str) -> tuple[dict, Path]:
        out = root / "out"
        code = MODULE.main(["--site", self.site, *args, "--output-dir", str(out)])
        self.assertEqual(code, 0)
        return json.loads((out / "source_manifest.json").read_text(encoding="utf-8")), out

    def test_exports_merge_metrics_queries_and_generic_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gsc = root / "client-secret-name.csv"
            write_csv(gsc, ["Page", "Query", "Clicks", "Impressions", "CTR", "Position"], [
                {"Page": f"{self.site}guide/?a=1", "Query": "beach one", "Clicks": 2, "Impressions": 20, "CTR": "10%", "Position": 9},
                {"Page": f"{self.site}guide/?a=2", "Query": "beach two", "Clicks": 3, "Impressions": 30, "CTR": "10%", "Position": 7},
            ])
            wp = root / "wp.json"
            wp.write_text(json.dumps([
                {"live_url": self.site, "post_type": "page", "post_status": "publish", "post_title": "Home", "post_id": 1},
                {"live_url": f"{self.site}guide/", "post_type": "post", "post_status": "publish", "post_title": "Guide", "language_code": "en"},
            ]), encoding="utf-8")
            crawl = root / "crawl.csv"
            write_csv(crawl, ["Address", "Status Code", "Content Type", "Title 1", "H1-1", "Crawl Depth"], [
                {"Address": f"{self.site}guide/", "Status Code": 200, "Content Type": "text/html", "Title 1": "Guide", "H1-1": "Guide", "Crawl Depth": 2},
            ])
            manifest, out = self.run_prepare(
                root,
                "--gsc", str(gsc), "--wordpress", str(wp), "--crawler", str(crawl),
                "--require", "gsc", "--require", "wordpress", "--require", "crawler",
                "--declare-source-universe-complete",
            )
            self.assertTrue(manifest["universe_complete"])
            self.assertEqual(manifest["normalized_unique_urls"], 2)
            self.assertEqual(manifest["expected_normalized_identities"], 2)
            self.assertEqual({item["id"] for item in manifest["sources"]}, {"gsc-1", "wordpress-1", "crawler-1"})
            self.assertNotIn("client-secret-name", "|".join(item["id"] for item in manifest["sources"]))
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                rows = {row["url"]: row for row in csv.DictReader(handle)}
            self.assertEqual(manifest["expected_normalized_identities"], len(rows))
            guide = rows[f"{self.site}guide/"]
            self.assertEqual(guide["latestClicks"], "5.0")
            self.assertEqual(guide["latestImpressions"], "50.0")
            self.assertAlmostEqual(float(guide["gscCtr"]), 0.1)
            self.assertAlmostEqual(float(guide["gscPosition"]), 7.8)
            self.assertEqual(guide["gscMetricSource"], "gsc-1")
            self.assertEqual(guide["topQueries"], "beach one | beach two")
            self.assertEqual(guide["sourceTypes"], "crawler,gsc,wordpress")
            self.assertEqual(guide["language"], "en")

    def test_declaration_is_explicit_and_all_required_rows_must_be_collected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            write_csv(inventory, ["url"], [{"url": self.site}])
            implicit, _ = self.run_prepare(root, "--inventory", str(inventory))
            self.assertFalse(implicit["universe_complete"])

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            write_csv(inventory, ["url"], [{"url": self.site}])
            explicit, _ = self.run_prepare(root, "--inventory", str(inventory), "--declare-source-universe-complete")
            self.assertTrue(explicit["universe_complete"])

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gsc = root / "gsc.csv"
            write_csv(gsc, ["Page", "Clicks"], [{"Page": self.site, "Clicks": 1}])
            mixed, _ = self.run_prepare(
                root, "--gsc", str(gsc), "--require", "gsc",
                "--unavailable", "gsc=second property unavailable", "--declare-source-universe-complete",
            )
            self.assertFalse(mixed["universe_complete"])
            self.assertEqual([item["status"] for item in mixed["sources"]], ["collected", "attempted-unavailable"])

    def test_invalid_wrong_host_and_wrong_schema_sources_block_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wrong_host = root / "gsc.csv"
            write_csv(wrong_host, ["Page", "Clicks"], [{"Page": "https://other.test/", "Clicks": 1}])
            manifest, _ = self.run_prepare(root, "--gsc", str(wrong_host), "--declare-source-universe-complete")
            self.assertFalse(manifest["universe_complete"])
            self.assertEqual(manifest["sources"][0]["status"], "empty")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wrong_schema = root / "gsc.csv"
            write_csv(wrong_schema, ["Name", "Value"], [{"Name": "x", "Value": 1}])
            manifest, _ = self.run_prepare(root, "--gsc", str(wrong_schema), "--declare-source-universe-complete")
            self.assertFalse(manifest["universe_complete"])
            self.assertEqual(manifest["sources"][0]["status"], "invalid")

    def test_wordpress_drafts_and_crawler_assets_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wp = root / "wp.csv"
            write_csv(wp, ["live_url", "post_type", "post_status", "post_title"], [
                {"live_url": f"{self.site}public/", "post_type": "post", "post_status": "publish", "post_title": "Public"},
                {"live_url": f"{self.site}draft/", "post_type": "post", "post_status": "draft", "post_title": "Draft"},
                {"live_url": f"{self.site}private/", "post_type": "page", "post_status": "private", "post_title": "Private"},
            ])
            crawler = root / "crawler.csv"
            write_csv(crawler, ["Address", "Status Code", "Content Type"], [
                {"Address": f"{self.site}public/", "Status Code": 200, "Content Type": "text/html"},
                {"Address": f"{self.site}style.css", "Status Code": 200, "Content Type": "text/css"},
                {"Address": f"{self.site}photo.jpg", "Status Code": 200, "Content Type": "image/jpeg"},
            ])
            manifest, out = self.run_prepare(root, "--wordpress", str(wp), "--crawler", str(crawler), "--declare-source-universe-complete")
            self.assertTrue(manifest["universe_complete"])
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                urls = {row["url"] for row in csv.DictReader(handle)}
            self.assertEqual(urls, {f"{self.site}public/"})

    def test_ga4_double_slash_is_a_path_and_metrics_sum_within_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ga4 = root / "ga4.csv"
            write_csv(ga4, ["hostname", "landingPagePlusQueryString", "sessions", "engagedSessions", "views"], [
                {"hostname": "proofrank.test", "landingPagePlusQueryString": "//guide/?a=1", "sessions": 2, "engagedSessions": 1, "views": 3},
                {"hostname": "proofrank.test", "landingPagePlusQueryString": "//guide/?a=2", "sessions": 4, "engagedSessions": 3, "views": 5},
            ])
            manifest, out = self.run_prepare(root, "--ga4", str(ga4), "--declare-source-universe-complete")
            self.assertTrue(manifest["universe_complete"])
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["url"], f"{self.site}guide/")
            self.assertEqual(row["ga4Sessions"], "6.0")
            self.assertEqual(row["ga4EngagedSessions"], "4.0")
            self.assertEqual(row["ga4Views"], "8.0")

    def test_crawler_cache_distinguishes_status_records_from_real_html(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crawler = root / "crawler.csv"
            write_csv(crawler, ["Address", "Status Code", "Final URL", "Content Type", "Rendered HTML", "HTML Complete"], [
                {"Address": self.site, "Status Code": 200, "Final URL": self.site, "Content Type": "text/html", "Rendered HTML": "<html><body>Home</body></html>", "HTML Complete": "true"},
                {"Address": f"{self.site}no-html/", "Status Code": 200, "Final URL": f"{self.site}no-html/", "Content Type": "text/html", "Rendered HTML": "", "HTML Complete": ""},
            ])
            manifest, out = self.run_prepare(root, "--crawler", str(crawler), "--declare-source-universe-complete")
            cache = json.loads((out / "page_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(len(cache["pages"]), 2)
            self.assertIn("html", cache["pages"][self.site])
            self.assertIs(cache["pages"][self.site]["html_complete"], True)
            self.assertNotIn("html", cache["pages"][f"{self.site}no-html/"])
            self.assertEqual(manifest["outputs"]["page_cache"]["html_records"], 1)
            self.assertEqual(manifest["outputs"]["page_cache"]["complete_html_records"], 1)
            report = json.loads((out / "prepare_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["page_cache_records"], 2)
            self.assertEqual(report["html_records"], 1)
            self.assertEqual(report["complete_html_records"], 1)

    def test_crawler_conflicts_select_one_conservative_atomic_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            healthy = root / "healthy.csv"
            failed = root / "failed.csv"
            write_csv(healthy, ["Address", "Status Code", "Final URL", "Content Type", "Rendered HTML", "Full HTML"], [{
                "Address": self.site,
                "Status Code": 200,
                "Final URL": self.site,
                "Content Type": "text/html",
                "Rendered HTML": "<html><body>Current-looking page</body></html>",
                "Full HTML": "yes",
            }])
            write_csv(failed, ["Address", "Status Code", "Final URL", "Content Type", "Rendered HTML"], [{
                "Address": self.site,
                "Status Code": 404,
                "Final URL": f"{self.site}gone/",
                "Content Type": "text/html",
                "Rendered HTML": "",
            }])

            for index, ordered in enumerate(((healthy, failed), (failed, healthy)), start=1):
                _, out = self.run_prepare(
                    root / f"order-{index}",
                    "--crawler", str(ordered[0]), "--crawler", str(ordered[1]),
                    "--declare-source-universe-complete",
                )
                cache = json.loads((out / "page_cache.json").read_text(encoding="utf-8"))
                page = cache["pages"][self.site]
                self.assertEqual(page["status"], 404)
                self.assertEqual(page["final_url"], f"{self.site}gone/")
                self.assertNotIn("html", page)
                self.assertTrue(page["conflicting_snapshots"])
                self.assertEqual(page["candidate_count"], 2)

    def test_cross_origin_crawler_final_url_cannot_supply_same_origin_html(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, outside in enumerate((
                "https://outside.test/landing/",
                "http://proofrank.test/landing/",
            ), start=1):
                crawler = root / f"crawler-{index}.csv"
                write_csv(crawler, ["Address", "Status Code", "Final URL", "Content Type", "Rendered HTML"], [{
                    "Address": self.site,
                    "Status Code": 200,
                    "Final URL": outside,
                    "Content Type": "text/html",
                    "Rendered HTML": "<html><body>Outside</body></html>",
                }])
                manifest, out = self.run_prepare(
                    root / f"origin-{index}", "--crawler", str(crawler),
                    "--declare-source-universe-complete",
                )
                page = json.loads((out / "page_cache.json").read_text(encoding="utf-8"))["pages"][self.site]
                self.assertEqual(page["final_url"], outside)
                self.assertNotIn("html", page)
                self.assertEqual(manifest["outputs"]["page_cache"]["html_records"], 0)

    def test_unattested_html_is_saved_for_review_but_cannot_green_light(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snippet = root / "snippet.csv"
            complete = root / "complete.csv"
            fields = ["Address", "Status Code", "Final URL", "Content Type", "Rendered HTML", "body_complete"]
            write_csv(snippet, fields, [{
                "Address": self.site,
                "Status Code": 200,
                "Final URL": self.site,
                "Content Type": "text/html",
                "Rendered HTML": "<main>only a snippet</main>",
                "body_complete": "",
            }])
            write_csv(complete, fields, [{
                "Address": self.site,
                "Status Code": 200,
                "Final URL": self.site,
                "Content Type": "text/html",
                "Rendered HTML": "<html><body>full document</body></html>",
                "body_complete": "true",
            }])

            manifest, out = self.run_prepare(
                root / "snippet-only", "--crawler", str(snippet),
                "--declare-source-universe-complete",
            )
            page = json.loads((out / "page_cache.json").read_text(encoding="utf-8"))["pages"][self.site]
            self.assertIn("html", page)
            self.assertNotIn("html_complete", page)
            self.assertEqual(manifest["outputs"]["page_cache"]["complete_html_records"], 0)

            manifest, out = self.run_prepare(
                root / "conflict", "--crawler", str(complete), "--crawler", str(snippet),
                "--declare-source-universe-complete",
            )
            page = json.loads((out / "page_cache.json").read_text(encoding="utf-8"))["pages"][self.site]
            self.assertEqual(page["html"], "<main>only a snippet</main>")
            self.assertNotIn("html_complete", page)
            self.assertTrue(page["conflicting_snapshots"])
            self.assertEqual(manifest["outputs"]["page_cache"]["complete_html_records"], 0)

    def test_overlapping_gsc_files_select_one_atomic_metric_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            small = root / "small.csv"
            large = root / "large.csv"
            write_csv(small, ["Page", "Query", "Clicks", "Impressions", "CTR", "Position"], [{
                "Page": self.site, "Query": "small", "Clicks": 2, "Impressions": 20,
                "CTR": "99%", "Position": 9,
            }])
            write_csv(large, ["Page", "Query", "Clicks", "Impressions", "CTR", "Position"], [{
                "Page": self.site, "Query": "large", "Clicks": 3, "Impressions": 100,
                "CTR": "88%", "Position": 5,
            }])
            manifest, out = self.run_prepare(
                root, "--gsc", str(small), "--gsc", str(large),
                "--declare-source-universe-complete",
            )
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(float(row["latestClicks"]), 3.0)
            self.assertEqual(float(row["latestImpressions"]), 100.0)
            self.assertAlmostEqual(float(row["gscCtr"]), 0.03)
            self.assertAlmostEqual(float(row["gscPosition"]), 5.0)
            self.assertEqual(row["gscMetricSource"], "gsc-2")
            self.assertEqual(row["topQueries"], "large | small")
            self.assertIn("Potentially overlapping files are not summed", manifest["selection_semantics"]["gsc_across_files"])

    def test_reused_output_removes_stale_generated_page_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crawler = root / "crawler.csv"
            inventory = root / "inventory.csv"
            write_csv(crawler, ["Address", "Status Code", "Content Type"], [{
                "Address": self.site, "Status Code": 200, "Content Type": "text/html",
            }])
            write_csv(inventory, ["url"], [{"url": self.site}])
            _, out = self.run_prepare(root, "--crawler", str(crawler))
            self.assertTrue((out / "page_cache.json").is_file())
            manifest, out = self.run_prepare(root, "--inventory", str(inventory))
            self.assertFalse((out / "page_cache.json").exists())
            self.assertNotIn("page_cache", manifest["outputs"])

    def test_ten_thousand_rows_are_not_truncated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crawler = root / "crawler.csv"
            with crawler.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["Address", "Status Code", "Content Type"])
                writer.writeheader()
                for index in range(10_000):
                    writer.writerow({"Address": f"{self.site}page-{index}/", "Status Code": 200, "Content Type": "text/html"})
            manifest, _ = self.run_prepare(root, "--crawler", str(crawler), "--declare-source-universe-complete")
            self.assertEqual(manifest["normalized_unique_urls"], 10_000)
            self.assertEqual(manifest["expected_normalized_identities"], 10_000)
            self.assertEqual(manifest["sources"][0]["accepted"], 10_000)

    def test_csv_formula_text_is_neutralized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.csv"
            write_csv(inventory, ["url", "title", "topQueries"], [
                {"url": self.site, "title": "=HYPERLINK(\"https://evil.test\")", "topQueries": "+SUM(1,1)"},
            ])
            _, out = self.run_prepare(root, "--inventory", str(inventory), "--declare-source-universe-complete")
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertTrue(row["title"].startswith("'="))
            self.assertTrue(row["topQueries"].startswith("'+"))

    def test_number_parses_common_thousands_and_decimal_formats(self):
        self.assertEqual(MODULE.number("1,234"), 1234.0)
        self.assertEqual(MODULE.number("1.234"), 1.234)
        self.assertEqual(MODULE.number("0.123"), 0.123)
        self.assertEqual(MODULE.number("1.234,56"), 1234.56)
        self.assertEqual(MODULE.number("1,234.56"), 1234.56)

    def test_saved_urlset_is_provenance_bound_and_extension_locs_are_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sitemap = root / "pages.xml"
            sitemap.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://proofrank.test/one/</loc>
    <image:image><image:loc>https://proofrank.test/image.jpg</image:loc></image:image>
  </url>
</urlset>
""", encoding="utf-8")
            manifest, out = self.run_prepare(
                root, "--source", f"sitemap={sitemap}", "--require", "sitemap",
                "--declare-source-universe-complete",
            )
            self.assertTrue(manifest["universe_complete"])
            source = manifest["sources"][0]
            self.assertEqual(source["kind"], "sitemap")
            self.assertEqual(source["status"], "collected")
            self.assertEqual(source["sitemap_type"], "urlset")
            self.assertEqual(source["page_locs"], 1)
            self.assertEqual(source["child_sitemap_locs"], 0)
            self.assertEqual(source["records"], 1)
            self.assertEqual(manifest["outputs"]["sitemaps"], [{
                "path": sitemap.name,
                "sha256": MODULE.sha256(sitemap),
            }])
            with (out / "inventory.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(list(csv.DictReader(handle)), [])

    def test_sitemap_index_and_children_are_each_explicitly_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index = root / "index.xml"
            child = root / "child.xml"
            index.write_text("""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://proofrank.test/child.xml</loc></sitemap>
</sitemapindex>""", encoding="utf-8")
            child.write_text("""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://proofrank.test/</loc></url>
</urlset>""", encoding="utf-8")
            manifest, _ = self.run_prepare(
                root, "--sitemap", str(index), "--sitemap", str(child),
                "--declare-source-universe-complete",
            )
            self.assertTrue(manifest["universe_complete"])
            self.assertEqual([item["sitemap_type"] for item in manifest["sources"]], ["sitemapindex", "urlset"])
            self.assertEqual(manifest["sources"][0]["child_sitemap_locs"], 1)
            self.assertEqual(manifest["sources"][1]["page_locs"], 1)
            self.assertEqual(manifest["outputs"]["sitemaps"], [
                {"path": index.name, "sha256": MODULE.sha256(index)},
                {"path": child.name, "sha256": MODULE.sha256(child)},
            ])

    def test_invalid_or_non_namespaced_sitemap_blocks_required_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            malformed = root / "malformed.xml"
            malformed.write_text("<urlset><url><loc>https://proofrank.test/</loc>", encoding="utf-8")
            manifest, _ = self.run_prepare(
                root / "malformed", "--sitemap", str(malformed),
                "--declare-source-universe-complete",
            )
            self.assertFalse(manifest["universe_complete"])
            self.assertEqual(manifest["sources"][0]["status"], "invalid")
            self.assertEqual(manifest["outputs"]["sitemaps"][0]["sha256"], MODULE.sha256(malformed))

            no_namespace = root / "no-namespace.xml"
            no_namespace.write_text("""<urlset><url><loc>https://proofrank.test/</loc></url></urlset>""", encoding="utf-8")
            manifest, _ = self.run_prepare(
                root / "namespace", "--sitemap", str(no_namespace),
                "--declare-source-universe-complete",
            )
            self.assertFalse(manifest["universe_complete"])
            self.assertEqual(manifest["sources"][0]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
