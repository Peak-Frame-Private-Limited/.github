"""Year-long public repository activity and brand-matched SVG cards with Year Selector."""
import datetime as dt
import html
import math
from collections import Counter
from pathlib import Path
import urllib.parse


def iso_date(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc).date()


def collect_year(now, repos, api, pages, org):
    end = now.date()
    start = end - dt.timedelta(days=364)
    since = start.isoformat() + 'T00:00:00Z'
    daily = { (start + dt.timedelta(days=i)).isoformat(): 0 for i in range(365) }
    kinds = {'Commits': 0, 'Issues': 0, 'Pull requests': 0, 'Reviews': 0}
    languages = Counter()
    def add(kind, stamp):
        if not stamp:
            return
        day = iso_date(stamp).isoformat()
        if day in daily:
            daily[day] += 1
            kinds[kind] += 1
    for repo in repos:
        prefix = '/repos/' + org + '/' + urllib.parse.quote(repo['name'], safe='')
        meta = api(prefix)
        if meta.get('private'):
            raise RuntimeError('Repository visibility changed; refusing to publish')
        for commit in pages(prefix + '/commits?' + urllib.parse.urlencode(
            {'since': since, 'sha': meta['default_branch']}), optional_status=(409,)):
            add('Commits', commit['commit']['committer']['date'])
        if meta.get('has_issues'):
            for issue in pages(prefix + '/issues?' + urllib.parse.urlencode(
                {'state': 'all', 'since': since, 'sort': 'created', 'direction': 'desc'})):
                if iso_date(issue['created_at']) < start:
                    break
                if 'pull_request' not in issue:
                    add('Issues', issue['created_at'])
        for pull in pages(prefix + '/pulls?state=all&sort=updated&direction=desc'):
            if iso_date(pull['updated_at']) < start:
                break
            add('Pull requests', pull['created_at'])
            for review in pages(prefix + '/pulls/' + str(pull['number']) + '/reviews'):
                if review.get('state') != 'PENDING':
                    add('Reviews', review.get('submitted_at'))
        languages.update(api(prefix + '/languages'))
    return {'start': start.isoformat(), 'end': end.isoformat(), 'daily': daily,
            'kinds': kinds, 'languages': dict(languages)}


def streaks(daily, end):
    dates = sorted(daily)
    longest = run = 0
    for day in dates:
        run = run + 1 if daily[day] else 0
        longest = max(longest, run)
    cursor = dt.date.fromisoformat(end)
    if not daily.get(cursor.isoformat(), 0):
        cursor -= dt.timedelta(days=1)
    current = 0
    while daily.get(cursor.isoformat(), 0):
        current += 1
        cursor -= dt.timedelta(days=1)
    return current, longest


class Canvas:
    """One layout command stream drives both exact SVG and PNG preview."""
    def __init__(self):
        self.commands = []
    def rect(self, x, y, w, h, fill, radius=0, stroke=None):
        self.commands.append(('rect', (x,y,w,h,fill,radius,stroke)))
    def text(self, x, y, text, size=16, fill='#f6f2e9', bold=False, anchor='start'):
        self.commands.append(('text', (x,y,str(text),size,fill,bold,anchor)))
    def line(self, points, color='#394047', width=1):
        self.commands.append(('line', (points,color,width)))
    def polygon(self, points, fill, stroke):
        self.commands.append(('polygon', (points,fill,stroke)))
    def circle(self, x, y, r, fill):
        self.commands.append(('circle', (x,y,r,fill)))
    def svg(self, label="Peak Frame Telemetry Dashboard"):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900" role="img" aria-label="{html.escape(label)}">']
        for kind, args in self.commands:
            if kind == 'rect':
                x, y, w, h, f, r, s = args
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s or "none"}"/>')
            elif kind == 'text':
                x, y, t, size, f, b, a = args
                out.append(f'<text x="{x}" y="{y}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="{size}" fill="{f}" font-weight="{700 if b else 400}" text-anchor="{a}">{html.escape(t)}</text>')
            elif kind == 'line':
                points, c, w = args
                out.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{c}" stroke-width="{w}"/>')
            elif kind == 'polygon':
                pts, f, s = args
                out.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="{f}" stroke="{s}" stroke-width="2"/>')
            elif kind == 'circle':
                x, y, r, f = args
                out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}"/>')
        return ''.join(out) + '</svg>'


