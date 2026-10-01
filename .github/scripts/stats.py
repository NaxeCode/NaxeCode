#!/usr/bin/env python3
"""Render profile stat cards (Stella / cosmic theme) from the GitHub GraphQL API.

Usage: GITHUB_TOKEN=... stats.py <login> <out_dir>
Writes overview.svg, languages.svg and years.svg. Standard library only.
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request
from html import escape

# Stella HUD glass, with the aura shader's Oklab stops converted to sRGB.
SPACE, GLASS, BORDER = "#0b0e1a", "#171b28", "#384155"
TEXT, LABEL, MUTED, NOTE = "#f1f3fc", "#bdd3ef", "#8b95ad", "#ffcba8"
CYAN, BLUE, VIOLET, ROSE, AMBER, ICE = "#22baf3", "#7c83ff", "#cb69f3", "#ff6592", "#fea334", "#94dcf5"
AURA = [CYAN, BLUE, VIOLET, ROSE, AMBER]
ACCENTS = AURA + [ICE, NOTE, MUTED]
SANS = "Inter, 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', monospace"
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


def stars(width, height, seed):
    """A sparse, deterministic starfield so cards don't flicker between runs."""
    rng = random.Random(seed)
    out = []
    for _ in range(width * height // 1500):
        x, y = rng.uniform(4, width - 4), rng.uniform(4, height - 4)
        r, o = rng.choice((0.5, 0.6, 0.8, 1.1)), rng.uniform(0.12, 0.45)
        color = ICE if rng.random() < 0.15 else TEXT
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" opacity="{o:.2f}"/>')
    return "".join(out)


def card(width, height, title, body):
    stops = "".join(f'<stop offset="{i / (len(AURA) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(AURA))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<defs>
<linearGradient id="aura" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>
<linearGradient id="glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GLASS}"/><stop offset="1" stop-color="{SPACE}"/></linearGradient>
<radialGradient id="nebulaA" cx="0.88" cy="0.05" r="0.75"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.22"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
<radialGradient id="nebulaB" cx="0.05" cy="1" r="0.7"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.14"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
<linearGradient id="rim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="0.5" stop-color="{BLUE}" stop-opacity="0.7"/><stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<clipPath id="frame"><rect width="{width}" height="{height}" rx="18"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{width}" height="{height}" fill="url(#glass)"/>
<rect width="{width}" height="{height}" fill="url(#nebulaA)"/>
<rect width="{width}" height="{height}" fill="url(#nebulaB)"/>
{stars(width, height, seed=title)}
<rect x="40" y="0" width="{width - 80}" height="1.5" fill="url(#rim)"/>
</g>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="18" fill="none" stroke="{BORDER}"/>
<text x="24" y="36" fill="{LABEL}" font-family="{SANS}" font-size="11" font-weight="600" letter-spacing="2.2">{escape(title.upper())}</text>
{body}
</svg>
"""


def sparkline(days, x, y, w, h):
    """Weekly contribution totals over the last 52 weeks, as a glowing line."""
    weeks = [sum(c for _, c in days[i:i + 7]) for i in range(0, len(days), 7)][-52:]
    peak = max(weeks) or 1
    step = w / (len(weeks) - 1)
    pts = [(x + i * step, y + h - h * c / peak) for i, c in enumerate(weeks)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return (
        f'<defs><linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.35"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{x},{y + h} {line} {x + w},{y + h}" fill="url(#haze)"/>'
        f'<polyline points="{line}" fill="none" stroke="url(#aura)" stroke-width="5" stroke-opacity="0.18" stroke-linejoin="round"/>'
        f'<polyline points="{line}" fill="none" stroke="url(#aura)" stroke-width="1.8" stroke-linejoin="round"/>'
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{TEXT}"/>'
        f'<text x="{x + w}" y="{y + h + 18}" fill="{MUTED}" font-family="{MONO}" font-size="10" letter-spacing="1" text-anchor="end">52 WEEKS</text>'
    )


def overview(s):
    current, longest = streaks(s["days"])
    total = sum(s["years"].values())
    stats = [
        (f"{s['last_year']:,}", "last 12 months", CYAN),
        (f"{s['prs']:,}", f"PRs · {s['merged']:,} merged", VIOLET),
        (f"{current:,}d", "current streak", ROSE),
        (f"{longest:,}d", "longest streak, 12 mo", AMBER),
    ]
    body = [
        f'<text x="24" y="84" fill="url(#aura)" font-family="{SANS}" font-size="42" font-weight="800" letter-spacing="-1">{total:,}</text>',
        f'<text x="24" y="106" fill="{LABEL}" font-family="{SANS}" font-size="13">contributions since {s["since"]}</text>',
        sparkline(s["days"], x=236, y=52, w=160, h=54),
    ]
    for i, (value, label, color) in enumerate(stats):
        x, y = 24 + (i % 2) * 188, 142 + (i // 2) * 32
        body.append(f'<circle cx="{x + 3}" cy="{y - 4}" r="3" fill="{color}"/><circle cx="{x + 3}" cy="{y - 4}" r="7" fill="{color}" opacity="0.18"/>')
        body.append(f'<text x="{x + 16}" y="{y}" font-family="{SANS}" font-size="13.5"><tspan fill="{TEXT}" font-weight="700">{value}</tspan><tspan fill="{MUTED}" dx="6">{escape(label)}</tspan></text>')
    return card(420, 200, "GitHub at a glance", "\n".join(body))


def languages(s, top=8):
    langs = s["langs"][:top]
    total = sum(size for _, size in langs) or 1
    body, x, bar_w = [], 24.0, 372
    body.append(f'<clipPath id="bar"><rect x="24" y="54" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    for i, (name, size) in enumerate(langs):
        w = bar_w * size / total
        body.append(f'<rect x="{x:.1f}" y="54" width="{w + 0.5:.1f}" height="8" fill="{ACCENTS[i % len(ACCENTS)]}"/>')
        x += w
    body.append("</g>")
    for i, (name, size) in enumerate(langs):
        cx, cy = 24 + (i % 2) * 188, 94 + (i // 2) * 27
        color = ACCENTS[i % len(ACCENTS)]
        body.append(f'<circle cx="{cx + 4}" cy="{cy - 4.5}" r="3.5" fill="{color}"/><circle cx="{cx + 4}" cy="{cy - 4.5}" r="7.5" fill="{color}" opacity="0.18"/>')
        body.append(f'<text x="{cx + 18}" y="{cy}" font-family="{SANS}" font-size="13.5"><tspan fill="{TEXT}">{escape(name)}</tspan><tspan fill="{MUTED}" dx="6">{100 * size / total:.1f}%</tspan></text>')
    return card(420, 200, "Top languages · public repos", "\n".join(body))


def years(s):
    data = list(s["years"].items())
    width, height, left, right, top, bottom = 852, 200, 24, 24, 56, 160
    peak = max(c for _, c in data) or 1
    slot = (width - left - right) / len(data)
    bar = slot * 0.5
    this_year = str(dt.date.today().year)
    body = [
        f'<defs><linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset="0.55" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
        f'<linearGradient id="beamNow" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{ROSE}"/><stop offset="1" stop-color="{AMBER}"/></linearGradient></defs>',
        f'<line x1="{left}" y1="{bottom + 0.5}" x2="{width - right}" y2="{bottom + 0.5}" stroke="{BORDER}"/>',
    ]
    for i, (year, count) in enumerate(data):
        h = max(2, (bottom - top - 18) * count / peak)
        x = left + i * slot + (slot - bar) / 2
        now = str(year) == this_year
        fill = "url(#beamNow)" if now else "url(#beam)"
        body.append(f'<rect x="{x:.1f}" y="{bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="4" fill="{fill}" opacity="0.55" filter="url(#glow)"/>')
        body.append(f'<rect x="{x:.1f}" y="{bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="4" fill="{fill}"/>')
        body.append(f'<text x="{x + bar / 2:.1f}" y="{bottom - h - 8:.1f}" fill="{NOTE if now else LABEL}" font-family="{SANS}" font-size="11.5" font-weight="600" text-anchor="middle">{count:,}</text>')
        body.append(f'<text x="{x + bar / 2:.1f}" y="{bottom + 20}" fill="{MUTED}" font-family="{MONO}" font-size="10.5" text-anchor="middle">{year}</text>')
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
