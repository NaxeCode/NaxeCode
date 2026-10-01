#!/usr/bin/env python3
"""Naxe brand kit: logo tiles + 1280x640 social cards in the Stella cosmic aesthetic."""
import os, random, subprocess, textwrap, html

OUT = os.environ.get("BRAND_OUT", os.path.join(os.path.dirname(__file__), "out"))
os.makedirs(OUT, exist_ok=True)

# Stella HUD glass + aura shader stops (Oklab -> sRGB).
SPACE, GLASS, GLASS_HI, BORDER = "#0b0e1a", "#171b28", "#1f2538", "#384155"
TEXT, LABEL, MUTED, NOTE, ICE = "#f1f3fc", "#bdd3ef", "#8b95ad", "#ffcba8", "#94dcf5"
CYAN, BLUE, VIOLET, ROSE, AMBER = "#22baf3", "#7c83ff", "#cb69f3", "#ff6592", "#fea334"
AURA = [CYAN, BLUE, VIOLET, ROSE, AMBER]
C = dict(grey=MUTED, grey2=LABEL, bg0="#10131f", bg3=BORDER, red=ROSE)
CAT = dict(systems=("SYSTEMS", CYAN), tools=("TOOLS", BLUE), games=("GAMES", VIOLET),
           web=("WEB", AMBER), home=("NAXE", None))
STATUS = dict(active=CYAN, wip=AMBER, prototype=VIOLET, archived=MUTED)
SW = 7  # glyph stroke width
FG = TEXT


def star4(cx, cy, r, col):
    k = r * 0.28
    return (f'<path d="M{cx} {cy-r} Q{cx+k} {cy-k} {cx+r} {cy} Q{cx+k} {cy+k} {cx} {cy+r} '
            f'Q{cx-k} {cy+k} {cx-r} {cy} Q{cx-k} {cy-k} {cx} {cy-r}Z" fill="{col}"/>')


def s(d, col, w=SW, extra=""):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def dot(x, y, r, col):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>'


def stars(w, h, n, seed, rmax=1.2, avoid=None):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        if avoid and any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in avoid):
            continue
        col = ICE if rng.random() < 0.18 else TEXT
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(0.35, rmax):.2f}" fill="{col}" opacity="{rng.uniform(0.15, 0.6):.2f}"/>')
    return "".join(out)


