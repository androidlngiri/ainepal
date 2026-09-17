# सजिलो एआई खबर — Production Roadmap

What it would actually take to turn this from a one-off demo page into a real, trustworthy news product. Ordered by priority (P0 = blocks calling this "real" at all, P1 = needed to run it responsibly and reliably, P2 = growth/polish). Each item includes *why* and concrete *next steps*, not just a label.

---

## P0 — Can't call this a real product without these

### 1. Replace hand-written HTML with a real content pipeline
Right now every story is hardcoded into one HTML file. A real app needs an automated flow: **fetch → verify → translate/simplify → publish**, running on a schedule, not by hand each time.
- [ ] Pick real news sources: RSS feeds, NewsAPI, GNews, or direct scraping (with permission/ToS check) of outlets you trust (Reuters, AP, TechCrunch, official company blogs/press releases)
- [ ] Build a backend job (cron / scheduled cloud function) that pulls new stories every N hours
- [ ] Store articles in a real database (Postgres, or even a managed headless CMS like Sanity/Strapi) instead of static HTML — title, summary (EN), summary (NE), source URL, category, published_at, status (draft/reviewed/live)
- [ ] Separate the **content layer** from the **presentation layer** so the frontend just renders whatever's in the database

### 2. Fix the accuracy/hallucination risk before this touches real readers
This is the single biggest risk for a *news* product specifically. An LLM summarizing and translating news can introduce factual errors, wrong numbers, or misattributed quotes — and readers won't know to doubt it.
- [ ] Every auto-generated Nepali summary needs to be checked against the original source before going live — either a human editor or, at minimum, an automated "does this summary contradict the source" verification pass
- [ ] Never let translation change numbers, dates, names, or quotes without a flag for human review
- [ ] Add a visible correction/retraction mechanism (an "edited" or "corrected on [date]" note) — real news outlets have one, you need one too

### 3. Legal and copyright groundwork
- [ ] Confirm each source's terms of service allow scraping/republishing summaries (many news sites explicitly prohibit automated scraping even for summarization)
- [ ] Never reproduce full paragraphs or lyrics/quotes over ~1–2 sentences verbatim — always original paraphrase (this app already does this, keep enforcing it in the pipeline, not just by hand)
- [ ] Always link back to and clearly attribute the original source (already doing this — keep it mandatory in the pipeline, not optional)
- [ ] Talk to a lawyer familiar with Nepali media law and cross-border copyright if this will run publicly at scale — content aggregation laws vary by country

### 4. Real hosting and infrastructure
- [ ] Move off a single static HTML file to a proper host (Vercel, Netlify, or a VPS) with a real domain (e.g. `sajiloaikhabar.com`)
- [ ] HTTPS, CDN for fast loading in Nepal specifically (check latency from Kathmandu, not just US servers)
- [ ] Basic uptime monitoring (UptimeRobot, Better Uptime) with alerts if the site or the content pipeline goes down

### 5. Editorial policy and disclosure
- [ ] Clearly and permanently disclose that summaries are AI-translated/simplified (not written by human journalists) — readers deserve to know this, and it protects you legally and ethically
- [ ] Write a one-page editorial policy: what sources you use, how translation works, how corrections are handled, who to contact with concerns

---

## P1 — Needed to run this responsibly and not fall over

### 6. Translation quality, specifically for Nepali
- [ ] Get a native Nepali speaker (ideally with journalism/editing background) to review a sample of outputs regularly — machine-simplified Nepali can sound stiff or use wrong registers for a general audience
- [ ] Build a style guide: which English tech terms to translate vs. keep as loanwords (e.g. "एआई" vs "आर्टिफिसियल इन्टेलिजेन्स" vs "AI") — consistency matters for readability
- [ ] Handle Nepali numerals/dates consistently (Bikram Sambat vs Gregorian — decide and be consistent, most Nepali readers expect BS dates for context)

### 7. Monitoring and reliability
- [ ] Alerting when the scraping/fetch pipeline fails silently (most common way an "automated" news site quietly stops updating without anyone noticing)
- [ ] Logging for every pipeline step (fetched → translated → reviewed → published) so you can debug when something looks wrong
- [ ] Rate limiting and basic bot/spam protection on any public-facing forms or APIs

### 8. Performance and mobile reality-check
- [ ] Test actual load times on mid-range Android phones on 3G/4G Nepali networks, not just a desktop browser — this audience matters a lot here
- [ ] Compress/optimize fonts (Devanagari webfonts can be heavy) — consider font subsetting
- [ ] Add a proper favicon set, social share preview image (Open Graph tags), and meta description in Nepali

### 9. Accessibility
- [ ] Screen reader testing for Devanagari script specifically (support varies across screen readers)
- [ ] Keyboard navigation and visible focus states throughout
- [ ] Color contrast check for both light and dark themes (WCAG AA minimum)

### 10. SEO and discoverability
- [ ] Nepali-language SEO: proper `<title>`, meta tags, structured data (Article schema) per story
- [ ] Sitemap.xml, robots.txt
- [ ] Submit to Google News if pursuing that (has its own eligibility requirements — original reporting expectations may conflict with a pure-aggregation model, worth checking)

### 11. Basic analytics
- [ ] Privacy-respecting analytics (Plausible, Fathom, or self-hosted) to know which categories/stories people actually read
- [ ] Use this to prioritize which news categories are worth the translation effort

---

## P2 — Worth doing once the core is solid

- [ ] Search functionality across past stories
- [ ] Archive/browse-by-date view
- [ ] Category-specific RSS feeds so people can subscribe
- [ ] Email/SMS daily digest (very practical for a Nepali audience where not everyone browses websites daily)
- [ ] User accounts to save/bookmark stories
- [ ] A lightweight native or PWA wrapper for offline reading (relevant given connectivity gaps outside Kathmandu)
- [ ] Multiple simplification levels (e.g. "सरल" vs "विस्तृत" — simple vs detailed) for different reading levels
- [ ] Community correction reporting ("यो खबरमा गल्ती छ?" button)
- [ ] Monetization path if this needs to be self-sustaining: sponsorships, a "support us" model, or a paid detailed-briefing tier — ads are the obvious default but consider whether they fit a "simple, trustworthy news" brand

---

## Practical note on sequencing

If you can only do three things before calling this "real," do these, in order:
1. **Automate the pipeline** (item 1) — without this it's just a static page you edit by hand forever.
2. **Add a verification/review step** (item 2) — this is a news product; an unverified auto-translated factual error that goes viral is the single worst outcome here.
3. **Disclose clearly how it's made** (item 5) — this one is cheap to do and buys you a lot of trust and legal safety while the rest matures.

Everything else can be built incrementally after the site is actually trustworthy and running on its own.
