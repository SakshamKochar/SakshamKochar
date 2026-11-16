#!/usr/bin/env python3
"""Draws every figure on this profile.

Standard library only. Run `python scripts/build.py` to regenerate assets/.
Static figures are deterministic (fixed seeds). The activity figure is drawn
from live contribution data when GITHUB_TOKEN is set, which is how the nightly
workflow keeps it current.
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

THEMES = {
    "dark": dict(
        bg="#07090d", panel="#0c1118", line="#1b2430", grid="#141b25",
        ink="#e6edf3", mute="#7d8796", faint="#3a4553",
        accent="#00e1ff", violet="#8b7bff", amber="#ffb454", green="#3ddc97", pink="#ff6b9a",
    ),
    "light": dict(
        bg="#ffffff", panel="#f6f8fa", line="#d5dbe3", grid="#e7ebf0",
        ink="#0d1117", mute="#57606a", faint="#b6bfca",
        accent="#0a7ea4", violet="#6b4bd8", amber="#b76e00", green="#1a7f4b", pink="#c2255c",
    ),
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def svg(w, h, t, css, body, label):
    base = Template("""
text{font-family:$sans;fill:$ink}
.m{font-family:$mono}
.cap{font-family:$mono;font-size:11px;fill:$mute;letter-spacing:.3px}
.dim{fill:$mute}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""").substitute(sans=SANS, mono=MONO, **t)
    css = Template(css).substitute(sans=SANS, mono=MONO, **t)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{esc(label)}">\n<title>{esc(label)}</title>\n'
        f"<style>{base}{css}</style>\n"
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["line"]}"/>\n'
        f"{body}\n</svg>\n"
    )


def smooth_path(pts):
    """Catmull-Rom spline through pts, as cubic beziers."""
    if len(pts) < 2:
        return ""
    d = [f"M{r(pts[0][0])},{r(pts[0][1])}"]
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{r(c1[0])},{r(c1[1])} {r(c2[0])},{r(c2[1])} {r(p2[0])},{r(p2[1])}")
    return "".join(d)


# ---------------------------------------------------------------- fig. 1 hero
def hero(t):
    W, H = 840, 320
    rng = random.Random(7)
    x0, x1, y0, y1 = 476, 800, 74, 236

    def f(u):
        return 0.14 + 0.68 / (1 + math.exp(-(u - 0.52) * 7.5)) + 0.05 * math.sin(u * 9.5)

    def X(u):
        return x0 + u * (x1 - x0)

    def Y(v):
        return y1 - v * (y1 - y0)

    b = []
    # grid and axes
    for i in range(5):
        y = y0 + i * (y1 - y0) / 4
        b.append(f'<line x1="{x0}" y1="{r(y)}" x2="{x1}" y2="{r(y)}" stroke="{t["grid"]}"/>')
    b.append(f'<path d="M{x0},{y0 - 6}V{y1}H{x1 + 6}" fill="none" stroke="{t["faint"]}"/>')
    # interval band
    us = [i / 60 for i in range(61)]
    top = [(X(u), Y(min(f(u) + 0.13, 1.04))) for u in us]
    bot = [(X(u), Y(max(f(u) - 0.13, 0))) for u in reversed(us)]
    band = "M" + "L".join(f"{r(x)},{r(y)}" for x, y in top + bot) + "Z"
    b.append(f'<path class="band" d="{band}" fill="{t["accent"]}" opacity=".09"/>')
    # observations
    for i in range(78):
        u = rng.random()
        out = i % 13 == 0
        v = f(u) + rng.gauss(0, 0.2 if out else 0.075)
        v = max(0.02, min(1.02, v))
        col = t["amber"] if out else t["mute"]
        b.append(
            f'<circle class="pt" cx="{r(X(u))}" cy="{r(Y(v))}" r="{2.6 if out else 2.1}" fill="{col}" '
            f'style="animation-delay:{u * 1.6:.2f}s"/>'
        )
    # fitted curve
    curve = "M" + "L".join(f"{r(X(u))},{r(Y(f(u)))}" for u in us)
    b.append(f'<path class="fit" pathLength="1" d="{curve}" fill="none" stroke="{t["accent"]}" stroke-width="2.6" stroke-linecap="round"/>')
    b.append(f'<circle class="now" cx="{r(X(1))}" cy="{r(Y(f(1)))}" r="4" fill="{t["accent"]}"/>')
    b.append(f'<circle class="ring" cx="{r(X(1))}" cy="{r(Y(f(1)))}" r="4" fill="none" stroke="{t["accent"]}"/>')
    # chart furniture
    b.append(f'<text class="cap" x="{x0}" y="54">fig. 1 · signal from noise</text>')
    lx, ly = x0, 264
    b.append(f'<circle cx="{lx + 4}" cy="{ly - 4}" r="2.4" fill="{t["mute"]}"/><text class="cap" x="{lx + 13}" y="{ly}">observed</text>')
    b.append(f'<circle cx="{lx + 88}" cy="{ly - 4}" r="2.6" fill="{t["amber"]}"/><text class="cap" x="{lx + 97}" y="{ly}">outlier</text>')
    b.append(f'<path d="M{lx + 160},{ly - 4}h16" stroke="{t["accent"]}" stroke-width="2.6" stroke-linecap="round"/><text class="cap" x="{lx + 183}" y="{ly}">fitted</text>')
    b.append(f'<rect x="{lx + 236}" y="{ly - 9}" width="16" height="10" rx="2" fill="{t["accent"]}" opacity=".2"/><text class="cap" x="{lx + 259}" y="{ly}">interval</text>')
    # words
    b.append(f'<text class="m" x="44" y="76" font-size="12" fill="{t["accent"]}">In [1]:<tspan fill="{t["mute"]}"> whoami</tspan></text>')
    b.append('<text x="42" y="138" font-size="47" font-weight="800" letter-spacing="-1.4">Saksham Kochar</text>')
    b.append(f'<text x="44" y="174" font-size="16.5" fill="{t["mute"]}">I find the signal in messy data,</text>')
    b.append(f'<text x="44" y="197" font-size="16.5" fill="{t["mute"]}">then build the tool that puts it to work.</text>')
    roles = [
        "Data Science Intern @ Blink Charging",
        "Academic Officer @ The AI Society at ASU",
        "B.S. Data Science, Arizona State, class of 2028",
        "Instructional Aide, ASU Math and Statistics",
    ]
    b.append(f'<rect x="44" y="230" width="3" height="20" rx="1.5" fill="{t["accent"]}"/>')
    for i, role in enumerate(roles):
        b.append(
            f'<text class="m role" x="58" y="245" font-size="13.5" opacity="{1 if i == 0 else 0}" '
            f'style="animation-delay:{i * 4}s">{esc(role)}</text>'
        )
    b.append(f'<text class="cap" x="44" y="286">Tempe, Arizona · open to data science and ML internships</text>')
    css = """