def aura_stops():
    return "".join(f'<stop offset="{i / (len(AURA) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(AURA))


GLYPHS = {
    "naxe": lambda a: s("M40 92V36", FG, 9) + s("M88 92V36", FG, 9) + s("M40 36L88 92", a, 9) + dot(98, 30, 5, a),
    "digest": lambda a: dot(40, 88, 7, a) + s("M40 64A24 24 0 0 1 64 88", a) + s("M40 42A46 46 0 0 1 86 88", a) + star4(90, 40, 12, FG),
    "watchlist": lambda a: s("M44 30H84V98L64 82L44 98Z", FG) + star4(64, 56, 13, a),
    "engine": lambda a: dot(64, 64, 15, FG) + s("M22 76C18 64 58 40 88 36C118 32 110 52 76 70C50 84 26 88 22 76Z", a, 6) + star4(98, 94, 9, a),
    "ground": lambda a: s("M24 64H44L54 40L68 88L78 56L86 64H104", a) + s("M32 98H96", FG, 6) + s("M48 98V92M64 98V92M80 98V92", FG, 5),
    "photon": lambda a: dot(32, 94, 4, C["grey"]) + dot(46, 82, 5, C["grey2"]) + dot(60, 70, 6, FG) + dot(76, 58, 7, FG)
        + dot(92, 42, 11, a) + s("M92 20V26M92 58V64M70 42H76M108 42H114", a, 5),
    "mux": lambda a: s("M28 38C52 38 52 64 76 64", FG) + s("M28 64H76", FG) + s("M28 90C52 90 52 64 76 64", FG) + s("M76 64H100", a, 9) + dot(100, 64, 8, a),
    "jp": lambda a: s("M34 76V66A30 30 0 0 1 94 66V76", FG) + f'<rect x="26" y="70" width="16" height="26" rx="6" fill="{a}"/>'
        + f'<rect x="86" y="70" width="16" height="26" rx="6" fill="{a}"/>' + s("M56 78V90M64 72V96M72 78V90", a, 5),
    "shell": lambda a: f'<rect x="24" y="30" width="80" height="22" rx="8" fill="none" stroke="{FG}" stroke-width="6"/>'
        + dot(38, 41, 4, a) + dot(52, 41, 4, C["grey"]) + s("M72 64A26 26 0 1 0 96 98A20 20 0 0 1 72 64Z", a, 6, 'fill="' + a + '"').replace('fill="none" ', ''),
    "dotfiles": lambda a: s("M36 46L56 64L36 82", a, 9) + s("M66 84H94", FG, 9),
    "windots": lambda a: f'<rect x="30" y="30" width="30" height="30" rx="5" fill="{a}"/><rect x="68" y="30" width="30" height="30" rx="5" fill="none" stroke="{FG}" stroke-width="5"/>'
        f'<rect x="30" y="68" width="30" height="30" rx="5" fill="none" stroke="{FG}" stroke-width="5"/><rect x="68" y="68" width="30" height="30" rx="5" fill="none" stroke="{FG}" stroke-width="5"/>',
    "keycap": lambda a: f'<rect x="28" y="34" width="72" height="64" rx="14" fill="none" stroke="{FG}" stroke-width="6"/>'
        f'<rect x="40" y="42" width="48" height="38" rx="8" fill="{a}"/>' + s("M64 50C58 58 56 62 56 66A8 8 0 0 0 72 66C72 62 70 58 64 50Z", C["bg0"], 3, f'fill="{C["bg0"]}"').replace('fill="none" ', ''),
    "minnen": lambda a: s("M28 58Q64 92 100 58", a) + s("M40 70L34 82M64 76V90M88 70L94 82", FG, 6) + star4(96, 30, 8, C["grey2"]) + dot(78, 26, 3, C["grey"]),
    "ahmar": lambda a: s("M64 26L96 64L64 102L32 64Z", a) + s("M40 96L88 32", FG, 6) + s("M80 36L92 28L86 42", FG, 5),
    "constellara": lambda a: s("M30 88L50 58L76 70L96 36", C["grey2"], 3) + s("M50 58L58 32", C["grey2"], 3)
        + dot(30, 88, 5, FG) + dot(50, 58, 5, FG) + dot(76, 70, 5, FG) + dot(58, 32, 4, FG) + star4(96, 36, 15, a),
    "persistence": lambda a: s("M36 28V100M56 28V100M76 28V100M96 28V100", C["bg3"], 4) + dot(36, 48, 7, a) + dot(56, 80, 7, FG) + dot(76, 60, 7, a) + dot(96, 90, 7, FG) + s("M28 100H104", FG, 5),
    "schoolapi": lambda a: s("M50 30C38 30 42 60 30 64C42 68 38 98 50 98", FG) + s("M78 30C90 30 86 60 98 64C86 68 90 98 78 98", FG) + dot(64, 64, 7, a),
    "moonlit": lambda a: f'<path d="M70 28A36 36 0 1 0 100 82A28 28 0 0 1 70 28Z" fill="{a}"/>' + star4(96, 36, 10, FG),
    "pomo": lambda a: s("M24 88H104", FG, 6) + f'<path d="M34 88A30 30 0 0 1 94 88Z" fill="{a}"/>' + s("M64 88V68M64 88L76 76", C["bg0"], 5) + s("M40 102H88", C["grey"], 5),
    "chat": lambda a: s("M28 38H80V74H50L36 86V74H28Z", FG, 6) + f'<path d="M58 60H100V92H92V104L78 92H58Z" fill="{a}"/>',
}


def inner(glyph, accent, uid):
    """Tile markup (128 box). accent None = aura gradient (personal mark)."""
    grad = accent is None
    paint = f"url(#{uid}aura)" if grad else accent
    neb = VIOLET if grad else accent
    g = GLYPHS[glyph](paint)
    return (
        f'<defs><linearGradient id="{uid}glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GLASS_HI}"/><stop offset="1" stop-color="{SPACE}"/></linearGradient>'
        f'<radialGradient id="{uid}neb" cx="0.85" cy="0.1" r="0.9"><stop offset="0" stop-color="{neb}" stop-opacity="0.38"/><stop offset="1" stop-color="{neb}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="{uid}neb2" cx="0.1" cy="1" r="0.8"><stop offset="0" stop-color="{CYAN if grad else BLUE}" stop-opacity="0.16"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="{uid}aura" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">{aura_stops()}</linearGradient>'
        f'<linearGradient id="{uid}rim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEXT}" stop-opacity="0"/><stop offset="0.5" stop-color="{TEXT}" stop-opacity="0.35"/><stop offset="1" stop-color="{TEXT}" stop-opacity="0"/></linearGradient>'
        f'<filter id="{uid}glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4"/></filter>'
        f'<clipPath id="{uid}clip"><rect x="3" y="3" width="122" height="122" rx="29"/></clipPath></defs>'
        f'<g clip-path="url(#{uid}clip)"><rect width="128" height="128" fill="url(#{uid}glass)"/>'
        f'<rect width="128" height="128" fill="url(#{uid}neb)"/><rect width="128" height="128" fill="url(#{uid}neb2)"/>'
        f'{stars(128, 128, 9, uid + glyph, 0.9)}<rect x="28" y="3" width="72" height="1.2" fill="url(#{uid}rim)"/></g>'
        f'<rect x="3" y="3" width="122" height="122" rx="29" fill="none" stroke="{BORDER}" stroke-width="2"/>'
        f'<g filter="url(#{uid}glow)" opacity="0.75">{g}</g>{g}'
    )


def tile(glyph, accent, size=128):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 128 128">'
            f'{inner(glyph, accent, "t")}</svg>')