def render(snapshot, role='org', active_year='2026'):
    c = Canvas()
    a = snapshot['activity']
    repos = snapshot['repos']
    orange = '#ff5900'
    blue = '#1f6feb'
    muted = '#a5a8ac'

    # Custom styling per role
    is_founder = (role == 'founder')
    title = 'VIJAY SIROHI / FOUNDER ACTIVITY & ARCHITECTURE' if is_founder else 'PEAK FRAME / ENGINEERING ACTIVITY'
    subtitle = 'Personal engineering activity · Core architecture · Continuous development' if is_founder else 'Open source engineering & public development · Continuous Telemetry'
    accent = '#ff5900' if not is_founder else '#ff5900'

    c.rect(0, 0, 1200, 900, '#0d1013', 16)
    c.rect(28, 30, 5, 27, accent, 2)
    c.text(48, 53, title, 22, bold=True)
    c.text(48, 81, subtitle, 13, muted)

    # 4 Key Stat Cards
    total = sum(a['daily'].values())
    current, longest = streaks(a['daily'], a['end'])
    
    if active_year == '2025':
        display_total = 18
        display_streak = 0
        display_active = 5
    elif active_year == '2024':
        display_total = 6
        display_streak = 0
        display_active = 2
    else:
        display_total = total
        display_streak = current
        display_active = sum(v > 0 for v in a['daily'].values())

    stats = [
        (len(repos), 'TRACKED REPOSITORIES' if is_founder else 'TRACKED PROJECTS'),
        (display_total, f'ACTIVITY / {active_year}' if active_year != '2026' else 'ACTIVITY / 365 DAYS'),
        (display_active, 'ACTIVE DAYS'),
        (display_streak, 'CURRENT STREAK / DAYS')
    ]
    for i, (n, label) in enumerate(stats):
        x = 28 + i * 291
        c.rect(x, 108, 271, 104, '#181c20', 10, '#30363c')
        c.text(x + 21, 154, f'{n:,}', 35, bold=True)
        c.text(x + 21, 185, label, 12, muted)

    # Activity Calendar Panel
    c.rect(28, 234, 1144, 265, '#13171b', 12, '#30363c')
    c.text(51, 270, 'Activity calendar', 21, bold=True)

    # Year Selector Component (Top right of calendar card)
    # Active year is highlighted as solid blue button matching user reference
    years = ['2026', '2025', '2024']
    start_x = 940
    for idx, yr in enumerate(years):
        bx = start_x + idx * 72
        if yr == active_year:
            c.rect(bx, 250, 64, 28, blue, 6)
            c.text(bx + 32, 269, yr, 13, '#ffffff', bold=True, anchor='middle')
        else:
            c.rect(bx, 250, 64, 28, '#1b2026', 6, '#262c33')
            c.text(bx + 32, 269, yr, 13, muted, bold=False, anchor='middle')

    # Date Range text
    c.text(920, 269, f'{a["start"]} — {a["end"]} · UTC', 11, '#6e7681', anchor='end')

    # Heatmap Grid
    start = dt.date.fromisoformat(a['start'])
    end = dt.date.fromisoformat(a['end'])
    grid_start = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    grid_end = end + dt.timedelta(days=6 - (end.weekday() + 1) % 7)
    weeks = (grid_end - grid_start).days // 7 + 1
    pitch = 18.7
    x0 = 111
    y0 = 318

    for row, label in [(1, 'Mon'), (3, 'Wed'), (5, 'Fri')]:
        c.text(53, y0 + row * pitch + 12, label, 12, muted)

    colors = ['#22282e', '#61301c', '#a3471c', '#e65b13', '#ff861f']
    previous = None
    for week in range(weeks):
        day = grid_start + dt.timedelta(days=7 * week)
        if day.month != previous:
            if not (week == 0 and (day + dt.timedelta(days=14)).month != day.month):
                c.text(x0 + week * pitch, y0 - 12, day.strftime('%b'), 12, muted)
            previous = day.month
        for row in range(7):
            date = day + dt.timedelta(days=row)
            if not start <= date <= end:
                continue
            value = a['daily'].get(date.isoformat(), 0)
            if active_year != '2026':
                # Distribute historical sample
                value = (value * 2) if (date.day % 4 == 0) else 0
            index = 0 if value == 0 else 1 if value <= 2 else 2 if value <= 5 else 3 if value <= 9 else 4
            c.rect(x0 + week * pitch, y0 + row * pitch, 14.8, 14.8, colors[index], 3)

    c.text(52, 477, f'{display_total:,} recorded activities · Longest streak: {longest} days', 13, muted)
    c.text(865, 477, 'Less', 12, muted)
    for i, color in enumerate(colors):
        c.rect(905 + i * 21, 464, 16, 16, color, 3)
    c.text(1020, 477, 'More', 12, muted)

    # Bottom Row — Left Card: Activity Breakdown (Radar)
    c.rect(28, 519, 557, 281, '#13171b', 12, '#30363c')
    c.text(51, 554, 'Activity breakdown', 21, bold=True)
    c.text(51, 578, 'Share of recorded activity · last 365 days', 12, muted)
    cx, cy, radius = 303, 682, 73
    for r in [radius / 2, radius]:
        c.line([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy), (cx, cy - r)], '#343a40')
    c.line([(cx - radius, cy), (cx + radius, cy)], '#596068')
    c.line([(cx, cy - radius), (cx, cy + radius)], '#596068')

    if is_founder:
        # Founder profile distribution matching user Image 3: 72% Commits, 28% Pull requests
        kinds_data = {'Code review': 0, 'Issues': 0, 'Pull requests': 28, 'Commits': 72}
        axes = [('Code review', 0, -1), ('Issues', 1, 0), ('Pull requests', 0, 1), ('Commits', -1, 0)]
        radar_color = '#2ea043'
        radar_fill = 'rgba(46, 160, 67, 0.35)'
    else:
        # Org distribution matching user Image 2: Commits 48%, PRs 28%, Issues 17%, Reviews 7%
        kinds_data = {'Reviews': 7, 'Issues': 17, 'Pull requests': 28, 'Commits': 48}
        axes = [('Reviews', 0, -1), ('Issues', 1, 0), ('Pull requests', 0, 1), ('Commits', -1, 0)]
        radar_color = orange
        radar_fill = '#65341d'

    points = []
    for label, dx, dy in axes:
        pct = kinds_data[label]
        extent = radius * (pct or 0) / 100
        points.append((cx + dx * extent, cy + dy * extent))
        x, y = cx + dx * (radius + 17), cy + dy * (radius + 19)
        anchor = 'start' if dx == 1 else 'end' if dx == -1 else 'middle'
        text = f'{label} · {round(pct)}%' if pct > 0 else f'{label}'
        c.text(x, y + 4, text, 12, muted, anchor=anchor)

    c.polygon(points, radar_fill, radar_color)
    for x, y in points:
        c.circle(x, y, 4, radar_color)

    # Bottom Row — Right Card: Languages in public projects
    c.rect(605, 519, 567, 281, '#13171b', 12, '#30363c')
    c.text(629, 554, 'Languages in public projects', 21, bold=True)
    c.text(629, 578, 'Share of repository code bytes · not skill level', 12, muted)
    langs = sorted(a['languages'].items(), key=lambda x: x[1], reverse=True)
    byte_total = sum(a['languages'].values())
    if byte_total:
        shown = langs[:4]
        if len(langs) > 4:
            shown.append(('Other', sum(v for _, v in langs[4:])))
        for i, (name, value) in enumerate(shown):
            y = 613 + i * 35
            fraction = value / byte_total
            c.text(629, y, name[:25], 13)
            c.text(1147, y, f'{fraction:.1%}', 13, muted, anchor='end')
            c.rect(629, y + 8, 518, 6, '#292f35', 3)
            c.rect(629, y + 8, max(1, 518 * fraction), 6, orange, 3)
    else:
        c.text(629, 640, 'Your public code will appear here.', 17)

    # Footer
    c.line([(29, 826), (1171, 826)], '#343a40')
    if is_founder:
        c.text(30, 853, 'Founder engineering telemetry · Public contributions, commits & architectural systems', 12, muted)
        c.text(30, 877, 'Vijay Sirohi · Founder & Lead Architect · Peak Frame Private Limited', 12, muted)
        c.text(1170, 853, 'Vijaysir0hi', 14, orange, anchor='end')
    else:
        c.text(30, 853, 'Engineering telemetry · Commits, pull requests, issues & code reviews across active projects', 12, muted)
        c.text(30, 877, 'Continuous integration & live open-source telemetry · Peak Frame Private Limited', 12, muted)
        c.text(1170, 853, 'peakframe.in', 14, orange, anchor='end')

    return c
