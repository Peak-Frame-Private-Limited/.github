"""Year-long public repository activity and brand-matched SVG cards."""
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
        # Re-check visibility before fetching/publishing repo-specific data.
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
    def circle(self,x,y,r,fill):
        self.commands.append(('circle',(x,y,r,fill)))
    def svg(self):
        out=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900" role="img" aria-label="Peak Frame public organization activity calendar and statistics">']
        for kind,args in self.commands:
            if kind=='rect':
                x,y,w,h,f,r,s=args
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s or "none"}"/>')
            elif kind=='text':
                x,y,t,size,f,b,a=args
                out.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" fill="{f}" font-weight="{700 if b else 400}" text-anchor="{a}">{html.escape(t)}</text>')
            elif kind=='line':
                points,c,w=args
                out.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{c}" stroke-width="{w}"/>')
            elif kind=='polygon':
                pts,f,s=args
                out.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="{f}" stroke="{s}" stroke-width="2"/>')
            elif kind=='circle':
                x,y,r,f=args
                out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}"/>')
        return ''.join(out)+'</svg>'
    def png(self,path):
        from PIL import Image, ImageDraw, ImageFont
        scale=2
        image=Image.new('RGB',(2400,1800),'#0d1013');d=ImageDraw.Draw(image)
        def pts(values):return [(round(x*scale),round(y*scale)) for x,y in values]
        for kind,args in self.commands:
            if kind=='rect':
                x,y,w,h,f,r,s=args
                d.rounded_rectangle((x*scale,y*scale,(x+w)*scale,(y+h)*scale),radius=r*scale,fill=f,outline=s,width=scale)
            elif kind=='text':
                x,y,t,size,f,b,a=args
                font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if b else '')+'.ttf',size*scale)
                anchor={'start':'ls','middle':'ms','end':'rs'}[a]
                d.text((x*scale,y*scale),t,font=font,fill=f,anchor=anchor)
            elif kind=='line':
                p,c,w=args;d.line(pts(p),fill=c,width=max(1,round(w*scale)))
            elif kind=='polygon':
                p,f,s=args;d.polygon(pts(p),fill=f);d.line(pts(p+[p[0]]),fill=s,width=2*scale)
            elif kind=='circle':
                x,y,r,f=args;d.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),fill=f)
        image.save(path)


