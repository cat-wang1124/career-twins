# Career-Twins: own-it-end-to-end walkthrough

A single doc you can keep open. Three parts: **what the project is**, **how to run/test it**, **how to push it from bash**. Everything below assumes macOS Terminal (zsh is the default since macOS Catalina; bash works the same for these commands).

---

## 1. The project in 60 seconds

**What it does.** You give it a LinkedIn URL or résumé text. It returns ~20 engineers on similar career trajectories, each with a one-line "why this match" and (where available) a personal-site link. It's a small, opinionated demo of the Exa search API.

**The dataflow.**

```
frontend/index.html  ──fetch──►  backend/server.py  ──calls──►  backend/twins.py  ──HTTP──►  Exa API
   (vanilla JS form)                (FastAPI route)              (the core logic)
```

**The three files that matter.**

| File | Lines | What it owns |
|---|---|---|
| `backend/twins.py` | ~320 | The whole brain: classify input → call Exa → fan out enrichment → cache. `find_twins()` is the only function you need to read first. |
| `backend/server.py` | ~90 | FastAPI wrapper. One real endpoint: `POST /api/twins`. Also serves the frontend static files. |
| `frontend/script.js` | ~150 | Vanilla JS. Reads the form, calls `/api/twins`, renders cards. No build step. |

**Read order if you have 15 minutes:** `README.md` → `backend/twins.py` (top-down, `find_twins` first) → `tests/test_twins.py` (the tests *are* the spec) → `backend/server.py` → `frontend/script.js`.

**Mental model for `find_twins`:**

1. Classify the input: URL vs. résumé text. Wrong shape → `ValueError`.
2. Check the JSON cache (7-day TTL, keyed by sha256 of `kind|n|payload`). Hit → return.
3. **One** Exa call for the seed: `find_similar_and_contents` for URLs, `search_and_contents` for text.
4. **Fan out** N enrichment calls in a `ThreadPoolExecutor(max_workers=10)`. Each one runs `get_contents` (for the "why match" summary) + `search` (for the personal site). Failures are caught and logged — they don't kill the request.
5. Re-sort by Exa's original ranking, cache, return.

That's the whole thing. Everything else is parsing helpers or plumbing.

**Why the design choices** (worth being able to defend in an interview):

- *JSON cache instead of SQLite*: inspectable in a code review; demo-grade.
- *ThreadPool, not asyncio*: the Exa SDK is sync. Threads are the lower-friction way to parallelize sync I/O.
- *Vanilla JS, no React*: smaller surface, no build step, no `node_modules`. The aesthetic is part of the point.
- *Exa's `summary={query: ...}` instead of a separate OpenAI call*: one billing line, one network hop, grounded in the candidate's own page.

---

## 2. Run it locally

I already set this up. The venv exists at `.venv/`, dependencies are installed, and **all 12 tests pass**. To do it yourself from scratch:

```bash
# 1. From the project folder
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/career-twins

# 2. Create + activate the virtual environment (Python's equivalent of an isolated package install)
python3 -m venv .venv
source .venv/bin/activate          # your prompt should now show (.venv)

# 3. Install the deps
pip install -r requirements.txt

# 4. Set up your Exa key
cp .env.example .env
# open .env and paste your key from https://dashboard.exa.ai

# 5. Run the tests (they mock Exa, so no key needed)
pytest -v

# 6. Run the server
uvicorn backend.server:app --reload --port 8000
```

Then in your browser:
- `http://localhost:8000` — the UI
- `http://localhost:8000/docs` — FastAPI's auto-generated Swagger UI. Great for poking the API without the frontend.
- `http://localhost:8000/api/health` — should return `{"status":"ok"}`

**The dev loop you'll use 100 times:**

```bash
source .venv/bin/activate     # once per terminal session
pytest -v                     # after every change to backend/
# uvicorn was started with --reload, so editing files auto-restarts the server
```

When you're done: `deactivate` exits the venv. `Ctrl+C` kills uvicorn.

**Where things will go wrong, and what to do:**

- `command not found: python3` → install via `brew install python@3.11`.
- `ModuleNotFoundError: exa_py` → you forgot `source .venv/bin/activate`.
- `EXA_API_KEY is not set` when calling the API → you didn't fill in `.env`, or you started uvicorn from a shell that hadn't loaded it. The simplest fix: `export EXA_API_KEY=your_key` in the same shell, then start uvicorn.
- Tests pass but the live API hangs → Exa is slow or down. Check `https://status.exa.ai`.

---

## 3. Bash + Git, coming from Windows

You've been in PowerShell/cmd. Here's the mapping for the commands you'll actually use day-to-day.

