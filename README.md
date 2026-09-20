# Content Analyzer

A REST API that takes any article URL, extracts the clean article text (no
header, footer, ads, or navigation), and runs sentiment and readability
analysis on it. Results are persisted so past analyses can be looked up
later. Comes with a small browser UI for demoing it live.

## Problem

Pulling clean article text out of an arbitrary webpage is harder than it
looks: every site has a different layout, and most of the page is
navigation, ads, and related-content widgets rather than the article
itself. Once you have the text, sentiment and readability scores are
useful signals for content review, research, or monitoring, but only if
the extraction underneath them is reliable.

## Approach

**Extraction.** The page is downloaded, then handed to
[trafilatura](https://trafilatura.readthedocs.io/), which uses text density
heuristics rather than site-specific CSS selectors to find the main content
block. That's what lets this work on arbitrary sites instead of one
specific domain. If trafilatura can't find anything, a simple "largest text
block" fallback using BeautifulSoup kicks in. Sites behind bot protection
(Cloudflare challenges, paywalls returning a 403) fail with a clear error
message rather than a crash, since there's no way around those without
something like a headless browser, which felt out of scope here.

**Analysis.** Sentiment comes from
[VADER](https://github.com/cjhutto/vaderSentiment), a rule-based model that
works well on general web text without needing training data. Readability
uses [textstat](https://github.com/textstat/textstat)'s implementations of
the standard published formulas (Flesch Reading Ease, Flesch-Kincaid Grade,
Gunning Fog, SMOG, Automated Readability Index). Word length, syllables per
word, and personal pronoun count are computed directly since they're not
part of textstat's API.

**Persistence.** Every analysis is stored in SQLite via SQLAlchemy, so
`GET /analyses` and `GET /analyses/{id}` can look up anything analyzed
before without re-fetching the page.

## Architecture

```
Browser / client
      |
      v
   FastAPI  ----->  extraction.py (requests + trafilatura, BS4 fallback)
      |
      v
  analysis.py (VADER + textstat)
      |
      v
  SQLite (via SQLAlchemy)
```

## API

```
POST /analyze          body: {"url": "https://..."}
GET  /analyses          list recent analyses (paginated: ?limit=&offset=)
GET  /analyses/{id}     full detail for one analysis
GET  /health
GET  /                  simple browser UI
```

## Running it

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/` for the UI, or call the API directly:

```
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Web_scraping"}'
```

## Tests

```
pytest
```

12 tests covering the analysis functions directly (word/sentence counts,
pronoun detection excluding the country name "US", sentiment direction,
readability output shape) and the API end to end (success, extraction
failure, listing, 404, invalid URL), with extraction mocked so the tests
don't depend on the network.

## Known limitations

- Sites with aggressive bot protection or JavaScript-rendered content
  without a server-rendered fallback won't extract cleanly. A headless
  browser (Playwright/Selenium) would fix this at the cost of being much
  slower and heavier to run.
- Listing/hub pages (a homepage, a category page) don't have one coherent
  article to extract, so they're correctly rejected rather than returning
  garbage.
- SQLite is fine for a demo; a real deployment would move to Postgres by
  changing the `DATABASE_URL` environment variable, nothing else in the
  code needs to change.

## Stack

Python, FastAPI, SQLAlchemy, SQLite, trafilatura, BeautifulSoup, VADER,
textstat, pytest.
