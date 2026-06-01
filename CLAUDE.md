# CLAUDE.md

Context for Claude Code working on this project. Read this first.

## What this is

A small demo built on [Exa's](https://exa.ai) search API. Takes a LinkedIn URL
or résumé text, returns ~20 engineers with similar career trajectories, each
enriched with a "why this match" summary and a personal site lookup.

Built as an interview prep artifact for an Exa SWE interview — so:
- Stays small and readable (one engineer can hold the whole thing in their head)
- Demonstrates real opinions about the Exa API (see README "Notes from the build")
- Doesn't pretend to be a product

## Architecture

```
frontend/  →  backend/server.py  →  backend/twins.py  →  Exa API
(HTML/JS)     (FastAPI)             (core logic)
```

- **`backend/twins.py`** is the heart. `find_twins(query, num_twins)` is the
  single entry point. Everything else is parsing helpers, caching, and
  parallelized enrichment.
- **`backend/server.py`** is a thin FastAPI wrapper. One real endpoint
  (`POST /api/twins`), plus static-file serving for the frontend.
- **`frontend/`** is plain HTML/CSS/JS, no build step. Editorial dark theme:
  warm off-black background, cream foreground, amber accent. Instrument Serif
  for display, Fraunces for body, JetBrains Mono for technical text.

## Conventions to follow

- **Keep the dependency footprint small.** This is a demo. Don't add React,
  Tailwind, or a database. If you find yourself reaching for those, push back.
- **Plain functions over classes.** Only `Twin` and `TwinResult` are dataclasses
  because they cross the API boundary.
- **Catch broad exceptions in enrichment paths.** A single failed lookup
  shouldn't kill the whole request. See `_enrich`.
- **Cache aggressively for demos.** The `.cache/twins.json` file is gitignored;
  it makes repeat runs free. TTL is 7 days.
- **Don't log API keys or user input verbatim.** Be careful with `log.info`.

## Working with the Exa API

A few things that are easy to get wrong:

1. **Use `maxAgeHours`, not `livecrawl`.** The latter is deprecated. If you
   add freshness control somewhere new, use `maxAgeHours`.
2. **`category="people"` and `category="company"` don't accept date filters
   or `excludeDomains`.** Sending them returns a 400.
3. **Always pass a `query` to `highlights` and `summary`.** Default
   highlights are noticeably worse than guided ones.
4. **`find_similar` requires the URL to be in Exa's index.** If you add a new
   input mode, decide upfront which endpoint it should use and document the
   reasoning in a comment.
5. **`outputSchema` exists and is great for structured output.** Currently
   unused; would be a natural fit if we added e.g. a "career path graph"
   feature.

The OpenAPI spec lives at https://docs.exa.ai/reference/search and is the
source of truth — the Python SDK lags it slightly.

## Testing

```bash
pytest -v
```

Tests mock the Exa client entirely (`fake_exa()` in `tests/test_twins.py`).
**Never write tests that hit the real API** — they'll flake and burn credits.

Coverage gaps worth filling if you add features:
- Cache TTL expiry (we test caching exists but not that it expires)
- Concurrent enrichment ordering (we test order is preserved, not that
  parallelism actually happens)
- Server-level tests for `/api/twins` (currently only unit tests for `twins.py`)

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in EXA_API_KEY
uvicorn backend.server:app --reload --port 8000
```

`http://localhost:8000` for the UI, `http://localhost:8000/docs` for the
auto-generated API docs (FastAPI gives this for free).

## Things to potentially add (good agent tasks)

These are reasonable next steps if asked to extend. Listed roughly in order
of usefulness:

- **"Career path graph" mode.** Use `outputSchema` to extract role history as
  structured JSON for each twin, then render a flow diagram of common career
  paths into the user's current company.
- **Export to CSV** — for someone using this as a job-hunt research tool.
- **Side-by-side comparison view** — pick 3 twins, see their trajectories
  next to yours.
- **Tighten error messages.** Currently we surface raw `RuntimeError` from
  the Exa client; should map to friendlier UI text.
- **Add a `/api/cache/clear` endpoint** so the demo can be force-refreshed
  without restarting the server.
- **Streaming results.** Render twins as they finish enriching rather than
  waiting for all to complete. The `as_completed` loop in `find_twins`
  already lends itself to this; just need to switch to SSE.
- **Per-IP rate limiting on the server.** Currently anyone hitting the demo
  could burn through the Exa quota.

## Things to NOT add (resist these)

- A database. The cache file is fine.
- User auth. This is a demo.
- A separate frontend framework (React/Vue/Svelte). The HTML/JS is part of
  the aesthetic — minimalist, hand-written, no build step.
- Multiple LLM providers. Exa's `summary` parameter is the whole point;
  don't add an OpenAI call alongside it.

## When in doubt

- Read the [Exa OpenAPI spec](https://docs.exa.ai/reference/search) before
  touching anything that calls Exa.
- The README's "Notes from the build" section is the most important
  reference document — it captures the opinions about Exa that make this
  demo worth showing off. Don't dilute it. If you discover a new
  Exa-specific gotcha while working on this, add it there.
- Match the existing code style. Functions over classes, narrow type hints,
  comments where the *why* isn't obvious.
