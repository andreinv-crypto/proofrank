#!/usr/bin/env python3
"""Normalize saved SEO exports into evidence-bound ProofRank inputs.

This tool is deliberately offline: it reads local CSV/JSON exports, writes local
artifacts, and never authenticates to Google, a CMS, or a crawler.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


KINDS = {"auto", "inventory", "gsc", "ga4", "wordpress", "crawler", "sitemap"}
READY_STATUS = "collected"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
NON_PUBLIC_WP_STATUSES = {"auto-draft", "draft", "future", "pending", "private", "trash"}
NON_HTML_SUFFIXES = {
    ".7z", ".avi", ".css", ".doc", ".docx", ".eot", ".gif", ".gz", ".ico", ".jpeg", ".jpg",
    ".js", ".json", ".map", ".mov", ".mp3", ".mp4", ".mpeg", ".ogg", ".otf", ".pdf", ".png",
    ".rar", ".svg", ".tar", ".tif", ".tiff", ".ttf", ".wav", ".webm", ".webp", ".woff", ".woff2",
    ".xls", ".xlsx", ".xml", ".zip",
}
URL_KEYS = (
    "url", "address", "page", "permalink", "link", "live_url", "liveurl", "path", "finalurl",
    "final_url", "landingpageplusquerystring", "landingpage", "landing", "pagepathandscreenclass",
)
HTML_KEYS = ("html", "rendered html", "rendered_html", "body")
HTML_COMPLETE_KEYS = (
    "html_complete", "htmlComplete", "full_html", "fullHtml", "body_complete", "bodyComplete",
)
SUM_FIELDS = {"latestClicks", "latestImpressions", "ga4Sessions", "ga4EngagedSessions", "ga4Views"}
MAX_FIELDS = {"wordCount", "linkCount"}
TEXT_FIELDS = (
    "title", "h1", "postType", "mechanismLane", "strategicCluster", "language", "sourceRecordId",
    "sourceDecision", "canonical", "indexability", "metaRobots", "contentType", "crawlerStatus",
    "finalUrl",
)
OUTPUT_FIELDS = (
    "url", "title", "h1", "postType", "mechanismLane", "strategicCluster", "latestClicks",
    "latestImpressions", "topQueries", "wordCount", "linkCount", "gscCtr", "gscPosition",
    "gscMetricSource",
    "ga4Sessions", "ga4EngagedSessions", "ga4Views", "language", "sourceRecordId", "sourceDecision",
    "canonical", "indexability", "crawlDepth", "metaRobots", "contentType", "crawlerStatus", "finalUrl",
    "sourceTypes", "sourceIds",
)
PERCENT_RE = re.compile(r"%[0-9A-Fa-f]{2}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def key_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def keyed(row: dict) -> dict:
    return {key_name(key): value for key, value in row.items()}


def first(row: dict, names, default=""):
    normalized = keyed(row)
    for name in names:
        value = normalized.get(key_name(name))
        if value not in (None, ""):
            if isinstance(value, dict):
                return value.get("rendered") or value.get("raw") or default
            return value
    return default


def number(value, default=0.0) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "").replace("%", "")
    if not text:
        return default
    if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+", text):
        text = text.replace(",", "")
    elif "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def integer(value, default=0) -> int:
    return int(number(value, float(default)))


def explicit_true(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 1
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "complete", "full"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_url(raw: object, site: str, hostname: str = "") -> str:
    value = str(raw or "").strip().strip("<>\"'")
    if not value or value.lower() in {"(not set)", "not set", "/(not set)"}:
        return ""
    base = urllib.parse.urlsplit(site)
    base_host = (base.hostname or "").lower()
    if not base_host:
        return ""
    supplied_host = str(hostname or "").strip().lower().split(":", 1)[0]
    if value.startswith("//") and supplied_host:
        value = "/" + value.lstrip("/")
    if value.startswith("/"):
        target_host = supplied_host or base_host
        value = urllib.parse.urlunsplit((base.scheme or "https", target_host, value, "", ""))
    if value.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return ""
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(site, value))
    host = (parsed.hostname or "").lower()
    if host.removeprefix("www.") != base_host.removeprefix("www."):
        return ""
    scheme = (parsed.scheme or base.scheme or "https").lower()
    port = parsed.port
    netloc = base_host
    base_port = base.port
    if base_port and not ((scheme == "https" and base_port == 443) or (scheme == "http" and base_port == 80)):
        netloc = f"{base_host}:{base_port}"
    elif port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{base_host}:{port}"
    try:
        decoded = urllib.parse.unquote(parsed.path or "/", errors="strict")
    except (UnicodeDecodeError, ValueError):
        decoded = parsed.path or "/"
    decoded = unicodedata.normalize("NFC", decoded)
    decoded = re.sub(r"/{2,}", "/", decoded)
    if not decoded.startswith("/"):
        decoded = "/" + decoded
    path = urllib.parse.quote(decoded, safe="/:@!$&'()*+,;=-._~")
    path = PERCENT_RE.sub(lambda match: match.group(0).lower(), path)
    last = path.rsplit("/", 1)[-1]
    if path != "/" and not path.endswith("/") and not re.search(r"\.[A-Za-z0-9]{2,8}$", last):
        path += "/"
    return urllib.parse.urlunsplit((scheme, netloc, path or "/", "", ""))


def origin(value: object, base: str) -> tuple[str, str, int] | None:
    try:
        parsed = urllib.parse.urlsplit(urllib.parse.urljoin(base, str(value or "").strip()))
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return None
        port = parsed.port or (443 if scheme == "https" else 80)
        return scheme, parsed.hostname.lower(), port
    except ValueError:
        return None


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() != ".json":
        raise ValueError(f"Unsupported source format: {path.name}; use CSV or JSON")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    collection = next((payload.get(name) for name in ("rows", "pages", "items", "data") if name in payload), None)
    if isinstance(collection, list):
        return [row for row in collection if isinstance(row, dict)]
    if isinstance(collection, dict):
        rows = []
        for identity, raw in collection.items():
            row = dict(raw or {}) if isinstance(raw, dict) else {}
            row.setdefault("url", identity)
            rows.append(row)
        return rows
    if any(key_name(key) in {key_name(item) for item in URL_KEYS} for key in payload):
        return [payload]
    return []


def xml_tag_parts(tag: str) -> tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", 1)
        return namespace, local_name.lower()
    return "", tag.lower()


def inspect_sitemap(path: Path) -> dict:
    """Validate one saved sitemap file without recursively resolving children."""
    try:
        root = ET.fromstring(path.read_bytes())
    except (OSError, ET.ParseError) as exc:
        return {
            "valid": False,
            "reason": f"invalid sitemap XML: {exc}",
            "sitemap_type": "",
            "page_locs": 0,
            "child_sitemap_locs": 0,
            "loc_count": 0,
        }

    namespace, root_name = xml_tag_parts(root.tag)
    if namespace != SITEMAP_NAMESPACE or root_name not in {"urlset", "sitemapindex"}:
        return {
            "valid": False,
            "reason": "root must be sitemap:urlset or sitemap:sitemapindex in the standard sitemap namespace",
            "sitemap_type": root_name,
            "page_locs": 0,
            "child_sitemap_locs": 0,
            "loc_count": 0,
        }

    container_name = "url" if root_name == "urlset" else "sitemap"
    loc_count = 0
    for container in list(root):
        child_namespace, child_name = xml_tag_parts(container.tag)
        if child_namespace != SITEMAP_NAMESPACE or child_name != container_name:
            continue
        for element in list(container):
            element_namespace, element_name = xml_tag_parts(element.tag)
            if (
                element_namespace == SITEMAP_NAMESPACE
                and element_name == "loc"
                and str(element.text or "").strip()
            ):
                loc_count += 1
                break

    valid = loc_count > 0
    return {
        "valid": valid,
        "reason": "" if valid else "sitemap contains no non-empty direct sitemap-namespace loc entries",
        "sitemap_type": root_name,
        "page_locs": loc_count if root_name == "urlset" else 0,
        "child_sitemap_locs": loc_count if root_name == "sitemapindex" else 0,
        "loc_count": loc_count,
    }


def source_fields(rows: list[dict]) -> set[str]:
    fields = set()
    for row in rows[:50]:
        fields.update(keyed(row))
    return fields


def detect_kind(rows: list[dict]) -> str:
    fields = source_fields(rows)
    if "keys" in fields and fields & {"clicks", "impressions", "position", "ctr"}:
        return "gsc"
    if fields & {"landingpageplusquerystring", "landingpage", "pagepathandscreenclass", "landing"} and fields & {"sessions", "engagedsessions", "views"}:
        return "ga4"
    if "address" in fields and fields & {"statuscode", "indexability", "crawldepth", "contenttype", "title1", "h11"}:
        return "crawler"
    if fields & {"liveurl", "permalink", "link"} and fields & {"posttype", "poststatus", "languagecode", "postid", "slug", "type"}:
        return "wordpress"
    if fields & {"page", "url"} and fields & {"clicks", "impressions", "position", "ctr"}:
        return "gsc"
    return "inventory"


def validate_schema(kind: str, rows: list[dict]) -> tuple[bool, str]:
    if not rows:
        return False, "source contains no data rows"
    fields = source_fields(rows)
    url_aliases = {key_name(item) for item in URL_KEYS}
    if kind == "gsc":
        valid = bool(fields & {"page", "url", "keys"}) and bool(fields & {"clicks", "impressions", "position", "ctr"})
    elif kind == "ga4":
        valid = bool(fields & {"landingpageplusquerystring", "landingpage", "pagepathandscreenclass", "landing", "url", "page"})
    elif kind == "wordpress":
        valid = bool(fields & {"liveurl", "permalink", "link", "url"})
    elif kind == "crawler":
        valid = bool(fields & {"address", "url"}) and bool(fields & {"statuscode", "status", "indexability", "contenttype", "crawldepth", "html", "renderedhtml"})
    else:
        valid = bool(fields & url_aliases)
    return (True, "") if valid else (False, f"columns do not match the declared {kind} export shape")


def gsc_identity(row: dict) -> tuple[str, list[str]]:
    direct = first(row, ("page", "url", "top_page"))
    queries = []
    query = first(row, ("query", "keyword"))
    if query:
        queries.append(str(query))
    keys = row.get("keys")
    if isinstance(keys, list):
        for item in keys:
            text = str(item or "").strip()
            if text.startswith(("http://", "https://", "/")) and not direct:
                direct = text
            elif text and text not in queries:
                queries.append(text)
    return str(direct or ""), queries


def adapt_row(kind: str, row: dict, site: str) -> tuple[dict, dict | None] | None:
    host = str(first(row, ("hostname", "host")) or "")
    queries = []
    if kind == "gsc":
        raw_url, queries = gsc_identity(row)
    elif kind == "wordpress":
        raw_url = first(row, ("live_url", "liveurl", "url", "permalink", "link"))
    elif kind == "crawler":
        raw_url = first(row, ("address", "url"))
    elif kind == "ga4":
        raw_url = first(row, ("landingPagePlusQueryString", "landingPage", "pagePathAndScreenClass", "landing", "url", "page"))
    else:
        raw_url = first(row, URL_KEYS)

    url = normalize_url(raw_url, site, host)
    if not url:
        return None

    if kind == "wordpress":
        post_status = str(first(row, ("post_status", "postStatus", "status")) or "").strip().lower()
        if post_status in NON_PUBLIC_WP_STATUSES:
            return None

    content_type = str(first(row, ("content type", "contentType", "mime_type", "mimeType")) or "").strip()
    if kind == "crawler":
        lower_content_type = content_type.lower()
        suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        if lower_content_type and "html" not in lower_content_type and "xhtml" not in lower_content_type:
            return None
        if not lower_content_type and suffix in NON_HTML_SUFFIXES:
            return None

    raw_final_url = first(row, ("final address", "final url", "finalUrl", "final_url"))
    if raw_final_url in (None, ""):
        final_url = url
        final_url_same_site = True
    else:
        final_url_same_site = origin(raw_final_url, url) == origin(url, url)
        final_url = normalize_url(raw_final_url, site) if final_url_same_site else ""
        if not final_url_same_site:
            # Preserve the conflicting evidence instead of silently rewriting an
            # external/invalid final URL to the requested URL.
            final_url = str(raw_final_url).strip()
    record = {
        "url": url,
        "title": first(row, ("title", "title 1", "seo title", "yoastTitle", "post_title", "live_title")),
        "h1": first(row, ("h1", "h1-1", "h1 1", "live_h1")),
        "postType": first(row, ("postType", "post_type", "type")),
        "mechanismLane": first(row, ("mechanismLane", "mechanism", "lane")),
        "strategicCluster": first(row, ("strategicCluster", "cluster", "sourceCluster")),
        "latestClicks": number(first(row, ("latestClicks", "clicks"))),
        "latestImpressions": number(first(row, ("latestImpressions", "impressions"))),
        "topQueries": set(queries or [str(first(row, ("topQueries", "top_queries")) or "")]) - {""},
        "wordCount": number(first(row, ("wordCount", "word count", "word_count"))),
        "linkCount": number(first(row, ("linkCount", "link count", "link_count"))),
        "gscCtr": number(first(row, ("ctr",))),
        "gscPosition": number(first(row, ("position",))),
        "ga4Sessions": number(first(row, ("sessions",))),
        "ga4EngagedSessions": number(first(row, ("engagedSessions", "engaged sessions"))),
        "ga4Views": number(first(row, ("views",))),
        "language": first(row, ("language", "language_code", "lang")),
        "sourceRecordId": first(row, ("sourceRecordId", "post_id", "id", "ID")),
        "sourceDecision": first(row, ("decision",)),
        "canonical": first(row, ("canonical", "canonical link element 1")),
        "indexability": first(row, ("indexability",)),
        "crawlDepth": number(first(row, ("crawlDepth", "crawl depth"))),
        "metaRobots": first(row, ("meta robots 1", "metaRobots", "robots")),
        "contentType": content_type,
        "crawlerStatus": first(row, ("status code", "statusCode", "http status")),
        "finalUrl": final_url,
    }

    cache = None
    if kind == "crawler":
        html = str(first(row, HTML_KEYS) or "")
        html_complete = explicit_true(first(row, HTML_COMPLETE_KEYS))
        status = integer(first(row, ("status code", "statusCode", "http status", "status")))
        cache = {
            "url": url,
            "status": status,
            "final_url": final_url,
        }
        # Error documents and cross-origin/invalid final URLs are not page-HTML
        # evidence for the requested same-origin URL.
        if html and 200 <= status < 300 and final_url_same_site:
            cache["html"] = html
            if html_complete:
                cache["html_complete"] = True
    return record, cache


def merge_record(target: dict, source: dict, *, sum_metrics: bool) -> None:
    for field in TEXT_FIELDS:
        if source.get(field) not in (None, "") and target.get(field) in (None, ""):
            target[field] = source[field]
    target.setdefault("topQueries", set()).update(source.get("topQueries", set()))
    for field in SUM_FIELDS:
        current = number(target.get(field))
        incoming = number(source.get(field))
        target[field] = current + incoming if sum_metrics else max(current, incoming)
    for field in MAX_FIELDS | {"crawlDepth"}:
        target[field] = max(number(target.get(field)), number(source.get(field)))
    for field in ("gscCtr", "gscPosition"):
        if field not in target and field in source:
            target[field] = number(source.get(field))


def merge_gsc_source(target: dict, source: dict) -> None:
    """Aggregate one GSC file without trusting exported aggregate CTR values."""
    target.setdefault("topQueries", set()).update(source.get("topQueries", set()))
    clicks = max(0.0, number(source.get("latestClicks")))
    impressions = max(0.0, number(source.get("latestImpressions")))
    position = number(source.get("gscPosition"))
    target["_gsc_clicks"] = number(target.get("_gsc_clicks")) + clicks
    target["_gsc_impressions"] = number(target.get("_gsc_impressions")) + impressions
    if impressions > 0 and position > 0:
        target["_gsc_position_weight"] = number(target.get("_gsc_position_weight")) + position * impressions
        target["_gsc_position_impressions"] = number(target.get("_gsc_position_impressions")) + impressions
    total_impressions = target["_gsc_impressions"]
    position_impressions = number(target.get("_gsc_position_impressions"))
    target["latestClicks"] = target["_gsc_clicks"]
    target["latestImpressions"] = total_impressions
    target["gscCtr"] = target["_gsc_clicks"] / total_impressions if total_impressions else 0.0
    target["gscPosition"] = (
        number(target.get("_gsc_position_weight")) / position_impressions
        if position_impressions else 0.0
    )


def gsc_snapshot_key(snapshot: dict) -> tuple:
    # Use one file atomically across potentially overlapping exports. Prefer the
    # file with more impression evidence; a content fingerprint breaks ties
    # without depending on CLI order or a private filename.
    comparable = {
        "clicks": number(snapshot.get("latestClicks")),
        "impressions": number(snapshot.get("latestImpressions")),
        "ctr": number(snapshot.get("gscCtr")),
        "position": number(snapshot.get("gscPosition")),
        "queries": sorted(snapshot.get("topQueries", set())),
    }
    fingerprint = hashlib.sha256(
        json.dumps(comparable, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return (-comparable["impressions"], fingerprint)


def apply_gsc_snapshot(target: dict) -> None:
    snapshot = target.get("_gsc_snapshot")
    if not snapshot:
        return
    for field in ("latestClicks", "latestImpressions", "gscCtr", "gscPosition"):
        target[field] = snapshot[field]
    target["gscMetricSource"] = snapshot["source_id"]


def merge_gsc_global(target: dict, source: dict, source_id: str) -> None:
    target.setdefault("sourceIds", set()).add(source_id)
    target.setdefault("sourceTypes", set()).add("gsc")
    target.setdefault("topQueries", set()).update(source.get("topQueries", set()))
    candidate = {
        "source_id": source_id,
        "latestClicks": number(source.get("latestClicks")),
        "latestImpressions": number(source.get("latestImpressions")),
        "gscCtr": number(source.get("gscCtr")),
        "gscPosition": number(source.get("gscPosition")),
        "topQueries": set(source.get("topQueries", set())),
    }
    current = target.get("_gsc_snapshot")
    if current is None or gsc_snapshot_key(candidate) < gsc_snapshot_key(current):
        target["_gsc_snapshot"] = candidate
    apply_gsc_snapshot(target)


def merge_global(target: dict, source: dict, source_id: str, source_kind: str) -> None:
    target.setdefault("sourceIds", set()).add(source_id)
    target.setdefault("sourceTypes", set()).add(source_kind)
    merge_record(target, source, sum_metrics=False)
    apply_gsc_snapshot(target)


def cache_core(snapshot: dict) -> dict:
    result = {
        "url": snapshot["url"],
        "status": integer(snapshot.get("status")),
        "final_url": str(snapshot.get("final_url") or ""),
    }
    if snapshot.get("html"):
        result["html"] = str(snapshot["html"])
        if snapshot.get("html_complete") is True:
            result["html_complete"] = True
    return result


def cache_fingerprint(snapshot: dict) -> str:
    return hashlib.sha256(
        json.dumps(cache_core(snapshot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def cache_selection_key(snapshot: dict) -> tuple:
    core = cache_core(snapshot)
    status = core["status"]
    has_html = bool(core.get("html"))
    has_attested_complete_html = has_html and core.get("html_complete") is True
    # Conservative ordering prevents a 200+HTML row from masking a stale,
    # failed, redirected, or HTML-missing observation when freshness is unknown.
    if not 200 <= status < 300:
        tier = 0
    elif not has_html:
        tier = 1
    elif not has_attested_complete_html:
        tier = 2
    else:
        tier = 3
    return (tier, status, core["final_url"], cache_fingerprint(core))


def select_cache_snapshot(current: dict | None, candidate: dict, source_id: str) -> dict:
    candidate_ids = set(candidate.get("observed_source_ids", [])) | {source_id}
    candidate_count = integer(candidate.get("candidate_count"), 1) or 1
    candidate_conflict = bool(candidate.get("conflicting_snapshots"))
    if current is None:
        selected = cache_core(candidate)
        selected["selected_source_id"] = candidate.get("selected_source_id") or source_id
        selected["observed_source_ids"] = sorted(candidate_ids)
        selected["source_ids"] = sorted(candidate_ids)
        selected["candidate_count"] = candidate_count
        if candidate_conflict:
            selected["conflicting_snapshots"] = True
        return selected

    current_ids = set(current.get("observed_source_ids", []))
    current_count = integer(current.get("candidate_count"), 1) or 1
    conflict = (
        bool(current.get("conflicting_snapshots"))
        or candidate_conflict
        or cache_fingerprint(current) != cache_fingerprint(candidate)
    )
    if cache_selection_key(candidate) < cache_selection_key(current):
        selected = cache_core(candidate)
        selected_source_id = candidate.get("selected_source_id") or source_id
    else:
        selected = cache_core(current)
        selected_source_id = current.get("selected_source_id") or source_id
    all_ids = current_ids | candidate_ids
    selected["selected_source_id"] = selected_source_id
    selected["observed_source_ids"] = sorted(all_ids)
    selected["source_ids"] = sorted(all_ids)
    selected["candidate_count"] = current_count + candidate_count
    if conflict:
        selected["conflicting_snapshots"] = True
    return selected


def parse_assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected KIND=PATH or KIND=REASON")
    kind, detail = value.split("=", 1)
    kind = kind.strip().lower()
    if not kind or not detail.strip():
        raise argparse.ArgumentTypeError("Both kind and value are required")
    return kind, detail.strip()


def csv_safe(value):
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_inventory(path: Path, records: dict[str, dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for url in sorted(records):
            row = dict(records[url])
            row["topQueries"] = " | ".join(sorted(row.get("topQueries", set())))
            row["sourceTypes"] = ",".join(sorted(row.get("sourceTypes", set())))
            row["sourceIds"] = ",".join(sorted(row.get("sourceIds", set())))
            writer.writerow({field: csv_safe(row.get(field, "")) for field in OUTPUT_FIELDS})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prepare provenance-preserving ProofRank inputs from saved SEO exports")
    parser.add_argument("--site", required=True)
    parser.add_argument("--source", action="append", default=[], help="KIND=PATH; KIND is auto, gsc, ga4, wordpress, crawler, inventory, or sitemap")
    for kind in ("gsc", "ga4", "wordpress", "crawler", "inventory", "sitemap"):
        source_format = "XML" if kind == "sitemap" else "CSV/JSON"
        parser.add_argument(f"--{kind}", action="append", default=[], metavar="PATH", help=f"Saved {kind} {source_format}; repeatable")
    parser.add_argument("--require", action="append", default=[], help="Required source kind; repeatable")
    parser.add_argument("--unavailable", action="append", default=[], help="KIND=REASON for an attempted but unavailable source")
    parser.add_argument("--not-attempted", action="append", default=[], help="KIND=REASON for a declared source not yet attempted")
    parser.add_argument(
        "--declare-source-universe-complete",
        action="store_true",
        help="Explicitly attest that the selected source scope is complete; all required rows must still be collected",
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    site = normalize_url(args.site, args.site)
    if not site:
        parser.error("--site must be an absolute HTTP(S) URL")
    assignments = list(args.source)
    for kind in ("gsc", "ga4", "wordpress", "crawler", "inventory", "sitemap"):
        assignments.extend(f"{kind}={path}" for path in getattr(args, kind))

    required_kinds = {str(kind).strip().lower() for kind in args.require if str(kind).strip()}
    invalid_required = required_kinds - (KINDS - {"auto"})
    if invalid_required:
        parser.error(f"Unsupported required source kind(s): {', '.join(sorted(invalid_required))}")
    safe_default_required = not required_kinds

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict] = {}
    page_cache: dict[str, dict] = {}
    sitemap_outputs: list[dict] = []
    manifest_sources = []
    kind_counts = defaultdict(int)

    for assignment in assignments:
        requested_kind, raw_path = parse_assignment(assignment)
        if requested_kind not in KINDS:
            parser.error(f"Unsupported source kind: {requested_kind}")
        path = Path(raw_path).resolve()
        if not path.is_file():
            parser.error(f"Source file not found: {raw_path}")
        if requested_kind == "sitemap":
            kind_counts["sitemap"] += 1
            source_id = f"sitemap-{kind_counts['sitemap']}"
            file_sha256 = sha256(path)
            sitemap_outputs.append({"path": path.name, "sha256": file_sha256})
            inspected = inspect_sitemap(path)
            valid = bool(inspected["valid"] and inspected["loc_count"] > 0)
            entry = {
                "id": source_id,
                "kind": "sitemap",
                "required": safe_default_required or "sitemap" in required_kinds,
                "status": READY_STATUS if valid else "invalid",
                "path": path.name,
                "sha256": file_sha256,
                "records": inspected["loc_count"],
                "accepted": inspected["loc_count"] if valid else 0,
                "rejected": 0,
                "unique_urls": 0,
                "unique_urls_added": 0,
                "sitemap_type": inspected["sitemap_type"],
                "page_locs": inspected["page_locs"],
                "child_sitemap_locs": inspected["child_sitemap_locs"],
            }
            if inspected["reason"]:
                entry["reason"] = inspected["reason"]
            manifest_sources.append(entry)
            continue
        try:
            rows = load_rows(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            rows = []
            load_error = str(exc)
        else:
            load_error = ""
        actual_kind = detect_kind(rows) if requested_kind == "auto" else requested_kind
        kind_counts[actual_kind] += 1
        source_id = f"{actual_kind}-{kind_counts[actual_kind]}"
        required = safe_default_required or actual_kind in required_kinds
        valid_schema, schema_reason = validate_schema(actual_kind, rows) if not load_error else (False, load_error)
        accepted = 0
        source_records: dict[str, dict] = {}
        source_cache: dict[str, dict] = {}
        if valid_schema:
            seen_rows = set()
            for raw in rows:
                fingerprint = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
                if fingerprint in seen_rows:
                    continue
                seen_rows.add(fingerprint)
                adapted = adapt_row(actual_kind, raw, site)
                if not adapted:
                    continue
                normalized, cache = adapted
                target = source_records.setdefault(normalized["url"], {"url": normalized["url"]})
                if actual_kind == "gsc":
                    merge_gsc_source(target, normalized)
                else:
                    merge_record(target, normalized, sum_metrics=actual_kind == "ga4")
                if cache:
                    source_cache[cache["url"]] = select_cache_snapshot(
                        source_cache.get(cache["url"]), cache, source_id
                    )
                accepted += 1

        before = len(records)
        for url, normalized in source_records.items():
            target = records.setdefault(url, {"url": url})
            if actual_kind == "gsc":
                merge_gsc_global(target, normalized, source_id)
            else:
                merge_global(target, normalized, source_id, actual_kind)
        for url, cache in source_cache.items():
            page_cache[url] = select_cache_snapshot(page_cache.get(url), cache, source_id)

        if not valid_schema:
            status, reason = "invalid", schema_reason
        elif not accepted:
            status, reason = "empty", "no same-site public page rows were accepted"
        else:
            status, reason = READY_STATUS, ""
        entry = {
            "id": source_id,
            "kind": actual_kind,
            "required": required,
            "status": status,
            "path": path.name,
            "sha256": sha256(path),
            "records": len(rows),
            "accepted": accepted,
            "rejected": max(0, len(rows) - accepted),
            "unique_urls": len(source_records),
            "unique_urls_added": len(records) - before,
        }
        if reason:
            entry["reason"] = reason
        manifest_sources.append(entry)

    for option, status in ((args.unavailable, "attempted-unavailable"), (args.not_attempted, "not-attempted")):
        for assignment in option:
            kind, reason = parse_assignment(assignment)
            if kind not in KINDS - {"auto"}:
                parser.error(f"Unsupported source kind: {kind}")
            kind_counts[kind] += 1
            manifest_sources.append({
                "id": f"{kind}-{kind_counts[kind]}",
                "kind": kind,
                "required": safe_default_required or kind in required_kinds,
                "status": status,
                "reason": reason,
                "records": 0,
                "accepted": 0,
                "rejected": 0,
                "unique_urls": 0,
            })

    declared_kinds = {source["kind"] for source in manifest_sources}
    for kind in sorted(required_kinds - declared_kinds):
        kind_counts[kind] += 1
        manifest_sources.append({
            "id": f"{kind}-{kind_counts[kind]}",
            "kind": kind,
            "required": True,
            "status": "not-attempted",
            "reason": "required source kind was declared but no file or status was supplied",
            "records": 0,
            "accepted": 0,
            "rejected": 0,
            "unique_urls": 0,
        })

    required_entries = [source for source in manifest_sources if source["required"]]
    universe_complete = bool(
        args.declare_source_universe_complete
        and required_entries
        and all(source["status"] == READY_STATUS for source in required_entries)
    )

    inventory_path = output_dir / "inventory.csv"
    page_cache_path = output_dir / "page_cache.json"
    manifest_path = output_dir / "source_manifest.json"
    report_path = output_dir / "prepare_report.json"
    write_inventory(inventory_path, records)
    if page_cache:
        page_cache_path.write_text(json.dumps({
            "site": site,
            "generated_at": utc_now(),
            "pages": {url: page_cache[url] for url in sorted(page_cache)},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    elif page_cache_path.is_file():
        # This filename is a generated output owned by this command. Never let a
        # cache from a previous run survive and become detached from the manifest.
        page_cache_path.unlink()

    output_manifest = {
        "inventory": {"path": inventory_path.name, "sha256": sha256(inventory_path), "records": len(records)},
    }
    if sitemap_outputs:
        output_manifest["sitemaps"] = sitemap_outputs
    if page_cache:
        output_manifest["page_cache"] = {
            "path": page_cache_path.name,
            "sha256": sha256(page_cache_path),
            "records": len(page_cache),
            "html_records": sum(1 for row in page_cache.values() if row.get("html")),
            "complete_html_records": sum(1 for row in page_cache.values() if row.get("html_complete") is True),
            "conflicted_records": sum(1 for row in page_cache.values() if row.get("conflicting_snapshots")),
        }
    semantics = {
        "gsc_within_file": "Exact duplicate rows are removed; clicks and impressions are summed, CTR is clicks/impressions, and position is impression-weighted over rows with positive impressions and position.",
        "gsc_across_files": "Potentially overlapping files are not summed. One file snapshot is selected atomically per URL by greatest impressions, with a content fingerprint tie-breaker; sourceIds still records every observed file.",
        "crawler_cache": "Status, final_url, HTML, and html_complete are selected as one atomic snapshot. With unknown freshness, non-2xx, then HTML-missing, then unattested/snippet HTML, then explicitly attested full HTML observations are preferred conservatively. HTML is retained only for 2xx exact-origin final URLs, and is usable for completeness only when a saved export explicitly supplies a true html_complete/full_html/body_complete alias.",
        "sitemaps": "Saved sitemap XML is validated and hashed as provenance only; child indexes are never resolved recursively, so every local sitemap XML used by the audit must be supplied explicitly.",
    }
    manifest = {
        "version": 1,
        "generated_at": utc_now(),
        "site": site,
        "declaration_requested": bool(args.declare_source_universe_complete),
        "universe_complete": universe_complete,
        "normalized_unique_urls": len(records),
        "expected_normalized_identities": len(records),
        "expected_count_origin": "AUTO_DERIVED_FROM_PREPARED_UNION",
        "sources": manifest_sources,
        "outputs": output_manifest,
        "selection_semantics": semantics,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "version": 1,
        "generated_at": utc_now(),
        "site": site,
        "network_used": False,
        "source_universe_complete": universe_complete,
        "source_count": len(manifest_sources),
        "required_source_count": len(required_entries),
        "normalized_unique_urls": len(records),
        "expected_count_origin": "AUTO_DERIVED_FROM_PREPARED_UNION",
        "page_cache_records": len(page_cache),
        "html_records": sum(1 for row in page_cache.values() if row.get("html")),
        "complete_html_records": sum(1 for row in page_cache.values() if row.get("html_complete") is True),
        "conflicted_cache_records": sum(1 for row in page_cache.values() if row.get("conflicting_snapshots")),
        "sources": manifest_sources,
        "outputs": output_manifest,
        "selection_semantics": semantics,
        "boundary": (
            "Saved-file import only. The expected count is auto-derived from the prepared union, so "
            "completeness applies only to the operator-declared source scope. No OAuth, live API, "
            "crawler control, CMS login, or production write was performed."
        ),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "inventory": str(inventory_path.resolve()),
        "page_cache": str(page_cache_path.resolve()) if page_cache else None,
        "source_manifest": str(manifest_path.resolve()),
        "prepare_report": str(report_path.resolve()),
        "unique_urls": len(records),
        "source_universe_complete": universe_complete,
        "source_count": len(manifest_sources),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