.pt{animation:pt 16s ease-in-out infinite}
@keyframes pt{0%{opacity:0}5%{opacity:1}90%{opacity:1}97%,100%{opacity:0}}
.fit{stroke-dasharray:1;animation:fit 16s ease-in-out infinite}
@keyframes fit{0%,12%{stroke-dashoffset:1;opacity:1}36%{stroke-dashoffset:0}90%{stroke-dashoffset:0;opacity:1}97%,100%{stroke-dashoffset:0;opacity:0}}
.band{animation:band 16s ease-in-out infinite}
@keyframes band{0%,30%{opacity:0}44%{opacity:.09}90%{opacity:.09}97%,100%{opacity:0}}
.now{animation:now 16s ease-in-out infinite}
@keyframes now{0%,34%{opacity:0}38%{opacity:1}90%{opacity:1}97%,100%{opacity:0}}
.ring{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 2s ease-out infinite}
@keyframes ring{0%{opacity:.7;transform:scale(1)}100%{opacity:0;transform:scale(3.4)}}
.role{animation:role 16s linear infinite}
@keyframes role{0%{opacity:0}2.5%{opacity:1}22.5%{opacity:1}25%,100%{opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b), "Saksham Kochar. Data scientist. A fitted curve emerging from noisy observations.")


# ------------------------------------------------------- project strips
SW, SH = 420, 132


def strip(t, caption, body, css, label):
    head = f'<text class="cap" x="18" y="24">{esc(caption)}</text>'
    return svg(SW, SH, t, css, head + "\n" + body, label)