def render(snapshot):
    c=Canvas();a=snapshot['activity'];repos=snapshot['repos'];orange='#ff5900';muted='#a5a8ac'
    c.rect(0,0,1200,900,'#0d1013',16)
    c.rect(28,30,5,27,orange,2)
    c.text(48,53,'PEAK FRAME / ENGINEERING ACTIVITY',23,bold=True)
    c.text(48,81,'Public organization repositories · Scheduled refresh: every 6 hours',14,muted)
    total=sum(a['daily'].values());current,longest=streaks(a['daily'],a['end'])
    stats=[(len(repos),'TRACKED PROJECTS'),(total,'ACTIVITY / 365 DAYS'),(sum(v>0 for v in a['daily'].values()),'ACTIVE DAYS'),(current,'CURRENT STREAK / DAYS')]
    for i,(n,label) in enumerate(stats):
        x=28+i*291;c.rect(x,108,271,104,'#181c20',10,'#30363c');c.text(x+21,154,f'{n:,}',35,bold=True);c.text(x+21,185,label,12,muted)
    c.rect(28,234,1144,265,'#13171b',12,'#30363c')
    c.text(51,270,'Activity calendar',21,bold=True)
    c.text(1148,269,f'{a["start"]} — {a["end"]} · UTC',13,muted,anchor='end')
    start=dt.date.fromisoformat(a['start']);end=dt.date.fromisoformat(a['end'])
    grid_start=start-dt.timedelta(days=(start.weekday()+1)%7)
    grid_end=end+dt.timedelta(days=6-(end.weekday()+1)%7)
    weeks=(grid_end-grid_start).days//7+1;pitch=18.7;x0=111;y0=318
    for row,label in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:c.text(53,y0+row*pitch+12,label,12,muted)
    colors=['#22282e','#61301c','#a3471c','#e65b13','#ff861f']
    previous=None
    for week in range(weeks):
        day=grid_start+dt.timedelta(days=7*week)
        if day.month!=previous:
            if not (week==0 and (day+dt.timedelta(days=14)).month!=day.month):
                c.text(x0+week*pitch,y0-12,day.strftime('%b'),12,muted)
            previous=day.month
        for row in range(7):
            date=day+dt.timedelta(days=row)
            if not start<=date<=end:continue
            value=a['daily'].get(date.isoformat(),0)
            index=0 if value==0 else 1 if value<=2 else 2 if value<=5 else 3 if value<=9 else 4
            c.rect(x0+week*pitch,y0+row*pitch,14.8,14.8,colors[index],3)
    c.text(52,477,f'{total:,} recorded activities · Longest streak: {longest} days',13,muted)
    c.text(865,477,'Less',12,muted)
    for i,color in enumerate(colors):c.rect(905+i*21,464,16,16,color,3)
    c.text(1020,477,'More',12,muted)
    c.rect(28,519,557,281,'#13171b',12,'#30363c');c.text(51,554,'Activity breakdown',21,bold=True)
    c.text(51,578,'Share of recorded activity · last 365 days',12,muted)
    cx,cy,radius=303,682,73
    for r in [radius/2,radius]:c.line([(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy),(cx,cy-r)],'#343a40')
    c.line([(cx-radius,cy),(cx+radius,cy)],'#596068');c.line([(cx,cy-radius),(cx,cy+radius)],'#596068')
    axes=[('Reviews',0,-1),('Issues',1,0),('Pull requests',0,1),('Commits',-1,0)]
    points=[]
    for label,dx,dy in axes:
        pct=100*a['kinds'][label]/total if total else None
        extent=radius*(pct or 0)/100;points.append((cx+dx*extent,cy+dy*extent))
        x,y=cx+dx*(radius+17),cy+dy*(radius+19)
        anchor='start' if dx==1 else 'end' if dx==-1 else 'middle'
        text=f'{label} · {round(pct)}%' if pct is not None else f'{label} · —'
        c.text(x,y+4,text,12,muted,anchor=anchor)
    if total:
        c.polygon(points,'#65341d',orange)
        for x,y in points:c.circle(x,y,4,orange)
    else:c.circle(cx,cy,4,'#74797f');c.text(51,786,'No recorded activity yet',12,muted)
    c.rect(605,519,567,281,'#13171b',12,'#30363c');c.text(629,554,'Languages in public projects',21,bold=True)
    c.text(629,578,'Share of repository code bytes · not skill level',12,muted)
    langs=sorted(a['languages'].items(),key=lambda x:x[1],reverse=True);byte_total=sum(a['languages'].values())
    if byte_total:
        shown=langs[:4]
        if len(langs)>4:shown.append(('Other',sum(v for _,v in langs[4:])))
        for i,(name,value) in enumerate(shown):
            y=613+i*35;fraction=value/byte_total
            c.text(629,y,name[:25],13);c.text(1147,y,f'{fraction:.1%}',13,muted,anchor='end')
            c.rect(629,y+8,518,6,'#292f35',3);c.rect(629,y+8,max(1,518*fraction),6,orange,3)
    else:
        c.text(629,640,'Your public code will appear here.',17)
        c.text(629,670,'No eligible public project repositories',14,muted)
        c.text(629,692,'with detected language data yet.',14,muted)
    c.line([(29,826),(1171,826)],'#343a40')
    stamp=snapshot['updated'].replace('T',' ').replace('Z',' UTC')
    c.text(30,853,'Last successful refresh: '+stamp,12,muted)
    c.text(30,877,'Commits + issues opened + PRs opened + submitted reviews. Profile automation excluded.',12,muted)
    c.text(1170,853,'peakframe.in',14,orange,anchor='end')
    return c
