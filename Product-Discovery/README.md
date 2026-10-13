# Product Discovery

Read ../CLAUDE_HANDOFF.md first. This folder is the GitHub-based shared workspace for Codex and Claude cloud.

Product_Review.html opens as a standalone review interface. Product_Review.xlsx is the partner workbook. Evidence.json contains five initial public post snapshots, not a verified viral-product shortlist.

## Existing collector

Set META_ACCESS_TOKEN only in the execution environment. Never commit tokens or .env files.

```sh
python3 collect_meta.py --ig-user YOUR_AUTHORIZED_INSTAGRAM_ID --hashtag amazonfinds --hours 24 --pages 2 --output fresh_posts.json
python3 content_system.py fresh_posts.json --output fresh_analysis
```

Import fresh_analysis/analysis.json into the HTML review. --account username collects a partial latest-25-post account sample. Hashtag results do not establish account or seller identity. This adapter leaves views/shares unavailable; actual view-count collection remains required.

TikTok is currently an import path, not a competitor scraper. JSON/CSV fields: platform, account, account_type, product, url, posted_at (ISO timestamp with timezone), captured_at, views, likes, comments, shares, image_url, caption, transcript, format, hook, offer, audience, awareness, sophistication, strategy_evidence, buyer_questions, seller_url, decision, notes.

Default freshness is a verified publication time within 24 hours, not collection time. Unknown dates stay out of the recent view. Distinct accounts and repeated comparable videos must be verified before claiming 100 qualified candidates. Missing metrics are not zero. Sales and paid returns remain unproven.

REA assessment source: https://github.com/morluto/rea. TikTok API authorization source: https://developers.tiktok.com/docs/en/tiktok-api-v2-video-list.
