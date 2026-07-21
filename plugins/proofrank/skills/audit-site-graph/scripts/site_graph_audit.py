#!/usr/bin/env python3
"""Read-only multilingual site graph, schema, duplicate, and overlap audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


USER_AGENT = "ProofRankSiteGraphAudit/0.1 (+read-only)"
MAX_RESPONSE_BYTES = 3_000_000
MAX_SITEMAP_BYTES = 10_000_000
TOKEN_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
PERCENT_RE = re.compile(r"%[0-9A-Fa-f]{2}")
URL_FIELDS = ("url", "permalink", "page", "path", "finalUrl", "final_url")
HTML_FIELDS = ("html", "body", "rendered_html")
HTML_COMPLETE_FIELDS = (
    "html_complete", "htmlComplete", "full_html", "fullHtml", "body_complete", "bodyComplete",
)
SOURCE_READY_STATUSES = {"collected", "complete", "included", "loaded", "resolved"}
EXPECTED_COUNT_ORIGINS = {
    "AUTO_DERIVED_FROM_PREPARED_UNION",
    "SYNTHETIC_CONTROL_FIXTURE",
    "MANIFEST_DECLARED",
    "NOT_PROVIDED",
}
DECLARED_SCOPE_WARNING = (
    "Completeness applies only to the operator-declared source scope and supplied evidence; "
    "it is not independent proof that every site source or URL was supplied."
)
NON_PAGE_LINK_SUFFIXES = {
    ".7z", ".avi", ".css", ".doc", ".docx", ".eot", ".gif", ".gz", ".ico", ".jpeg", ".jpg",
    ".js", ".json", ".map", ".mov", ".mp3", ".mp4", ".mpeg", ".ogg", ".otf", ".pdf", ".png",
    ".rar", ".svg", ".tar", ".tif", ".tiff", ".ttf", ".wav", ".webm", ".webp", ".woff", ".woff2",
    ".xls", ".xlsx", ".xml", ".zip",
}

STOPWORDS = {
    # Russian
    "а", "без", "более", "бы", "был", "была", "были", "было", "быть", "в", "вам", "вас",
    "весь", "во", "вот", "все", "всего", "вы", "где", "да", "для", "до", "его", "ее", "если",
    "есть", "еще", "же", "за", "здесь", "и", "из", "или", "им", "их", "к", "как", "когда",
    "который", "ли", "мы", "на", "над", "не", "него", "нее", "нет", "но", "о", "об", "один",
    "он", "она", "они", "оно", "от", "по", "под", "при", "про", "с", "со", "так", "также",
    "там", "то", "того", "тоже", "только", "у", "уже", "что", "чтобы", "это", "этот", "я",
    # Spanish
    "a", "al", "algo", "ante", "como", "con", "contra", "cual", "cuando", "de", "del", "desde",
    "donde", "el", "ella", "en", "entre", "era", "es", "esa", "ese", "esta", "este", "fue", "ha",
    "hasta", "hay", "la", "las", "lo", "los", "más", "muy", "no", "o", "para", "pero", "por",
    "que", "qué", "se", "sin", "sobre", "son", "su", "sus", "también", "todo", "un", "una", "y",
    # English
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "in",
    "is", "it", "of", "on", "or", "our", "that", "the", "this", "to", "was", "we", "what", "when",
    "where", "which", "who", "will", "with", "you", "your",
}

BRAND_TERMS = set()

GENERIC_ANCHORS = {
    "", "здесь", "подробнее", "читать", "читать далее", "далее", "ссылка", "узнать больше",
    "aquí", "leer más", "más información", "ver más", "enlace",
    "click here", "here", "read more", "learn more", "more", "this page", "link", "continue",
}

COMMON_LANGUAGE_CODES = {
    "ar", "bg", "ca", "cs", "da", "de", "el", "en", "es", "et", "fi", "fr", "he",
    "hi", "hr", "hu", "id", "it", "ja", "ko", "lt", "lv", "nl", "no", "pl", "pt",
    "ro", "ru", "sk", "sl", "sr", "sv", "th", "tr", "uk", "vi", "zh",
}

LANE_PREFIXES = (
    ("/tag/", "taxonomy"),
    ("/tags/", "taxonomy"),
    ("/author/", "taxonomy"),
    ("/category/", "taxonomy"),
    ("/categories/", "taxonomy"),
    ("/product-category/", "commerce_taxonomy"),
)

NON_CONTENT_LANES = {
    "asset", "attachment", "commerce_taxonomy", "error", "feed", "inventory_only",
    "legacy_amp", "pagination", "redirect", "search", "taxonomy",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def numeric(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def boolish(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def normalize_expected_count_origin(value, expected_normalized_identities) -> str:
    if expected_normalized_identities is None:
        return "NOT_PROVIDED"
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return normalized if normalized in EXPECTED_COUNT_ORIGINS else "MANIFEST_DECLARED"


def source_scope_assurance(source_universe: dict) -> str:
    if not source_universe.get("declared"):
        return "NOT_DECLARED"
    if source_universe.get("source_universe_complete"):
        return "DECLARED_SCOPE_BOUND"
    return "DECLARED_SCOPE_INCOMPLETE"


def first_value(row: dict, fields) -> str:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return str(value)
    return ""


def normalize_url(value: str, site: str, keep_query: bool = False) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    base = urllib.parse.urlsplit(site)
    absolute = urllib.parse.urljoin(site, value)
    parsed = urllib.parse.urlsplit(absolute)
    scheme = (parsed.scheme or base.scheme or "https").lower()
    host = (parsed.hostname or base.hostname or "").lower()
    base_host = (base.hostname or "").lower()
    if host.removeprefix("www.") == base_host.removeprefix("www."):
        host = base_host
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    try:
        decoded_path = urllib.parse.unquote(parsed.path or "/", errors="strict")
    except (UnicodeDecodeError, ValueError):
        decoded_path = parsed.path or "/"
    decoded_path = unicodedata.normalize("NFC", decoded_path)
    decoded_path = re.sub(r"/{2,}", "/", decoded_path)
    if not decoded_path.startswith("/"):
        decoded_path = "/" + decoded_path
    path = urllib.parse.quote(decoded_path, safe="/:@!$&'()*+,;=-._~")
    path = PERCENT_RE.sub(lambda m: m.group(0).lower(), path)
    last = path.rsplit("/", 1)[-1]
    if path != "/" and not path.endswith("/") and not re.search(r"\.[A-Za-z0-9]{2,8}$", last):
        path += "/"
    query = parsed.query if keep_query else ""
    return urllib.parse.urlunsplit((scheme, netloc, path or "/", query, ""))


def url_path(url: str) -> str:
    return urllib.parse.urlsplit(url).path or "/"


def same_site(url: str, site: str) -> bool:
    left = (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    right = (urllib.parse.urlsplit(site).hostname or "").lower().removeprefix("www.")
    return bool(left and left == right)


def origin_tuple(value: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlsplit(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80 if scheme == "http" else None
    return scheme, host, port


def same_origin(left: str, right: str) -> bool:
    return origin_tuple(left) == origin_tuple(right) and bool(origin_tuple(left)[1])


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that leave the exact approved scheme/host/port."""

    def __init__(self, approved_origin: str):
        super().__init__()
        self.approved_origin = approved_origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        if not same_origin(target, self.approved_origin):
            raise PermissionError(f"Cross-origin redirect blocked: {target}")
        return super().redirect_request(req, fp, code, msg, headers, target)


def open_same_origin(url: str, site: str):
    if not same_origin(url, site):
        raise PermissionError(f"URL is outside the approved origin: {url}")
    opener = urllib.request.build_opener(SameOriginRedirectHandler(site))
    response = opener.open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=30)
    if not same_origin(response.geturl(), site):
        response.close()
        raise PermissionError(f"Final URL is outside the approved origin: {response.geturl()}")
    return response


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    return [token for token in TOKEN_RE.findall(normalized) if len(token) > 1 and token not in STOPWORDS]


def signal_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in BRAND_TERMS and not token.isdigit()}


def clean_signal_text(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("/", "http://", "https://")):
        return ""
    if len(PERCENT_RE.findall(value)) >= 2:
        return ""
    return value


def is_page_like_url(url: str) -> bool:
    """Exclude obvious same-origin assets from the page-identity universe."""
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    return suffix not in NON_PAGE_LINK_SUFFIXES