def card(p):
    label, accent = CAT[p["cat"]]
    accent = p.get("accent", accent)
    lab_col = accent or LABEL
    neb = accent or VIOLET
    lines = textwrap.wrap(p["tagline"], 56)[:3]
    chips, x = [], 88
    for t in p["tech"]:
        w = int(len(t) * 14.2 + 40)
        chips.append(f'<rect x="{x}" y="452" width="{w}" height="46" rx="23" fill="{GLASS}" fill-opacity="0.8" stroke="{BORDER}" stroke-width="2"/>'
                     f'<text x="{x + w/2}" y="482" text-anchor="middle" font-family="Geist Mono" font-size="22" fill="{LABEL}">{html.escape(t)}</text>')
        x += w + 14
    status = p.get("status", "active")
    scol = STATUS[status]
    desc = "".join(f'<tspan x="88" dy="{0 if i == 0 else 52}">{html.escape(l)}</tspan>' for i, l in enumerate(lines))
    title_fill = "url(#titleAura)" if accent is None else TEXT
    pw = 52 + len(status) * 14
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640">
<defs>
 <linearGradient id="space" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GLASS}"/><stop offset="1" stop-color="{SPACE}"/></linearGradient>
 <radialGradient id="nebA" cx="0.92" cy="0.05" r="0.75"><stop offset="0" stop-color="{neb}" stop-opacity="0.34"/><stop offset="1" stop-color="{neb}" stop-opacity="0"/></radialGradient>
 <radialGradient id="nebB" cx="0.02" cy="1" r="0.7"><stop offset="0" stop-color="{BLUE}" stop-opacity="0.2"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
 <radialGradient id="nebC" cx="0.6" cy="1.1" r="0.5"><stop offset="0" stop-color="{ROSE}" stop-opacity="0.08"/><stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></radialGradient>
 <linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">{aura_stops()}</linearGradient>
 <linearGradient id="titleAura" x1="0" y1="0" x2="1" y2="0">{aura_stops()}</linearGradient>
