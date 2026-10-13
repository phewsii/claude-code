"""Normalize public post evidence and produce a partner review CSV. No dependencies."""
import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

METRICS = ('views', 'likes', 'comments', 'shares', 'saves')
ALIASES = {'views': 'view_count', 'likes': 'like_count', 'comments': 'comments_count', 'shares': 'share_count', 'url': 'permalink', 'posted_at': 'timestamp'}
# Field names used by common scraper/provider exports (e.g. Apify TikTok and Instagram scrapers,
# TikTok Research API). First non-empty match wins. Dotted names read nested objects.
PROVIDER_ALIASES = {
    'url': ('webVideoUrl', 'share_url', 'shortCode'),
    'views': ('playCount', 'play_count', 'videoPlayCount', 'videoViewCount', 'view_count', 'stats.playCount'),
    'likes': ('diggCount', 'likesCount', 'like_count', 'stats.diggCount'),
    'comments': ('commentCount', 'commentsCount', 'comment_count', 'stats.commentCount'),
    'shares': ('shareCount', 'share_count', 'stats.shareCount'),
    'saves': ('collectCount', 'favorites_count', 'stats.collectCount'),
    'posted_at': ('createTimeISO', 'create_time', 'createTime', 'taken_at'),
    'account': ('authorMeta.name', 'ownerUsername', 'username', 'author.uniqueId', 'author.username'),
    'caption': ('text', 'video_description', 'desc'),
    'image_url': ('videoMeta.coverUrl', 'displayUrl', 'thumbnail_url', 'cover_image_url'),
    'profile_url': ('authorMeta.profileUrl',),
}
TEXT_FIELDS = ('platform', 'account', 'account_type', 'product', 'caption', 'transcript', 'format', 'hook', 'hook_timestamp', 'offer', 'image_url', 'captured_at', 'decision', 'notes', 'sampling', 'audience', 'profile_url', 'seller_url', 'buyer_questions', 'awareness', 'sophistication', 'strategy_evidence', 'image_source')

def pick(source, name):
    value = source
    for part in name.split('.'):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value

def provider_value(source, key):
    for name in PROVIDER_ALIASES.get(key, ()):
        value = pick(source, name)
        if value not in (None, ''):
            if key == 'posted_at' and isinstance(value, (int, float)) or (key == 'posted_at' and str(value).isdigit()):
                return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
            if key == 'url' and name == 'shortCode':
                return 'https://www.instagram.com/p/%s/' % value
            return value
    return None

def profile_link(platform, account):
    if not account or account == 'Unverified' or not re.fullmatch(r'[A-Za-z0-9._]+', account):
        return ''
    if platform == 'TikTok':
        return 'https://www.tiktok.com/@' + account
    if platform == 'Instagram':
        return 'https://www.instagram.com/' + account + '/'
    return ''

def public_url(value):
    parsed = urlparse(str(value or ''))
    return str(value) if parsed.scheme == 'https' and parsed.hostname else ''

def number(value):
    if value in (None, '', 'Unavailable'):
        return None
    result = float(str(value).replace(',', ''))
    if result < 0 or not result < float('inf'):
        raise ValueError('Metrics must be finite nonnegative numbers')
    return int(result) if result.is_integer() else result

def first(*values):
    return next((v for v in values if v not in (None, '')), None)

def normalize(source):
    row = {key: first(source.get(key), source.get(alias), provider_value(source, key)) for key, alias in ALIASES.items()}
    row.update({key: first(source.get(key), row.get(key), provider_value(source, key)) or '' for key in TEXT_FIELDS})
    row['url'] = public_url(row['url'])
    if not row['url']:
        raise ValueError('Every post requires an HTTPS evidence URL')
    row['image_url'] = public_url(row['image_url'])
    for key in METRICS:
        row[key] = number(first(source.get(key), source.get(ALIASES.get(key)), provider_value(source, key)))
    text = str(row['caption'] or '').lower()
    row['giveaway'] = bool(re.search(r'giveaway|to enter|win a|winner will', text))
    row['keyword_cta'] = bool(re.search(r'comment.{0,60}(send|link|prime|chat|shop)|type.{0,30}shop', text))
    row['offer_signal'] = bool(re.search(r'\$\d|deal|discount|marked down|sale|% off', text))
    row['funnel'] = 'Purchase-focused caption (inferred)' if row['offer_signal'] or row['keyword_cta'] else 'Unclassified'
    row['format'] = row['format'] or 'Not reviewed'
    row['hook'] = row['hook'] or 'Not reviewed'
    row['decision'] = row['decision'] or 'Review'
    row['account'] = row['account'] or 'Unverified'
    row['platform'] = row['platform'] or ('Instagram' if 'instagram.com' in urlparse(row['url']).hostname else 'TikTok' if 'tiktok.com' in urlparse(row['url']).hostname else 'Other')
    row['profile_url'] = public_url(row['profile_url']) or profile_link(row['platform'], row['account'])
    row['seller_url'] = public_url(row['seller_url'])
    row['comparables'] = [c for c in source.get('comparables') or [] if isinstance(c, dict) and public_url(c.get('url'))]
    row['published_time_verified'] = False
    try:
        published = datetime.fromisoformat(str(row['posted_at']).replace('Z', '+00:00'))
        row['published_time_verified'] = published.tzinfo is not None
    except ValueError:
        pass
    return row