def infer_lane(url: str, supplied: str = "", post_type: str = "") -> str:
    supplied = str(supplied or "").strip()
    path = url_path(url).lower()
    parts = [part for part in path.split("/") if part]
    mechanism_path = path
    if parts and parts[0] in COMMON_LANGUAGE_CODES:
        mechanism_path = "/" + "/".join(parts[1:]) + ("/" if path.endswith("/") else "")
    if mechanism_path.endswith("/amp/"):
        return "legacy_amp"
    for prefix, lane in LANE_PREFIXES:
        if mechanism_path.startswith(prefix):
            return lane
    if re.search(r"/page/\d+/$", mechanism_path):
        return "pagination"
    if supplied:
        return supplied
    normalized_type = str(post_type or "").strip().lower()
    if normalized_type in {"post", "page", "article", "guide"}:
        return "content"
    if normalized_type in {"product", "listing", "offer"}:
        return "commerce"
    if normalized_type:
        return normalized_type
    return "content"


def language_lane(url: str, lang: str = "") -> str:
    supplied = str(lang or "").strip().lower().replace("_", "-").split("-", 1)[0]
    if supplied:
        return supplied
    path = url_path(url).lower()
    first = next((part for part in path.split("/") if part), "")
    return first if first in COMMON_LANGUAGE_CODES else "und"


def is_content_lane(lane: str) -> bool:
    return str(lane or "content").strip().lower() not in NON_CONTENT_LANES


class PageParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts = []
        self.h1_parts = []
        self.visible_parts = []
        self.content_parts = []
        self.links = []
        self.jsonld_raw = []
        self.canonical = ""
        self.robots = ""
        self.lang = ""
        self._stack = []
        self._skip_depth = 0
        self._in_title = False
        self._in_h1 = False
        self._h1_done = False
        self._anchor = None
        self._jsonld = False
        self._json_parts = []

    def _location(self) -> str:
        if "footer" in self._stack:
            return "footer"
        if "nav" in self._stack:
            return "nav"
        return "content"

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = {str(k).lower(): v for k, v in attrs}
        if not self._stack and tag == "html":
            self.lang = str(attrs_dict.get("lang") or "").strip()
        if tag not in self.VOID_TAGS:
            self._stack.append(tag)
        if tag == "script" and str(attrs_dict.get("type") or "").strip().lower() == "application/ld+json":
            self._jsonld = True
            self._json_parts = []
            self._skip_depth += 1
            return
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        elif tag == "h1" and not self._h1_done:
            self._in_h1 = True
        elif tag == "link":
            rel = str(attrs_dict.get("rel") or "").lower().split()
            if "canonical" in rel and attrs_dict.get("href"):
                self.canonical = urllib.parse.urljoin(self.base_url, attrs_dict["href"])
        elif tag == "meta" and str(attrs_dict.get("name") or "").lower() == "robots":
            self.robots = str(attrs_dict.get("content") or "")
        elif tag == "a" and attrs_dict.get("href") and self._anchor is None:
            href = str(attrs_dict["href"]).strip()
            if not href.lower().startswith(("mailto:", "tel:", "javascript:", "data:")) and not href.startswith("#"):
                self._anchor = {
                    "target": urllib.parse.urljoin(self.base_url, href),
                    "parts": [],
                    "rel": str(attrs_dict.get("rel") or ""),
                    "location": self._location(),
                }
        elif tag == "img" and self._anchor is not None and attrs_dict.get("alt"):
            self._anchor["parts"].append(str(attrs_dict["alt"]))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "script" and self._jsonld:
            self._jsonld = False
            self.jsonld_raw.append("".join(self._json_parts).strip())
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._h1_done = True
        elif tag == "a" and self._anchor is not None:
            self._anchor["anchor"] = " ".join(" ".join(self._anchor.pop("parts")).split())
            self.links.append(self._anchor)
            self._anchor = None
        if self._stack:
            if self._stack[-1] == tag:
                self._stack.pop()
            elif tag in self._stack:
                index = len(self._stack) - 1 - self._stack[::-1].index(tag)
                self._stack = self._stack[:index]

    def handle_data(self, data):
        if self._jsonld:
            self._json_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._in_h1:
            self.h1_parts.append(data)
        if self._anchor is not None:
            self._anchor["parts"].append(data)
        if self._skip_depth == 0:
            stripped = " ".join(data.split())
            if stripped:
                self.visible_parts.append(stripped)
                if self._location() == "content":
                    self.content_parts.append(stripped)

    def result(self) -> dict:
        return {
            "title": " ".join(" ".join(self.title_parts).split()),
            "h1": " ".join(" ".join(self.h1_parts).split()),
            "visible_text": " ".join(self.visible_parts),
            "content_text": " ".join(self.content_parts),
            "links": self.links,
            "jsonld_raw": self.jsonld_raw,
            "canonical": self.canonical,
            "robots": self.robots,
            "lang": self.lang,
        }


def extract_schema_types(node) -> list[str]:
    result = []
    if isinstance(node, dict):
        value = node.get("@type")
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, list):
            result.extend(str(item) for item in value if isinstance(item, str))
        for child in node.values():
            result.extend(extract_schema_types(child))
    elif isinstance(node, list):
        for child in node:
            result.extend(extract_schema_types(child))
    return result


def schema_strings(node, keys=("url", "image", "logo", "sameAs")):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys:
                if isinstance(value, str):
                    yield key, value
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            yield key, item
            yield from schema_strings(value, keys)
    elif isinstance(node, list):
        for child in node:
            yield from schema_strings(child, keys)


