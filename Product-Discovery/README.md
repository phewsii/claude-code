# Product Discovery

Read ../CLAUDE_HANDOFF.md first. This folder is the GitHub-based shared workspace for Codex and Claude cloud.

## Files

- **Product_Review.html**: standalone review page. Open it in any browser; it needs no server.
- **Product_Review.xlsx**: partner workbook. It has three sheets: Ideas (pictures, links, decision and judgment dropdowns), Evidence (source values) and Coverage (progress toward 100 accounts).
- **Evidence.json**: the evidence both outputs are built from. It currently holds 5 undated Instagram hashtag-top posts. It is not a verified shortlist.
- **build_outputs.py**: rebuilds the HTML evidence block and the workbook from one evidence file.
- **content_system.py**: normalizes JSON/CSV evidence, links comparable videos and reports coverage.
- **collect_meta.py**: bounded Meta Graph API adapter. It does not return views.
- **images/**: cached product images for the workbook, named by the first 16 hex characters of the SHA-1 of `image_url` plus `.jpg`.

## Review page

- **Products view.** A list on the left and the selected item on the right. On a phone, the detail opens as a full-screen sheet.
- **Filters.** Search, published window (24 h by default), platform, seller type and decision chips with counts.
- **Detail.** Original post, profile and store links. Save/Test/Pass/Review buttons. Primary KPIs are always visible. A plain-language "Why it's here" list is generated from the evidence, with your own rationale below it.
- **Supporting sections.** The comparable-video cluster and market judgment (awareness stage, sophistication, hook, timestamp, supporting evidence) are always shown. The caption, transcript and evidence edits are collapsed.
- **Keyboard.** `↑`/`↓` or `J`/`K` move between items. `R`/`S`/`T`/`P` set the decision, `O` opens the post, `/` focuses search and `Esc` backs out.
- **Persistence.** Decisions, edits and imported rows are saved in browser localStorage for this file path. Use Export → Clear local edits to revert.
- **Export.** "Reviewed snapshot (.html)" is a portable page with decisions built in. "Reviewed data (.json)" can be re-imported or handed to Codex. "Current view (.csv)" has formula-injection guarding.
- **Import.** Accepts JSON (a `posts` array or a bare array) and CSV. Every row needs an https post URL. Existing decisions and edited fields are kept on merge.
- **Accounts view.** Groups posts by verified account. "View posts" drills into one account; remove the filter with the chip next to the count.

Freshness always uses a verified publish time that includes a timezone. Undated rows never enter the 24-hour view. Missing metrics show as Unavailable, never 0.

## Collection pipeline

```sh
# 1. Collect (on a machine with network access and credentials)
META_ACCESS_TOKEN=... python3 collect_meta.py --ig-user YOUR_IG_ID --hashtag amazonfinds --hours 24 --output fresh_posts.json
#    or export a TikTok/Instagram dataset from a scraping provider as JSON

# 2. Normalize, cluster comparables, report coverage
python3 content_system.py fresh_posts.json --output fresh_analysis

# 3. Rebuild the review page and workbook
python3 build_outputs.py fresh_analysis/analysis.json
```

`content_system.py` reads its own field names plus common provider export fields:

| Provider fields | Becomes |
| --- | --- |
| `webVideoUrl`, `shortCode` | `url` |
| `playCount`, `videoPlayCount`, `videoViewCount` | `views` |
| `diggCount`, `likesCount` | `likes` |
| `commentCount`, `commentsCount` | `comments` |
| `shareCount` | `shares` |
| `collectCount` | `saves` |
| `createTimeISO`, `createTime` (epoch) | `posted_at` |
| `authorMeta.name`, `ownerUsername` | `account` |
| `videoMeta.coverUrl`, `displayUrl` | `image_url` |

These mappings are written from the documented field names. They have not been run against a live provider export, so check one real file before trusting them. Profile links are derived from the handle. Posts with the same product name from different accounts are linked as comparables; this is an exact-name match, so review it.

A qualified account is a named account with a post published within 24 hours, verified views and no giveaway. The analyzer prints the count of qualified accounts out of 100 and writes it to the workbook Coverage sheet. The bar is never lowered to reach 100.

Organic metrics do not establish sales or paid-ad profitability.

REA assessment source: https://github.com/morluto/rea. TikTok API authorization source: https://developers.tiktok.com/docs/en/tiktok-api-v2-video-list.
# Live Browser Collection

Read `LIVE_COLLECTION_UPDATE.md` first. The canonical `Evidence.json` now contains 1,816 observations, with 1,597 observed view counters. `TikTok_Verified_Account_Review.csv` contains 100 directly checked public profiles, not 100 qualified viral sellers. There are 126 detail reads and 99 follower counters. Missing values remain unavailable. The rolling 24-hour metric-coverage count changes as evidence ages; it is not proof of virality or paid readiness.

Rebuild with `python3 build_outputs.py` using Python with openpyxl installed. Preserve the existing UI format. Do not replace canonical evidence with the five legacy Meta observations, which are retained separately in `Meta_Legacy_Evidence.json`.

