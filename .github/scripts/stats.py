#!/usr/bin/env python3
"""Render profile stat cards (Stella / cosmic theme) from the GitHub GraphQL API.

Usage: GITHUB_TOKEN=... stats.py <login> <out_dir>
Writes dashboard.svg: one panel with overview, languages and yearly contributions
sharing a single background. Standard library only.
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


W, ROW, YEARS_H, FOOT = 880, 204, 196, 40
H = ROW + YEARS_H + FOOT


def stars(width, height, seed):
    """A sparse, deterministic starfield so the panel doesn't flicker between runs."""
    rng = random.Random(seed)
    out = []
    for _ in range(width * height // 1700):
        x, y = rng.uniform(4, width - 4), rng.uniform(4, height - 4)
        r, o = rng.choice((0.5, 0.6, 0.8, 1.1)), rng.uniform(0.1, 0.4)
        color = ICE if rng.random() < 0.15 else TEXT
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" opacity="{o:.2f}"/>')
    return "".join(out)


def label(x, y, text):
    return f'<text x="{x}" y="{y}" fill="{LABEL}" font-family="{SANS}" font-size="11" font-weight="600" letter-spacing="2.2">{escape(text.upper())}</text>'


def stat_line(x, y, value, text, color):
    return (f'<circle cx="{x + 3}" cy="{y - 4}" r="3" fill="{color}"/><circle cx="{x + 3}" cy="{y - 4}" r="7" fill="{color}" opacity="0.18"/>'
            f'<text x="{x + 16}" y="{y}" font-family="{SANS}" font-size="13.5"><tspan fill="{TEXT}" font-weight="700">{value}</tspan>'
            f'<tspan fill="{MUTED}" dx="6">{escape(text)}</tspan></text>')


def sparkline(days, x, y, w, h):
    """Weekly contribution totals over the last 52 weeks, as a glowing line."""
    weeks = [sum(c for _, c in days[i:i + 7]) for i in range(0, len(days), 7)][-52:]
    peak = max(weeks) or 1
    step = w / (len(weeks) - 1)
    pts = [(x + i * step, y + h - h * c / peak) for i, c in enumerate(weeks)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return (
        f'<polygon points="{x},{y + h} {line} {x + w},{y + h}" fill="url(#haze)"/>'
        f'<polyline points="{line}" fill="none" stroke="url(#aura)" stroke-width="5" stroke-opacity="0.18" stroke-linejoin="round"/>'
        f'<polyline points="{line}" fill="none" stroke="url(#aura)" stroke-width="1.8" stroke-linejoin="round"/>'
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{TEXT}"/>'
        f'<text x="{x + w}" y="{y + h + 18}" fill="{MUTED}" font-family="{MONO}" font-size="10" letter-spacing="1" text-anchor="end">52 WEEKS</text>'
    )


def overview(s, x0):
    current, longest = streaks(s["days"])
    total = sum(s["years"].values())
    out = [
        label(x0, 40, "GitHub at a glance"),
        f'<text x="{x0}" y="88" fill="url(#aura)" font-family="{SANS}" font-size="42" font-weight="800" letter-spacing="-1">{total:,}</text>',
        f'<text x="{x0}" y="110" fill="{LABEL}" font-family="{SANS}" font-size="13">contributions since {s["since"]}</text>',
        sparkline(s["days"], x=x0 + 212, y=56, w=168, h=54),
    ]
    stats = [
        (f"{s['last_year']:,}", "last 12 months", CYAN),
        (f"{s['prs']:,}", f"PRs · {s['merged']:,} merged", VIOLET),
        (f"{current:,}d", "current streak", ROSE),
        (f"{longest:,}d", "longest streak, 12 mo", AMBER),
    ]
    for i, (value, text, color) in enumerate(stats):
        out.append(stat_line(x0 + (i % 2) * 192, 148 + (i // 2) * 30, value, text, color))
    return "".join(out)


def languages(s, x0, top=8):
    langs = s["langs"][:top]
    total = sum(size for _, size in langs) or 1
    bar_w = W - x0 - 32
    out = [label(x0, 40, "Top languages · public repos"),
           f'<clipPath id="bar"><rect x="{x0}" y="58" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">']
    x = float(x0)
    for i, (_, size) in enumerate(langs):
        w = bar_w * size / total
        out.append(f'<rect x="{x:.1f}" y="58" width="{w + 0.5:.1f}" height="8" fill="{ACCENTS[i % len(ACCENTS)]}"/>')
        x += w
    out.append("</g>")
    for i, (name, size) in enumerate(langs):
        cx, cy = x0 + (i % 2) * 196, 98 + (i // 2) * 26
        color = ACCENTS[i % len(ACCENTS)]
        out.append(f'<circle cx="{cx + 4}" cy="{cy - 4.5}" r="3.5" fill="{color}"/><circle cx="{cx + 4}" cy="{cy - 4.5}" r="7.5" fill="{color}" opacity="0.18"/>'
                   f'<text x="{cx + 18}" y="{cy}" font-family="{SANS}" font-size="13.5"><tspan fill="{TEXT}">{escape(name)}</tspan>'
                   f'<tspan fill="{MUTED}" dx="6">{100 * size / total:.1f}%</tspan></text>')
    return "".join(out)


def years(s, y0):
    data = list(s["years"].items())
    left, right, top, bottom = 32, 32, y0 + 54, y0 + YEARS_H - 40
    peak = max(c for _, c in data) or 1
    slot = (W - left - right) / len(data)
    bar = slot * 0.5
    this_year = str(dt.date.today().year)
    out = [label(left, y0 + 36, "Contributions per year"),
           f'<line x1="{left}" y1="{bottom + 0.5}" x2="{W - right}" y2="{bottom + 0.5}" stroke="{BORDER}"/>']
    for i, (year, count) in enumerate(data):
        h = max(2, (bottom - top - 18) * count / peak)
        x = left + i * slot + (slot - bar) / 2
        now = str(year) == this_year
        fill = "url(#beamNow)" if now else "url(#beam)"
        out.append(f'<rect x="{x:.1f}" y="{bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="4" fill="{fill}" opacity="0.55" filter="url(#glow)"/>')
        out.append(f'<rect x="{x:.1f}" y="{bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="4" fill="{fill}"/>')
        out.append(f'<text x="{x + bar / 2:.1f}" y="{bottom - h - 8:.1f}" fill="{NOTE if now else LABEL}" font-family="{SANS}" font-size="11.5" font-weight="600" text-anchor="middle">{count:,}</text>')
        out.append(f'<text x="{x + bar / 2:.1f}" y="{bottom + 20}" fill="{MUTED}" font-family="{MONO}" font-size="10.5" text-anchor="middle">{year}</text>')
    return "".join(out)


def divider(x1, y1, x2, y2, gid):
    # A rect, not a line: objectBoundingBox gradients don't paint on zero-width shapes.
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    return f'<rect x="{x1}" y="{y1}" width="{w}" height="{h}" fill="url(#{gid})"/>'


def dashboard(s, login):
    stops = "".join(f'<stop offset="{i / (len(AURA) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(AURA))
    fade = f'<stop offset="0" stop-color="{BORDER}" stop-opacity="0"/><stop offset="0.5" stop-color="{BORDER}"/><stop offset="1" stop-color="{BORDER}" stop-opacity="0"/>'
    updated = dt.datetime.now(dt.timezone.utc).strftime("%b %d, %Y · %H:%M UTC")
    title = f"{login}'s GitHub activity"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<defs>
<linearGradient id="aura" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>
<linearGradient id="glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GLASS}"/><stop offset="1" stop-color="{SPACE}"/></linearGradient>
<radialGradient id="nebulaA" cx="0.92" cy="0.02" r="0.7"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.2"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
<radialGradient id="nebulaB" cx="0.02" cy="0.98" r="0.65"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.12"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
<radialGradient id="nebulaC" cx="0.55" cy="0.5" r="0.5"><stop offset="0" stop-color="{BLUE}" stop-opacity="0.06"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
<linearGradient id="rim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="0.5" stop-color="{BLUE}" stop-opacity="0.7"/><stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></linearGradient>
<linearGradient id="fadeV" x1="0" y1="0" x2="0" y2="1">{fade}</linearGradient>
<linearGradient id="fadeH" x1="0" y1="0" x2="1" y2="0">{fade}</linearGradient>
<linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.35"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></linearGradient>
<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset="0.55" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
<linearGradient id="beamNow" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{ROSE}"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#glass)"/>
<rect width="{W}" height="{H}" fill="url(#nebulaA)"/><rect width="{W}" height="{H}" fill="url(#nebulaB)"/><rect width="{W}" height="{H}" fill="url(#nebulaC)"/>
{stars(W, H, seed=login)}
<rect x="60" y="0" width="{W - 120}" height="1.5" fill="url(#rim)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{BORDER}"/>
{divider(W // 2, 28, W // 2, ROW - 16, "fadeV")}
{divider(32, ROW, W - 32, ROW, "fadeH")}
{overview(s, 32)}
{languages(s, W // 2 + 28)}
{years(s, ROW)}
{divider(32, H - FOOT, W - 32, H - FOOT, "fadeH")}
<text x="32" y="{H - 15}" fill="{MUTED}" font-family="{MONO}" font-size="10.5" letter-spacing="1">AUTO-UPDATED · {escape(updated.upper())}</text>
<text x="{W - 32}" y="{H - 15}" fill="{MUTED}" font-family="{MONO}" font-size="10.5" letter-spacing="1" text-anchor="end">GITHUB.COM/{escape(login.upper())}</text>
</svg>
"""


def main():
    login, out = sys.argv[1], sys.argv[2]
    s = fetch(login)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "dashboard.svg"), "w") as f:
        f.write(dashboard(s, login))
    print(f"wrote dashboard: {sum(s['years'].values()):,} contributions, {len(s['langs'])} languages")


if __name__ == "__main__":
    main()
