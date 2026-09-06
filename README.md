# Peptide Stack Scanner

Scans public forum posts (Reddit, Hacker News) for peptides people say they are taking,
finds which ones are mentioned together ("stacks"), and publishes a static dashboard to
GitHub Pages. Runs daily via GitHub Actions; the corpus accumulates in `data/corpus.jsonl`
so trends get better over time.

**Not medical advice.** Counts are mentions in public posts, not people, and imply nothing
about safety or efficacy.

## How it works

1. `scanner/sources.py` pulls recent posts + comments from ~20 subreddits (OAuth API if
   credentials are set, otherwise RSS), plus Hacker News (Algolia) and pullpush.io.
2. `scanner/peptides.py` holds a dictionary of ~90 compounds with alias regexes
   (e.g. `tirz`, `mounjaro` -> Tirzepatide) and blend names (`Wolverine` -> BPC-157 + TB-500).
3. `scanner/extract.py` tags each post with peptides, nearby doses, and inferred goals.
4. `scanner/aggregate.py` computes top stacks, co-mention matrix, weekly timeline, risers.
5. `docs/index.html` renders `docs/data.json` with no build step.

## Run locally

```bash
pip install -r requirements.txt
python -m scanner.main            # scan + write docs/data.json (5-15 min unauthenticated)
python -m scanner.main --aggregate-only   # rebuild data.json from existing corpus
python -m http.server -d docs 8000        # open http://localhost:8000
```

Flags: `--no-reddit`, `--no-hn`, `--no-pullpush`, `--rss-extended`, `--subs Peptides,Biohackers`.

## Reddit credentials (recommended)

Unauthenticated Reddit RSS is throttled to roughly 10 requests/minute and is often blocked
from cloud IPs such as GitHub Actions runners. Create a free "script" app at
https://www.reddit.com/prefs/apps and add these repository secrets:

| Secret | Value |
|---|---|
| `REDDIT_CLIENT_ID` | the string under the app name |
| `REDDIT_CLIENT_SECRET` | the app secret |
| `REDDIT_USERNAME` / `REDDIT_PASSWORD` | optional, enables the higher-rate password grant |

With credentials the scanner uses `oauth.reddit.com` (100 req/min) and pulls
new/top/comments/search listings per subreddit.

## Adding peptides or subreddits

Edit `PEPTIDES` / `BLENDS` in `scanner/peptides.py` and `SUBREDDITS` in `scanner/sources.py`,
then run `python -m scanner.main --aggregate-only` — existing corpus records keep their
original tags, so re-scanned posts pick up new names on the next run.
