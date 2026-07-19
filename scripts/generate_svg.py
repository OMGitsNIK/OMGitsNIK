#!/usr/bin/env python3
"""
Generates assets/terminal.svg — a self-contained terminal-style profile card.

Live stats (commits, stars, repos, followers, top languages, visitors) are
BAKED INTO the SVG at build time. Run it in a GitHub Action on a schedule so
the SVG stays fresh — GitHub renders <img>-embedded SVGs in a sandbox that
blocks live network calls, so the data has to be baked in, not fetched at
view time.

Usage:
  GH_USER=OMGitsNIK GITHUB_TOKEN=xxxx python scripts/generate_svg.py
Without a token it renders a clean "syncing…" placeholder for the numbers.
"""
import os, json, re, datetime, urllib.request, urllib.error

USER  = os.environ.get("GH_USER", "OMGitsNIK")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
OUT   = os.environ.get("OUT_PATH", "assets/terminal.svg")

# ── palette ──
C = dict(prompt="#7c3aed", cmd="#e2e8f0", out="#94a3b8",
         cyan="#00f5d4", pink="#f0abfc", green="#14f195", dim="#5b7089")
LANG_FALLBACK = {"Python":"#3572A5","JavaScript":"#f1e05a","TypeScript":"#3178c6",
    "Rust":"#dea584","Solidity":"#AA6746","Java":"#b07219","C++":"#f34b7d",
    "HTML":"#e34c26","CSS":"#563d7c","Jupyter Notebook":"#DA5B0B","Shell":"#89e051"}

def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ─────────────────────────── DATA ───────────────────────────
GQL = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    repositories(first:100, ownerAffiliations:OWNER, isFork:false,
                 orderBy:{field:STARGAZERS,direction:DESC}){
      totalCount
      nodes{ stargazerCount
        languages(first:8, orderBy:{field:SIZE,direction:DESC}){
          edges{ size node{ name color } } } }
    }
    contributionsCollection{ totalCommitContributions restrictedContributionsCount }
    pullRequests{ totalCount }
  }
}"""

def fetch_stats():
    """Return dict of live stats, or None on any failure (→ placeholder mode)."""
    if not TOKEN:
        return None
    try:
        body = json.dumps({"query": GQL, "variables": {"login": USER}}).encode()
        req = urllib.request.Request("https://api.github.com/graphql", data=body,
              headers={"Authorization": f"bearer {TOKEN}",
                       "User-Agent": "readme-gen", "Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        u = d["data"]["user"]
        repos = u["repositories"]["nodes"]
        stars = sum(r["stargazerCount"] for r in repos)
        cc = u["contributionsCollection"]
        commits = cc["totalCommitContributions"] + cc.get("restrictedContributionsCount", 0)
        lang_sz = {}
        lang_col = {}
        for r in repos:
            for e in r["languages"]["edges"]:
                n = e["node"]["name"]
                lang_sz[n] = lang_sz.get(n, 0) + e["size"]
                lang_col[n] = e["node"]["color"] or LANG_FALLBACK.get(n, "#00f5d4")
        total = sum(lang_sz.values()) or 1
        top = sorted(lang_sz.items(), key=lambda k: -k[1])[:5]
        langs = [(n, round(sz*100/total), lang_col.get(n, "#00f5d4")) for n, sz in top]
        return dict(commits=commits, stars=stars,
                    repos=u["repositories"]["totalCount"],
                    followers=u["followers"]["totalCount"],
                    prs=u["pullRequests"]["totalCount"], langs=langs)
    except Exception as e:
        print("stats fetch failed:", e)
        return None

def fetch_visitors():
    """Best-effort: read komarev's count out of its badge SVG."""
    try:
        req = urllib.request.Request(
            f"https://komarev.com/ghpvc/?username={USER}&base=0",
            headers={"User-Agent": "readme-gen"})
        svg = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        nums = re.findall(r">\s*([\d,]+)\s*<", svg)
        nums = [n for n in nums if re.fullmatch(r"[\d,]+", n)]
        return nums[-1] if nums else None
    except Exception as e:
        print("visitors fetch failed:", e)
        return None

# ─────────────────────────── RENDER ───────────────────────────
CMD_F, OUT_F = 17, 15.5
PITCH, GAP   = 24, 13
X, COL2      = 44, 560

