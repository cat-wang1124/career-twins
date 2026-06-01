# Career Twin Finder

> Find twenty engineers whose careers look like yours.

A small demo built on [Exa's](https://exa.ai) search API. Paste a LinkedIn URL
or résumé text; get back twenty humans on similar trajectories, each annotated
with a one-line "why this match" summary and a link to their personal site
when discoverable.

## Demo

[Live demo](https://career-twins.onrender.com) · [Screenshot](#)

## Run locally

```bash
git clone <this-repo>
cd career-twins
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# put your Exa key in .env (get one at https://dashboard.exa.ai)

uvicorn backend.server:app --reload --port 8000
```

Then open `http://localhost:8000`.

## Test

```bash
pytest -v
```

Tests mock the Exa client, so they don't hit the network or burn credits.

## How it works

```
Input: LinkedIn URL OR résumé text (≥200 chars)
   │
   ▼
[URL  ] → exa.find_similar_and_contents(url, category="people")
[Text ] → exa.search_and_contents(text, category="people", type="auto")
   │
   ▼
N similar people, each with highlights
   │
   ▼
For each (parallel, threadpool of 10):
   • exa.get_contents([url], summary={query: "why match?"}) → "why match"
   • exa.search(name + " blog", category="personal site")   → personal site
   │
   ▼
Render
```

## Notes from the build

A few things I noticed using the Exa API that aren't on the marketing pages:

1. **`livecrawl` is silently deprecated.** The OpenAPI spec moved freshness
   control to `maxAgeHours` (integer, 0 = always fetch, -1 = always cache,
   positive = max staleness in hours). The SDK still accepts the old param
   for back-compat, but new code should use `maxAgeHours`.

2. **`category="people"` doesn't support date filters or `excludeDomains`.**
   Sending them returns a 400, not a silent ignore. This matters when you're
   composing a query and your code path assumes all categories accept the
   same filter set.

3. **Highlight quality jumps when you pass a `query`.** Default highlights are
   fine; `highlights={"query": "current role, technical background"}` is
   dramatically better for downstream LLM consumption. Same for `summary` —
   you basically always want to pass a `query`.

4. **`findSimilar` requires the seed URL to be in Exa's index.** Less-indexed
   LinkedIn profiles fall back to semantic search. The app handles this by
   exposing both code paths via the UI's tab toggle.

5. **`/contents` with a `summary.query` is a cheap way to do per-result LLM
   synthesis.** No second LLM call needed, no separate billing line — it all
   stays inside one Exa request. Used here for the "why this match" line.

6. **Cost is reasonable for prototyping.** A 20-twin lookup runs ~21 API calls
   (1 seed search + 20 enrichments). With the free tier's 1000 calls/month,
   that's about 47 lookups before hitting the wall. The local cache (`.cache/`)
   keeps demo runs free.

## File layout

```
career-twins/
├── backend/
│   ├── twins.py         # core logic: find_twins, enrichment, caching
│   ├── server.py        # FastAPI app
│   └── __init__.py
├── frontend/
│   ├── index.html       # single-page UI
│   ├── style.css        # editorial dark theme
│   └── script.js        # vanilla JS, no build step
├── tests/
│   └── test_twins.py    # pytest, fully mocked
├── requirements.txt
├── render.yaml          # one-click deploy to Render
├── .env.example
├── CLAUDE.md            # context for Claude Code if you fork this
└── README.md
```

## Deploy

The included `render.yaml` deploys to Render's free tier:

1. Push to GitHub
2. New Web Service on [render.com](https://render.com), connect the repo
3. Add `EXA_API_KEY` in the Render dashboard
4. Deploy

Free tier sleeps after 15 minutes of inactivity. First request after sleep
takes ~30s to wake. Fine for a demo, not for production.

## License

MIT.