def analyze(rows):
    unique = {}
    for source in rows:
        row = normalize(source)
        key = row['url'].split('?')[0].rstrip('/')
        if key in unique:
            if unique[key] != row:
                raise ValueError('Conflicting duplicate post: ' + key)
            continue
        unique[key] = row
    posts = list(unique.values())
    groups = defaultdict(list)
    for row in posts:
        if row['account'] != 'Unverified':
            groups[(row['platform'], row['account'])].append(row)
    systems = []
    for (platform, account), group in groups.items():
        eligible = [r for r in group if not r['giveaway'] and r['views'] is not None]
        median = statistics.median(r['views'] for r in eligible) if eligible else None
        for row in group:
            row['views_vs_sample'] = round(row['views'] / median, 2) if median and row in eligible and len(eligible) >= 5 else None
        dates = []
        for row in group:
            try:
                dates.append(datetime.fromisoformat(str(row['posted_at']).replace('Z', '+00:00')).date())
            except ValueError:
                pass
        span = (max(dates) - min(dates)).days + 1 if dates else None
        systems.append({'platform': platform, 'account': account, 'sample_posts': len(group), 'purchase_focused_captions': sum(r['offer_signal'] or r['keyword_cta'] for r in group), 'keyword_ctas': sum(r['keyword_cta'] for r in group), 'giveaways': sum(r['giveaway'] for r in group), 'median_sample_views': median, 'posts_per_week': round(len(dates) / span * 7, 2) if span and span >= 7 and all(r['sampling'] == 'complete_window' for r in group) else None, 'repeated_products': dict(Counter(r['product'] for r in group if r['product'])), 'limitations': 'Sample comparisons are descriptive, not age-adjusted. Sales, conversion and buying intent are unverified. Frequency requires a complete dated window.'})
    cluster_comparables(posts)
    return {'posts': posts, 'systems': systems, 'coverage': coverage(posts), 'limitations': 'Caption rules are tentative tags, not video analysis. Unknown metrics remain blank. Hashtag top posts are a selected sample, not a representative account history.'}

def product_key(name):
    return re.sub(r'[^a-z0-9]+', ' ', str(name or '').lower()).strip()

def cluster_comparables(posts):
    """Link posts naming the same product from different accounts. Exact product-name match only."""
    groups = defaultdict(list)
    for row in posts:
        key = product_key(row['product'])
        if key and row['account'] != 'Unverified' and not row['giveaway']:
            groups[key].append(row)
    for group in groups.values():
        for row in group:
            known = {c['url'] for c in row['comparables']}
            for other in group:
                if other['account'] != row['account'] and other['url'] not in known:
                    row['comparables'].append({'url': other['url'], 'account': other['account'], 'views': other['views'], 'posted_at': other['posted_at']})
                    known.add(other['url'])

def published(row):
    try:
        value = datetime.fromisoformat(str(row['posted_at']).replace('Z', '+00:00'))
    except ValueError:
        return None
    return value if value.tzinfo else None

def coverage(posts, now=None, hours=24):
    """Progress toward the 100-account goal. Qualified = named account, verified publish time inside
    the window, verified views, not a giveaway. Nothing here is relaxed to reach the target."""
    now = now or datetime.now(timezone.utc)
    named = {(r['platform'], r['account']) for r in posts if r['account'] != 'Unverified'}
    qualified = set()
    for r in posts:
        when = published(r)
        if r['account'] != 'Unverified' and when and 0 <= (now - when).total_seconds() <= hours * 3600 and r['views'] is not None and not r['giveaway']:
            qualified.add((r['platform'], r['account']))
    total = len(posts) or 1
    return {'checked_at': now.isoformat(), 'window_hours': hours, 'posts': len(posts), 'named_accounts': len(named),
            'qualified_accounts': len(qualified), 'target_accounts': 100,
            'older_or_incomplete_accounts': len(named - qualified),
            'metric_coverage': {m: round(sum(r[m] is not None for r in posts) / total, 3) for m in METRICS},
            'dated_posts': sum(published(r) is not None for r in posts),
            'with_image': sum(bool(r['image_url']) for r in posts),
            'with_profile_link': sum(bool(r['profile_url']) for r in posts),
            'with_store_link': sum(bool(r['seller_url']) for r in posts),
            'with_3plus_comparables': sum(len(r['comparables']) >= 3 for r in posts),
            'giveaways_excluded': sum(r['giveaway'] for r in posts)}

def load(path):
    if path.suffix.lower() == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as stream:
            return list(csv.DictReader(stream))
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return data.get('posts', data.get('data', []))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('analysis'))
    args = parser.parse_args()
    result = analyze(load(args.input))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'analysis.json').write_text(json.dumps(result, indent=2))
    columns = ['product', 'platform', 'account', 'url', 'profile_url', 'seller_url', 'image_url', 'views', 'likes', 'comments', 'shares', 'saves', 'posted_at', 'funnel', 'format', 'hook', 'offer', 'giveaway', 'keyword_cta', 'views_vs_sample', 'decision', 'notes', 'caption']
    with (args.output / 'partner_review.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in result['posts']:
            safe = {key: ("'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@')) else value) for key, value in row.items()}
            writer.writerow(safe)
    c = result['coverage']
    print('Wrote analysis.json and partner_review.csv:', len(result['posts']), 'posts')
    print('Qualified accounts (named, published <%dh, views verified, no giveaway): %d / %d; named accounts: %d; dated posts: %d; views coverage: %.0f%%'
          % (c['window_hours'], c['qualified_accounts'], c['target_accounts'], c['named_accounts'], c['dated_posts'], c['metric_coverage']['views'] * 100))

if __name__ == '__main__':
    main()