def minhash_signature(tokens: list[str], hashes=32, shingle_size=4):
    if len(tokens) < shingle_size:
        return None
    shingles = {" ".join(tokens[i:i + shingle_size]) for i in range(len(tokens) - shingle_size + 1)}
    if not shingles:
        return None
    values = [int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big") for s in shingles]
    mask = (1 << 64) - 1
    signature = []
    for index in range(hashes):
        seed = (0x9E3779B97F4A7C15 * (index + 1)) & mask
        signature.append(min((value ^ seed) & mask for value in values))
    return signature


def merge_record(known: dict, url: str, row: dict, source: str, site: str):
    if not url:
        return
    current = known.setdefault(url, {
        "url": url,
        "path": url_path(url),
        "title": "",
        "h1": "",
        "lane": "",
        "cluster": "",
        "post_type": "",
        "latest_clicks": 0.0,
        "latest_impressions": 0.0,
        "since_work_clicks": 0.0,
        "since_work_impressions": 0.0,
        "inventory_word_count": 0.0,
        "inventory_link_count": 0.0,
        "top_queries": "",
        "in_sitemap": False,
        "sources": [],
    })
    current["sources"].append(source)
    aliases = {
        "title": ("title", "yoastTitle"),
        "h1": ("h1",),
        "cluster": ("strategicCluster", "cluster", "sourceCluster"),
        "post_type": ("postType", "post_type"),
        "top_queries": ("topQueries", "top_queries"),
    }
    for target, fields in aliases.items():
        value = first_value(row, fields)
        if value and not current[target]:
            current[target] = value
    lane = first_value(row, ("mechanismLane", "mechanism", "lane"))
    if lane and not current["lane"]:
        current["lane"] = lane
    metric_aliases = {
        "latest_clicks": ("latestClicks", "clicks"),
        "latest_impressions": ("latestImpressions", "impressions"),
        "since_work_clicks": ("sinceWorkClicks",),
        "since_work_impressions": ("sinceWorkImpressions",),
        "inventory_word_count": ("wordCount", "word_count"),
        "inventory_link_count": ("linkCount", "link_count", "links"),
    }
    for target, fields in metric_aliases.items():
        value = first_value(row, fields)
        if value != "":
            current[target] = max(current[target], numeric(value))
    if boolish(row.get("inSitemap") or row.get("in_sitemap")) or bool(row.get("sitemap")):
        current["in_sitemap"] = True
    current["lane"] = infer_lane(url, current["lane"], current["post_type"])


def load_inventory(path: str, site: str, known: dict):
    source = str(Path(path).resolve())
    suffix = Path(path).suffix.lower()
    rows = []
    if suffix == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    elif suffix == ".json":
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            collection = None
            for key in ("pages", "items", "rows"):
                if key in data:
                    collection = data[key]
                    break
            if isinstance(collection, dict):
                rows = []
                for key, value in collection.items():
                    row = dict(value or {}) if isinstance(value, dict) else {}
                    row.setdefault("url", key)
                    rows.append(row)
            elif isinstance(collection, list):
                rows = collection
            else:
                raise ValueError(f"No pages/items/rows collection in {path}")
    else:
        raise ValueError(f"Unsupported inventory format: {path}")
    accepted = 0
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        identity = first_value(raw, URL_FIELDS)
        url = normalize_url(identity, site)
        if not url or not same_site(url, site):
            continue
        merge_record(known, url, raw, source, site)
        accepted += 1
    return {"path": source, "rows": len(rows), "accepted": accepted}


def empty_source_universe(observed_normalized_identities: int = 0) -> dict:
    """A missing manifest cannot prove the URL source universe is complete."""
    return {
        "declared": False,
        "path": None,
        "sha256": None,
        "version": None,
        "site": None,
        "site_matches": False,
        "inventory_binding_complete": False,
        "page_cache_binding_complete": False,
        "sitemap_binding_complete": False,
        "input_binding_complete": False,
        "universe_declared_complete": False,
        "required_sources_complete": False,
        "source_universe_complete": False,
        "required_source_count": 0,
        "required_sources_incomplete": [],
        "expected_normalized_identities": None,
        "expected_count_origin": "NOT_PROVIDED",
        "observed_normalized_identities": observed_normalized_identities,
        "identity_count_matches": None,
        "scope_assurance": "NOT_DECLARED",
        "scope_warning": DECLARED_SCOPE_WARNING,
        "gate_reasons": ["source manifest was not declared"],
        "sources": [],
    }


def load_source_manifest(
    path: str,
    expected_site: str = "",
    inventory_paths: list[str] | None = None,
    page_cache_path: str | None = None,
    sitemap_hashes: list[str] | None = None,
    observed_normalized_identities: int = 0,
) -> dict:
    """Load and bind a local provenance declaration to the audited site and evidence files."""
    manifest_path = Path(path).resolve()
    body = manifest_path.read_bytes()
    data = json.loads(body.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Source manifest must be a JSON object")

    raw_sources = data.get("sources", [])
    if isinstance(raw_sources, dict):
        expanded = []
        for source_id, value in raw_sources.items():
            entry = dict(value or {}) if isinstance(value, dict) else {"status": value}
            entry.setdefault("id", source_id)
            expanded.append(entry)
        raw_sources = expanded
    if not isinstance(raw_sources, list):
        raise ValueError("Source manifest 'sources' must be a list or object")

    sources = []
    seen_ids = set()
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Source manifest entry {index} must be an object")
        source_id = str(raw.get("id") or raw.get("name") or f"source-{index}").strip()
        if source_id in seen_ids:
            raise ValueError(f"Duplicate source manifest id: {source_id}")
        seen_ids.add(source_id)
        status = str(raw.get("status") or "unspecified").strip().lower().replace("_", "-")
        required = boolish(raw.get("required"))
        entry = {
            "id": source_id,
            "kind": str(raw.get("kind") or raw.get("type") or "unspecified").strip(),
            "required": required,
            "status": status,
        }
        for key in ("path", "location", "records", "sha256", "reason", "note"):
            if raw.get(key) not in (None, ""):
                entry[key] = raw[key]
        sources.append(entry)

    declared_value = data.get("universe_complete")
    if declared_value is None:
        declared_value = data.get("source_universe_complete")
    universe_declared_complete = boolish(declared_value) if declared_value is not None else False
    incomplete = [
        {
            "id": source["id"],
            "kind": source["kind"],
            "status": source["status"],
            **({"reason": source["reason"]} if source.get("reason") else {}),
        }
        for source in sources
        if source["required"] and source["status"] not in SOURCE_READY_STATUSES
    ]
    required_source_count = sum(1 for source in sources if source["required"])
    required_sources_complete = bool(required_source_count) and not incomplete

    expected_normalized_identities = data.get("expected_normalized_identities")
    if expected_normalized_identities is not None:
        if isinstance(expected_normalized_identities, bool):
            raise ValueError("expected_normalized_identities must be a non-negative integer")
        try:
            parsed_expected_identities = int(expected_normalized_identities)
        except (TypeError, ValueError) as error:
            raise ValueError("expected_normalized_identities must be a non-negative integer") from error
        if (
            parsed_expected_identities < 0
            or str(expected_normalized_identities).strip() != str(parsed_expected_identities)
        ):
            raise ValueError("expected_normalized_identities must be a non-negative integer")
        expected_normalized_identities = parsed_expected_identities
    identity_count_matches = (
        None
        if expected_normalized_identities is None
        else observed_normalized_identities == expected_normalized_identities
    )
    expected_count_origin = normalize_expected_count_origin(
        data.get("expected_count_origin"), expected_normalized_identities
    )

    manifest_site_raw = str(data.get("site") or "").strip()
    manifest_site_parts = urllib.parse.urlsplit(manifest_site_raw)
    manifest_site_is_absolute = bool(
        manifest_site_parts.scheme in {"http", "https"} and manifest_site_parts.hostname
    )
    manifest_site = (
        normalize_url(manifest_site_raw, manifest_site_raw)
        if manifest_site_is_absolute else ""
    )
    site_matches = bool(expected_site and manifest_site and same_origin(manifest_site, expected_site))

    raw_outputs = data.get("outputs") if isinstance(data.get("outputs"), dict) else {}

    def declared_hashes(value) -> list[str]:
        items = value if isinstance(value, list) else [value]
        hashes = []
        for item in items:
            if isinstance(item, str):
                item = {"path": item}
            if not isinstance(item, dict):
                continue
            digest = str(item.get("sha256") or "").strip().lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                hashes.append(digest)
        return hashes

    inventory_output = raw_outputs.get("inventories", raw_outputs.get("inventory"))
    expected_inventory_hashes = declared_hashes(inventory_output)
    supplied_inventory_hashes = [
        file_sha256(Path(value)).lower()
        for value in inventory_paths or []
        if Path(value).is_file()
    ]
    inventory_binding_complete = bool(
        expected_inventory_hashes
        and Counter(expected_inventory_hashes) == Counter(supplied_inventory_hashes)
    )

    expected_page_cache_hashes = declared_hashes(raw_outputs.get("page_cache"))
    supplied_page_cache_hashes = []
    if page_cache_path and Path(page_cache_path).is_file():
        supplied_page_cache_hashes.append(file_sha256(Path(page_cache_path)).lower())
    page_cache_binding_complete = (
        Counter(expected_page_cache_hashes) == Counter(supplied_page_cache_hashes)
        if expected_page_cache_hashes or supplied_page_cache_hashes
        else True
    )
    expected_sitemap_hashes = declared_hashes(raw_outputs.get("sitemaps", raw_outputs.get("sitemap")))
    supplied_sitemap_hashes = [
        str(value).strip().lower()
        for value in sitemap_hashes or []
        if re.fullmatch(r"[0-9a-fA-F]{64}", str(value).strip())
    ]
    required_sitemap_source = any(
        source["required"]
        and source["kind"].strip().lower() == "sitemap"
        and source["status"] in SOURCE_READY_STATUSES
        for source in sources
    )
    if required_sitemap_source:
        sitemap_binding_complete = bool(
            expected_sitemap_hashes
            and Counter(expected_sitemap_hashes) == Counter(supplied_sitemap_hashes)
        )
    else:
        sitemap_binding_complete = (
            Counter(expected_sitemap_hashes) == Counter(supplied_sitemap_hashes)
            if expected_sitemap_hashes or supplied_sitemap_hashes
            else True
        )
    input_binding_complete = (
        inventory_binding_complete and page_cache_binding_complete and sitemap_binding_complete
    )

    gate_reasons = []
    if not universe_declared_complete:
        gate_reasons.append("source universe was not explicitly declared complete")
    if not sources:
        gate_reasons.append("manifest contains no source rows")
    if not required_source_count:
        gate_reasons.append("manifest contains no required source rows")
    if incomplete:
        gate_reasons.append("one or more required source rows are not collected")
    if not site_matches:
        gate_reasons.append("manifest site does not match the audited origin")
    if not inventory_binding_complete:
        gate_reasons.append("manifest inventory hash set does not exactly match the supplied inventories")
    if not page_cache_binding_complete:
        gate_reasons.append("manifest page-cache hash does not match the supplied page cache")
    if not sitemap_binding_complete:
        gate_reasons.append("manifest sitemap hash set does not exactly match the resolved sitemap inputs")
    if identity_count_matches is False:
        gate_reasons.append(
            "observed normalized source identity count does not match expected_normalized_identities"
        )
    source_universe_complete = not gate_reasons
    result = {
        "declared": True,
        "path": str(manifest_path),
        "sha256": hashlib.sha256(body).hexdigest(),
        "version": data.get("version"),
        "site": manifest_site or None,
        "site_matches": site_matches,
        "inventory_binding_complete": inventory_binding_complete,
        "page_cache_binding_complete": page_cache_binding_complete,
        "sitemap_binding_complete": sitemap_binding_complete,
        "input_binding_complete": input_binding_complete,
        "universe_declared_complete": universe_declared_complete,
        "required_sources_complete": required_sources_complete,
        "source_universe_complete": source_universe_complete,
        "required_source_count": required_source_count,
        "required_sources_incomplete": incomplete,
        "expected_normalized_identities": expected_normalized_identities,
        "expected_count_origin": expected_count_origin,
        "observed_normalized_identities": observed_normalized_identities,
        "identity_count_matches": identity_count_matches,
        "scope_warning": DECLARED_SCOPE_WARNING,
        "gate_reasons": gate_reasons,
        "sources": sources,
    }
    result["scope_assurance"] = source_scope_assurance(result)
    return result


def read_bytes(source: str, allow_network: bool, site: str, local_parent: Path | None = None):
    parsed = urllib.parse.urlsplit(source)
    if parsed.scheme in {"http", "https"}:
        if local_parent:
            local_candidate = local_parent / Path(parsed.path).name
            if local_candidate.exists():
                return local_candidate.read_bytes(), str(local_candidate.resolve()), local_candidate.parent
        if not allow_network:
            raise PermissionError(f"Network disabled for {source}")
        if not same_site(source, site):
            raise PermissionError(f"Cross-host sitemap blocked: {source}")
        with open_same_origin(source, site) as response:
            body = response.read(MAX_SITEMAP_BYTES + 1)
            if len(body) > MAX_SITEMAP_BYTES:
                raise ValueError(f"Sitemap exceeds {MAX_SITEMAP_BYTES} bytes")
            return body, response.geturl(), None
    path = Path(source)
    if not path.is_absolute() and local_parent:
        path = local_parent / path
    return path.read_bytes(), str(path.resolve()), path.resolve().parent


def load_sitemaps(sources: list[str], site: str, allow_network: bool):
    urls = set()
    visited = set()
    resolved = []
    hashes = []
    unresolved = []

    def visit(source: str, parent: Path | None = None):
        identity = str(source)
        if identity in visited:
            return
        visited.add(identity)
        try:
            body, resolved_source, local_parent = read_bytes(source, allow_network, site, parent)
            root = ET.fromstring(body)
            resolved.append(resolved_source)
            hashes.append(hashlib.sha256(body).hexdigest())
        except Exception as exc:
            unresolved.append({"source": identity, "error": str(exc)})
            return
        def tag_parts(tag: str) -> tuple[str, str]:
            if tag.startswith("{") and "}" in tag:
                namespace, local_name = tag[1:].split("}", 1)
                return namespace, local_name.lower()
            return "", tag.lower()

        root_namespace, kind = tag_parts(root.tag)

        def direct_locs(container_name: str) -> list[str]:
            values = []
            for container in list(root):
                namespace, local_name = tag_parts(container.tag)
                if namespace != root_namespace or local_name != container_name:
                    continue
                for element in list(container):
                    namespace, local_name = tag_parts(element.tag)
                    if namespace == root_namespace and local_name == "loc" and element.text:
                        values.append(element.text.strip())
            return values

        if kind == "sitemapindex":
            for child in direct_locs("sitemap"):
                visit(child, local_parent)
        elif kind == "urlset":
            for value in direct_locs("url"):
                url = normalize_url(value, site)
                if url and same_site(url, site):
                    urls.add(url)
        else:
            unresolved.append({"source": resolved_source, "error": f"Unsupported root element: {kind}"})

    for source in sources:
        visit(source)
    return {
        "urls": urls,
        "resolved": resolved,
        "hashes": hashes,
        "unresolved": unresolved,
    }


def load_page_cache(path: str, site: str):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    default_html_complete = boolish(data.get("html_complete")) if isinstance(data, dict) else False
    if isinstance(data, list):
        collection = data
    elif isinstance(data, dict):
        collection = data.get("pages", data.get("rows", []))
    else:
        collection = []
    rows = []
    if isinstance(collection, dict):
        for key, value in collection.items():
            row = dict(value or {}) if isinstance(value, dict) else {}
            row.setdefault("url", key)
            rows.append(row)
    elif isinstance(collection, list):
        rows = collection
    pages = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        identity = first_value(row, URL_FIELDS)
        url = normalize_url(identity, site)
        if not url or not same_site(url, site):
            continue
        html = first_value(row, HTML_FIELDS)
        html_complete_raw = first_value(row, HTML_COMPLETE_FIELDS)
        pages[url] = {
            "url": url,
            "status": int(numeric(row.get("status"), 0)),
            "final_url": normalize_url(row.get("final_url") or row.get("finalUrl") or url, site),
            "html": html,
            "html_complete": boolish(html_complete_raw) if html_complete_raw else default_html_complete,
            "truncated": boolish(row.get("truncated")),
            "conflicting_snapshots": boolish(row.get("conflicting_snapshots")),
            "source": str(Path(path).resolve()),
        }
    return pages


def fetch_page(url: str, site: str):
    try:
        with open_same_origin(url, site) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            truncated = len(body) > MAX_RESPONSE_BYTES
            body = body[:MAX_RESPONSE_BYTES]
            html = body.decode("utf-8", errors="replace") if "html" in content_type.lower() else ""
            return {
                "url": url,
                "status": int(response.status),
                "final_url": normalize_url(response.geturl(), site),
                "html": html,
                "html_complete": bool(html) and not truncated,
                "truncated": truncated,
                "source": "approved_live_get",
            }
    except urllib.error.HTTPError as exc:
        return {"url": url, "status": int(exc.code), "final_url": url, "html": "", "html_complete": False, "truncated": False, "source": "approved_live_get"}
    except Exception as exc:
        return {"url": url, "status": 0, "final_url": url, "html": "", "html_complete": False, "truncated": False, "source": "approved_live_get", "error": str(exc)}


def crawl_pages(urls: list[str], site: str, max_pages: int, delay_ms: int):
    ordered = sorted(set(urls), key=lambda value: (0 if url_path(value) == "/" else 1, value))
    if max_pages > 0:
        ordered = ordered[:max_pages]
    pages = {}
    for index, url in enumerate(ordered, 1):
        page = fetch_page(url, site)
        pages[url] = page
        print(f"[{index}/{len(ordered)}] {page['status']} {url}", file=sys.stderr)
        if index < len(ordered) and delay_ms > 0:
            time.sleep(delay_ms / 1000)
    return pages


def add_finding(findings: list, finding_type: str, severity: str, status: str, **fields):
    finding = {"type": finding_type, "severity": severity, "status": status}
    finding.update(fields)
    findings.append(finding)


def parse_cached_pages(cache: dict, known: dict, site: str, findings: list):
    analyses = {}
    links = []
    schema_counts = Counter()
    for url, cached in cache.items():
        record = known.get(url, {})
        status = int(cached.get("status") or 0)
        html = cached.get("html") or ""
        final_url = cached.get("final_url") or url
        truncated = bool(cached.get("truncated"))
        conflicting_snapshots = bool(cached.get("conflicting_snapshots"))
        html_complete = bool(cached.get("html_complete"))
        identity_redirect = bool(final_url and normalize_url(final_url, site) != url)
        same_origin_identity_redirect = bool(identity_redirect and same_origin(final_url, site))
        html_usable = bool(
            html
            and html_complete
            and 200 <= status < 300
            and same_origin(final_url, site)
            and not identity_redirect
            and not truncated
            and not conflicting_snapshots
        )
        analysis = {
            "url": url,
            "path": url_path(url),
            "status": status,
            "final_url": final_url,
            "html_available": html_usable,
            "html_present": bool(html),
            "html_complete": html_complete,
            "html_truncated": truncated,
            "conflicting_snapshots": conflicting_snapshots,
            "identity_redirect": identity_redirect,
            "same_origin_identity_redirect": same_origin_identity_redirect,
            "title": record.get("title", ""),
            "h1": record.get("h1", ""),
            "canonical": "",
            "robots": "",
            "noindex": False,
            "lang": "",
            "lane": record.get("lane") or infer_lane(url),
            "cluster": record.get("cluster", ""),
            "word_count": int(record.get("inventory_word_count") or 0),
            "text_hash": "",
            "minhash": None,
            "schema_types": [],
            "schema_blocks": 0,
            "tokens": [],
        }
        if html_usable:
            parser = PageParser(final_url)
            try:
                parser.feed(html)
            except Exception as exc:
                add_finding(findings, "html_parse_warning", "low", "confirmed", url=url, evidence=str(exc))
            parsed = parser.result()
            analysis["title"] = parsed["title"] or analysis["title"]
            analysis["h1"] = parsed["h1"] or analysis["h1"]
            analysis["canonical"] = normalize_url(parsed["canonical"], site) if parsed["canonical"] else ""
            analysis["robots"] = parsed["robots"]
            analysis["noindex"] = "noindex" in parsed["robots"].lower()
            analysis["lang"] = parsed["lang"]
            analysis["lane"] = infer_lane(url, analysis["lane"], record.get("post_type", ""))
            tokens = tokenize(parsed["content_text"] or parsed["visible_text"])
            analysis["tokens"] = tokens
            analysis["word_count"] = len(tokens)
            normalized_text = " ".join(tokens)
            analysis["text_hash"] = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() if len(tokens) >= 40 else ""
            analysis["minhash"] = minhash_signature(tokens) if len(tokens) >= 80 else None
            for link in parsed["links"]:
                target = normalize_url(link["target"], site)
                if not target or not same_site(target, site):
                    continue
                links.append({
                    "source": url,
                    "target": target,
                    "anchor": link.get("anchor", ""),
                    "rel": link.get("rel", ""),
                    "location": link.get("location", "content"),
                })
            for block_index, raw in enumerate(parsed["jsonld_raw"]):
                if not raw:
                    add_finding(findings, "schema_parse_error", "high", "confirmed", url=url, evidence=f"JSON-LD block {block_index} is empty")
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    add_finding(findings, "schema_parse_error", "high", "confirmed", url=url, evidence=f"JSON-LD block {block_index}: {exc}")
                    continue
                analysis["schema_blocks"] += 1
                types = extract_schema_types(data)
                analysis["schema_types"].extend(types)
                schema_counts.update(types)
                if isinstance(data, dict) and "@context" not in data:
                    add_finding(findings, "schema_context_candidate", "medium", "candidate", url=url, evidence=f"JSON-LD block {block_index} has no root @context")
                if not types:
                    add_finding(findings, "schema_missing_type", "medium", "confirmed", url=url, evidence=f"JSON-LD block {block_index} has no @type")
                for key, value in schema_strings(data):
                    if value and not value.startswith(("http://", "https://", "#")):
                        add_finding(findings, "schema_relative_url_candidate", "low", "candidate", url=url, evidence=f"{key}={value[:180]}")
                if isinstance(data, dict):
                    headline = data.get("headline") or data.get("name")
                    visible = analysis["h1"] or analysis["title"]
                    left, right = signal_tokens(str(headline or "")), signal_tokens(visible)
                    if left and right and len(left & right) / len(left | right) < 0.2:
                        add_finding(findings, "schema_visible_mismatch_candidate", "medium", "candidate", url=url, evidence=f"schema={headline!s} | visible={visible}")
        analyses[url] = analysis
    return analyses, links, schema_counts


def reconcile_discovered_page_identities(known: dict, analyses: dict, links: list, site: str) -> dict[str, list[str]]:
    """Add page-like identities revealed by parsed evidence before coverage is computed."""
    discovered = defaultdict(set)
    for link in links:
        target = link.get("target")
        if target and same_origin(target, site) and is_page_like_url(target) and target not in known:
            discovered[target].add("internal_link")
    for url, page in analyses.items():
        final_url = page.get("final_url")
        if (
            page.get("identity_redirect")
            and final_url
            and same_origin(final_url, site)
            and is_page_like_url(final_url)
            and final_url not in known
        ):
            discovered[final_url].add("redirect_final_url")
        canonical = page.get("canonical")
        if canonical and same_origin(canonical, site) and is_page_like_url(canonical) and canonical not in known:
            discovered[canonical].add("canonical")
    for url, evidence_types in discovered.items():
        merge_record(known, url, {}, "discovered:" + ",".join(sorted(evidence_types)), site)
    return {url: sorted(evidence_types) for url, evidence_types in sorted(discovered.items())}


def build_graph(known: dict, analyses: dict, links: list, site: str, graph_complete: bool, findings: list):
    inbound = Counter()
    inbound_content = Counter()
    outgoing = Counter()
    adjacency = defaultdict(set)
    observed = set()
    for link in links:
        source, target = link["source"], link["target"]
        inbound[target] += 1
        outgoing[source] += 1
        adjacency[source].add(target)
        observed.add((source, target))
        if link["location"] == "content":
            inbound_content[target] += 1
        anchor = " ".join(str(link.get("anchor") or "").lower().split())
        if anchor in GENERIC_ANCHORS:
            add_finding(findings, "generic_anchor", "low", "confirmed", source=source, target=target, evidence=anchor or "(empty)")
        target_page = analyses.get(target)
        if target_page:
            status = target_page.get("status", 0)
            if status >= 400:
                add_finding(findings, "broken_internal_link", "high", "confirmed", source=source, target=target, evidence=f"cached status={status}")
            elif target_page.get("identity_redirect") or 300 <= status < 400:
                add_finding(
                    findings,
                    "link_to_redirect",
                    "medium",
                    "confirmed",
                    source=source,
                    target=target,
                    evidence=f"cached status={status}; final_url={target_page.get('final_url') or 'unknown'}",
                )
            elif status == 0:
                add_finding(
                    findings,
                    "link_target_unverified",
                    "info",
                    "withheld",
                    source=source,
                    target=target,
                    evidence="target exists in the cache, but no HTTP status was supplied",
                )
            if target_page.get("noindex"):
                add_finding(findings, "link_to_noindex", "medium", "confirmed", source=source, target=target, evidence="target meta robots contains noindex")
            canonical = target_page.get("canonical")
            if canonical and canonical.rstrip("/") != target.rstrip("/"):
                add_finding(findings, "link_to_noncanonical", "medium", "confirmed", source=source, target=target, evidence=f"canonical={canonical}")

    home = normalize_url(site, site)
    depths = {home: 0} if home in analyses and analyses[home].get("html_available") else {}
    queue = deque([home]) if depths else deque()
    while queue:
        source = queue.popleft()
        for target in adjacency.get(source, set()):
            if target in analyses and target not in depths:
                depths[target] = depths[source] + 1
                queue.append(target)

    for url, page in analyses.items():
        if not page.get("html_available") or page.get("status") != 200 or page.get("noindex") or url == home:
            continue
        if inbound[url] == 0:
            if graph_complete:
                add_finding(findings, "orphan_candidate", "high", "candidate", url=url, evidence="zero observed inbound links in complete graph")
            else:
                add_finding(findings, "zero_inbound_partial", "info", "withheld", url=url, evidence="zero observed inbound links, but graph coverage is incomplete")
        if graph_complete and url not in depths:
            add_finding(findings, "unreachable_from_home_candidate", "medium", "candidate", url=url, evidence="not reachable from homepage in complete parsed graph")
        elif graph_complete and depths.get(url, 0) > 3:
            add_finding(findings, "deep_page_candidate", "medium", "candidate", url=url, evidence=f"click depth={depths[url]}")
    return inbound, inbound_content, outgoing, depths, observed


def duplicate_findings(analyses: dict, findings: list, threshold: float, max_pairs: int):
    exact = defaultdict(list)
    for url, page in analyses.items():
        if page.get("status") == 200 and not page.get("noindex") and page.get("text_hash"):
            exact[page["text_hash"]].append(url)
    exact_pairs = set()
    for digest, urls in exact.items():
        if len(urls) > 1:
            sorted_urls = sorted(urls)
            for index, left in enumerate(sorted_urls):
                for right in sorted_urls[index + 1:]:
                    exact_pairs.add((left, right))
            add_finding(findings, "exact_duplicate_candidate", "high", "candidate", urls=sorted_urls, evidence=f"same normalized content sha256={digest[:16]}")

    buckets = defaultdict(list)
    pages = {url: page for url, page in analyses.items() if page.get("minhash") and page.get("status") == 200 and not page.get("noindex")}
    for url, page in pages.items():
        signature = page["minhash"]
        for band in range(8):
            start = band * 4
            buckets[(band, tuple(signature[start:start + 4]))].append(url)
    candidates = set()
    for members in buckets.values():
        if len(members) < 2:
            continue
        members = sorted(set(members))
        for index, left in enumerate(members):
            for right in members[index + 1:]:
                if (left, right) not in exact_pairs:
                    candidates.add((left, right))
                    if len(candidates) >= max_pairs:
                        break
            if len(candidates) >= max_pairs:
                break
        if len(candidates) >= max_pairs:
            break
    for left, right in sorted(candidates):
        first, second = pages[left], pages[right]
        if first.get("lane") != second.get("lane") or language_lane(left, first.get("lang")) != language_lane(right, second.get("lang")):
            continue
        similarity = sum(a == b for a, b in zip(first["minhash"], second["minhash"])) / len(first["minhash"])
        if similarity >= threshold:
            add_finding(findings, "near_duplicate_candidate", "medium", "candidate", source=left, target=right, evidence=f"MinHash similarity={similarity:.3f}; requires content/mechanism review")


def cannibalization_findings(known: dict, analyses: dict, findings: list, threshold: float, max_pairs: int):
    signals = {}
    for url, record in known.items():
        page = analyses.get(url, {})
        title = clean_signal_text(page.get("title") or record.get("title") or "")
        h1 = clean_signal_text(page.get("h1") or record.get("h1") or "")
        queries = clean_signal_text(record.get("top_queries") or "")
        lane = record.get("lane") or page.get("lane") or infer_lane(url)
        if not is_content_lane(lane):
            continue
        tokens = signal_tokens(f"{title} {h1} {queries}")
        if len(tokens) >= 2:
            signals[url] = {
                "tokens": tokens,
                "lane": lane,
                "language": language_lane(url, page.get("lang", "")),
                "title": title,
                "impressions": record.get("latest_impressions", 0),
                "since_work_impressions": record.get("since_work_impressions", 0),
            }
    index = defaultdict(list)
    for url, signal in signals.items():
        for token in signal["tokens"]:
            index[token].append(url)
    pairs = set()
    shared_counts = Counter()
    ceiling = max(200, int(len(signals) * 0.2))
    for token, members in index.items():
        if len(members) > ceiling:
            continue
        members = sorted(set(members))
        for idx, left in enumerate(members):
            for right in members[idx + 1:]:
                if signals[left]["lane"] != signals[right]["lane"] or signals[left]["language"] != signals[right]["language"]:
                    continue
                pair = (left, right)
                shared_counts[pair] += 1
                if shared_counts[pair] >= 2:
                    pairs.add(pair)
                if len(pairs) >= max_pairs:
                    break
            if len(pairs) >= max_pairs:
                break
        if len(pairs) >= max_pairs:
            break
    for left, right in sorted(pairs):
        a, b = signals[left], signals[right]
        if numeric(a["impressions"]) + numeric(b["impressions"]) <= 0:
            continue
        shared = a["tokens"] & b["tokens"]
        similarity = len(shared) / len(a["tokens"] | b["tokens"])
        if similarity >= threshold:
            add_finding(
                findings,
                "cannibalization_candidate",
                "medium",
                "candidate",
                source=left,
                target=right,
                evidence=f"title/H1/query token Jaccard={similarity:.3f}; shared={', '.join(sorted(shared)[:12])}; finalized search-performance confirmation required",
            )


def link_opportunities(known: dict, analyses: dict, inbound_content: Counter, observed: set, graph_complete: bool, findings: list, limit=50):
    if not graph_complete:
        return
    sources = []
    for url, record in known.items():
        page = analyses.get(url)
        if not page or page.get("status") != 200 or page.get("noindex") or not page.get("html_available"):
            continue
        if not is_content_lane(page.get("lane")):
            continue
        tokens = signal_tokens(f"{page.get('title', '')} {page.get('h1', '')} {record.get('top_queries', '')}")
        sources.append((url, record, page, tokens))
    targets = sorted(sources, key=lambda item: (-numeric(item[1].get("latest_impressions")), inbound_content[item[0]], item[0]))
    emitted = 0
    for target, target_record, target_page, target_tokens in targets:
        if emitted >= limit or numeric(target_record.get("latest_impressions")) <= 0 or inbound_content[target] > 1 or len(target_tokens) < 2:
            continue
        candidates = []
        for source, source_record, source_page, source_tokens in sources:
            if source == target or (source, target) in observed:
                continue
            if target_page.get("lane") != source_page.get("lane") or language_lane(target, target_page.get("lang")) != language_lane(source, source_page.get("lang")):
                continue
            if target_record.get("cluster") and source_record.get("cluster") and target_record.get("cluster") != source_record.get("cluster"):
                continue
            overlap = len(target_tokens & source_tokens) / len(target_tokens | source_tokens) if target_tokens | source_tokens else 0
            if overlap > 0:
                candidates.append((overlap, numeric(source_record.get("latest_impressions")), source))
        candidates.sort(reverse=True)
        if candidates:
            best = [item[2] for item in candidates[:3]]
            add_finding(
                findings,
                "internal_link_opportunity",
                "medium",
                "candidate",
                target=target,
                sources=best,
                evidence=f"latest impressions={numeric(target_record.get('latest_impressions')):.0f}; contextual inbound={inbound_content[target]}; topical source candidates={len(candidates)}",
            )
            emitted += 1


def csv_value(value):
    if isinstance(value, (dict, list, tuple, set)):
        value = json.dumps(list(value) if isinstance(value, set) else value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in fields})


def finding_url(finding: dict) -> str:
    if finding.get("source") and finding.get("target"):
        return f"{finding['source']} ↔ {finding['target']}"
    return finding.get("url") or finding.get("target") or finding.get("source") or ", ".join(finding.get("urls", [])[:2])


def content_gate_passes(
    graph_eligible_total: int,
    html_pages: int,
    homepage_parsed: bool,
    unresolved_sitemaps: int,
) -> bool:
    """Require full active-page evidence; 99.87% is deliberately not 100%."""
    return bool(
        graph_eligible_total
        and html_pages == graph_eligible_total
        and homepage_parsed
        and not unresolved_sitemaps
    )


def build_release_contract(
    source_universe: dict,
    coverage: dict,
    evidence_hashes: dict,
) -> dict:
    """Return a deterministic read-only gate, never authorization for a live change."""
    blocker_codes = []

    def block(code: str, condition: bool) -> None:
        if condition and code not in blocker_codes:
            blocker_codes.append(code)

    declared = bool(source_universe.get("declared"))
    block("SOURCE_MANIFEST_MISSING", not declared)
    if declared:
        block("SOURCE_ROWS_MISSING", not source_universe.get("sources"))
        block(
            "SOURCE_UNIVERSE_NOT_DECLARED_COMPLETE",
            not source_universe.get("universe_declared_complete"),
        )
        block("REQUIRED_SOURCES_MISSING", not source_universe.get("required_source_count"))
        block(
            "REQUIRED_SOURCES_INCOMPLETE",
            bool(source_universe.get("required_source_count"))
            and not source_universe.get("required_sources_complete"),
        )
        block("SOURCE_SITE_MISMATCH", not source_universe.get("site_matches"))
        block("INVENTORY_HASH_MISMATCH", not source_universe.get("inventory_binding_complete"))
        block("PAGE_CACHE_HASH_MISMATCH", not source_universe.get("page_cache_binding_complete"))
        block("SITEMAP_HASH_MISMATCH", not source_universe.get("sitemap_binding_complete"))
        block(
            "SOURCE_IDENTITY_COUNT_MISMATCH",
            source_universe.get("identity_count_matches") is False,
        )
        block(
            "SOURCE_UNIVERSE_CONTRADICTED",
            bool(source_universe.get("discovered_identity_count")),
        )

    block("NO_ACTIVE_IDENTITIES", not coverage["graph_eligible_urls"])
    block(
        "ACTIVE_HTML_INCOMPLETE",
        coverage["html_pages"] != coverage["graph_eligible_urls"],
    )
    block("HOMEPAGE_HTML_MISSING", not coverage["homepage_parsed"])
    block("UNRESOLVED_SITEMAPS", bool(coverage["unresolved_sitemaps"]))

    expected = source_universe.get("expected_normalized_identities")
    expected_count_origin = normalize_expected_count_origin(
        source_universe.get("expected_count_origin"), expected
    )
    scope_assurance = source_scope_assurance(source_universe)
    classification_target = max(
        coverage["known_urls"],
        expected if isinstance(expected, int) else source_universe.get("observed_normalized_identities", 0),
    )
    classified_count = coverage["html_pages"] + coverage["resolved_non_graph_urls"]
    unclassified_count = max(0, classification_target - classified_count)
    release_gate_passed = bool(coverage["graph_complete"])
    return {
        "schema_version": "1.0",
        "decision": "READY_FOR_HUMAN_REVIEW" if release_gate_passed else "WITHHOLD",
        "release_gate_passed": release_gate_passed,
        "live_change_authorized": False,
        "scope_assurance": scope_assurance,
        "scope_warning": DECLARED_SCOPE_WARNING,
        "stages": {
            "source_universe": {
                "passed": bool(coverage["source_universe_complete"]),
                "observed_normalized_identities": source_universe.get(
                    "observed_normalized_identities", 0
                ),
                "expected_normalized_identities": expected,
                "expected_count_origin": expected_count_origin,
                "identity_count_matches": source_universe.get("identity_count_matches"),
            },
            "active_html": {
                "passed": bool(coverage["content_graph_complete"]),
                "eligible_identities": coverage["graph_eligible_urls"],
                "full_html_identities": coverage["html_pages"],
                "confirmed_terminal_identities": coverage["resolved_non_graph_urls"],
                "coverage": coverage["html_coverage"],
                "required_coverage": 1.0,
                "homepage_parsed": bool(coverage["homepage_parsed"]),
                "unresolved_sitemaps": coverage["unresolved_sitemaps"],
            },
            "final": {"passed": release_gate_passed},
        },
        "unclassified_count": unclassified_count,
        "blocker_codes": blocker_codes,
        "evidence_hashes": evidence_hashes,
        "decision_boundary": (
            "Read-only evidence result. " + DECLARED_SCOPE_WARNING + " "
            "READY_FOR_HUMAN_REVIEW does not authorize, apply, or roll back any live change."
        ),
    }


def build_report(audit: dict) -> str:
    coverage = audit["coverage"]
    counts = audit["finding_counts"]
    lines = [
        "# ProofRank evidence-first site graph audit",
        "",
        f"Generated: `{audit['generated_at']}`",
        "",
        "## Result",
        "",
    ]
    if coverage["graph_complete"]:
        lines.append("The parsed internal-link graph passed the completeness gate. URL actions remain candidates until page mechanisms and search evidence are verified.")
    else:
        lines.append("The graph is incomplete. ProofRank withholds topology-dependent orphan, click-depth, reachability, and internal-link-opportunity conclusions where inputs are insufficient.")
    lines += [
        "",
        "## Coverage",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Known normalized URLs | {coverage['known_urls']} |",
        f"| Active graph-eligible URLs | {coverage['graph_eligible_urls']} |",
        f"| Resolved redirect / gone URLs | {coverage['resolved_non_graph_urls']} |",
        f"| URLs marked as sitemap entries | {coverage['sitemap_urls']} |",
        f"| Cache / GET records | {coverage['page_records']} |",
        f"| URLs with parsed HTML | {coverage['html_pages']} |",
        f"| HTML coverage | {coverage['html_coverage']:.2%} |",
        f"| Unresolved child sitemaps | {coverage['unresolved_sitemaps']} |",
        f"| Homepage parsed | {'yes' if coverage['homepage_parsed'] else 'no'} |",
        f"| Declared source scope explicitly marked complete | {'yes' if coverage['universe_declared_complete'] else 'no'} |",
        f"| Manifest site matches audit | {'yes' if coverage['source_site_matches'] else 'no'} |",
        f"| Manifest inventory hash set bound | {'yes' if coverage['source_inventory_binding_complete'] else 'no'} |",
        f"| Supplied HTML-cache hash bound | {'yes' if coverage['source_page_cache_binding_complete'] else 'no'} |",
        f"| Resolved sitemap hash set bound | {'yes' if coverage['source_sitemap_binding_complete'] else 'no'} |",
        f"| Declared-source-scope gate passed | {'yes' if coverage['source_universe_complete'] else 'no'} |",
        f"| Scope assurance | {audit['release_contract']['scope_assurance']} |",
        f"| Expected-count origin | {audit['release_contract']['stages']['source_universe']['expected_count_origin']} |",
        f"| Observed-content coverage gate passed | {'yes' if coverage['content_graph_complete'] else 'no'} |",
        f"| Final whole-site graph gate passed | {'yes' if coverage['graph_complete'] else 'no'} |",
        "",
        "## Findings",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Highest-priority evidence", ""]
    priority = {"high": 0, "medium": 1, "low": 2, "info": 3}
    top = sorted(audit["findings"], key=lambda item: (priority.get(item.get("severity"), 9), item.get("type", "")))[:25]
    if not top:
        lines.append("No measurable findings were produced from the supplied inputs.")
    else:
        lines += ["| Severity | Status | Type | URL / target | Evidence |", "|---|---|---|---|---|"]
        for item in top:
            evidence = str(item.get("evidence", "")).replace("|", "\\|").replace("\n", " ")[:220]
            lines.append(f"| {item.get('severity', '')} | {item.get('status', '')} | {item.get('type', '')} | {finding_url(item)} | {evidence} |")
    lines += [
        "",
        "## Decision boundary",
        "",
        DECLARED_SCOPE_WARNING,
        "",
        "This report does not authorize CMS edits, redirects, deletion, consolidation, noindex, schema deployment, sitemap submission, or other live changes. Verify the page mechanism and current search evidence before URL actions.",
        "",
        "## Output files",
        "",
        "- `audit.json`",
        "- `decision.json`",
        "- `pages.csv`",
        "- `links.csv`",
        "- `findings.csv`",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only multilingual site graph and content-overlap audit")
    parser.add_argument("--site", required=True)
    parser.add_argument("--inventory", action="append", default=[], help="CSV or JSON inventory; repeatable")
    parser.add_argument("--page-cache", help="Saved JSON page cache with rendered HTML")
    parser.add_argument("--sitemap", action="append", default=[], help="Local XML or approved URL; repeatable")
    parser.add_argument("--source-manifest", help="Local JSON declaration of source provenance and required-source completeness")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--crawl", action="store_true", help="Fetch seed URLs using read-only GET")
    parser.add_argument("--allow-network", action="store_true", help="Explicitly enable network reads")
    parser.add_argument("--max-pages", type=int, default=100, help="Network page limit; 0 means all seeds")
    parser.add_argument("--delay-ms", type=int, default=250)
    parser.add_argument("--save-cache", action="store_true")
    parser.add_argument(
        "--complete-threshold",
        type=float,
        default=1.0,
        help="Required active-page HTML coverage for topology claims; safety policy requires 1.0",
    )
    parser.add_argument("--near-duplicate-threshold", type=float, default=0.82)
    parser.add_argument("--cannibalization-threshold", type=float, default=0.62)
    parser.add_argument("--max-pairs", type=int, default=5000)
    parser.add_argument("--brand-term", action="append", default=[], help="Brand or location term to exclude from overlap signals; repeatable")
    parser.add_argument(
        "--gate-exit-code",
        action="store_true",
        help="Return 2 when the read-only release gate withholds; default report generation returns 0",
    )
    args = parser.parse_args(argv)

    for term in args.brand_term:
        BRAND_TERMS.update(tokenize(term))

    site = normalize_url(args.site, args.site)
    if args.crawl and not args.allow_network:
        parser.error("--crawl requires --allow-network")
    if any(urllib.parse.urlsplit(source).scheme in {"http", "https"} for source in args.sitemap) and not args.allow_network:
        parser.error("remote --sitemap requires --allow-network")
    if args.complete_threshold != 1.0:
        parser.error(
            "--complete-threshold must be 1.0: orphan, reachability, click-depth, and "
            "link-opportunity claims require every active graph-eligible URL"
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    known = {}
    input_manifest = []
    for inventory in args.inventory:
        input_manifest.append(load_inventory(inventory, site, known))

    sitemap_data = (
        load_sitemaps(args.sitemap, site, args.allow_network)
        if args.sitemap else {"urls": set(), "resolved": [], "hashes": [], "unresolved": []}
    )
    observed_source_identities = {
        url for url in set(known) | set(sitemap_data["urls"])
        if is_page_like_url(url)
    }
    source_universe = (
        load_source_manifest(
            args.source_manifest,
            expected_site=site,
            inventory_paths=args.inventory,
            page_cache_path=args.page_cache,
            sitemap_hashes=sitemap_data["hashes"],
            observed_normalized_identities=len(observed_source_identities),
        )
        if args.source_manifest else empty_source_universe(len(observed_source_identities))
    )
    for url in sorted(sitemap_data["urls"]):
        merge_record(known, url, {"inSitemap": True}, "sitemap", site)

    cache = load_page_cache(args.page_cache, site) if args.page_cache else {}
    for url in cache:
        merge_record(known, url, {}, cache[url].get("source", "page_cache"), site)

    if args.crawl:
        seeds = sorted(set(known) | set(sitemap_data["urls"]))
        if not seeds:
            seeds = [site]
        live_cache = crawl_pages(seeds, site, args.max_pages, args.delay_ms)
        cache.update(live_cache)
        for url in live_cache:
            merge_record(known, url, {}, "approved_live_get", site)
        if args.save_cache:
            with (output_dir / "page_cache.json").open("w", encoding="utf-8") as handle:
                json.dump({"site": site, "generated_at": utc_now(), "pages": cache}, handle, ensure_ascii=False, indent=2)

    findings = []
    analyses, links, schema_counts = parse_cached_pages(cache, known, site, findings)
    discovered_identities = reconcile_discovered_page_identities(known, analyses, links, site)
    if discovered_identities:
        source_universe["source_universe_complete"] = False
        source_universe.setdefault("gate_reasons", []).append(
            f"{len(discovered_identities)} page-like identities were discovered outside the declared source universe"
        )
        source_universe["discovered_identity_count"] = len(discovered_identities)
        add_finding(
            findings,
            "source_universe_contradicted",
            "high",
            "withheld",
            evidence=(
                f"{len(discovered_identities)} undeclared page-like identities were found in internal links, "
                "same-origin redirect destinations, or canonicals; sample="
                + ", ".join(list(discovered_identities)[:5])
            ),
        )
    conflicting_cache_records = [
        url for url, page in analyses.items() if page.get("conflicting_snapshots")
    ]
    if conflicting_cache_records:
        add_finding(
            findings,
            "cache_snapshot_conflict",
            "high",
            "withheld",
            evidence=(
                f"{len(conflicting_cache_records)} URL(s) have conflicting crawler snapshots with unknown freshness; "
                "their HTML is excluded from topology coverage until one authoritative snapshot is selected; sample="
                + ", ".join(conflicting_cache_records[:5])
            ),
        )
    excluded_html_records = sum(
        1 for page in analyses.values()
        if page.get("html_present")
        and not page.get("html_available")
        and (not page.get("status") or 200 <= int(page.get("status")) < 300)
    )
    if excluded_html_records:
        add_finding(
            findings,
            "html_evidence_excluded",
            "info",
            "withheld",
            evidence=(
                f"{excluded_html_records} cache record(s) contained HTML but were excluded from the coverage gate "
                "because full-HTML completeness was not explicitly attested, the status was unknown, the final URL "
                "changed identity or left the audited origin, the response was truncated, or crawler snapshots conflict."
            ),
        )
    known_total = len(known)
    identified_sitemap_urls = sum(1 for record in known.values() if record.get("in_sitemap"))
    resolved_non_graph = {
        url for url, page in analyses.items()
        if page.get("same_origin_identity_redirect") or int(page.get("status") or 0) in {404, 410}
    }
    graph_eligible_total = max(0, known_total - len(resolved_non_graph))
    html_pages = sum(1 for page in analyses.values() if page.get("html_available"))
    html_coverage = html_pages / graph_eligible_total if graph_eligible_total else 0.0
    homepage = normalize_url(site, site)
    homepage_parsed = bool(analyses.get(homepage, {}).get("html_available"))
    content_graph_complete = content_gate_passes(
        graph_eligible_total,
        html_pages,
        homepage_parsed,
        len(sitemap_data["unresolved"]),
    )
    graph_complete = bool(content_graph_complete and source_universe["source_universe_complete"])

    if not source_universe["source_universe_complete"]:
        incomplete_ids = ", ".join(source["id"] for source in source_universe["required_sources_incomplete"]) or "none"
        gate_reasons = "; ".join(source_universe.get("gate_reasons", [])) or "unspecified"
        add_finding(
            findings,
            "source_universe_incomplete" if source_universe["declared"] else "source_universe_not_declared",
            "info",
            "withheld",
            evidence=(
                f"universe declared complete={'yes' if source_universe['universe_declared_complete'] else 'no'}; "
                f"required sources complete={'yes' if source_universe['required_sources_complete'] else 'no'}; "
                f"incomplete required sources={incomplete_ids}; reasons={gate_reasons}."
            ),
        )

    if not graph_complete:
        add_finding(
            findings,
            "graph_claims_withheld",
            "info",
            "withheld",
            evidence=(
                f"active HTML coverage={html_coverage:.2%} ({html_pages}/{graph_eligible_total}); "
                f"known URLs={known_total}; resolved redirects/gone={len(resolved_non_graph)}; "
                f"completeness threshold={args.complete_threshold:.2%}; "
                f"homepage parsed={'yes' if homepage_parsed else 'no'}; "
                f"unresolved sitemaps={len(sitemap_data['unresolved'])}; "
                f"source universe complete={'yes' if source_universe['source_universe_complete'] else 'no'}. "
                "Whole-site orphan, click-depth, unreachable-from-home, and internal-link-opportunity claims are withheld."
            ),
        )

    inbound, inbound_content, outgoing, depths, observed = build_graph(known, analyses, links, site, graph_complete, findings)
    duplicate_findings(analyses, findings, args.near_duplicate_threshold, args.max_pairs)
    cannibalization_findings(known, analyses, findings, args.cannibalization_threshold, args.max_pairs)
    link_opportunities(known, analyses, inbound_content, observed, graph_complete, findings)

    page_rows = []
    for url in sorted(known):
        record = known[url]
        page = analyses.get(url, {})
        page_rows.append({
            "url": url,
            "path": url_path(url),
            "title": page.get("title") or record.get("title", ""),
            "h1": page.get("h1") or record.get("h1", ""),
            "status": page.get("status", ""),
            "lane": page.get("lane") or record.get("lane", ""),
            "cluster": page.get("cluster") or record.get("cluster", ""),
            "in_sitemap": record.get("in_sitemap", False),
            "html_available": page.get("html_available", False),
            "noindex": page.get("noindex", False),
            "canonical": page.get("canonical", ""),
            "word_count": page.get("word_count", record.get("inventory_word_count", 0)),
            "inbound_total": inbound[url],
            "inbound_content": inbound_content[url],
            "outbound_total": outgoing[url],
            "depth": depths.get(url, ""),
            "schema_types": sorted(set(page.get("schema_types", []))),
            "latest_impressions": record.get("latest_impressions", 0),
            "latest_clicks": record.get("latest_clicks", 0),
            "source_count": len(record.get("sources", [])),
        })

    finding_counts = Counter(item["type"] for item in findings)
    lane_counts = Counter(row["lane"] for row in page_rows)
    coverage = {
        "known_urls": known_total,
        "graph_eligible_urls": graph_eligible_total,
        "resolved_non_graph_urls": len(resolved_non_graph),
        "sitemap_urls": identified_sitemap_urls,
        "page_records": len(analyses),
        "html_pages": html_pages,
        "html_coverage": html_coverage,
        "unresolved_sitemaps": len(sitemap_data["unresolved"]),
        "homepage_parsed": homepage_parsed,
        "complete_threshold": args.complete_threshold,
        "source_manifest_declared": source_universe["declared"],
        "universe_declared_complete": source_universe["universe_declared_complete"],
        "required_sources_complete": source_universe["required_sources_complete"],
        "source_site_matches": source_universe["site_matches"],
        "source_inventory_binding_complete": source_universe["inventory_binding_complete"],
        "source_page_cache_binding_complete": source_universe["page_cache_binding_complete"],
        "source_sitemap_binding_complete": source_universe["sitemap_binding_complete"],
        "source_input_binding_complete": source_universe["input_binding_complete"],
        "expected_source_identities": source_universe["expected_normalized_identities"],
        "observed_source_identities": source_universe["observed_normalized_identities"],
        "source_identity_count_matches": source_universe["identity_count_matches"],
        "source_universe_complete": source_universe["source_universe_complete"],
        "content_graph_complete": content_graph_complete,
        "graph_complete": graph_complete,
    }
    evidence_hashes = {
        "algorithm": "sha256",
        "source_manifest": source_universe.get("sha256"),
        "inventories": [file_sha256(Path(path)) for path in args.inventory],
        "page_cache": file_sha256(Path(args.page_cache)) if args.page_cache else None,
        "sitemaps": list(sitemap_data["hashes"]),
    }
    source_universe["scope_assurance"] = source_scope_assurance(source_universe)
    source_universe["scope_warning"] = DECLARED_SCOPE_WARNING
    release_contract = build_release_contract(source_universe, coverage, evidence_hashes)
    audit = {
        "generated_at": utc_now(),
        "mode": "approved_live_readonly" if args.crawl else ("saved_html_cache" if args.page_cache else "local_coverage"),
        "site": site,
        "inputs": {
            "inventories": input_manifest,
            "page_cache": str(Path(args.page_cache).resolve()) if args.page_cache else None,
            "source_universe": source_universe,
            "sitemaps_resolved": sitemap_data["resolved"],
            "sitemaps_unresolved": sitemap_data["unresolved"],
            "network_enabled": args.allow_network,
            "crawl_enabled": args.crawl,
            "max_pages": args.max_pages,
        },
        "coverage": coverage,
        "scope_assurance": release_contract["scope_assurance"],
        "scope_warning": release_contract["scope_warning"],
        "release_contract": release_contract,
        "lane_counts": dict(lane_counts),
        "schema_type_counts": dict(schema_counts),
        "finding_counts": dict(finding_counts),
        "findings": findings,
        "pages": page_rows,
        "links": links,
        "decision_boundary": (
            DECLARED_SCOPE_WARNING
            + " No live changes are authorized by this audit. Confirm the CMS mechanism and any "
            "required finalized search-performance evidence before URL actions."
        ),
    }

    with (output_dir / "audit.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2)
    with (output_dir / "decision.json").open("w", encoding="utf-8") as handle:
        json.dump(release_contract, handle, ensure_ascii=False, indent=2)
    write_csv(output_dir / "pages.csv", page_rows, [
        "url", "path", "title", "h1", "status", "lane", "cluster", "in_sitemap", "html_available",
        "noindex", "canonical", "word_count", "inbound_total", "inbound_content", "outbound_total", "depth",
        "schema_types", "latest_impressions", "latest_clicks", "source_count",
    ])
    write_csv(output_dir / "links.csv", links, ["source", "target", "anchor", "rel", "location"])
    write_csv(output_dir / "findings.csv", findings, ["type", "severity", "status", "url", "source", "target", "urls", "sources", "evidence"])
    (output_dir / "report.md").write_text(build_report(audit), encoding="utf-8")
    print(json.dumps({
        "output_dir": str(output_dir.resolve()),
        "mode": audit["mode"],
        "coverage": audit["coverage"],
        "decision": release_contract["decision"],
        "finding_counts": audit["finding_counts"],
    }, ensure_ascii=True, indent=2))
    if args.gate_exit_code and not release_contract["release_gate_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
