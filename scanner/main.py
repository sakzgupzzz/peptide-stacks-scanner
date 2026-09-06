"""CLI: scan sources, merge into corpus, write dashboard data.

Usage: python -m scanner.main [--no-reddit] [--no-pullpush] [--no-hn] [--corpus data/corpus.jsonl] [--out docs/data.json]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from .aggregate import aggregate
from .extract import extract
from .sources import SEARCH_TERMS, SUBREDDITS, HackerNews, PullPush, RedditOAuth, RedditRSS

log = logging.getLogger("main")


def load_corpus(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if path.exists():
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    out[r["id"]] = r
    return out


def save_corpus(path: Path, corpus: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in sorted(corpus.values(), key=lambda r: r["ts"]):
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


def run(args) -> int:
    corpus_path, out_path = Path(args.corpus), Path(args.out)
    corpus = load_corpus(corpus_path)
    before = len(corpus)
    seen_raw = 0
    t0 = time.time()

    def ingest(docs, label):
        nonlocal seen_raw
        n_new = 0
        for d in docs:
            seen_raw += 1
            rec = extract(d)
            if rec and rec["id"] not in corpus:
                corpus[rec["id"]] = rec
                n_new += 1
            elif rec and rec["score"] > corpus[rec["id"]].get("score", 0):
                corpus[rec["id"]]["score"] = rec["score"]
        log.info("%s: +%d records (%d total)", label, n_new, len(corpus))

    subs = args.subs.split(",") if args.subs else SUBREDDITS
    if not args.no_reddit:
        oauth = RedditOAuth()
        if oauth.available() and oauth.auth():
            ingest(oauth.fetch(subs), "reddit-oauth")
        else:
            log.info("no Reddit OAuth creds; using RSS fallback")
            ingest(RedditRSS(extended=args.rss_extended).fetch(subs), "reddit-rss")
    if not args.no_hn:
        ingest(HackerNews().fetch(SEARCH_TERMS), "hackernews")
    if not args.no_pullpush:
        ingest(PullPush().fetch(SEARCH_TERMS, per_term=args.pullpush_size), "pullpush")

    save_corpus(corpus_path, corpus)
    data = aggregate(list(corpus.values()))
    data["run"] = {"raw_seen": seen_raw, "new_records": len(corpus) - before, "seconds": round(time.time() - t0, 1)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    log.info("wrote %s (%d records, %d stacks) in %.0fs", out_path, data["totals"]["docs"], data["totals"]["distinct_stacks"], time.time() - t0)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus.jsonl")
    ap.add_argument("--out", default="docs/data.json")
    ap.add_argument("--subs", default="", help="comma-separated subreddit override")
    ap.add_argument("--no-reddit", action="store_true")
    ap.add_argument("--no-pullpush", action="store_true")
    ap.add_argument("--no-hn", action="store_true")
    ap.add_argument("--pullpush-size", type=int, default=100)
    ap.add_argument("--rss-extended", action="store_true", help="also pull top/search RSS feeds per sub (slower)")
    ap.add_argument("--aggregate-only", action="store_true", help="skip fetching; rebuild data.json from corpus")
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.v else logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)
    if args.aggregate_only:
        corpus = load_corpus(Path(args.corpus))
        Path(args.out).write_text(json.dumps(aggregate(list(corpus.values())), ensure_ascii=False, separators=(",", ":")))
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
