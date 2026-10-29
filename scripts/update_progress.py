"""Public organization progress. Python standard library; no third-party stats service."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity_cards import collect_year, render

ROOT = Path(__file__).resolve().parents[1]
ORG = os.environ.get('PROFILE_ORG', 'Peak-Frame-Private-Limited')
TOKEN = os.environ.get('GH_TOKEN', '')
EXCLUDE = {'.github', '.github-private'}


def api(path, optional_status=()):
    headers = {'User-Agent': 'Peakframe-profile-progress',
               'Accept': 'application/vnd.github+json'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    request = urllib.request.Request('https://api.github.com' + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in optional_status:
            return None
        # Stop on partial failures. Keep the last successful published snapshot.
        raise RuntimeError(f'GitHub API returned HTTP {error.code} for {path}') from None


def pages(path, optional_status=()):
    page = 1
    while True:
        result = api(path + ('&' if '?' in path else '?') +
                     urllib.parse.urlencode({'per_page': 100, 'page': page}), optional_status)
        if result is None:
            return
        if not isinstance(result, list):
            raise RuntimeError('Expected an API list')
        yield from result
        if len(result) < 100:
            return
        page += 1


def eligible(repo):
    return (not repo.get('private', True) and not repo.get('fork')
            and not repo.get('archived') and not repo.get('disabled')
            and repo['name'] not in EXCLUDE)


def collect(now):
    if not re.fullmatch(r'[A-Za-z0-9-]+', ORG):
        raise ValueError('Invalid organization slug')
    since = (now - dt.timedelta(days=30)).isoformat().replace('+00:00', 'Z')
    repos = [r for r in pages(f'/orgs/{ORG}/repos?type=public&sort=full_name') if eligible(r)]
    result = {'updated': now.isoformat().replace('+00:00', 'Z'), 'org': ORG,
              'repos': [], 'milestones': [], 'releases': []}
    for repo in repos:
        prefix = '/repos/' + ORG + '/' + urllib.parse.quote(repo['name'], safe='')
        commits = sum(1 for _ in pages(prefix + '/commits?' + urllib.parse.urlencode(
            {'since': since, 'sha': repo['default_branch']}), optional_status=(409,)))
        merged = 0
        for pull in pages(prefix + '/pulls?state=closed&sort=updated&direction=desc'):
            if pull['updated_at'] < since:
                break
            if pull.get('merged_at') and pull['merged_at'] >= since:
                merged += 1
        open_issues = sum(1 for issue in pages(prefix + '/issues?state=open')
                          if 'pull_request' not in issue) if repo.get('has_issues') else 0
        open_prs = sum(1 for _ in pages(prefix + '/pulls?state=open'))
        result['repos'].append({'name': repo['name'], 'url': repo['html_url'],
            'commits': commits, 'merged': merged, 'open_issues': open_issues,
            'open_prs': open_prs, 'stars': repo['stargazers_count'],
            'pushed_at': repo.get('pushed_at')})
        if repo.get('has_issues'):
            for milestone in pages(prefix + '/milestones?state=open&sort=due_on&direction=asc'):
                result['milestones'].append({'repo': repo['name'], 'title': milestone['title'],
                    'url': milestone['html_url'], 'open': milestone['open_issues'],
                    'closed': milestone['closed_issues'], 'due': milestone.get('due_on')})
        release = api(prefix + '/releases/latest', optional_status=(404,))
        if release:
            result['releases'].append({'repo': repo['name'], 'name': release.get('name') or release['tag_name'],
                'url': release['html_url'], 'published': release['published_at']})
    result['activity'] = collect_year(now, result['repos'], api, pages, ORG)
    return result


def md(value):
    # External titles are data, never embedded HTML or Markdown instructions.
    text = html.escape(str(value), quote=True).replace('\n', ' ').replace('\r', ' ')
    for char in ('\\', '|', '[', ']', '*', '_', '`', '<', '>'):
        text = text.replace(char, '\\' + char)
    return text


def link(label, url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com':
        raise ValueError('Unexpected source URL')
    return f'[{md(label)}](<{url}>)'


def completion(milestone):
    total = milestone['open'] + milestone['closed']
    return None if total == 0 else round(100 * milestone['closed'] / total)


def svg(snapshot):
    repos = snapshot['repos']
    values = [len(repos), sum(r['commits'] for r in repos),
              sum(r['merged'] for r in repos), sum(r['stars'] for r in repos)]
    labels = ['PUBLIC PROJECTS', 'COMMITS / 30 DAYS', 'MERGED PRs / 30 DAYS', 'TOTAL STARS']
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="230" viewBox="0 0 1200 230" role="img" aria-label="Peak Frame public development activity">',
             '<rect width="1200" height="230" rx="12" fill="#121314"/>',
             '<rect x="30" y="30" width="4" height="20" fill="#ff5900"/>',
             '<text x="48" y="46" fill="#f8f6f0" font-family="Arial,sans-serif" font-size="17">PEAK FRAME / PUBLIC DEVELOPMENT</text>']
    for i, (value, label) in enumerate(zip(values, labels)):
        x = 36 + i * 295
        parts += [f'<text x="{x}" y="123" fill="#f8f6f0" font-family="Arial,sans-serif" font-size="49" font-weight="700">{value:,}</text>',
                  f'<text x="{x}" y="159" fill="#c5c5c5" font-family="Arial,sans-serif" font-size="14">{label}</text>']
        if i < 3:
            parts.append(f'<path d="M{x+265}82v88" stroke="#393939"/>')
    parts.append('<text x="36" y="207" fill="#aaa" font-family="Arial,sans-serif" font-size="13">Continuous Telemetry · Active Open-Source Engineering</text></svg>')
    return ''.join(parts)


def markdown(snapshot):
    repos = snapshot['repos']
    image = f'https://raw.githubusercontent.com/{snapshot["org"]}/.github/HEAD/profile/assets/progress.svg'
    totals = (len(repos), sum(r['commits'] for r in repos), sum(r['merged'] for r in repos), sum(r['stars'] for r in repos))
    lines = [f'![Public projects: {totals[0]}; default-branch commits in 30 days: {totals[1]}; merged PRs in 30 days: {totals[2]}; stars: {totals[3]}]({image})', '',
             f'**Last successful refresh:** {snapshot["updated"].replace("T", " ").replace("Z", " UTC")}', '',
             'Public projects only · Rolling 30-day activity · Profile automation excluded', '']
    if 'activity' in snapshot:
        chart = f'https://raw.githubusercontent.com/{snapshot["org"]}/.github/HEAD/profile/assets/activity.svg'
        annual = sum(snapshot['activity']['daily'].values())
        lines += [f'![Peak Frame activity calendar: {annual} recorded activities over the last 365 days. Includes activity mix and repository languages.]({chart})', '',
                  'Calendar: commits, issues opened, pull requests opened and submitted reviews in tracked public repositories. UTC dates; not GitHub’s personal contribution score.', '']
    if repos:
        lines += ['### Repository activity', '', '| Repository | Commits / 30d | Merged PRs / 30d | Open issues | Open PRs | Last push (UTC) |',
                  '| :--- | ---: | ---: | ---: | ---: | :--- |']
        for r in sorted(repos, key=lambda r: r['pushed_at'] or '', reverse=True):
            lines.append(f'| {link(r["name"], r["url"])} | {r["commits"]} | {r["merged"]} | {r["open_issues"]} | {r["open_prs"]} | {(r["pushed_at"] or "—")[:10]} |')
    else:
        lines += ['No public project repositories are available to track yet. Public projects will appear here automatically. Private work is not included.']
    lines += ['', '### Milestone progress', '']
    if snapshot['milestones']:
        lines += ['| Project / milestone | Completion | Closed / total items | Due (UTC) |', '| :--- | :--- | ---: | :--- |']
        for m in snapshot['milestones']:
            pct = completion(m)
            progress = 'No items assigned' if pct is None else f'{pct}%'
            lines.append(f'| {link(m["repo"]+" / "+m["title"],m["url"])} | {progress} | {m["closed"]} / {m["closed"]+m["open"]} | {(m["due"] or "Not set")[:10]} |')
    else:
        lines.append('No open public milestones yet. Milestones with assigned issues or pull requests will appear here automatically.')
    lines += ['', '### Latest releases', '']
    releases = sorted(snapshot['releases'], key=lambda r: r['published'], reverse=True)[:5]
    lines += [f'- **{md(r["repo"])}** · {link(r["name"],r["url"])} · {r["published"][:10]}' for r in releases] or ['No public stable releases published yet.']
    return '\n'.join(lines)


def replace_block(readme, content):
    start, end = '<!-- PROGRESS:START -->', '<!-- PROGRESS:END -->'
    if readme.count(start) != 1 or readme.count(end) != 1 or readme.index(end) < readme.index(start):
        raise ValueError('README needs exactly one correctly ordered progress marker pair')
    before, rest = readme.split(start)
    _, after = rest.split(end)
    return before + start + '\n' + content + '\n' + end + after


def main():
    snapshot = collect(dt.datetime.now(dt.timezone.utc).replace(microsecond=0))
    readme = ROOT / 'profile/README.md'
    updated = replace_block(readme.read_text(), markdown(snapshot))
    graphic = svg(snapshot)
    activity_graphic = render(snapshot).svg()
    # All API calls and rendering complete before touching the output files.
    (ROOT / 'profile/assets/progress.svg').write_text(graphic)
    (ROOT / 'profile/assets/activity.svg').write_text(activity_graphic)
    (ROOT / 'profile/progress.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    readme.write_text(updated)
    print(f'Updated public progress for {len(snapshot["repos"])} project repositories.')


if __name__ == '__main__':
    main()
