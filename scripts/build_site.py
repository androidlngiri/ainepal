#!/usr/bin/env python3
"""
sajilo-ai-khabar pipeline, step 2: build the static site from data/articles.json

Reads only articles where needs_review is false, injects them into the HTML
template, and writes docs/index.html (served by GitHub Pages from the /docs
folder). Run this after fetch_and_translate.py.

    python scripts/build_site.py
"""

import json
import html
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "articles.json"
TEMPLATE_FILE = REPO_ROOT / "templates" / "site_template.html"
OUTPUT_FILE = REPO_ROOT / "docs" / "index.html"

CATEGORY_LABELS = {
    "product": "प्रोडक्ट",
    "biz": "व्यापार",
    "legal": "कानुनी",
    "chip-tag": "चिप र पूर्वाधार",
}


def get_seed_articles():
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
            "needs_review": False,
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
            "needs_review": False,
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
            "needs_review": False,
        },
    ]


def esc(s):
    return html.escape(s or "", quote=True)


def build_feature(article):
    return f"""
  <div class="feature" data-cat="{esc(article['category'])}">
    <span class="tag {esc(article['category'])}">{CATEGORY_LABELS.get(article['category'], '')}</span>
    <h2>{esc(article['headline_ne'])}</h2>
    <p>{esc(article['summary_ne'])}</p>
    <div class="meta-line">
      <span>स्रोत: {esc(article['source'])}</span>
      <a class="read-more" href="{esc(article['link'])}" target="_blank" rel="noopener">थप पढ्नुहोस् →</a>
    </div>
  </div>
"""


def build_story(article, index):
    num = str(index + 1).zfill(2)
    return f"""
    <div class="story" data-cat="{esc(article['category'])}">
      <div class="story-num">{num}</div>
      <div>
        <span class="tag {esc(article['category'])}">{CATEGORY_LABELS.get(article['category'], '')}</span>
        <h3>{esc(article['headline_ne'])}</h3>
        <p>{esc(article['summary_ne'])}</p>
        <div class="meta-line">
          <span>स्रोत: {esc(article['source'])}</span>
          <a class="read-more" href="{esc(article['link'])}" target="_blank" rel="noopener">थप पढ्नुहोस् →</a>
        </div>
      </div>
    </div>
"""


def main():
    if not DATA_FILE.exists() or DATA_FILE.read_text(encoding="utf-8").strip() == "":
        articles = get_seed_articles()
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        articles = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if not articles:
        articles = get_seed_articles()

    live = [a for a in articles if not a.get("needs_review", False)]
    live.sort(key=lambda a: a["published_at"], reverse=True)

    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    if not live:
        feature_html = '<div class="empty-state">अहिलेसम्म कुनै पुष्टि भएको खबर छैन। केही समयपछि फेरि हेर्नुहोस्।</div>'
        story_html = ""
    else:
        feature_html = build_feature(live[0])
        story_html = "".join(build_story(a, i) for i, a in enumerate(live[1:]))

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = (
        template
        .replace("{{FEATURE_BLOCK}}", feature_html)
        .replace("{{STORY_BLOCKS}}", story_html)
        .replace("{{LAST_UPDATED}}", now_str)
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"Built {OUTPUT_FILE} with {len(live)} live article(s) "
          f"({len(articles) - len(live)} held back for review).")


if __name__ == "__main__":
    main()
