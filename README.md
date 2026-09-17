# सजिलो एआई खबर — Free Automated Pipeline

A self-updating AI news site in simple Nepali, running entirely on free infrastructure:
**GitHub Actions** (scheduler) + **RSS feeds** (source) + an LLM API (translate/simplify/verify)
+ **GitHub Pages** (hosting).

```
RSS feeds → fetch_and_translate.py → data/articles.json → build_site.py → docs/index.html → GitHub Pages
                     ↑ runs every 4 hours via GitHub Actions, for free
```

## What's genuinely free here, and what isn't

| Piece | Cost |
|---|---|
| GitHub Actions scheduling | Free (public repo) |
| RSS feeds | Free |
| GitHub Pages hosting | Free |
| Domain | Free (`yourname.github.io/repo`) unless you buy a custom one |
| **LLM API calls** | **Not literally $0** with Anthropic, but very cheap (a few cents per run at this volume). See "Zero-cost alternative" below if you need exactly $0. |

Be honest with yourself about this line item — it's the only one that isn't free by default.

## Setup (about 15 minutes)

1. **Create a GitHub repo** and push this whole folder to it (`git init`, `git add .`,
   `git commit -m "init"`, then push to a new repo on github.com).

2. **Get an Anthropic API key**: console.anthropic.com → API Keys → Create Key.
   New accounts get a small amount of free credit, enough to test this for a while.

3. **Add the key as a repo secret**: on GitHub, go to your repo →
   Settings → Secrets and variables → Actions → New repository secret →
   name it `ANTHROPIC_API_KEY`, paste the key.

4. **Enable GitHub Pages**: Settings → Pages → under "Build and deployment",
   set Source to "Deploy from a branch", branch = `main`, folder = `/docs`. Save.
   Your site will appear at `https://yourusername.github.io/your-repo-name/`
   within a minute or two.

5. **Run it once manually** to seed the site instead of waiting 4 hours:
   Actions tab → "Update Sajilo AI Khabar" workflow → "Run workflow" button.

6. Check the Actions log. It'll print how many new articles it found, how many
   passed verification, and how many were held back for review.

That's it — from here it runs on its own every 4 hours.

## Zero-cost alternative: swap in Gemini's free tier

If you want $0 with no exceptions, Google's Gemini API has a genuinely free tier
(with rate limits). To swap it in:
- `pip install google-generativeai` instead of `anthropic` in `requirements.txt`
- Replace the `anthropic.Anthropic(...)` client and `call_json()` function in
  `scripts/fetch_and_translate.py` with the equivalent `google.generativeai` calls
  (same prompts, same JSON-in/JSON-out shape — only the API client changes)
- Add `GEMINI_API_KEY` as the GitHub secret instead of `ANTHROPIC_API_KEY`,
  and update the workflow file's `env:` line to match

Happy to write that swapped version in full if you'd rather start with Gemini.

## The review queue — read this before treating it as "done"

Any article where the automated verification step flags a possible mismatch
between the Nepali summary and the original source is saved to
`data/articles.json` with `"needs_review": true`, but it is **excluded** from
`docs/index.html` until someone fixes it. This is deliberate — see the
production roadmap's #2 priority (accuracy over automation). To review:

1. Open `data/articles.json`, find entries with `"needs_review": true`.
2. Read `review_reason` for what the check flagged.
3. Either fix `headline_ne`/`summary_ne` by hand and set `"needs_review": false`,
   or delete the entry to drop it.
4. Commit the change, or just wait — the next scheduled run rebuilds the site
   from whatever's currently approved.

This step is the one piece of this pipeline that isn't automatable for free
without accepting real accuracy risk. Budget yourself a few minutes a day for it.

## Tuning knobs

- **Feed list**: edit the `FEEDS` list in `scripts/fetch_and_translate.py` to
  add/remove sources.
- **Run frequency**: edit the `cron` line in
  `.github/workflows/update-news.yml` (currently every 4 hours).
- **How many articles show on the site**: `MAX_STORED_ARTICLES` in
  `fetch_and_translate.py`.
- **API spend cap per run**: `MAX_NEW_PER_RUN` limits how many new articles get
  translated in a single run.

## What this still doesn't cover

See `production-roadmap.md` for the fuller list, but the big ones this
pipeline does NOT solve on its own: legal review of whether each source's
terms of service permit this kind of summarization, a real domain name if you
want one, analytics, and the human review step described above. This gets you
a genuinely running, free, automated pipeline — not a finished product.