def strip_blink(t):
    rng = random.Random(21)
    cats = [(t["green"], 0.62), (t["amber"], 0.14), (t["pink"], 0.09), (t["violet"], 0.09), (t["faint"], 0.06)]
    cols, rows, s, g = 29, 5, 10, 3.2
    b = []
    for c in range(cols):
        for rw in range(rows):
            x, y = 18 + c * (s + g), 36 + rw * (s + g)
            roll, acc, col = rng.random(), 0, cats[-1][0]
            for cc, p in cats:
                acc += p
                if roll < acc:
                    col = cc
                    break
            d = c * 0.11 + rng.random() * 0.25
            b.append(f'<rect x="{r(x)}" y="{r(y)}" width="{s}" height="{s}" rx="2.2" fill="{t["faint"]}"/>')
            b.append(f'<rect class="c" x="{r(x)}" y="{r(y)}" width="{s}" height="{s}" rx="2.2" fill="{col}" style="animation-delay:{d:.2f}s"/>')
    b.append(f'<rect class="scan" x="14" y="32" width="2" height="{rows * (s + g) + 4}" rx="1" fill="{t["accent"]}"/>')
    lx = 18
    for name, col in [("completed", t["green"]), ("no start", t["amber"]), ("fault", t["pink"]), ("interrupted", t["violet"])]:
        b.append(f'<rect x="{lx}" y="110" width="8" height="8" rx="2" fill="{col}"/><text class="cap" x="{lx + 13}" y="118" font-size="10">{name}</text>')
        lx += 22 + len(name) * 6.4
    css = """
.c{animation:c 11s ease infinite}
@keyframes c{0%{opacity:0}4%{opacity:1}88%{opacity:1}96%,100%{opacity:0}}
.scan{animation:scan 11s linear infinite}
@keyframes scan{0%{transform:translateX(0);opacity:1}30%{transform:translateX(388px);opacity:1}33%,100%{transform:translateX(388px);opacity:0}}
"""
    return strip(t, "fig. 2 · raw charger logs, classified (illustrative)", "\n".join(b), css,
                 "A grid of charging sessions being classified into categories")


def strip_recompute(t):
    routes = [("sell now", 0.62), ("list and wait", 0.7), ("rent while listed", 0.78), ("host longer", 0.93),
              ("repair", 0.55), ("harvest parts", 0.4), ("recycle", 0.16)]
    b = []
    for i, (name, v) in enumerate(routes):
        y = 37 + i * 13
        best = name == "host longer"
        col = t["accent"] if best else t["faint"]
        b.append(f'<text class="m" x="128" y="{y + 8}" font-size="10" text-anchor="end" fill="{t["ink"] if best else t["mute"]}">{name}</text>')
        b.append(f'<rect class="bar" x="138" y="{y}" width="{r(v * 210)}" height="9" rx="2.5" fill="{col}" style="animation-delay:{i * 0.12:.2f}s"/>')
        if best:
            b.append(f'<text class="m tag" x="{r(138 + v * 210 + 8)}" y="{y + 8}" font-size="10" fill="{t["accent"]}">best route</text>')
    css = """
.bar{transform-box:fill-box;transform-origin:left center;animation:bar 10s cubic-bezier(.2,.8,.2,1) infinite}
@keyframes bar{0%{transform:scaleX(0)}14%{transform:scaleX(1)}90%{transform:scaleX(1);opacity:1}97%,100%{transform:scaleX(1);opacity:0}}
.tag{animation:tag 10s ease infinite}
@keyframes tag{0%,18%{opacity:0}24%{opacity:1}90%{opacity:1}97%,100%{opacity:0}}
"""
    return strip(t, "fig. 3 · seven routes scored, one best call", "\n".join(b), css,
                 "Seven possible routes for a retired GPU server, scored as bars")


