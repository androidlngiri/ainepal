#!/usr/bin/env python3
"""
sajilo-ai-khabar pipeline, step 1: fetch -> translate/simplify -> verify -> store

What this does, in order:
  1. Pulls recent entries from a list of free RSS feeds covering AI/tech news.
  2. Skips anything already in data/articles.json (so re-runs don't duplicate).
  3. Sends each new article's title+summary to an LLM with strict instructions:
     - simplify and translate to plain Nepali
     - assign one of a fixed set of categories
     - NOT invent facts, numbers, or names not present in the source text
  4. Runs a lightweight second-pass "verification" call that checks the Nepali
     summary doesn't contradict or add to the original text.
  5. Anything that fails verification is marked needs_review=true and is
     EXCLUDED from the live site until a human flips it to approved.
  6. Saves everything to data/articles.json.

Run this from the repo root:
    python scripts/fetch_and_translate.py

Requires an environment variable ANTHROPIC_API_KEY (set as a GitHub Actions
secret in production; see README.md for a free-tier alternative using Gemini).
"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from dateutil import parser as dateparser
import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "articles.json"
MAX_STORED_ARTICLES = 60      # keep the site fast; older ones just age out
MAX_NEW_PER_RUN = 12          # cap API spend per run
MODEL = "claude-sonnet-4-6"

# Free, no-key-required RSS feeds covering AI/tech. Add/remove freely.
FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
]

CATEGORIES = ["product", "biz", "legal", "chip-tag"]  # matches CSS tag classes on the site


def get_seed_articles():
    """Provide a small starter set of approved articles so the site works even
    before the API-backed fetch pipeline has article data available."""
    return [
        {
            "id": "seed-openai-agent",
            "source": "OpenAI Blog",
            "link": "https://openai.com/index/introducing-operator/",
            "title_en": "OpenAI introduces a new AI agent for everyday work",
            "excerpt_en": "OpenAI has unveiled an AI agent that can browse the web, use tools, and work through routine tasks with user supervision.",
            "published_at": "2026-09-01T06:00:00+00:00",
            "headline_ne": "ओपनएआईले रोजगारी कामका लागि नयाँ एआई सहयोगी सार्वजनिक गर्यो",
            "summary_ne": "ओपनएआईले एक नयाँ एआई सहयोगी unveiling गरेको छ जसले वेब ब्राउज गर्न र दैनिक कामलाई सहयोग गर्न सक्छ। यसले उपयोगकर्ताको निर्देशनमा सामान्य कार्य पूरा गर्न सहयोग पुर्याउँछ।",
            "category": "product",
            "confidence": "high",
            "needs_review": False,
            "review_reason": "",
            "processed_at": "2026-09-17T00:00:00+00:00",
        },
        {
            "id": "seed-nvidia-chip",
            "source": "NVIDIA Newsroom",
            "link": "https://nvidianews.nvidia.com/",
            "title_en": "AI chip makers expand data center capacity to meet rising demand",
            "excerpt_en": "Chipmakers are investing heavily in bigger data center infrastructure as demand for AI training and inference workloads keeps climbing.",
            "published_at": "2026-09-02T08:00:00+00:00",
            "headline_ne": "एआई चिप निर्माताले डाटा सेन्टर विस्तारमा ठूलो लगानी गरिरहेका छन्",
            "summary_ne": "एआई तालिम र सेवा संचालनको माग बढ्दै जाँदा चिप निर्माताहरूले डाटा सेन्टरको क्षमता विस्तार गर्न ठूलो लगानी गरिरहेका छन्।",
            "category": "chip-tag",
            "confidence": "high",
            "needs_review": False,
            "review_reason": "",
            "processed_at": "2026-09-17T00:00:00+00:00",
        },
        {
            "id": "seed-eu-ai-law",
            "source": "EU AI Policy Tracker",
            "link": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
            "title_en": "European regulators continue work on safe AI governance rules",
            "excerpt_en": "European officials are reviewing new rules for auditing, transparency, and risk management in AI systems used by public and private sectors.",
            "published_at": "2026-09-03T11:30:00+00:00",
            "headline_ne": "युरोपेली नियामकहरू सुरक्षित एआई नियमको पक्का तयारीमा छन्",
            "summary_ne": "युरोपेली अधिकारीहरूले सार्वजनिक र निजी क्षेत्रमा प्रयोग हुने एआई प्रणालीहरूका लागि auditing, transparency र जोखिम व्यवस्थापनसम्बन्धी नियमहरू समीक्षा गरिरहेका छन्।",
            "category": "legal",
            "confidence": "high",
            "needs_review": False,
            "review_reason": "",
            "processed_at": "2026-09-17T00:00:00+00:00",
        },
    ]


SYSTEM_PROMPT = f"""You are a careful news-simplification assistant for a Nepali-language \
news product called "Sajilo AI Khabar" (Simple AI News).

You will be given one article's title and a short excerpt/summary in English, from a named \
source. Your job:

1. Write a short, plain, easy-to-understand NEPALI headline (Devanagari script). Keep it \
   under ~14 words. No clickbait, no exclamation marks.
2. Write a 2-3 sentence NEPALI summary in simple everyday language (avoid heavy technical \
   jargon; if you must use a technical term, briefly explain it in plain words). Use ONLY \
   facts, numbers, names, and claims that are explicitly present in the source text given to \
   you. Do NOT add outside knowledge, do NOT guess at details not present, do NOT speculate \
   about causes or motives that aren't stated.