| You want to... | Windows | Bash (macOS/Linux) |
|---|---|---|
| Show current folder | `cd` (no args) | `pwd` |
| List files | `dir` | `ls`  (`ls -la` for everything incl. dotfiles) |
| Change folder | `cd folder` | `cd folder` (same) |
| Go up one level | `cd ..` | `cd ..` (same) |
| Home folder | `cd %USERPROFILE%` | `cd ~` |
| Make folder | `mkdir foo` | `mkdir foo` (same) |
| Delete file | `del foo.txt` | `rm foo.txt` |
| Delete folder | `rmdir /s foo` | `rm -rf foo` ← **dangerous, no undo** |
| Copy | `copy a b` | `cp a b`  (`-r` for folders) |
| Move/rename | `move a b` | `mv a b` |
| Show file contents | `type foo.txt` | `cat foo.txt` |
| Page through a file | `more foo.txt` | `less foo.txt` (press `q` to quit) |
| Find text in files | `findstr "x" *.py` | `grep "x" *.py`  (`grep -r "x" .` to recurse) |
| Set env var (session) | `set FOO=bar` | `export FOO=bar` |
| Run thing in background | `start /b ...` | `... &` |
| Get help on a command | `command /?` | `man command` or `command --help` |
| Clear screen | `cls` | `clear` (or `Ctrl+L`) |

**Three habits that will save you:**

1. **Tab-completion is your friend.** Type `cd back<TAB>` → bash fills in `backend/`. Works for files, folders, and most command flags.
2. **`Ctrl+R` searches your shell history.** Type `Ctrl+R`, then start typing a command you ran earlier — it autofills. Press `Enter` to run, or `→` to edit.
3. **`pwd` and `ls` constantly.** Bash doesn't show you the path in the prompt by default. When something doesn't work, check where you are.

### Git from bash

Git is the same git you'd use anywhere; it's the *shell* that's new. Setup once:

```bash
# Tell git who you are (once per machine)
git config --global user.name "Catherine Wang"
git config --global user.email "1124cat@gmail.com"

# Optional but nice: better default branch name, colored output, default editor
git config --global init.defaultBranch main
git config --global color.ui auto
git config --global core.editor "code --wait"   # VS Code; or use 'nano' / 'vim'
```

**Auth to GitHub.** Two options, pick one:

- **Easiest**: install GitHub CLI: `brew install gh`, then `gh auth login` → follow the browser flow. After that, pushing "just works" — `gh` handles your credentials.
- **Manual**: use an SSH key (`ssh-keygen -t ed25519 -C "1124cat@gmail.com"`, then add `~/.ssh/id_ed25519.pub` to GitHub → Settings → SSH Keys, then use `git@github.com:you/repo.git` as the remote).

### First push of career-twins

From the project folder:

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/career-twins

# 1. Initialize the repo (creates .git/)
git init

# 2. See what git sees
git status

# 3. Stage everything that's not in .gitignore
git add .

# 4. Take a snapshot
git commit -m "Initial commit: career-twins demo"

# 5. Create the remote repo on GitHub (one of these)
gh repo create career-twins --public --source=. --remote=origin --push
# --- OR if you didn't install gh: ---
# Go to github.com → New repo → name it career-twins → don't init with README → copy the URL it shows
# git remote add origin https://github.com/your-username/career-twins.git
# git branch -M main
# git push -u origin main
```

### The everyday loop after that

```bash
git status                    # what's changed?
git diff                      # what did I change line-by-line?
git add backend/twins.py      # stage a specific file
git add .                     # stage everything
git commit -m "Add CSV export to /api/twins"
git push                      # send to GitHub
```

Branching, when you're ready:

```bash
git checkout -b feature/csv-export    # new branch
# ... edit, add, commit ...
git push -u origin feature/csv-export # first push of a new branch
# Then open a PR on github.com, or: gh pr create --fill
```

**Three things to never do (or to do very carefully):**

- `git push --force` — overwrites history on GitHub. Almost never what you want on `main`.
- `git reset --hard` — discards local changes with no undo.
- Committing `.env`. Your `.gitignore` already excludes it; verify with `git status` before every commit that your API key isn't being staged.

### Reading what `.gitignore` does

Open `.gitignore` and you'll see it excludes `.venv/`, `__pycache__/`, `.cache/`, `.env`, and a few editor files. That's why `git add .` is safe — those won't end up on GitHub.

---

## 4. End-to-end ownership checklist

Things you should be able to do (or explain) before saying you own this:

- [ ] Run `pytest -v` and explain what each of the 12 tests covers.
- [ ] Trace a single request: form submit → `script.js` fetch → `server.py` route → `twins.py:find_twins` → Exa → back. Know which file you'd edit at each step.
- [ ] Explain why the cache key uses `sha256(kind|n|payload)` — and what would break if you dropped `n`.
- [ ] Add a new endpoint (e.g. `POST /api/cache/clear`) and a test for it. The CLAUDE.md lists this as a "good agent task" — try it as your first solo change.
- [ ] Defend two design choices against a reviewer: (1) ThreadPool over asyncio, (2) JSON cache over SQLite. CLAUDE.md has the reasoning; make sure you'd say the same thing in your own words.
- [ ] Know the six "Notes from the build" gotchas in the README. These are the most interesting things about the project from an Exa-API perspective — they're what you'd talk about in an interview.
- [ ] Push a small change end-to-end: branch, commit, push, PR, merge. The mechanics should feel routine.

When all of those feel boring, you own it.