def strip_lifeops(t):
    b = []
    ax0, ax1, ay = 22, 398, 92
    hours = list(range(8, 21))

    def hx(h):
        return ax0 + (h - 8) / 12 * (ax1 - ax0)

    for h in hours:
        b.append(f'<line x1="{r(hx(h))}" y1="{ay - 40}" x2="{r(hx(h))}" y2="{ay + 3}" stroke="{t["grid"]}"/>')
        if h % 2 == 0:
            lab = f"{h if h <= 12 else h - 12}{'a' if h < 12 else 'p'}"
            b.append(f'<text class="cap" x="{r(hx(h))}" y="{ay + 18}" font-size="10" text-anchor="middle">{lab}</text>')
    b.append(f'<pattern id="h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="6" fill="{t["faint"]}"/></pattern>')
    for a, z in [(10, 11), (13, 14.5), (17, 17.5)]:
        b.append(f'<rect x="{r(hx(a))}" y="{ay - 36}" width="{r(hx(z) - hx(a))}" height="32" rx="4" fill="url(#h)" opacity=".7"/>')
    blocks = [(8, 10, t["accent"]), (11, 13, t["violet"]), (14.5, 17, t["green"]), (17.5, 19, t["amber"])]
    for i, (a, z, col) in enumerate(blocks):
        b.append(
            f'<rect class="blk" x="{r(hx(a) + 2)}" y="{ay - 36}" width="{r(hx(z) - hx(a) - 4)}" height="32" rx="4" fill="{col}" opacity=".9" '
            f'style="animation-delay:{0.5 + i * 0.55:.2f}s"/>'
        )
    css = """
.blk{transform-box:fill-box;transform-origin:center top;animation:blk 10s cubic-bezier(.2,.9,.3,1.2) infinite both}
@keyframes blk{0%{opacity:0;transform:translateY(-22px) scaleY(.6)}7%{opacity:.9;transform:none}84%{opacity:.9;transform:none}90%,100%{opacity:0;transform:none}}
"""
    return strip(t, "fig. 4 · focus blocks packed around meetings (striped)", "\n".join(b), css,
                 "A day timeline where focus blocks are scheduled around fixed meetings")


def strip_research(t):
    x0, x1, y0, y1 = 22, 318, 38, 100
    series = [
        ("burnout", t["accent"], [0.18, 0.2, 0.22, 0.25, 0.3, 0.36, 0.5, 0.58, 0.7, 0.84, 0.97], 2.6),
        ("ADHD", t["violet"], [0.3, 0.31, 0.33, 0.34, 0.37, 0.45, 0.6, 0.7, 0.72, 0.7, 0.74], 1.7),
        ("trauma", t["amber"], [0.36, 0.38, 0.4, 0.43, 0.46, 0.52, 0.55, 0.56, 0.55, 0.53, 0.54], 1.7),
        ("depression", t["mute"], [0.6, 0.6, 0.61, 0.6, 0.6, 0.64, 0.62, 0.6, 0.58, 0.57, 0.56], 1.7),
    ]
    b = []
    for i in range(3):
        y = y0 + i * (y1 - y0) / 2
        b.append(f'<line x1="{x0}" y1="{r(y)}" x2="{x1}" y2="{r(y)}" stroke="{t["grid"]}"/>')
    for yr, k in [(2015, 0), (2020, 5), (2025, 10)]:
        x = x0 + k / 10 * (x1 - x0)
        anchor = "start" if k == 0 else ("end" if k == 10 else "middle")
        b.append(f'<text class="cap" x="{r(x)}" y="{y1 + 18}" font-size="10" text-anchor="{anchor}">{yr}</text>')
    ends = []
    for i, (name, col, vals, sw) in enumerate(series):
        pts = [(x0 + k / 10 * (x1 - x0), y1 - v * (y1 - y0)) for k, v in enumerate(vals)]
        b.append(f'<path class="ln" pathLength="1" d="{smooth_path(pts)}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" style="animation-delay:{i * 0.3:.1f}s"/>')
        ends.append((pts[-1][1], name, col))
    ends.sort()
    ly = 40
    for y, name, col in ends:
        ly = max(ly, y + 3.5)
        b.append(f'<text class="m lab" x="{x1 + 9}" y="{r(ly)}" font-size="10" fill="{col}">{name}</text>')
        ly += 12
    css = """
.ln{stroke-dasharray:1;animation:ln 11s ease-in-out infinite both}
@keyframes ln{0%{stroke-dashoffset:1;opacity:1}24%{stroke-dashoffset:0}86%{stroke-dashoffset:0;opacity:1}93%,100%{stroke-dashoffset:0;opacity:0}}
.lab{animation:lab 11s ease infinite}
@keyframes lab{0%,22%{opacity:0}30%{opacity:1}86%{opacity:1}93%,100%{opacity:0}}
"""
    return strip(t, "fig. 5 · search interest by term (stylized)", "\n".join(b), css,
                 "Four trend lines from 2015 to 2025 with burnout rising fastest")