</defs>
<rect width="1280" height="640" fill="url(#space)"/>
<rect width="1280" height="640" fill="url(#nebA)"/><rect width="1280" height="640" fill="url(#nebB)"/><rect width="1280" height="640" fill="url(#nebC)"/>
{stars(1280, 640, 140, p["repo"], 1.6, avoid=[(80, 80, 1200, 520)])}{stars(1280, 640, 18, p["repo"] + "x", 1.0)}
<rect x="0" y="0" width="1280" height="4" fill="url(#hair)"/>
<svg x="88" y="92" width="152" height="152" viewBox="0 0 128 128">{inner(p["glyph"], accent, "c")}</svg>
<text x="276" y="140" font-family="Geist" font-weight="600" font-size="22" letter-spacing="6" fill="{lab_col}">{label}</text>
<text x="272" y="222" font-family="Geist" font-weight="700" font-size="{p.get("fs", 80)}" fill="{title_fill}">{html.escape(p["title"])}</text>
<text y="324" font-family="Geist" font-size="36" fill="{LABEL}">{desc}</text>
{"".join(chips)}
<rect x="88" y="548" width="1104" height="1.5" fill="{BORDER}"/>
<svg x="88" y="568" width="44" height="44" viewBox="0 0 128 128">{inner("naxe", None, "f")}</svg>
<text x="148" y="598" font-family="Geist Mono" font-size="24" fill="{MUTED}">github.com/NaxeCode/<tspan fill="{TEXT}">{p["repo"]}</tspan></text>
<rect x="{1192 - pw}" y="570" width="{pw}" height="40" rx="20" fill="{scol}" fill-opacity="0.1" stroke="{scol}" stroke-opacity="0.7" stroke-width="2"/>
<circle cx="{1192 - pw + 22}" cy="590" r="6" fill="{scol}"/>
<text x="{1192 - pw + 36}" y="598" font-family="Geist Mono" font-size="22" fill="{scol}">{status}</text>
</svg>'''


PROJECTS = [
    dict(repo="NaxeCode", glyph="naxe", cat="home", title="Aladdin Ali · Naxe", fs=72, tagline="Backend & platform engineer. APIs, data pipelines and fintech integrations. Making games since 2015.", tech=["C#/.NET", "TypeScript", "Postgres", "Redis"]),
    dict(repo="NaxeCode.github.io", glyph="naxe", cat="home", title="naxecode.github.io", fs=72, tagline="Portfolio site: projects, experience and the journey from games to backend systems.", tech=["Next.js", "TypeScript", "Tailwind", "Zod"]),
    dict(repo="Cosmic-Digest", glyph="digest", cat="systems", title="Cosmic Digest", tagline="RSS-to-email digest job with circuit breaking, idempotent delivery and an encrypted outbox.", tech=[".NET", "C#", "GitHub Actions"]),
    dict(repo="pulse", glyph="ground", cat="systems", title="Ground", status="wip", tagline="Financial-analysis platform foundation with clean service boundaries between web, API and workers.", tech=["Next.js", "ASP.NET Core", "Python", "Redis", "TimescaleDB"]),
    dict(repo="Photon-Trail", glyph="photon", cat="systems", title="Photon Trail", status="wip", tagline="Personal-finance pipeline: Plaid cursor sync into Postgres, AI categorization with confidence scores.", tech=["Next.js", "Plaid", "Postgres", "Drizzle"]),
    dict(repo="Cosmic-Watchlist", glyph="watchlist", cat="systems", title="Cosmic Watchlist", tagline="Server-first watchlist for anime, film, TV, games and books, with metadata enrichment and stats.", tech=["Next.js", "React", "Postgres", "Drizzle", "Auth.js"]),
    dict(repo="activitymux", glyph="mux", cat="tools", title="ActivityMux", tagline="Discord Rich Presence router for Windows and Linux: presets, process rules, manual pin.", tech=["Rust", "Tauri", "Discord RPC"]),
    dict(repo="jp-assist", glyph="jp", cat="tools", title="jp-assist", tagline="Real-time Japanese helpers for voice calls, running whisper.cpp and llama.cpp locally.", tech=["Python", "whisper.cpp", "llama.cpp", "ROCm"]),
    dict(repo="caelestia-shell-naxecode", glyph="shell", cat="tools", title="caelestia-shell · OLED", fs=68, tagline="Arch PKGBUILD for a caelestia-shell fork with an OLED blackout mode.", tech=["Quickshell", "QML", "Hyprland", "Arch"]),
    dict(repo="dotfiles", glyph="dotfiles", cat="tools", title="dotfiles", tagline="Arch + Hyprland setup with Everforest themes that switch at sunrise and sunset.", tech=["Hyprland", "Nushell", "Ghostty", "chezmoi"]),
    dict(repo="rainy75-linux-tools", glyph="keycap", cat="tools", title="rainy75-linux-tools", fs=68, tagline="Configure and test a WOBKEY Rainy 75 keyboard on Linux over VIA HID.", tech=["Python", "hidapi", "VIA"]),
    dict(repo="Minnen", glyph="minnen", cat="games", status="wip", title="Minnen", tagline="A psychological game about night terrors, set on a curved rolling-log world.", tech=["Haxe", "HaxeFlixel"]),
    dict(repo="Ahmar", glyph="ahmar", cat="games", accent=C["red"], status="prototype", title="Ahmar", tagline="Top-down action combat in the spirit of Hyper Light Drifter: dash, attack, stamina.", tech=["Haxe", "HaxeFlixel"]),
    dict(repo="CosmicEngine", glyph="engine", cat="games", title="CosmicEngine", tagline="A small 2D engine layer on MonoGame: pixel-perfect renderer, scenes and input actions.", tech=["C#", ".NET 10", "MonoGame"]),
    dict(repo="Constellara", glyph="constellara", cat="games", status="prototype", title="Constellara", tagline="3D platformer prototype: third-person camera, star shard collection and checkpoints.", tech=["Godot 4", "GDScript"]),
    dict(repo="Persistence", glyph="persistence", cat="games", status="archived", title="Persistence", tagline="Top-down exploration with four-lane rhythm battles.", tech=["Haxe", "HaxeFlixel"]),
    dict(repo="SchoolApi", glyph="schoolapi", cat="systems", status="archived", title="SchoolApi", tagline="Early ASP.NET Core Web API exercise with EF Core and SQLite.", tech=["ASP.NET Core", "EF Core", "SQLite"]),
    dict(repo="windows-dotfiles", glyph="windots", cat="tools", status="archived", title="windows-dotfiles", tagline="Windows 11 terminal config: Nushell, Starship, Yazi, PowerShell and WSL scripts.", tech=["Nushell", "PowerShell", "WSL"]),
    dict(repo="Moonlit", glyph="moonlit", cat="web", status="archived", title="Moonlit", tagline="Early prototype for a creator-subscription site.", tech=["Gatsby", "React", "Firebase"]),
    dict(repo="Sunset-Pomo-Orange-Timer", glyph="pomo", cat="web", status="archived", title="Sunset Pomo", tagline="A warm, minimal Pomodoro timer web app.", tech=["React", "Netlify"]),
    dict(repo="NaxeChat", glyph="chat", cat="web", status="archived", title="NaxeChat", tagline="React Native chat app with Firebase auth and realtime messaging.", tech=["React Native", "Expo", "Firebase"]),
]

if __name__ == "__main__":
    for p in PROJECTS:
        d = os.path.join(OUT, p["repo"]); os.makedirs(d, exist_ok=True)
        acc = p.get("accent", CAT[p["cat"]][1])
        open(f"{d}/logo.svg", "w").write(tile(p["glyph"], acc))
        open(f"{d}/social-preview.svg", "w").write(card(p))
        subprocess.run(["resvg", "-w", "1280", f"{d}/social-preview.svg", f"{d}/social-preview.png"], check=True)
        subprocess.run(["resvg", "-w", "512", f"{d}/logo.svg", f"{d}/logo.png"], check=True)
    print("ok", len(PROJECTS))
