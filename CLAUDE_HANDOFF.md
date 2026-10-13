# Shared Product Discovery workspace

Repository: phewsii/claude-code
Branch: claude/ui-redesign-account-collection-6e729h
Project directory: Product-Discovery/

Use repository-relative paths. The previous Mac-only OneDrive handoff did not work for a cloud container. All required project files are now in this repository. Do not try to access /Users paths.

## User goal

Collect 100 distinct product-selling accounts with products going very viral. Prefer posts published within 24 hours; separate older or incomplete candidates. Include verified views, all accessible supporting KPIs, product images, account/profile/store links, original videos, and a cluster of comparable videos per product. Avoid treating one spike, giveaways, or keyword comments as proof of purchase demand. Organic KPIs do not establish paid-ad profitability.

Redesign Product-Discovery/Product_Review.html in an Apple-inspired light style. Current UI is rough and hard to navigate. Prioritize an effortless product list, selected-item detail panel, original-post links, plain-language rationale and Save/Test/Pass. Search, date/platform/seller/status filters, previous/next navigation, responsive layout and keyboard access are required. Implement local persistence and portable reviewed snapshots. Preserve working import/export and evidence.

Include awareness stage and market sophistication as reviewed judgments with supporting hook/transcript/timestamps. Keep advanced fields collapsed and primary KPI evidence visible.

## Files and current reality

- Product_Review.html: initial standalone review interface. Default 24-hour filter intentionally excludes undated evidence. Import JSON; export HTML or current-view CSV.
- Product_Review.xlsx: initial partner workbook, 5 original-post native hyperlinks, decision dropdowns, one product photo, evidence tab.
- Evidence.json: 5 Meta hashtag-top post metric snapshots. Not 100 accounts, not qualified same-day winners. Views, publication times and account identities are not verified. One giveaway must be excluded from demand comparisons.
- collect_meta.py: bounded Meta API adapter, uses META_ACCESS_TOKEN environment variable. Credentials must never be committed. Views/shares currently unavailable. Latest 25 posts per explicit account; bounded hashtag pagination. Live CLI collection has not been verified.
- content_system.py: JSON/CSV normalizer, caption tags and sample account summaries. Missing metrics remain unavailable. Caption tags are tentative, not video analysis.
- Product-Discovery/README.md: execution instructions and coverage gaps.

## Next actions

1. Inspect and redesign the existing interface. Visually test desktop/mobile, search, filters, details, missing data, persistence and exports. A cloud container may serve HTML on localhost for its own permitted browser tests.
2. Establish actual Instagram and TikTok view-count collection. TikTok arbitrary-account scraping is not implemented; creator-authorized Display API is not a general competitor lookup.
3. Populate 100 verified distinct accounts with real evidence. Report exact count and freshness/metric coverage; never fill with fake rows or silently relax freshness.
4. Update the partner workbook alongside the review interface. Keep edits in this project folder.
5. Commit and push to this branch for Codex to fetch. Pull/fetch before edits; reconcile changes without force pushes.

## Verification

Analyzer unit checks passed. HTML filter logic passed DOM-mock checks, not visual browser QA. Workbook rendered; five native hyperlinks and validation dropdowns checked. Native links were added through standard XML export repair because the workbook library did not calculate HYPERLINK.

REA (morluto/rea) was evaluated as software reverse-engineering tooling. Its evidence-first method informed the implementation; it was not installed as a social scraper.

No paid provider, public deployment, complete TikTok collector, fresh 100-account list, or paid performance claim exists yet.

## Claude cloud session update (2026-10-13)

Done:
- Product_Review.html rebuilt in an Apple-style light design. It has a list/detail layout, Save/Test/Pass/Review buttons, search and filters (date, platform, seller type, decision), previous/next, keyboard shortcuts, a mobile full-screen detail sheet and a plain-language "Why it's here" list. It also has comparable-video clusters, awareness/sophistication with hook, timestamp and evidence fields, and collapsed advanced edits. Decisions, edits and imports persist in localStorage. Exports: portable reviewed HTML snapshot, JSON and current-view CSV. Import accepts JSON or CSV.
- Browser QA in headless Chromium at 1360px and 390px: 34 scripted checks passed. They covered filters, keyboard, persistence across reload, import merge, all three exports, the snapshot reopening in a fresh browser with decisions intact, no horizontal scroll on mobile, and no page errors. Test fixtures stayed in the session scratchpad and were not committed.
- content_system.py: maps common TikTok/Instagram provider export fields (not tested on a real export), adds saves, derives profile links, clusters comparables by exact product name, and adds a `coverage` report (qualified accounts out of 100).
- build_outputs.py (new): rebuilds the HTML evidence block and Product_Review.xlsx (Ideas/Evidence/Coverage sheets) from Evidence.json or an analysis.json. Native hyperlinks, dropdowns and cached images in images/.

Not done (blocked):
- 100-account collection. This cloud container cannot reach tiktok.com, instagram.com, graph.facebook.com or scraping providers. The proxy denies them and web fetch cannot resolve tiktok.com. No META_ACCESS_TOKEN or provider key is present. No rows were invented. Evidence.json is unchanged: 5 undated posts, 0 of 100 qualified accounts.
- To proceed, run collection where network access and credentials exist (Codex or the user's Mac). Use collect_meta.py or a provider export (e.g. a TikTok scraper dataset with playCount/createTimeISO), then `content_system.py` and `build_outputs.py`, and commit.
- Legacy sophistication labels "3 - Explain the mechanism" / "4 - Improve the mechanism" are normalized to the workbook's shorter wording.