def strip_fairclaim(t):
    rng = random.Random(5)
    left = [(52 + rng.uniform(-14, 14), 42 + i * 13.5) for i in range(6)]
    right = [(368 + rng.uniform(-12, 12), 46 + i * 20) for i in range(4)]
    pairs = [(0, 0), (1, 1), (2, 0), (3, 2), (4, 3), (5, 2)]
    b = []
    for i, (a, z) in enumerate(pairs):
        (xa, ya), (xz, yz) = left[a], right[z]
        mx = (xa + xz) / 2
        b.append(
            f'<path class="lk" pathLength="1" d="M{r(xa)},{r(ya)}C{r(mx)},{r(ya)} {r(mx)},{r(yz)} {r(xz)},{r(yz)}" fill="none" '
            f'stroke="{t["accent"]}" stroke-width="1.4" opacity=".75" style="animation-delay:{0.3 + i * 0.35:.2f}s"/>'
        )
    for x, y in left:
        b.append(f'<circle cx="{r(x)}" cy="{r(y)}" r="4.2" fill="{t["bg"]}" stroke="{t["mute"]}" stroke-width="1.6"/>')
    for x, y in right:
        b.append(f'<rect x="{r(x - 5)}" y="{r(y - 5)}" width="10" height="10" rx="2.5" fill="{t["violet"]}"/>')
    b.append(f'<text class="cap" x="52" y="124" font-size="10" text-anchor="middle">workers</text>')
    b.append(f'<text class="cap" x="368" y="124" font-size="10" text-anchor="middle">lawyers</text>')
    css = """
.lk{stroke-dasharray:1;animation:lk 10s ease-in-out infinite both}
@keyframes lk{0%{stroke-dashoffset:1;opacity:.75}12%{stroke-dashoffset:0}84%{stroke-dashoffset:0;opacity:.75}92%,100%{stroke-dashoffset:0;opacity:0}}
"""
    return strip(t, "fig. 6 · workers matched to the right lawyer", "\n".join(b), css,
                 "Workers on the left being connected to lawyers on the right")


def strip_play(t):
    rng = random.Random(11)
    b = []
    for _ in range(46):
        x, y = rng.uniform(14, 406), rng.uniform(34, 122)
        b.append(f'<circle class="tw" cx="{r(x)}" cy="{r(y)}" r="{rng.choice([0.7, 0.9, 1.2])}" fill="{t["mute"]}" style="animation-delay:{rng.uniform(0, 4):.1f}s"/>')
    stars = [(70, 96), (118, 62), (166, 84), (214, 50), (262, 74), (300, 104), (352, 60)]
    d = "M" + "L".join(f"{x},{y}" for x, y in stars)
    b.append(f'<path class="con" pathLength="1" d="{d}" fill="none" stroke="{t["accent"]}" stroke-width="1.2" opacity=".8"/>')
    for i, (x, y) in enumerate(stars):
        col = t["amber"] if i == 3 else t["ink"]
        b.append(f'<circle cx="{x}" cy="{y}" r="{3.4 if i == 3 else 2.4}" fill="{col}"/>')
    css = """
.tw{animation:tw 4s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}
.con{stroke-dasharray:1;animation:con 12s ease-in-out infinite both}
@keyframes con{0%{stroke-dashoffset:1;opacity:.8}30%{stroke-dashoffset:0}86%{stroke-dashoffset:0;opacity:.8}94%,100%{stroke-dashoffset:0;opacity:0}}
"""
    return strip(t, "fig. 7 · side quests", "\n".join(b), css, "A constellation being traced across a night sky")


