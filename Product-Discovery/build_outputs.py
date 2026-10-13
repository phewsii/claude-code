"""Rebuild Product_Review.html (embedded evidence) and Product_Review.xlsx from one evidence file.

    python3 build_outputs.py                      # uses Evidence.json
    python3 build_outputs.py fresh_analysis/analysis.json

Images are embedded in the workbook only when a cached copy exists in images/ (named by the
SHA-1 of image_url); nothing is downloaded here. Requires openpyxl and Pillow.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import content_system

HERE = Path(__file__).resolve().parent
DECISIONS = ['Review', 'Save', 'Test', 'Pass']
AWARENESS = ['Unreviewed', 'Unaware', 'Problem aware', 'Solution aware', 'Product aware', 'Most aware']
SOPHISTICATION = ['Unreviewed', '1 - First clear promise', '2 - Stronger promise', '3 - Explain mechanism', '4 - Improve mechanism', '5 - Identity and belief']
LEGACY_SOPH = {'3 - Explain the mechanism': '3 - Explain mechanism', '4 - Improve the mechanism': '4 - Improve mechanism'}

INK = '1D1D1F'
GREY = '6E6E73'
ACCENT = '0071E3'
HEAD_FILL = PatternFill('solid', fgColor='F5F5F7')
LINE = Border(bottom=Side(style='thin', color='E5E5EA'))


def load_result(path):
    raw = json.loads(path.read_text())
    rows = raw if isinstance(raw, list) else raw.get('posts', [])
    result = content_system.analyze(rows)
    if isinstance(raw, dict):
        for key in ('captured_at', 'limitations'):
            if raw.get(key):
                result[key] = raw[key]
    for row in result['posts']:
        row['sophistication'] = LEGACY_SOPH.get(row.get('sophistication'), row.get('sophistication') or 'Unreviewed')
        for key in ('hook', 'format'):
            if row.get(key) == 'Not reviewed':
                row[key] = ''
    return result


def embed_html(result, html_path):
    html = html_path.read_text()
    payload = json.dumps(result, separators=(',', ':')).replace('<', '\\u003c')
    pattern = re.compile(r'(<script id="evidence" type="application/json">)[\s\S]*?(</script>)')
    if not pattern.search(html):
        raise SystemExit('Evidence block not found in ' + str(html_path))
    html_path.write_text(pattern.sub(lambda m: m.group(1) + payload + m.group(2), html, count=1))


def age_label(row, now):
    when = content_system.published(row)
    if not when:
        return 'Undated'
    hours = (now - when).total_seconds() / 3600
    return 'Last 24 h' if 0 <= hours <= 24 else 'Older'


def why(row):
    parts = []
    if row['giveaway']:
        parts.append('Giveaway: exclude from demand comparison.')
    if row['keyword_cta']:
        parts.append('Keyword CTA inflates comments.')
    if row['views'] is None:
        parts.append('Views unverified.')
    if not content_system.published(row):
        parts.append('Publish time unverified.')
    if row['account'] == 'Unverified':
        parts.append('Account unverified.')
    if len(row['comparables']) < 3:
        parts.append('Fewer than 3 comparable videos.')
    note = (row.get('notes') or '').strip()
    return (note + ' ' if note else '') + ' '.join(parts)


def header(ws, title, subtitle, columns, widths):
    ws['A2'] = title
    ws['A2'].font = Font(size=20, bold=True, color=INK)
    ws['A3'] = subtitle
    ws['A3'].font = Font(size=11, color=GREY)
    for i, (name, width) in enumerate(zip(columns, widths), start=1):
        cell = ws.cell(row=5, column=i, value=name)
        cell.font = Font(bold=True, color=GREY, size=10)
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[5].height = 28
    ws.freeze_panes = 'A6'
    ws.sheet_view.showGridLines = False


def link(cell, url, text):
    url = content_system.public_url(url)
    if url:
        cell.value = text
        cell.hyperlink = url
        cell.font = Font(color=ACCENT, underline='single')
    else:
        cell.value = 'Not linked'
        cell.font = Font(color='86868B')


def dropdown(ws, options, ref):
    dv = DataValidation(type='list', formula1='"' + ','.join(options) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(ref)


def build_workbook(result, path):
    now = datetime.now(timezone.utc)
    posts = result['posts']
    cov = result['coverage']
    wb = Workbook()

    ideas = wb.active
    ideas.title = 'Ideas'
    cols = ['Picture', 'Product', 'Decision', 'Original post', 'Profile', 'Store', 'Views', 'Likes', 'Comments', 'Shares', 'Published', 'Age', 'Awareness', 'Sophistication', 'Comparables', 'Why / what is missing']
    header(ideas, 'Product Review',
           '%d of 100 qualified accounts (named, published within 24 h, views verified, no giveaway). %d posts total. Missing numbers are unavailable, not zero.'
           % (cov['qualified_accounts'], cov['posts']),
           cols, [14, 32, 12, 14, 12, 12, 11, 11, 11, 11, 18, 11, 16, 22, 12, 60])
    last = 5 + max(len(posts), 1)
    for r, row in enumerate(posts, start=6):
        n = r - 5
        ideas.row_dimensions[r].height = 78
        ideas.cell(row=r, column=1, value='No image' if not row['image_url'] else '')
        ideas.cell(row=r, column=2, value=row['product'] or 'Product not identified').font = Font(bold=True, color=INK)
        ideas.cell(row=r, column=3, value=row.get('decision') or 'Review')
        link(ideas.cell(row=r, column=4), row['url'], 'Watch post')
        link(ideas.cell(row=r, column=5), row['profile_url'], 'Profile')
        link(ideas.cell(row=r, column=6), row['seller_url'], 'Store')
        for c, key in zip(range(7, 11), 'GHIJ'):
            ev_col = {'G': 'E', 'H': 'F', 'I': 'G', 'J': 'H'}[key]
            ideas.cell(row=r, column=c, value='=IF(Evidence!%s%d="","Unavailable",Evidence!%s%d)' % (ev_col, r, ev_col, r)).number_format = '#,##0'
        when = content_system.published(row)
        ideas.cell(row=r, column=11, value=when.strftime('%Y-%m-%d %H:%M UTC') if when else 'Unverified')
        ideas.cell(row=r, column=12, value=age_label(row, now))
        ideas.cell(row=r, column=13, value=row.get('awareness') or 'Unreviewed')
        ideas.cell(row=r, column=14, value=row.get('sophistication') or 'Unreviewed')
        ideas.cell(row=r, column=15, value=len(row['comparables']))
        ideas.cell(row=r, column=16, value=why(row))
        for c in range(1, len(cols) + 1):
            cell = ideas.cell(row=r, column=c)
            cell.alignment = Alignment(vertical='center', wrap_text=c in (2, 16))
            cell.border = LINE
        cached = HERE / 'images' / (hashlib.sha1(row['image_url'].encode()).hexdigest()[:16] + '.jpg') if row['image_url'] else None
        if cached and cached.exists():
            img = XLImage(str(cached))
            scale = min(92 / img.width, 92 / img.height)
            img.width, img.height = int(img.width * scale), int(img.height * scale)
            ideas.add_image(img, 'A%d' % r)
            ideas.cell(row=r, column=1, value=None)
        else:
            ideas.cell(row=r, column=1).font = Font(color='86868B', size=9)
    dropdown(ideas, DECISIONS, 'C6:C%d' % last)
    dropdown(ideas, AWARENESS, 'M6:M%d' % last)
    dropdown(ideas, SOPHISTICATION, 'N6:N%d' % last)
    ideas.auto_filter.ref = 'B5:P%d' % last

    ev = wb.create_sheet('Evidence')
    fields = [('Product', 'product'), ('Platform', 'platform'), ('Account', 'account'), ('Post URL', 'url'), ('Views', 'views'), ('Likes', 'likes'), ('Comments', 'comments'), ('Shares', 'shares'), ('Saves', 'saves'),
              ('Published', 'posted_at'), ('Collected', 'captured_at'), ('Seller type', 'account_type'), ('Profile URL', 'profile_url'), ('Store URL', 'seller_url'), ('Sampling', 'sampling'),
              ('Hook', 'hook'), ('Hook timestamp', 'hook_timestamp'), ('Format', 'format'), ('Offer', 'offer'), ('Awareness', 'awareness'), ('Sophistication', 'sophistication'), ('Strategy evidence', 'strategy_evidence'),
              ('Transcript', 'transcript'), ('Caption', 'caption'), ('Audience', 'audience'), ('Buyer questions', 'buyer_questions'), ('Giveaway', 'giveaway'), ('Keyword CTA', 'keyword_cta'), ('Comparable URLs', 'comparables'), ('Image URL', 'image_url'), ('Notes', 'notes')]
    header(ev, 'Post Evidence', 'Source values. Blank metric = unavailable, not zero. Edit judgments on the Ideas sheet or in Product_Review.html.',
           [f[0] for f in fields], [30, 11, 18, 42, 11, 11, 11, 11, 11, 24, 24, 16, 34, 34, 16, 30, 12, 16, 20, 16, 22, 36, 40, 50, 20, 30, 10, 12, 50, 40, 50])
    for r, row in enumerate(posts, start=6):
        for c, (_, key) in enumerate(fields, start=1):
            value = row.get(key)
            if key == 'comparables':
                value = '\n'.join(x['url'] for x in value)
            elif isinstance(value, bool):
                value = 'Yes' if value else 'No'
            cell = ev.cell(row=r, column=c, value=value if value not in (None, '') else None)
            if key in ('url', 'profile_url', 'seller_url') and content_system.public_url(value):
                cell.hyperlink = value
                cell.font = Font(color=ACCENT, underline='single')
            if key in ('views', 'likes', 'comments', 'shares', 'saves'):
                cell.number_format = '#,##0'
            cell.alignment = Alignment(vertical='top', wrap_text=key in ('caption', 'transcript', 'notes', 'strategy_evidence', 'comparables'))
    ev.auto_filter.ref = 'A5:%s%d' % (get_column_letter(len(fields)), last)

    cv = wb.create_sheet('Coverage')
    cv.sheet_view.showGridLines = False
    cv['A2'] = 'Collection coverage'
    cv['A2'].font = Font(size=20, bold=True, color=INK)
    cv['A3'] = 'Checked %s. Nothing is relaxed to reach the target; older or incomplete accounts are counted separately.' % now.strftime('%Y-%m-%d %H:%M UTC')
    cv['A3'].font = Font(color=GREY)
    rows = [('Qualified accounts (target 100)', cov['qualified_accounts']), ('Older or incomplete named accounts', cov['older_or_incomplete_accounts']),
            ('Named accounts', cov['named_accounts']), ('Posts', cov['posts']), ('Dated posts', cov['dated_posts']),
            ('Posts with product image', cov['with_image']), ('Posts with profile link', cov['with_profile_link']), ('Posts with store link', cov['with_store_link']),
            ('Posts with 3+ comparable videos', cov['with_3plus_comparables']), ('Giveaways excluded', cov['giveaways_excluded'])]
    rows += [('%s coverage' % m.capitalize(), '%d%%' % round(v * 100)) for m, v in cov['metric_coverage'].items()]
    for i, (k, v) in enumerate(rows, start=5):
        cv.cell(row=i, column=1, value=k).border = LINE
        cell = cv.cell(row=i, column=2, value=v)
        cell.border = LINE
        cell.alignment = Alignment(horizontal='right')
    cv.column_dimensions['A'].width = 40
    cv.column_dimensions['B'].width = 14
    cv.cell(row=len(rows) + 6, column=1, value=result.get('limitations', '')).font = Font(color=GREY, size=10)
    wb.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path, nargs='?', default=HERE / 'Evidence.json')
    parser.add_argument('--html', type=Path, default=HERE / 'Product_Review.html')
    parser.add_argument('--xlsx', type=Path, default=HERE / 'Product_Review.xlsx')
    args = parser.parse_args()
    result = load_result(args.input)
    embed_html(result, args.html)
    build_workbook(result, args.xlsx)
    c = result['coverage']
    print('Built %s and %s from %d posts. Qualified accounts: %d / 100.' % (args.html.name, args.xlsx.name, c['posts'], c['qualified_accounts']))


if __name__ == '__main__':
    main()
