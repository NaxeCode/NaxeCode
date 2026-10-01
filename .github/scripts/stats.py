#!/usr/bin/env python3
"""Render profile stat cards (Everforest) from the GitHub GraphQL API.

Usage: GITHUB_TOKEN=... stats.py <login> <out_dir>
Writes overview.svg, languages.svg and years.svg. Standard library only.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

BG, BORDER, FG, MUTED, FAINT = "#2d353b", "#475258", "#d3c6aa", "#9da9a0", "#3d484d"
ACCENTS = ["#a7c080", "#7fbbb3", "#d699b6", "#e69875", "#dbbc7f", "#83c092", "#e67e80", "#9da9a0"]
SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', monospace"
HIDDEN_LANGS = {"HTML", "CSS", "SCSS", "Dockerfile", "Makefile", "Batchfile"}


def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch(login):
    user = gql(
        """query($login:String!){user(login:$login){
          createdAt
          pullRequests{totalCount} merged:pullRequests(states:MERGED){totalCount}
          contributionsCollection{contributionYears contributionCalendar{totalContributions
            weeks{contributionDays{date contributionCount}}}}}}""",
        login=login,
    )["user"]
    years = {}
    for year in user["contributionsCollection"]["contributionYears"]:
        c = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
              contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions}}}}""",
            login=login, **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )
        years[year] = c["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    langs, cursor = {}, None
    while True:
        page = gql(
            """query($login:String!,$after:String){user(login:$login){repositories(
              ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100,after:$after){
              pageInfo{hasNextPage endCursor}
              nodes{languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}""",
            login=login, after=cursor,
        )["user"]["repositories"]
        for repo in page["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name not in HIDDEN_LANGS:
                    langs[name] = langs.get(name, 0) + edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    days = [
        (d["date"], d["contributionCount"])
        for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]
        for d in w["contributionDays"]
    ]
    return {
        "since": user["createdAt"][:4],
        "prs": user["pullRequests"]["totalCount"],
        "merged": user["merged"]["totalCount"],
        "last_year": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "years": dict(sorted(years.items())),
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "days": days,
    }


def streaks(days):
    today = dt.date.today().isoformat()
    counts = [c for d, c in days if d <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    for i, c in enumerate(reversed(counts)):
        if c:
            current += 1
        elif i:  # a quiet today doesn't break the streak yet
            break
    return current, longest


def card(width, height, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<text x="22" y="34" fill="{MUTED}" font-family="{MONO}" font-size="12" letter-spacing="1.5">{escape(title.upper())}</text>
{body}
</svg>
"""


def sparkline(days, x, y, w, h):
    """Weekly contribution totals over the last 52 weeks, as a filled line."""
    weeks = [sum(c for _, c in days[i:i + 7]) for i in range(0, len(days), 7)][-52:]
    peak = max(weeks) or 1
    step = w / (len(weeks) - 1)
    pts = [(x + i * step, y + h - h * c / peak) for i, c in enumerate(weeks)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return (
        f'<polygon points="{x},{y + h} {line} {x + w},{y + h}" fill="{ACCENTS[0]}" fill-opacity="0.15"/>'
        f'<polyline points="{line}" fill="none" stroke="{ACCENTS[0]}" stroke-width="2" stroke-linejoin="round"/>'
        f'<text x="{x + w}" y="{y + h + 18}" fill="{MUTED}" font-family="{MONO}" font-size="11" text-anchor="end">52 weeks</text>'
    )


def overview(s):
    current, longest = streaks(s["days"])
    total = sum(s["years"].values())
    stats = [
        (f"{s['last_year']:,}", "last 12 months", ACCENTS[1]),
        (f"{s['prs']:,}", f"PRs · {s['merged']:,} merged", ACCENTS[2]),
        (f"{current:,}d", "current streak", ACCENTS[3]),
        (f"{longest:,}d", "longest streak, 12 mo", ACCENTS[4]),
    ]
    body = [
        f'<text x="22" y="82" fill="{ACCENTS[0]}" font-family="{SANS}" font-size="40" font-weight="700">{total:,}</text>',
        f'<text x="22" y="104" fill="{FG}" font-family="{SANS}" font-size="14">contributions since {s["since"]}</text>',
    ]
    body.append(sparkline(s["days"], x=236, y=50, w=162, h=56))
    for i, (value, label, color) in enumerate(stats):
        x, y = 22 + (i % 2) * 190, 140 + (i // 2) * 34
        body.append(f'<rect x="{x}" y="{y - 11}" width="4" height="22" rx="2" fill="{color}"/>')
        body.append(f'<text x="{x + 12}" y="{y + 6}" font-family="{SANS}" font-size="14"><tspan fill="{FG}" font-weight="700">{value}</tspan><tspan fill="{MUTED}" dx="6">{escape(label)}</tspan></text>')
    return card(420, 200, "GitHub at a glance", "\n".join(body))


def languages(s, top=8):
    langs = s["langs"][:top]
    total = sum(size for _, size in langs) or 1
    body, x, bar_w = [], 22.0, 376
    body.append(f'<clipPath id="bar"><rect x="22" y="52" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    for i, (name, size) in enumerate(langs):
        w = bar_w * size / total
        body.append(f'<rect x="{x:.1f}" y="52" width="{w + 0.5:.1f}" height="10" fill="{ACCENTS[i % len(ACCENTS)]}"/>')
        x += w
    body.append("</g>")
    for i, (name, size) in enumerate(langs):
        cx, cy = 22 + (i % 2) * 190, 92 + (i // 2) * 28
        body.append(f'<circle cx="{cx + 5}" cy="{cy - 5}" r="5" fill="{ACCENTS[i % len(ACCENTS)]}"/>')
        body.append(f'<text x="{cx + 18}" y="{cy}" font-family="{SANS}" font-size="14"><tspan fill="{FG}">{escape(name)}</tspan><tspan fill="{MUTED}" dx="6">{100 * size / total:.1f}%</tspan></text>')
    return card(420, 200, "Top languages · public repos", "\n".join(body))


def years(s):
    data = list(s["years"].items())
    width, height, left, right, top, bottom = 852, 200, 22, 22, 52, 162
    peak = max(c for _, c in data) or 1
    slot = (width - left - right) / len(data)
    bar = slot * 0.62
    this_year = str(dt.date.today().year)
    body = [f'<line x1="{left}" y1="{bottom + 0.5}" x2="{width - right}" y2="{bottom + 0.5}" stroke="{FAINT}"/>']
    for i, (year, count) in enumerate(data):
        h = max(2, (bottom - top - 18) * count / peak)
        x = left + i * slot + (slot - bar) / 2
        color = ACCENTS[1] if str(year) == this_year else ACCENTS[0]
        body.append(f'<rect x="{x:.1f}" y="{bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="3" fill="{color}"/>')
        body.append(f'<text x="{x + bar / 2:.1f}" y="{bottom - h - 6:.1f}" fill="{FG}" font-family="{SANS}" font-size="12" text-anchor="middle">{count:,}</text>')
        body.append(f'<text x="{x + bar / 2:.1f}" y="{bottom + 20}" fill="{MUTED}" font-family="{MONO}" font-size="11" text-anchor="middle">{year}</text>')
    return card(width, height, "Contributions per year", "\n".join(body))


def main():
    login, out = sys.argv[1], sys.argv[2]
    s = fetch(login)
    os.makedirs(out, exist_ok=True)
    for name, svg in (("overview", overview(s)), ("languages", languages(s)), ("years", years(s))):
        with open(os.path.join(out, f"{name}.svg"), "w") as f:
            f.write(svg)
    print(f"wrote cards: {sum(s['years'].values()):,} contributions, {len(s['langs'])} languages")


if __name__ == "__main__":
    main()