# ------------------------------------------------------------ fig. 8 pipeline
def pipeline(t):
    W, H = 840, 214
    stages = [
        ("01", "query", t["accent"], ["SQL", "PostgreSQL", "SQLite", "MySQL", "Parquet"]),
        ("02", "analyze", t["violet"], ["Python", "pandas", "NumPy", "time series", "NLP"]),
        ("03", "serve", t["green"], ["FastAPI", "SQLAlchemy", "REST", "Firebase", "Docker"]),
        ("04", "show", t["amber"], ["React", "TypeScript", "Power BI", "Three.js", "Figma"]),
    ]
    b = [f'<text class="cap" x="28" y="30">fig. 8 · the stack, in the order data moves through it</text>']
    bw, gap, x = 176, 26, 28
    cy = 76
    xs = []
    for i, (num, name, col, tools) in enumerate(stages):
        bx = x + i * (bw + gap)
        xs.append(bx)
        b.append(f'<rect x="{bx}" y="52" width="{bw}" height="48" rx="10" fill="{t["panel"]}" stroke="{t["line"]}"/>')
        b.append(f'<rect x="{bx}" y="52" width="4" height="48" rx="2" fill="{col}"/>')
        b.append(f'<text class="m" x="{bx + 18}" y="{cy - 3}" font-size="10.5" fill="{col}">{num}</text>')
        b.append(f'<text x="{bx + 18}" y="{cy + 15}" font-size="16" font-weight="700">{name}</text>')
        if i < len(stages) - 1:
            ax = bx + bw
            b.append(f'<path d="M{ax + 4},{cy}h{gap - 8}" stroke="{t["faint"]}" stroke-width="1.4" stroke-dasharray="2 4" stroke-linecap="round"/>')
            b.append(f'<circle class="dot" cx="{ax + 4}" cy="{cy}" r="2.6" fill="{col}" style="animation-delay:{i * 0.6:.1f}s"/>')
        for k, tool in enumerate(tools):
            ty = 124 + k * 17
            b.append(f'<circle cx="{bx + 7}" cy="{ty - 4}" r="1.8" fill="{col}"/>')
            b.append(f'<text class="m" x="{bx + 18}" y="{ty}" font-size="12" fill="{t["ink"]}">{esc(tool)}</text>')
    css = """
.dot{animation:dot 2.4s ease-in-out infinite}
@keyframes dot{0%{transform:translateX(0);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateX(18px);opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "Stack: query with SQL, PostgreSQL, SQLite, MySQL, Parquet. Analyze with Python, pandas, NumPy. "
               "Serve with FastAPI, SQLAlchemy, Firebase, Docker. Show with React, TypeScript, Power BI, Three.js, Figma.")


# ------------------------------------------------------------ fig. 9 activity
def fetch_calendar(login, token):
    q = ("query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{"
         "totalContributions weeks{contributionDays{date contributionCount}}}}}}")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"l": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-figures"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    return days


def activity(t, days):
    W, H = 840, 236
    b = [f'<text class="cap" x="28" y="30">fig. 9 · commit signal, last 12 months · redrawn nightly by scripts/build.py</text>']
    if not days:
        b.append(f'<path d="M40,150H800" stroke="{t["faint"]}" stroke-dasharray="3 6"/>')
        b.append(f'<text x="420" y="122" font-size="14" text-anchor="middle" fill="{t["mute"]}">Waiting for the first sync.</text>')
        b.append(f'<text class="cap" x="420" y="178" text-anchor="middle">This figure draws itself from live contribution data once the workflow has run.</text>')
        return svg(W, H, t, "", "\n".join(b), "Commit activity chart, waiting for first data sync")
    weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
    totals = [sum(c for _, c in w) for w in weeks]
    n = len(totals)
    roll = []
    for i in range(n):
        win = totals[max(0, i - 3):i + 1]
        roll.append(sum(win) / len(win))
    x0, x1, y0, y1 = 44, 540, 62, 180
    top = max(max(totals), 1)

    def X(i):
        return x0 + (i + 0.5) / n * (x1 - x0)

    def Y(v):
        return y1 - v / top * (y1 - y0)

    for i in range(3):
        y = y0 + i * (y1 - y0) / 2
        b.append(f'<line x1="{x0}" y1="{r(y)}" x2="{x1}" y2="{r(y)}" stroke="{t["grid"]}"/>')
    b.append(f'<text class="cap" x="{x0 - 6}" y="{y0 + 4}" font-size="10" text-anchor="end">{top}</text>')
    b.append(f'<text class="cap" x="{x0 - 6}" y="{y1 + 3}" font-size="10" text-anchor="end">0</text>')
    bw = max((x1 - x0) / n - 3, 2)
    for i, v in enumerate(totals):
        if v:
            b.append(f'<rect class="wk" x="{r(X(i) - bw / 2)}" y="{r(Y(v))}" width="{r(bw)}" height="{r(y1 - Y(v))}" rx="1.5" fill="{t["faint"]}" style="animation-delay:{i * 0.02:.2f}s"/>')
    pts = [(X(i), Y(v)) for i, v in enumerate(roll)]
    line = smooth_path(pts)
    b.append(f'<path d="{line}L{r(pts[-1][0])},{y1}L{r(pts[0][0])},{y1}Z" fill="{t["accent"]}" opacity=".08"/>')
    b.append(f'<path class="sig" pathLength="1" d="{line}" fill="none" stroke="{t["accent"]}" stroke-width="2.4" stroke-linecap="round"/>')
    b.append(f'<circle cx="{r(pts[-1][0])}" cy="{r(pts[-1][1])}" r="3.6" fill="{t["accent"]}"/>')
    last_month = None
    for i, w in enumerate(weeks):
        d = date.fromisoformat(w[0][0])
        if d.month != last_month and d.day <= 7 and i < n - 2:
            b.append(f'<text class="cap" x="{r(X(i))}" y="{y1 + 18}" font-size="10">{d.strftime("%b")}</text>')
        last_month = d.month
    lx = x0
    b.append(f'<rect x="{lx}" y="208" width="8" height="8" rx="2" fill="{t["faint"]}"/><text class="cap" x="{lx + 13}" y="216" font-size="10">weekly total</text>')
    b.append(f'<path d="M{lx + 104},212h16" stroke="{t["accent"]}" stroke-width="2.4" stroke-linecap="round"/><text class="cap" x="{lx + 127}" y="216" font-size="10">4-week rolling mean</text>')
    # right column: headline numbers and weekday profile
    total = sum(c for _, c in days)
    active = sum(1 for _, c in days if c)
    streak = best = 0
    for _, c in days:
        streak = streak + 1 if c else 0
        best = max(best, streak)
    rx = 584
    for k, (num, lab) in enumerate([(total, "total"), (active, "active days"), (best, "best streak")]):
        cx = rx + k * 82
        b.append(f'<text x="{cx}" y="80" font-size="24" font-weight="800">{num:,}</text>')
        b.append(f'<text class="cap" x="{cx}" y="96" font-size="9.5">{lab}</text>')
    wd = [0] * 7
    for ds, c in days:
        wd[date.fromisoformat(ds).weekday()] += c
    wtop = max(max(wd), 1)
    peak = wd.index(max(wd))
    for k, v in enumerate(wd):
        bx = rx + k * 31
        hgt = max(v / wtop * 58, 2)
        col = t["accent"] if k == peak else t["faint"]
        b.append(f'<rect x="{bx}" y="{r(180 - hgt)}" width="20" height="{r(hgt)}" rx="3" fill="{col}"/>')
        b.append(f'<text class="cap" x="{bx + 10}" y="198" font-size="10" text-anchor="middle">{"MTWTFSS"[k]}</text>')
    b.append(f'<text class="cap" x="{rx}" y="216" font-size="10">by weekday</text>')
    css = """
