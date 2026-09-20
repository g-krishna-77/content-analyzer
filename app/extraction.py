"""
Generic article extraction.

Unlike a scraper written for one specific site, this works against arbitrary
URLs: it downloads the page, hands the HTML to trafilatura (which uses text
density heuristics to find the main article body on almost any layout), and
falls back to a simple "biggest text block" heuristic with BeautifulSoup if
trafilatura can't find anything. Sites behind aggressive bot protection
(Cloudflare challenge pages, 403s) will still fail; that's surfaced as a
clear ExtractionError rather than a crash or silently empty result.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
import trafilatura
from bs4 import BeautifulSoup

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 15
MIN_BODY_LENGTH = 200  # below this, we treat extraction as having failed


class ExtractionError(Exception):
    """Raised when a URL can't be fetched or no article content can be found."""


@dataclass
class ExtractedArticle:
    url: str
    title: str
    text: str


def _fallback_extract(html: str) -> str | None:
    """
    Very simple fallback used only if trafilatura finds nothing: pick the
    <article>/<main> element with the most text, or failing that, the <div>
    with the most <p> text on the page.
    """
    soup = BeautifulSoup(html, "lxml")

    candidates = soup.select("article, main") or soup.find_all("div")
    best_text, best_len = "", 0
    for el in candidates:
        text = el.get_text(separator="\n", strip=True)
        if len(text) > best_len:
            best_text, best_len = text, len(text)

    return best_text or None


def extract_article(url: str) -> ExtractedArticle:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise ExtractionError(f"Could not reach {url}: {exc}") from exc

    if response.status_code != 200:
        raise ExtractionError(f"{url} returned HTTP {response.status_code}")

    html = response.text

    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else "").strip()

    body = trafilatura.extract(html, include_comments=False, include_tables=False)
    if not body or len(body) < MIN_BODY_LENGTH:
        body = _fallback_extract(html)

    if not body or len(body) < MIN_BODY_LENGTH:
        raise ExtractionError(
            f"Could not find article content on {url} "
            "(page may be a listing page, paywalled, or blocking bots)"
        )

    if not title:
        # last resort: first line of the extracted body
        title = body.split("\n", 1)[0][:200]

    return ExtractedArticle(url=url, title=title, text=body.strip())
