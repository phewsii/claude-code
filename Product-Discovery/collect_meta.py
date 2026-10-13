"""Read public Instagram discovery with an existing token from META_ACCESS_TOKEN."""
import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def query(path, params, token):
    url = 'https://graph.facebook.com/v26.0/' + path + '?' + urlencode(params)
    request = Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        body = json.loads(error.read())
        detail = body.get('error', {})
        raise RuntimeError('Meta error %s: %s' % (detail.get('code'), detail.get('message'))) from None
    if 'error' in result:
        raise RuntimeError('Meta request failed: ' + str(result['error'].get('message')))
    return result

def clean(post, captured, account='Unverified', sampling='hashtag_recent'):
    return {'id': str(post.get('id', '')), 'platform': 'Instagram', 'account': account,
            'caption': post.get('caption', ''), 'url': post.get('permalink', ''),
            'posted_at': post.get('timestamp'), 'captured_at': captured,
            'likes': post.get('like_count'), 'comments': post.get('comments_count'),
            'views': None, 'shares': None, 'sampling': sampling,
            'image_url': post.get('media_url', '') if post.get('media_type') == 'IMAGE' else '',
            'media_type': post.get('media_type'), 'product': '', 'account_type': 'Unverified'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ig-user', default='17841459335527856')
    parser.add_argument('--account', action='append', default=[])
    parser.add_argument('--hashtag', action='append', default=[])
    parser.add_argument('--pages', type=int, default=2)
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--output', type=Path, default=Path('meta_posts.json'))
    args = parser.parse_args()
    token = os.environ.get('META_ACCESS_TOKEN')
    if not token:
        parser.error('META_ACCESS_TOKEN is required; it is never saved in output')
    if not args.account and not args.hashtag:
        parser.error('Choose at least one --account or --hashtag')
    if not 1 <= args.pages <= 20 or not 1 <= args.hours <= 168:
        parser.error('pages must be 1-20 and hours 1-168')
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.hours)
    posts, failures = {}, []
    fields = 'id,caption,media_type,media_url,permalink,like_count,comments_count,timestamp'
    def store(items, account='Unverified', sampling='hashtag_recent'):
        for item in items:
            try:
                published = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
            except (KeyError, ValueError):
                continue
            if cutoff <= published <= now:
                row = clean(item, now.isoformat(), account, sampling)
                if row['url']:
                    posts[row['url']] = row
    for account in args.account:
        account = account.lstrip('@')
        if not account or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._' for c in account):
            parser.error('Invalid Instagram account name')
        try:
            result = query(args.ig_user, {'fields': 'business_discovery.username(%s){username,media.limit(25){%s}}' % (account, fields)}, token)
            discovery = result.get('business_discovery', {})
            media = discovery.get('media', {})
            store(media.get('data', []), discovery.get('username', account), 'account_recent_partial')
        except RuntimeError as error:
            failures.append({'source': account, 'error': str(error)})
    for hashtag in args.hashtag:
        try:
            lookup = query('ig_hashtag_search', {'user_id': args.ig_user, 'q': hashtag.lstrip('#')}, token)
            if not lookup.get('data'):
                failures.append({'source': hashtag, 'error': 'No hashtag result'})
                continue
            path = lookup['data'][0]['id'] + '/recent_media'
            params = {'user_id': args.ig_user, 'fields': fields, 'limit': 5}
            for _ in range(args.pages):
                result = query(path, params, token)
                store(result.get('data', []))
                paging = result.get('paging', {})
                after = paging.get('cursors', {}).get('after')
                if not paging.get('next') or not after:
                    break
                params['after'] = after
                time.sleep(0.3)
        except RuntimeError as error:
            failures.append({'source': hashtag, 'error': str(error)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'posts': list(posts.values()), 'captured_at': now.isoformat(), 'window_hours': args.hours, 'failures': failures}, indent=2))
    print('%d posts in last %d hours; %d source failures. Credentials excluded.' % (len(posts), args.hours, len(failures)))

if __name__ == '__main__':
    main()