.sig{stroke-dasharray:1;animation:sig 14s ease-in-out infinite}
@keyframes sig{0%{stroke-dashoffset:1}22%{stroke-dashoffset:0}100%{stroke-dashoffset:0}}
.wk{transform-box:fill-box;transform-origin:center bottom;animation:wk 14s ease infinite}
@keyframes wk{0%{transform:scaleY(0)}8%{transform:scaleY(1)}100%{transform:scaleY(1)}}
"""
    return svg(W, H, t, css, "\n".join(b),
               f"Commit activity over the last 12 months: {total} contributions on {active} active days")


def main():
    OUT.mkdir(exist_ok=True)
    figs = {
        "hero": hero, "blink": strip_blink, "recompute": strip_recompute, "lifeops": strip_lifeops,
        "research": strip_research, "fairclaim": strip_fairclaim, "play": strip_play, "pipeline": pipeline,
    }
    for name, fn in figs.items():
        for mode, t in THEMES.items():
            (OUT / f"{name}-{mode}.svg").write_text(fn(t))

    days = None
    mock = os.environ.get("ACTIVITY_JSON")
    token, login = os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_LOGIN", "SakshamKochar")
    if mock:
        days = [tuple(d) for d in json.loads(Path(mock).read_text())]
    elif token:
        try:
            days = fetch_calendar(login, token)
        except Exception as e:  # keep the last good figure rather than break the profile
            print(f"activity fetch failed, keeping existing figure: {e}", file=sys.stderr)
    have = (OUT / "activity-dark.svg").exists()
    if days or not have:
        for mode, t in THEMES.items():
            (OUT / f"activity-{mode}.svg").write_text(activity(t, days))
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
