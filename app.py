import hashlib
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from dateutil import parser as dateparser
from flask import Flask, g, jsonify, render_template

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "news.db"

FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
]

CATEGORY_LABELS = {
    "product": "प्रोडक्ट",
    "biz": "व्यापार",
    "legal": "कानुनी",
    "chip-tag": "चिप र पूर्वाधार",
}


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def article_id(link, title):
    return hashlib.sha256(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def normalize_category(title, summary=""):
    combined = f"{title} {summary}".lower()
    if any(word in combined for word in ["chip", "gpu", "nvidia", "data center", "processor", "hardware", "server"]):
        return "chip-tag"
    if any(word in combined for word in ["law", "legal", "regulation", "court", "policy", "ai act", "ruling", "suit"]):
        return "legal"
    if any(word in combined for word in ["funding", "market", "startup", "revenue", "valuation", "company", "exec", "business"]):
        return "biz"
    return "product"


def clean_excerpt(raw):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1000]


def generate_summary(title, source, excerpt):
    excerpt = excerpt.strip() or title
    base = f"{source} बाट आएको खबरले {title} मा ध्यान केन्द्रित गरेको छ।"
    if len(excerpt) > 160:
        return base + " यसले बजार, प्रविधि, र प्रयोगकर्ताको असरलाई समेट्दै बताउँछ।"
    return base + " यसले मुख्य विकास र यसको प्रभावलाई सरल नेपालीमा प्रस्तुत गर्छ।"


def seed_articles():
    return [
        {
            "id": "seed-openai-agent",
            "source": "OpenAI Blog",
            "link": "https://openai.com/index/introducing-operator/",
            "title": "OpenAI introduces a new AI agent for everyday work",
            "summary": "OpenAI releases an AI agent that can browse the web and handle routine digital tasks with user supervision.",
            "category": "product",
            "published_at": "2026-09-01T06:00:00+00:00",
            "headline_ne": "ओपनएआईले रोजगारी कामका लागि नयाँ एआई सहयोगी सार्वजनिक गर्यो",
            "summary_ne": "ओपनएआईले एक नयाँ एआई सहयोगी सार्वजनिक गरेको छ जसले वेब ब्राउज गर्न र दैनिक कामलाई सहयोग गर्न सक्छ। यसले उपयोगकर्ताको निर्देशनमा सामान्य कार्य पूरा गर्न सहयोग पुर्याउँछ।",
        },
        {
            "id": "seed-nvidia-chip",
            "source": "NVIDIA Newsroom",
            "link": "https://nvidianews.nvidia.com/",
            "title": "AI chip makers expand data center capacity to meet rising demand",
            "summary": "Chipmakers are investing in larger data centers as AI workloads keep climbing.",
            "category": "chip-tag",
            "published_at": "2026-09-02T08:00:00+00:00",
            "headline_ne": "एआई चिप निर्माताले डाटा सेन्टर विस्तारमा ठूलो लगानी गरिरहेका छन्",
            "summary_ne": "एआई तालिम र सेवा संचालनको माग बढ्दै जाँदा चिप निर्माताहरूले डाटा सेन्टरको क्षमता विस्तार गर्न ठूलो लगानी गरिरहेका छन्।",
        },
        {
            "id": "seed-eu-ai-law",
            "source": "EU AI Policy Tracker",
            "link": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
            "title": "European regulators continue work on safe AI governance rules",
            "summary": "European officials are reviewing transparency and risk management rules for AI systems.",
            "category": "legal",
            "published_at": "2026-09-03T11:30:00+00:00",
            "headline_ne": "युरोपेली नियामकहरू सुरक्षित एआई नियमको पक्का तयारीमा छन्",
            "summary_ne": "युरोपेली अधिकारीहरूले सार्वजनिक र निजी क्षेत्रमा प्रयोग हुने एआई प्रणालीहरूका लागि auditing, transparency र जोखिम व्यवस्थापनसम्बन्धी नियमहरू समीक्षा गरिरहेका छन्।",
        },
    ]


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            source TEXT,
            link TEXT,
            title TEXT,
            summary TEXT,
            category TEXT,
            published_at TEXT,
            headline_ne TEXT,
            summary_ne TEXT,
            is_live INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    db.commit()

    existing = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    if existing == 0:
        for item in seed_articles():
            db.execute(
                "INSERT INTO articles (id, source, link, title, summary, category, published_at, headline_ne, summary_ne, is_live, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                (
                    item["id"],
                    item["source"],
                    item["link"],
                    item["title"],
                    item["summary"],
                    item["category"],
                    item["published_at"],
                    item["headline_ne"],
                    item["summary_ne"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        db.commit()


def fetch_feed_entries():
    results = []
    for source_name, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for entry in feed.entries[:15]:
            link = entry.get("link") or ""
            title = (entry.get("title") or "").strip()
            if not link or not title:
                continue
            summary_raw = entry.get("summary") or entry.get("description") or ""
            published_raw = entry.get("published") or entry.get("updated") or datetime.now(timezone.utc).isoformat()
            try:
                published_at = dateparser.parse(published_raw).astimezone(timezone.utc).isoformat()
            except Exception:
                published_at = datetime.now(timezone.utc).isoformat()
            summary = clean_excerpt(summary_raw)
            category = normalize_category(title, summary)
            results.append(
                {
                    "id": article_id(link, title),
                    "source": source_name,
                    "link": link,
                    "title": title,
                    "summary": summary or generate_summary(title, source_name, summary),
                    "category": category,
                    "published_at": published_at,
                    "headline_ne": title[:80],
                    "summary_ne": generate_summary(title, source_name, summary),
                }
            )
    results.sort(key=lambda item: item["published_at"], reverse=True)
    return results


def sync_articles():
    db = get_db()
    existing = {row["id"] for row in db.execute("SELECT id FROM articles").fetchall()}
    for item in fetch_feed_entries():
        if item["id"] in existing:
            continue
        db.execute(
            "INSERT INTO articles (id, source, link, title, summary, category, published_at, headline_ne, summary_ne, is_live, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                item["id"],
                item["source"],
                item["link"],
                item["title"],
                item["summary"],
                item["category"],
                item["published_at"],
                item["headline_ne"],
                item["summary_ne"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        existing.add(item["id"])
    db.commit()


def get_articles(limit=20):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM articles WHERE is_live = 1 ORDER BY published_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(DB_PATH),
        SECRET_KEY="dev-secret-key",
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    @app.route("/")
    def index():
        sync_articles()
        articles = get_articles(limit=20)
        return render_template("index.html", articles=articles, category_labels=CATEGORY_LABELS)

    @app.route("/api/articles")
    def api_articles():
        sync_articles()
        return jsonify({"articles": get_articles(limit=20)})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    with app.app_context():
        init_db()
        sync_articles()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