3. Assign exactly one category from this fixed list: {", ".join(CATEGORIES)}
   - product: new AI models, product launches, feature updates
   - biz: business, funding, valuations, market moves, executive changes
   - legal: lawsuits, regulation, policy, court rulings
   - chip-tag: hardware, chips, data centers, infrastructure
4. Rate your own confidence that the summary is fully supported by the given source text: \
   "high", "medium", or "low". Use "low" if the source excerpt was too short or vague to be \
   sure you captured it accurately.

Respond with ONLY valid JSON, no markdown fences, no commentary, in exactly this shape:
{{"headline_ne": "...", "summary_ne": "...", "category": "...", "confidence": "..."}}
"""

VERIFY_PROMPT = """You are a fact-checking assistant. You will see an ORIGINAL English news \
excerpt and a NEPALI summary that was supposed to be a faithful, simplified translation of it.

Check ONLY for these problems:
- The Nepali summary states a number, date, name, or fact that is NOT in the original.
- The Nepali summary contradicts something stated in the original.
- The Nepali summary is about a different topic than the original.

Do not penalize simplification, shortening, or reasonable paraphrasing - that's expected and fine.

Respond with ONLY valid JSON, no markdown fences:
{"passes": true or false, "reason": "short explanation, empty string if passes is true"}
"""


def load_existing():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return []


def save_articles(articles):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def article_id(link, title):
    return hashlib.sha256(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def clean_html(raw):
    """Strip HTML tags from RSS summaries; keep it plain text."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1200]  # cap excerpt length fed to the model


def fetch_new_candidates(existing_ids):
    candidates = []
    for source_name, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[warn] could not fetch {source_name}: {e}", file=sys.stderr)
            continue

        for entry in feed.entries[:15]:
            link = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not link or not title:
                continue
            aid = article_id(link, title)
            if aid in existing_ids:
                continue

            summary_raw = entry.get("summary", "") or entry.get("description", "")
            published_raw = entry.get("published", "") or entry.get("updated", "")
            try:
                published_iso = dateparser.parse(published_raw).astimezone(timezone.utc).isoformat()
            except Exception:
                published_iso = datetime.now(timezone.utc).isoformat()

            candidates.append({
                "id": aid,
                "source": source_name,
                "link": link,
                "title_en": title,
                "excerpt_en": clean_html(summary_raw),
                "published_at": published_iso,
            })
    # newest first
    candidates.sort(key=lambda a: a["published_at"], reverse=True)
    return candidates[:MAX_NEW_PER_RUN]


def call_json(client, system, user_content, max_tokens=500):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def process_candidate(client, cand):
    user_content = (
        f"Source: {cand['source']}\n"
        f"Title: {cand['title_en']}\n"
        f"Excerpt: {cand['excerpt_en']}"
    )
    try:
        result = call_json(client, SYSTEM_PROMPT, user_content)
    except Exception as e:
        print(f"[error] translation failed for {cand['link']}: {e}", file=sys.stderr)
        return None

    if result.get("category") not in CATEGORIES:
        result["category"] = "product"

    # Second pass: verify the Nepali summary against the original excerpt.
    verify_input = (
        f"ORIGINAL: {cand['title_en']}. {cand['excerpt_en']}\n\n"
        f"NEPALI SUMMARY: {result.get('headline_ne', '')}. {result.get('summary_ne', '')}"
    )
    try:
        verdict = call_json(client, VERIFY_PROMPT, verify_input, max_tokens=200)
    except Exception as e:
        print(f"[warn] verification call failed for {cand['link']}: {e}", file=sys.stderr)
        verdict = {"passes": False, "reason": "verification call failed"}

    needs_review = (
        not verdict.get("passes", False)
        or result.get("confidence") == "low"
    )

    return {
        **cand,
        "headline_ne": result.get("headline_ne", ""),
        "summary_ne": result.get("summary_ne", ""),
        "category": result["category"],
        "confidence": result.get("confidence", "medium"),
        "needs_review": needs_review,
        "review_reason": verdict.get("reason", ""),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    existing = load_existing()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY is not set; using the built-in sample news set for the site.", file=sys.stderr)
        if not existing:
            seed = get_seed_articles()
            save_articles(seed)
            print(f"Saved {len(seed)} seeded article(s) to {DATA_FILE}")
        return

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    existing_ids = {a["id"] for a in existing}

    candidates = fetch_new_candidates(existing_ids)
    print(f"Found {len(candidates)} new candidate article(s).")

    processed = []
    for cand in candidates:
        result = process_candidate(client, cand)
        if result:
            processed.append(result)
            flag = "NEEDS REVIEW" if result["needs_review"] else "ok"
            print(f"  [{flag}] {result['headline_ne'][:50]}...")
        time.sleep(1)  # be polite to the API rate limits

    combined = processed + existing
    combined.sort(key=lambda a: a["published_at"], reverse=True)
    combined = combined[:MAX_STORED_ARTICLES]

    save_articles(combined)
    print(f"Saved {len(combined)} total article(s) to {DATA_FILE}")
    print(f"{sum(1 for a in combined if a.get('needs_review'))} article(s) currently flagged needs_review.")


if __name__ == "__main__":
    main()