def render(stats, visitors):
    S = lambda k: f"{stats[k]:,}" if stats else "—"
    # stats block
    if stats:
        stat_line = (f'<tspan fill="{C["dim"]}">commits·yr</tspan> <tspan fill="{C["cyan"]}">{S("commits")}</tspan>'
                     f'<tspan dx="18" fill="{C["dim"]}">stars</tspan> <tspan fill="{C["cyan"]}">★ {S("stars")}</tspan>'
                     f'<tspan dx="18" fill="{C["dim"]}">repos</tspan> <tspan fill="{C["cyan"]}">{S("repos")}</tspan>'
                     f'<tspan dx="18" fill="{C["dim"]}">followers</tspan> <tspan fill="{C["cyan"]}">{S("followers")}</tspan>')
        bar = ""
        for n, pct, col in stats["langs"]:
            blocks = "\u2588" * max(1, round(pct/9))
            bar += (f'<tspan fill="{col}"> {blocks}</tspan>'
                    f'<tspan fill="{C["out"]}"> {esc(n)} </tspan>'
                    f'<tspan fill="{C["dim"]}">{pct}%</tspan>')
        stats_block = [("out", stat_line), ("out", bar.strip())]
    else:
        stats_block = [("out", f'<tspan fill="{C["dim"]}">fetching live stats… auto-syncs via GitHub Actions</tspan>')]

    vis = visitors if visitors else "—"
    synced = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC") if stats else "pending first run"
    footer = (f'<tspan fill="{C["green"]}">◉</tspan> <tspan fill="{C["dim"]}">session: </tspan><tspan fill="{C["green"]}">live</tspan>'
              f'<tspan dx="14" fill="{C["dim"]}">·</tspan><tspan dx="14" fill="{C["dim"]}">visitors </tspan><tspan fill="{C["cyan"]}">{vis}</tspan>'
              f'<tspan dx="14" fill="{C["dim"]}">·</tspan><tspan dx="14" fill="{C["dim"]}">synced {synced}</tspan>')

    session = [
      ("cmd","whoami"),
      ("out",f'<tspan fill="{C["cyan"]}">nikhil rao</tspan> <tspan fill="{C["dim"]}">—</tspan> blockchain <tspan fill="{C["dim"]}">·</tspan> ai/ml <tspan fill="{C["dim"]}">·</tspan> full-stack engineer'),
      ("gap",),
      ("cmd","cat bio.txt"),
      ("out",f'On-chain engineer. Flagship: <tspan fill="{C["pink"]}">MYRMEX</tspan> — parametric insurance on'),
      ("out",f'Solana (Rust + Anchor). <tspan fill="{C["cyan"]}">YOLOv9 @ 92%</tspan> for marine research @ NIO.'),
      ("gap",),
      ("cmd","cat experience.log"),
      ("out",f'<tspan fill="{C["cyan"]}">[now] </tspan>Associate Engineer <tspan fill="{C["dim"]}">·</tspan> OneShield — P&amp;C SaaS <tspan fill="{C["dim"]}">·</tspan> PL/SQL <tspan fill="{C["dim"]}">·</tspan> +30% perf'),
      ("out",f'<tspan fill="{C["cyan"]}">[2024]</tspan> SWE Intern <tspan fill="{C["dim"]}">·</tspan> OneShield — policy module <tspan fill="{C["dim"]}">·</tspan> 30+ auto tests'),
      ("out",f'<tspan fill="{C["cyan"]}">[2023]</tspan> ML <tspan fill="{C["dim"]}">·</tspan> Nat\u2019l Institute of Oceanography — YOLOv9 <tspan fill="{C["dim"]}">·</tspan> 5k+ imgs'),
      ("gap",),
      ("cmd","cat education.txt"),
      ("out",f'B.E. Computer Engineering <tspan fill="{C["dim"]}">·</tspan> Honours AI/ML <tspan fill="{C["dim"]}">·</tspan> Don Bosco <tspan fill="{C["dim"]}">·</tspan> <tspan fill="{C["cyan"]}">CGPA 8.82</tspan>'),
      ("gap",),
      ("cmd","ls ~/stack"),
      ("out",f'<tspan fill="{C["cyan"]}">solana  anchor  rust  python  pytorch  next.js  fastapi  pl/sql</tspan>'),
      ("gap",),
      ("cmd","./status --now"),
      ("status","OPEN TO OPPORTUNITIES","Margao, Goa · IN"),
      ("gap",),
      ("cmd","gh --stats"),
      *stats_block,
      ("gap",),
      ("cmd","contact --list"),
      ("out",f'mail  <tspan fill="{C["cyan"]}">raonik1003@gmail.com</tspan><tspan x="{COL2}">gh</tspan>  <tspan fill="{C["cyan"]}">github.com/OMGitsNIK</tspan>'),
      ("out",f'in    <tspan fill="{C["cyan"]}">/in/nikhil-rao</tspan><tspan x="{COL2}">x</tspan>   <tspan fill="{C["cyan"]}">@AlphaQ12345</tspan>'),
      ("gap",),
      ("foot",footer),
      ("caret",),
    ]

    y = 76; parts = []
    for e in session:
        k = e[0]
        if k == "gap": y += GAP; continue
        if k == "cmd":
            parts.append(f'<text x="{X}" y="{y}" font-size="{CMD_F}" fill="{C["prompt"]}">❯<tspan dx="12" fill="{C["cmd"]}">{esc(e[1])}</tspan></text>'); y += PITCH
        elif k == "out":
            parts.append(f'<text x="{X}" y="{y}" font-size="{OUT_F}" fill="{C["out"]}">{e[1]}</text>'); y += PITCH
        elif k == "foot":
            parts.append(f'<text x="{X}" y="{y}" font-size="13" letter-spacing="0.5">{e[1]}</text>'); y += PITCH
        elif k == "status":
            parts.append(f'<circle class="pd" cx="{X+8}" cy="{y-5}" r="6" fill="{C["green"]}"/>'
                         f'<text x="{X+24}" y="{y}" font-size="{OUT_F}" fill="{C["green"]}">{esc(e[1])} <tspan fill="{C["dim"]}">·</tspan> <tspan fill="{C["out"]}">{esc(e[2])}</tspan></text>'); y += PITCH
        elif k == "caret":
            parts.append(f'<text x="{X}" y="{y}" font-size="{CMD_F}" fill="{C["prompt"]}">❯</text>'
                         f'<rect class="caret" x="{X+22}" y="{y-15}" width="11" height="18" fill="{C["cyan"]}"/>'); y += PITCH

    WIN_H = y + 16; VB_H = WIN_H + 16
    body = "\n    ".join(parts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {VB_H}" width="1200" height="{VB_H}" fill="none" font-family="'JetBrains Mono','Fira Code','Courier New',monospace" role="img" aria-label="Nikhil Rao — terminal profile">
  <defs>
    <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0e1626"/><stop offset="100%" stop-color="#0a111e"/></linearGradient>
    <radialGradient id="scrn" cx="50%" cy="26%" r="88%"><stop offset="0%" stop-color="#0b1220"/><stop offset="100%" stop-color="#070c16"/></radialGradient>
    <clipPath id="win"><rect x="8" y="8" width="1184" height="{WIN_H-8}" rx="12"/></clipPath>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#00f5d4" stroke-opacity="0.03"/></pattern>
    <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="#000" opacity="0.16"/></pattern>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00f5d4" stop-opacity="0"/><stop offset="50%" stop-color="#00f5d4" stop-opacity="0.05"/><stop offset="100%" stop-color="#00f5d4" stop-opacity="0"/></linearGradient>
    <style>
      @keyframes blink {{ 0%,49%{{opacity:1}} 50%,100%{{opacity:0}} }}
      @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.35}} }}
      @keyframes beam  {{ 0%{{transform:translateY(-60px)}} 100%{{transform:translateY({WIN_H}px)}} }}
      @keyframes flick {{ 0%,100%{{opacity:.14}} 96%{{opacity:.14}} 97%{{opacity:.22}} 98%{{opacity:.14}} }}
      .caret {{ animation:blink 1.1s step-end infinite; }}
      .pd    {{ animation:pulse 1.6s ease-in-out infinite; }}
      .beam  {{ animation:beam 5.5s linear infinite; }}
      .scan  {{ animation:flick 7s linear infinite; }}
    </style>
  </defs>
  <rect x="8" y="8" width="1184" height="{WIN_H-8}" rx="12" fill="url(#scrn)"/>
  <g clip-path="url(#win)">
    <rect x="8" y="8" width="1184" height="{WIN_H-8}" fill="url(#grid)"/>
    <rect x="8" y="8" width="1184" height="42" fill="url(#bar)"/>
    <line x1="8" y1="50" x2="1192" y2="50" stroke="#00f5d4" stroke-opacity="0.16"/>
    <circle cx="34" cy="29" r="6" fill="#ff5f57" opacity="0.92"/>
    <circle cx="56" cy="29" r="6" fill="#febc2e" opacity="0.92"/>
    <circle cx="78" cy="29" r="6" fill="#28c840" opacity="0.92"/>
    <text x="600" y="34" text-anchor="middle" font-size="14" letter-spacing="1" fill="#5b7089">nikhil@rao — ~/whoami — zsh</text>
    <text x="1168" y="34" text-anchor="end" font-size="12.5" letter-spacing="1" fill="#334155">◉ session: <tspan class="pd" fill="#14f195">live</tspan></text>
    <rect class="beam" x="8" y="0" width="1184" height="60" fill="url(#beam)"/>
    {body}
    <rect class="scan" x="8" y="8" width="1184" height="{WIN_H-8}" fill="url(#scan)"/>
  </g>
  <rect x="8" y="8" width="1184" height="{WIN_H-8}" rx="12" fill="none" stroke="#00f5d4" stroke-opacity="0.28"/>
</svg>
'''

if __name__ == "__main__":
    stats = fetch_stats()
    visitors = fetch_visitors()
    svg = render(stats, visitors)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT}  ·  stats={'live' if stats else 'placeholder'}  ·  visitors={visitors}")