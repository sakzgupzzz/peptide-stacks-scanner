"""Data sources. Each fetcher yields Doc dicts:
{id, source, subreddit, url, title, text, created_utc, score, author}
"""
from __future__ import annotations

import calendar
import html
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Iterator

import requests

log = logging.getLogger("sources")

UA = os.environ.get(
    "SCANNER_UA",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) peptide-stacks-scanner/0.2 (open-source research dashboard)",
)

SUBREDDITS = [
    "Peptides", "PeptideGuide", "bpc_157", "PeptidesUncensored", "peptidesforwomen",
    "Semaglutide", "tirzepatidecompound", "Retatrutide", "GLP1", "compoundedtirzepatide",
    "Biohackers", "moreplatesmoredates", "PEDs", "steroids", "Nootropics", "longevity",
    "Tesamorelin", "TRT", "Supplements", "PeptideSource", "glp1_stacks",
]

SEARCH_TERMS = [
    "peptide stack", "bpc-157", "tb-500", "retatrutide", "tirzepatide", "cjc-1295",
    "ipamorelin", "ghk-cu", "mots-c", "semax", "epitalon", "tesamorelin", "pt-141",
]

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s, flags=re.I)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


class Http:
    def __init__(self, min_interval: float = 1.2, max_retries: int = 4, backoff_base: float = 5.0):
        self.backoff_base = backoff_base
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._last = 0.0

    def get(self, url: str, **kw) -> requests.Response | None:
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.get(url, timeout=30, **kw)
            except requests.RequestException as e:
                log.warning("GET %s failed: %s", url, e)
                time.sleep(2 ** attempt)
                continue
            finally:
                self._last = time.time()
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503):
                backoff = min(180, self.backoff_base * (2 ** attempt))
                log.warning("GET %s -> %s, backoff %ss", url, r.status_code, backoff)
                time.sleep(backoff)
                continue
            log.info("GET %s -> %s (skip)", url, r.status_code)
            return None
        return None


# ---------------------------------------------------------------- Reddit OAuth
class RedditOAuth:
    """Uses a 'script' app. Env: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET (and optional
    REDDIT_USERNAME / REDDIT_PASSWORD for password grant; else client_credentials)."""

    def __init__(self):
        self.cid = os.environ.get("REDDIT_CLIENT_ID")
        self.sec = os.environ.get("REDDIT_CLIENT_SECRET")
        self.http = Http(min_interval=0.7)
        self.token = None

    def available(self) -> bool:
        return bool(self.cid and self.sec)

    def auth(self) -> bool:
        user, pw = os.environ.get("REDDIT_USERNAME"), os.environ.get("REDDIT_PASSWORD")
        data = {"grant_type": "password", "username": user, "password": pw} if user and pw else {"grant_type": "client_credentials"}
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token", auth=(self.cid, self.sec), data=data,
            headers={"User-Agent": UA}, timeout=30,
        )
        if r.status_code != 200:
            log.error("reddit oauth failed: %s %s", r.status_code, r.text[:200])
            return False
        self.token = r.json().get("access_token")
        self.http.s.headers["Authorization"] = f"bearer {self.token}"
        return bool(self.token)

    def listing(self, path: str, pages: int = 3, params: dict | None = None) -> Iterator[dict]:
        after = None
        for _ in range(pages):
            p = {"limit": 100, "raw_json": 1, **(params or {})}
            if after:
                p["after"] = after
            r = self.http.get("https://oauth.reddit.com" + path, params=p)
            if not r:
                return
            d = r.json().get("data", {})
            for c in d.get("children", []):
                yield c["data"]
            after = d.get("after")
            if not after:
                return

    def fetch(self, subs: list[str]) -> Iterator[dict]:
        for sub in subs:
            for kind, path, params, pages in [
                ("post", f"/r/{sub}/new", {}, 3),
                ("post", f"/r/{sub}/top", {"t": "month"}, 1),
                ("comment", f"/r/{sub}/comments", {}, 3),
            ]:
                for d in self.listing(path, pages=pages, params=params):
                    yield _reddit_item(d, kind)
            for term in ("stack", "protocol", "cycle"):
                for d in self.listing(f"/r/{sub}/search", pages=1, params={"q": term, "restrict_sr": 1, "sort": "new", "t": "year"}):
                    yield _reddit_item(d, "post")
        for term in SEARCH_TERMS:
            for d in self.listing("/search", pages=1, params={"q": term, "sort": "new", "t": "month"}):
                yield _reddit_item(d, "post")


