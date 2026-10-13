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

METRICS = ('views', 'likes', 'comments', 'shares')
ALIASES = {'views': 'view_count', 'likes': 'like_count', 'comments': 'comments_count', 'shares': 'share_count', 'url': 'permalink', 'posted_at': 'timestamp'}

def public_url(value):
    parsed = urlparse(str(value or ''))
    return str(value) if parsed.scheme == 'https' and parsed.hostname else ''

def number(value):
    if value in (None, '', 'Unavailable'):
        return None
    result = float(str(value).replace(',', ''))
    if result < 0 or not result < float('inf'):
        raise ValueError('Metrics must be finite nonnegative numbers')
    return result

def normalize(source):
    row = {key: source.get(key, source.get(alias)) for key, alias in ALIASES.items()}
    row.update({key: source.get(key, row.get(key, '')) for key in ('platform', 'account', 'account_type', 'product', 'caption', 'transcript', 'format', 'hook', 'offer', 'image_url', 'captured_at', 'decision', 'notes', 'sampling', 'audience', 'seller_url', 'buyer_questions', 'awareness', 'sophistication', 'strategy_evidence')})
    row['url'] = public_url(row['url'])
    if not row['url']:
        raise ValueError('Every post requires an HTTPS evidence URL')
    row['image_url'] = public_url(row['image_url'])
    for key in METRICS:
        row[key] = number(source.get(key, source.get(ALIASES.get(key))))
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
    return {'posts': posts, 'systems': systems, 'limitations': 'Caption rules are tentative tags, not video analysis. Unknown metrics remain blank. Hashtag top posts are a selected sample, not a representative account history.'}

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
    columns = ['product', 'platform', 'account', 'url', 'image_url', 'views', 'likes', 'comments', 'shares', 'posted_at', 'funnel', 'format', 'hook', 'offer', 'giveaway', 'keyword_cta', 'views_vs_sample', 'decision', 'notes', 'caption']
    with (args.output / 'partner_review.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in result['posts']:
            safe = {key: ("'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@')) else value) for key, value in row.items()}
            writer.writerow(safe)
    print('Wrote analysis.json and partner_review.csv:', len(result['posts']), 'posts')

if __name__ == '__main__':
    main()