def _reddit_item(d: dict, kind: str) -> dict:
    if kind == "comment" or d.get("body") is not None:
        text = d.get("body") or ""
        title = d.get("link_title") or ""
        url = "https://www.reddit.com" + (d.get("permalink") or "")
        _id = "t1_" + d["id"]
    else:
        text = d.get("selftext") or ""
        title = d.get("title") or ""
        url = "https://www.reddit.com" + (d.get("permalink") or "")
        _id = "t3_" + d["id"]
    return {
        "id": _id, "source": "reddit", "subreddit": d.get("subreddit", ""), "url": url,
        "title": title, "text": text, "created_utc": int(d.get("created_utc") or 0),
        "score": int(d.get("score") or 0), "author": d.get("author", ""),
    }


# ---------------------------------------------------------------- Reddit RSS (no auth)
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def _parse_atom(xml_text: str, sub: str) -> Iterator[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return
    for e in root.findall("a:entry", ATOM):
        eid = (e.findtext("a:id", default="", namespaces=ATOM) or "").strip()
        title = html.unescape(e.findtext("a:title", default="", namespaces=ATOM) or "")
        link_el = e.find("a:link", ATOM)
        url = link_el.attrib.get("href", "") if link_el is not None else ""
        content = e.findtext("a:content", default="", namespaces=ATOM) or ""
        updated = e.findtext("a:updated", default="", namespaces=ATOM) or e.findtext("a:published", default="", namespaces=ATOM) or ""
        author_el = e.find("a:author/a:name", ATOM)
        author = (author_el.text or "") if author_el is not None else ""
        try:
            ts = calendar.timegm(time.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            ts = int(time.time())
        text = strip_html(content)
        # RSS body for posts includes "submitted by /u/x [link] [comments]"; trim
        text = re.sub(r"submitted by\s+/u/\S+.*$", "", text, flags=re.S).strip()
        m = re.search(r"/comments/([a-z0-9]+)/", url)
        if eid.startswith("t1_") or eid.startswith("t3_"):
            _id = eid
        elif m:
            _id = "rss_" + m.group(1) + ("_" + eid[-8:] if "t1" in eid else "")
        else:
            _id = "rss_" + eid[-16:]
        yield {
            "id": _id, "source": "reddit", "subreddit": sub, "url": url, "title": title,
            "text": text, "created_utc": ts, "score": 0, "author": author.replace("/u/", ""),
        }


class RedditRSS:
    """Unauthenticated Atom feeds. Reddit throttles hard (~10 req/min/IP), so pace slowly."""

    def __init__(self, extended: bool = False):
        self.http = Http(min_interval=6.5, max_retries=4, backoff_base=30.0)
        self.extended = extended

    def fetch(self, subs: list[str]) -> Iterator[dict]:
        base = "https://www.reddit.com"
        for sub in subs:
            feeds = [
                f"{base}/r/{sub}/new.rss?limit=100",
                f"{base}/r/{sub}/comments.rss?limit=100",
            ]
            if self.extended:
                feeds += [
                    f"{base}/r/{sub}/top.rss?t=month&limit=100",
                    f"{base}/r/{sub}/search.rss?q=stack&restrict_sr=1&sort=new&limit=100",
                ]
            for u in feeds:
                r = self.http.get(u)
                if r is None:
                    if "new.rss" in u:
                        break  # sub probably doesn't exist / private
                    continue
                n = 0
                for d in _parse_atom(r.text, sub):
                    n += 1
                    yield d
                log.info("rss %s -> %d entries", u.split("reddit.com")[1][:50], n)


# ---------------------------------------------------------------- pullpush.io (Pushshift successor)
class PullPush:
    def __init__(self):
        self.http = Http(min_interval=3.0, max_retries=3)

    def fetch(self, terms: list[str], per_term: int = 100) -> Iterator[dict]:
        for term in terms:
            for kind in ("comment", "submission"):
                r = self.http.get(
                    f"https://api.pullpush.io/reddit/search/{kind}/",
                    params={"q": term, "size": per_term, "sort": "desc"},
                )
                if not r:
                    continue
                try:
                    items = r.json().get("data", [])
                except ValueError:
                    continue
                for d in items:
                    if not d.get("id"):
                        continue
                    yield _reddit_item(d, "comment" if kind == "comment" else "post")


# ---------------------------------------------------------------- Hacker News (Algolia)
class HackerNews:
    def __init__(self):
        self.http = Http(min_interval=0.5)

    def fetch(self, terms: list[str]) -> Iterator[dict]:
        since = int(time.time()) - 365 * 86400
        for term in terms:
            r = self.http.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"query": term, "tags": "(comment,story)", "hitsPerPage": 100, "numericFilters": f"created_at_i>{since}"},
            )
            if not r:
                continue
            for h in r.json().get("hits", []):
                text = strip_html(h.get("comment_text") or h.get("story_text") or "")
                title = h.get("title") or h.get("story_title") or ""
                yield {
                    "id": "hn_" + str(h["objectID"]), "source": "hackernews", "subreddit": "hn",
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                    "title": title, "text": text, "created_utc": int(h.get("created_at_i") or 0),
                    "score": int(h.get("points") or 0), "author": h.get("author") or "",
                }
