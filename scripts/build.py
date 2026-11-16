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
import re
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


def svg(w, h, t, css, body, label, frame=True):
    base = Template("""
text{font-family:$sans}
.m{font-family:$mono}
.cap{font-family:$mono;font-size:11px;letter-spacing:.3px}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""").substitute(sans=SANS, mono=MONO, **t)
    css = Template(css).substitute(sans=SANS, mono=MONO, **t)
    # Colours are attributes, not CSS, so a per-element fill always wins over the default.
    body = re.sub(r'<text class="cap"(?![^>]* fill=)', f'<text class="cap" fill="{t["mute"]}"', body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'fill="{t["ink"]}" role="img" aria-label="{esc(label)}">\n<title>{esc(label)}</title>\n'
        f"<style>{base}{css}</style>\n"
        + (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["line"]}"/>\n' if frame else "")
        + f"{body}\n</svg>\n"
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
        "3rd place, ASU Reverse the Future 2026",
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
.role{animation:role 20s linear infinite}
@keyframes role{0%{opacity:0}2%{opacity:1}18%{opacity:1}20%,100%{opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b), "Saksham Kochar. Data scientist. A fitted curve emerging from noisy observations.")


# ------------------------------------------------------- project strips
SW, SH = 420, 132


def strip(t, caption, body, css, label):
    head = f'<text class="cap" x="18" y="24">{esc(caption)}</text>'
    return svg(SW, SH, t, css, head + "\n" + body, label)


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
    return strip(t, "fig. 6 · focus blocks packed around meetings (striped)", "\n".join(b), css,
                 "A day timeline where focus blocks are scheduled around fixed meetings")


def strip_research(t):
    x0, x1, y0, y1 = 22, 318, 38, 100
    series = [
        ("depression", t["mute"], [0.84, 0.85, 0.86, 0.85, 0.86, 0.9, 0.88, 0.87, 0.83, 0.8, 0.78], 1.7),
        ("ADHD", t["accent"], [0.2, 0.21, 0.23, 0.25, 0.28, 0.36, 0.5, 0.6, 0.6, 0.61, 0.63], 2.6),
        ("trauma", t["violet"], [0.16, 0.17, 0.19, 0.22, 0.25, 0.31, 0.4, 0.46, 0.47, 0.48, 0.5], 2.0),
        ("burnout", t["amber"], [0.04, 0.04, 0.05, 0.06, 0.09, 0.08, 0.14, 0.12, 0.19, 0.16, 0.24], 1.7),
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
    return strip(t, "fig. 7 · search interest by term (stylized)", "\n".join(b), css,
                 "Four search interest trend lines from 2015 to 2025: depression highest throughout, ADHD and trauma roughly tripling, burnout rising from a low base")


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
    return strip(t, "fig. 8 · workers matched to the right lawyer", "\n".join(b), css,
                 "Workers on the left being connected to lawyers on the right")


def strip_play(t):
    rng = random.Random(11)
    pts = [(55, 98), (38, 88), (26, 76), (18, 64), (12, 54), (42, 58), (38, 40), (36, 28), (34, 18),
           (54, 54), (54, 34), (54, 21), (54, 10), (66, 57), (69, 39), (71, 27), (72, 17),
           (77, 64), (83, 50), (87, 41), (90, 33)]
    ox, oy, sc = 34, 30, 0.92
    P = [(ox + x * sc, oy + y * sc) for x, y in pts]
    bones = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
             (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]
    b = ['<g class="hand">']
    for i, j in bones:
        b.append(f'<line x1="{r(P[i][0])}" y1="{r(P[i][1])}" x2="{r(P[j][0])}" y2="{r(P[j][1])}" stroke="{t["faint"]}" stroke-width="1.6" stroke-linecap="round"/>')
    for k, (x, y) in enumerate(P):
        tip = k in (4, 8, 12, 16, 20)
        b.append(f'<circle cx="{r(x)}" cy="{r(y)}" r="{3 if tip else 2.1}" fill="{t["accent"] if tip else t["mute"]}"/>')
        if tip:
            b.append(f'<circle class="tip" cx="{r(x)}" cy="{r(y)}" r="3" fill="none" stroke="{t["accent"]}" style="animation-delay:{k * 0.06:.2f}s"/>')
    b.append("</g>")
    b.append(f'<path d="M146,78h22" stroke="{t["faint"]}" stroke-width="1.4" stroke-dasharray="2 4" stroke-linecap="round"/>')
    b.append(f'<circle class="go" cx="146" cy="78" r="2.4" fill="{t["accent"]}"/>')
    cols = [t["accent"], t["violet"], t["pink"], t["amber"]]
    for i in range(24):
        x = 184 + i * 9.2
        h = 14 + 52 * abs(math.sin(i * 0.55 + 0.6)) * rng.uniform(0.55, 1)
        b.append(f'<rect class="eq" x="{r(x)}" y="{r(78 - h / 2)}" width="5.4" height="{r(h)}" rx="2.7" fill="{cols[i * 4 // 24]}" '
                 f'style="animation-delay:-{rng.uniform(0, 1.4):.2f}s;animation-duration:{rng.uniform(0.7, 1.3):.2f}s"/>')
    css = """
.hand{transform-box:fill-box;transform-origin:50% 90%;animation:hand 4s ease-in-out infinite}
@keyframes hand{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(5deg)}}
.tip{opacity:0;transform-box:fill-box;transform-origin:center;animation:tip 2s ease-out infinite}
@keyframes tip{0%{opacity:.8;transform:scale(1)}100%{opacity:0;transform:scale(3)}}
.eq{transform-box:fill-box;transform-origin:center;animation:eq 1s ease-in-out infinite alternate}
@keyframes eq{0%{transform:scaleY(.35)}100%{transform:scaleY(1)}}
.go{animation:go 1.8s ease-in-out infinite}
@keyframes go{0%{transform:translateX(0);opacity:0}20%{opacity:1}80%{opacity:1}100%{transform:translateX(22px);opacity:0}}
"""
    return strip(t, "fig. 9 · hand landmarks in, sound out", "\n".join(b), css,
                 "A tracked hand skeleton with 21 landmarks driving an audio equalizer")


# ------------------------------------------------------------- highlights
def highlights(t):
    W, H = 840, 104
    tiles = [
        ("3rd", t["amber"], "Reverse the Future, ASU", "$3,000 prize, ReCompute"),
        ("9M", t["accent"], "Reddit posts analyzed", "sole-author study"),
        ("3.86", t["green"], "GPA at Arizona State", "Dean's List, every term"),
        ("2", t["violet"], "internships so far:", "Blink Charging, Saxo Bank"),
    ]
    b = []
    tw, gap = 201, 12
    for i, (big, col, l1, l2) in enumerate(tiles):
        x = i * (tw + gap)
        b.append(f'<g class="tile" style="animation-delay:{i * 0.18:.2f}s">')
        b.append(f'<rect x="{x + .5}" y=".5" width="{tw - 1}" height="{H - 1}" rx="12" fill="{t["bg"]}" stroke="{t["line"]}"/>')
        b.append(f'<text x="{x + 18}" y="46" font-size="32" font-weight="800" letter-spacing="-1" fill="{col}">{big}</text>')
        b.append(f'<text class="cap" x="{x + 18}" y="68" font-size="10.5" fill="{t["ink"]}">{esc(l1)}</text>')
        b.append(f'<text class="cap" x="{x + 18}" y="84" font-size="10.5">{esc(l2)}</text>')
        b.append(f'<rect class="glow" x="{x + 18}" y="96" width="{tw - 36}" height="2" rx="1" fill="{col}" style="animation-delay:{i * 0.5:.1f}s"/>')
        b.append("</g>")
    css = """
.tile{animation:tile 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes tile{0%{opacity:0;transform:translateY(8px)}100%{opacity:1;transform:none}}
.glow{transform-box:fill-box;transform-origin:left center;animation:glow 6s ease-in-out infinite}
@keyframes glow{0%{transform:scaleX(0);opacity:.9}45%{transform:scaleX(1);opacity:.9}80%,100%{transform:scaleX(1);opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "Highlights: 3rd place at ASU Reverse the Future with a $3,000 prize, 9 million Reddit posts analyzed, "
               "3.86 GPA, two internships", frame=False)


# ------------------------------------------------------- fig. 2 training log
def training_log(t):
    W, H = 840, 300
    rng = random.Random(4)
    x0, x1, y0, y1 = 58, 486, 66, 246
    cps = [
        (4, 0.22, "Saxo Bank", "Product Development Intern · May 2025", t["violet"]),
        (6, 0.14, "Research assistant, ASU", "and joined The AI Society · Jul 2025", t["green"]),
        (16, 0.26, "Blink Charging", "Data Science Intern · May 2026", t["accent"]),
        (19, 0.10, "Academic Officer, AI Society", "and Instructional Aide · Fall 2026", t["pink"]),
        (22, 0.13, "ReCompute takes 3rd place", "ASU Reverse the Future · Nov 2026", t["amber"]),
    ]
    span = 23.6

    def L(m):
        return 0.08 + sum(w / (1 + math.exp(-(m - c - 0.5) * 3.2)) for c, w, *_ in cps)

    def X(m):
        return x0 + m / span * (x1 - x0)

    def Y(v):
        return y1 - v * (y1 - y0)

    b = [f'<text class="cap" x="28" y="30">fig. 2 · training log: eval score over time, higher is better</text>']
    for i in range(4):
        y = y0 + i * (y1 - y0) / 3
        b.append(f'<line x1="{x0}" y1="{r(y)}" x2="{x1}" y2="{r(y)}" stroke="{t["grid"]}"/>')
    b.append(f'<path d="M{x0},{y0 - 8}V{y1}H{x1 + 8}" fill="none" stroke="{t["faint"]}"/>')
    b.append(f'<text class="cap" x="{x0 - 10}" y="{y0 + 4}" font-size="10" text-anchor="end">1.0</text>')
    b.append(f'<text class="cap" x="{x0 - 10}" y="{y1 + 3}" font-size="10" text-anchor="end">0.0</text>')
    b.append(f'<text class="cap" transform="translate(24,{(y0 + y1) / 2 + 12}) rotate(-90)" font-size="10">score</text>')
    for m, lab in [(0, "Jan 2025"), (6, "Jul"), (12, "Jan 2026"), (18, "Jul"), (22.4, "now")]:
        b.append(f'<line x1="{r(X(m))}" y1="{y1}" x2="{r(X(m))}" y2="{y1 + 4}" stroke="{t["faint"]}"/>')
        b.append(f'<text class="cap" x="{r(X(m))}" y="{y1 + 18}" font-size="10" text-anchor="middle">{lab}</text>')
    ms = [i * 0.2 for i in range(int(22.8 / 0.2) + 1)]
    noisy = "M" + "L".join(f"{r(X(m))},{r(Y(L(m) + rng.gauss(0, 0.022)))}" for m in ms)
    clean = "M" + "L".join(f"{r(X(m))},{r(Y(L(m)))}" for m in ms)
    b.append(f'<path class="tr" pathLength="1" d="{noisy}" fill="none" stroke="{t["faint"]}" stroke-width="1.2"/>')
    b.append(f'<path class="va" pathLength="1" d="{clean}" fill="none" stroke="{t["ink"]}" stroke-width="2.2" stroke-linecap="round"/>')
    kx = 526
    for i, (c, w, title, sub, col) in enumerate(cps):
        mx = c + 1.5
        d = 1.2 + c / 22.8 * 3.6
        px, py = X(mx), Y(L(mx))
        b.append(f'<g class="cp" style="animation-delay:{d:.2f}s">')
        b.append(f'<line x1="{r(X(c + 0.5))}" y1="{y0 - 4}" x2="{r(X(c + 0.5))}" y2="{y1}" stroke="{col}" stroke-width="1" stroke-dasharray="2 4" opacity=".55"/>')
        b.append(f'<circle cx="{r(px)}" cy="{r(py)}" r="9" fill="{t["bg"]}" stroke="{col}" stroke-width="1.8"/>')
        b.append(f'<text class="m" x="{r(px)}" y="{r(py + 3.6)}" font-size="10" font-weight="700" text-anchor="middle" fill="{col}">{i + 1}</text>')
        ky = 74 + i * 41
        b.append(f'<circle cx="{kx + 9}" cy="{ky - 4}" r="9" fill="none" stroke="{col}" stroke-width="1.8"/>')
        b.append(f'<text class="m" x="{kx + 9}" y="{ky - .4}" font-size="10" font-weight="700" text-anchor="middle" fill="{col}">{i + 1}</text>')
        b.append(f'<text x="{kx + 28}" y="{ky - 5}" font-size="13.5" font-weight="700">{esc(title)}</text>')
        b.append(f'<text class="cap" x="{kx + 28}" y="{ky + 10}" font-size="10.5">{esc(sub)}</text>')
        b.append("</g>")
    b.append(f'<text class="cap" x="{kx}" y="{H - 22}" font-size="10">checkpoint saved at every jump</text>')
    css = """
.va{stroke-dasharray:1;animation:va 18s ease-in-out infinite}
.tr{stroke-dasharray:1;animation:va 18s ease-in-out infinite}
@keyframes va{0%,4%{stroke-dashoffset:1;opacity:1}30%{stroke-dashoffset:0}92%{stroke-dashoffset:0;opacity:1}98%,100%{stroke-dashoffset:0;opacity:0}}
.cp{animation:cp 18s ease infinite both}
@keyframes cp{0%{opacity:0}3%{opacity:1}86%{opacity:1}92%,100%{opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "An eval score curve that climbs at five checkpoints: Saxo Bank internship, ASU research and The AI Society, "
               "Blink Charging internship, Academic Officer and Instructional Aide, and ReCompute taking 3rd place")


# ------------------------------------------------- fig. 3 blink: log to verdict
def blink_decode(t):
    W, H = 840, 330
    b = [f'<text class="cap" x="28" y="30">fig. 3 · one charging visit, from raw log to verdict (synthetic example)</text>']
    py, ph = 48, 258
    panels = [(28, 270, "01", "raw OCPP 1.6 stream"), (312, 238, "02", "128-bit vendor fault field"), (564, 248, "03", "one visit, one verdict")]
    for x, w, num, name in panels:
        b.append(f'<rect x="{x}" y="{py}" width="{w}" height="{ph}" rx="10" fill="{t["panel"]}" stroke="{t["line"]}"/>')
        b.append(f'<text class="m" x="{x + 16}" y="{py + 24}" font-size="10.5" fill="{t["accent"]}">{num}<tspan fill="{t["mute"]}"> · {name}</tspan></text>')
    for ax in (298, 550):
        b.append(f'<path d="M{ax + 2},{py + ph / 2}h10" stroke="{t["faint"]}" stroke-width="1.4" stroke-linecap="round"/>')
        b.append(f'<circle class="flow" cx="{ax + 2}" cy="{py + ph / 2}" r="2.4" fill="{t["accent"]}"/>')
    # 01 log lines
    lines = [
        ("09:14:02", "StatusNotification", "Preparing", None),
        ("09:14:09", "Authorize", "Accepted", None),
        ("09:14:11", "StartTransaction", "tx 48213", None),
        ("09:14:41", "MeterValues", "0.4 kWh", None),
        ("09:15:10", "MeterValues", "1.1 kWh", None),
        ("09:15:26", "StatusNotification", "Faulted", t["pink"]),
        ("", "vendorErrorCode", "0x…", t["pink"]),
        ("09:15:27", "StopTransaction", "queued", t["amber"]),
        ("09:21:40", "StatusNotification", "Available", None),
        ("09:21:44", "StatusNotification", "Preparing", None),
    ]
    lx = 44
    for i, (ts, msg, val, col) in enumerate(lines):
        y = py + 52 + i * 19.5
        c = col or t["ink"]
        b.append(
            f'<text class="m ll" font-size="10" style="animation-delay:{0.3 + i * 0.42:.2f}s">'
            f'<tspan x="{lx}" y="{r(y)}" fill="{t["mute"]}">{ts}</tspan>'
            f'<tspan x="{lx + 56}" y="{r(y)}" fill="{c}">{msg}</tspan>'
            f'<tspan x="{lx + 242}" y="{r(y)}" text-anchor="end" fill="{c if col else t["mute"]}">{esc(val)}</tspan></text>'
        )
    # 02 bitfield
    bits = {37: (t["pink"], "ground fault"), 82: (t["amber"], "contactor check failed")}
    value = sum(1 << k for k in bits)
    hx = f"{value:032x}"
    gx, gy, cs, cg = 328, py + 62, 10, 3.4
    b.append(f'<text class="m" x="{gx}" y="{py + 48}" font-size="9" fill="{t["mute"]}">0x {hx[:8]} {hx[8:16]} {hx[16:24]} {hx[24:]}</text>')
    for k in range(128):
        col_i, row_i = k % 16, k // 16
        x, y = gx + col_i * (cs + cg), gy + row_i * (cs + cg)
        b.append(f'<rect x="{r(x)}" y="{r(y)}" width="{cs}" height="{cs}" rx="2" fill="{t["line"]}"/>')
        if k in bits:
            b.append(f'<rect class="bit" x="{r(x)}" y="{r(y)}" width="{cs}" height="{cs}" rx="2" fill="{bits[k][0]}"/>')
            b.append(f'<rect class="halo" x="{r(x - 3)}" y="{r(y - 3)}" width="{cs + 6}" height="{cs + 6}" rx="4" fill="none" stroke="{bits[k][0]}"/>')
    b.append(f'<rect class="sweep" x="{gx - 2}" y="{gy - 3}" width="2" height="{8 * (cs + cg) + 2}" rx="1" fill="{t["accent"]}"/>')
    dy = gy + 8 * (cs + cg) + 20
    for j, (k, (col, name)) in enumerate(sorted(bits.items())):
        b.append(f'<g class="dec" style="animation-delay:{5.2 + j * 0.5:.1f}s"><rect x="{gx}" y="{dy + j * 20 - 9}" width="10" height="10" rx="2" fill="{col}"/>'
                 f'<text class="m" x="{gx + 18}" y="{dy + j * 20}" font-size="10.5">bit {k} <tspan fill="{t["mute"]}">→</tspan> {name}</text></g>')
    b.append(f'<text class="cap" x="{gx}" y="{py + ph - 14}" font-size="9.5">bit names are illustrative</text>')
    # 03 verdict
    cats = ["Success", "ZeroEnergy", "InterruptedFault", "FaultedPrecharge", "OrphanTransaction",
            "InProgress", "AuthDenied", "AuthNoStart", "AuthNoPlug", "PluggedNoAuth"]
    vx = 580
    for i, name in enumerate(cats):
        y = py + 54 + i * 18.6
        hit = name == "InterruptedFault"
        if hit:
            b.append(f'<rect class="hit" x="{vx - 6}" y="{r(y - 12.5)}" width="{248 - 20}" height="17.5" rx="5" fill="{t["pink"]}" opacity=".16"/>')
            b.append(f'<rect class="hit" x="{vx - 6}" y="{r(y - 12.5)}" width="3" height="17.5" rx="1.5" fill="{t["pink"]}"/>')
        b.append(f'<text class="m" x="{vx + 6}" y="{r(y)}" font-size="10.5" fill="{t["ink"] if hit else t["mute"]}">{name}</text>')
        if hit:
            b.append(f'<text class="m hit" x="{vx + 216}" y="{r(y)}" font-size="10" text-anchor="end" fill="{t["pink"]}">verdict</text>')
    b.append(f'<text class="cap" x="{vx}" y="{py + ph - 14}" font-size="9.5">exactly one outcome per visit</text>')
    css = """
.ll{animation:ll 14s ease infinite both}
@keyframes ll{0%{opacity:0}2%{opacity:1}90%{opacity:1}96%,100%{opacity:0}}
.sweep{animation:sweep 14s ease-in-out infinite}
@keyframes sweep{0%,26%{transform:translateX(0);opacity:0}28%{opacity:1}38%{transform:translateX(216px);opacity:1}40%,100%{transform:translateX(216px);opacity:0}}
.bit{animation:bit 14s ease infinite}
@keyframes bit{0%,32%{opacity:0}37%{opacity:1}90%{opacity:1}96%,100%{opacity:0}}
.halo{opacity:0;transform-box:fill-box;transform-origin:center;animation:halo 14s ease-out infinite}
@keyframes halo{0%,36%{opacity:0;transform:scale(.6)}40%{opacity:.9;transform:scale(1)}52%{opacity:0;transform:scale(1.9)}100%{opacity:0}}
.dec{animation:ll 14s ease infinite both}
.hit{animation:hit 14s ease infinite}
@keyframes hit{0%,46%{opacity:0}52%{opacity:1}90%{opacity:1}96%,100%{opacity:0}}
rect.hit{animation-name:hitbg}
@keyframes hitbg{0%,46%{opacity:0}52%{opacity:.16}90%{opacity:.16}96%,100%{opacity:0}}
rect.hit + rect.hit{animation-name:hit}
.flow{animation:flow 2.2s ease-in-out infinite}
@keyframes flow{0%{transform:translateX(0);opacity:0}20%{opacity:1}80%{opacity:1}100%{transform:translateX(10px);opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "A synthetic charging visit moving through three stages: a raw OCPP message stream, a 128-bit vendor fault "
               "field being decoded into named faults, and a ten-category classifier giving the visit one verdict")


# ---------------------------------------------- fig. 4 blink: energy and cost
def blink_energy(t):
    W, H = 840, 252
    rng = random.Random(9)
    b = [f'<text class="cap" x="28" y="30">fig. 4 · when a site draws power, and what the peaks cost (synthetic data)</text>']
    gx, gy, cw, ch, g = 70, 56, 18.5, 17, 3
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d, name in enumerate(days):
        b.append(f'<text class="cap" x="{gx - 10}" y="{r(gy + d * (ch + g) + 12)}" font-size="10" text-anchor="end">{name}</text>')
        for h in range(24):
            if d < 5:
                v = 0.08 + 0.75 * math.exp(-((h - 8) ** 2) / 5) + 0.95 * math.exp(-((h - 18) ** 2) / 7) + 0.18 * math.exp(-((h - 13) ** 2) / 10)
            else:
                v = 0.08 + 0.7 * math.exp(-((h - 13.5) ** 2) / 16)
            v = max(0.05, min(1, v + rng.uniform(-0.07, 0.07)))
            x, y = gx + h * (cw + g), gy + d * (ch + g)
            b.append(f'<rect x="{r(x)}" y="{r(y)}" width="{cw}" height="{ch}" rx="3" fill="{t["line"]}"/>')
            b.append(f'<rect class="hm" x="{r(x)}" y="{r(y)}" width="{cw}" height="{ch}" rx="3" fill="{t["accent"]}" opacity="{v:.2f}" style="animation-delay:{h * 0.09:.2f}s"/>')
    for h, lab in [(0, "12a"), (6, "6a"), (12, "12p"), (18, "6p"), (23, "11p")]:
        b.append(f'<text class="cap" x="{r(gx + h * (cw + g) + cw / 2)}" y="{gy + 7 * (ch + g) + 14}" font-size="10" text-anchor="middle">{lab}</text>')
    px = gx + 18 * (cw + g) - 2
    b.append(f'<rect class="pk" x="{r(px)}" y="{gy - 4}" width="{r(cw + 4)}" height="{5 * (ch + g) + 5}" rx="5" fill="none" stroke="{t["amber"]}" stroke-width="1.6"/>')
    b.append(f'<text class="m pk" x="{r(px + cw / 2 + 2)}" y="{gy + 7 * (ch + g) + 32}" font-size="10" text-anchor="middle" fill="{t["amber"]}">site peak</text>')
    # cost split
    sx = 616
    b.append(f'<text class="cap" x="{sx}" y="66" font-size="10.5" fill="{t["ink"]}">monthly cost split</text>')
    for i, (site, e, note) in enumerate([("site A", 0.72, ""), ("site B", 0.34, "peak shaving pays here")]):
        y = 84 + i * 62
        wtot = 196
        b.append(f'<text class="cap" x="{sx}" y="{y + 10}" font-size="10">{site}</text>')
        b.append(f'<rect class="cs" x="{sx}" y="{y + 18}" width="{r(wtot * e)}" height="14" rx="3" fill="{t["faint"]}"/>')
        b.append(f'<rect class="cs" x="{r(sx + wtot * e + 2)}" y="{y + 18}" width="{r(wtot * (1 - e) - 2)}" height="14" rx="3" fill="{t["amber"]}" style="animation-delay:.25s"/>')
        if note:
            b.append(f'<text class="m pk" x="{sx}" y="{y + 48}" font-size="10" fill="{t["amber"]}">{note}</text>')
    b.append(f'<rect x="{sx}" y="214" width="8" height="8" rx="2" fill="{t["faint"]}"/><text class="cap" x="{sx + 13}" y="222" font-size="10">energy</text>')
    b.append(f'<rect x="{sx + 66}" y="214" width="8" height="8" rx="2" fill="{t["amber"]}"/><text class="cap" x="{sx + 79}" y="222" font-size="10">demand charges</text>')
    css = """
.hm{animation:hm 12s ease infinite both}
@keyframes hm{0%{fill-opacity:0}6%{fill-opacity:1}88%{fill-opacity:1}95%,100%{fill-opacity:0}}
.pk{animation:pk 12s ease infinite}
@keyframes pk{0%,26%{opacity:0}32%{opacity:1}88%{opacity:1}95%,100%{opacity:0}}
.cs{transform-box:fill-box;transform-origin:left center;animation:cs 12s cubic-bezier(.2,.8,.2,1) infinite}
@keyframes cs{0%,22%{transform:scaleX(0)}34%{transform:scaleX(1)}88%{transform:scaleX(1);opacity:1}95%,100%{transform:scaleX(1);opacity:0}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "A weekday by hour heatmap of site power demand with the evening peak outlined, next to a cost split showing "
               "a site where demand charges dominate the bill")


# -------------------------------------------------- fig. 5 recompute fleet
def recompute_fleet(t):
    W, H = 840, 318
    rng = random.Random(49)
    b = [f'<text class="cap" x="28" y="30">fig. 5 · ReCompute: a 100-server test fleet, every machine routed</text>']
    gx, gy, cs, cg = 34, 54, 17, 5
    routes = [("host longer", t["accent"], 21), ("rent while listed", t["violet"], 12), ("repair", t["green"], 9), ("harvest parts", t["pink"], 7)]
    cells = list(range(100))
    rng.shuffle(cells)
    assign, k = {}, 0
    for name, col, n in routes:
        for c in cells[k:k + n]:
            assign[c] = col
        k += n
    assert len(assign) == 49
    for c in range(100):
        x, y = gx + (c % 10) * (cs + cg), gy + (c // 10) * (cs + cg)
        b.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="4" fill="{t["faint"]}"/>')
        b.append(f'<rect x="{x + 4}" y="{y + 5}" width="{cs - 8}" height="1.6" rx=".8" fill="{t["bg"]}" opacity=".55"/>')
        b.append(f'<rect x="{x + 4}" y="{y + 10}" width="{cs - 8}" height="1.6" rx=".8" fill="{t["bg"]}" opacity=".55"/>')
        if c in assign:
            d = 1.2 + (c % 10 + c // 10) * 0.16 + rng.random() * 0.3
            b.append(f'<rect class="rr" x="{x}" y="{y}" width="{cs}" height="{cs}" rx="4" fill="{assign[c]}" style="animation-delay:{d:.2f}s"/>')
    by = gy + 10 * (cs + cg) + 14
    b.append(f'<text class="cap" x="{gx}" y="{by}" font-size="10.5" fill="{t["ink"]}">49 of 100 rerouted</text>')
    b.append(f'<text class="cap" x="{gx}" y="{by + 15}" font-size="9.5">grey = default route kept · route mix illustrative</text>')
    # route key with bars
    kx = 292
    b.append(f'<text class="cap" x="{kx}" y="66" font-size="10.5" fill="{t["ink"]}">seven routes per machine</text>')
    allr = [("sell now", t["faint"], 0.5), ("list and wait", t["faint"], 0.58), ("rent while listed", t["violet"], 0.74),
            ("host longer", t["accent"], 0.95), ("repair", t["green"], 0.62), ("harvest parts", t["pink"], 0.44), ("recycle", t["faint"], 0.16)]
    for i, (name, col, v) in enumerate(allr):
        y = 82 + i * 22
        b.append(f'<text class="m" x="{kx}" y="{y + 9}" font-size="10.5" fill="{t["mute"]}">{name}</text>')
        b.append(f'<rect x="{kx + 122}" y="{y}" width="130" height="10" rx="3" fill="{t["line"]}"/>')
        b.append(f'<rect class="rb" x="{kx + 122}" y="{y}" width="{r(130 * v)}" height="10" rx="3" fill="{col}" style="animation-delay:{0.3 + i * 0.1:.1f}s"/>')
    b.append(f'<text class="cap" x="{kx}" y="{82 + 7 * 22 + 12}" font-size="9.5">each one stress-tested: bear, base, bull</text>')
    # result card
    rx_, rw = 580, 232
    b.append(f'<rect x="{rx_}" y="50" width="{rw}" height="248" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    mx, my = rx_ + 40, 104
    b.append(f'<path d="M{mx - 13},{my + 12}l-7,34 20,-10 20,10 -7,-34z" fill="{t["amber"]}" opacity=".45"/>')
    b.append(f'<circle class="medal" cx="{mx}" cy="{my}" r="23" fill="{t["bg"]}" stroke="{t["amber"]}" stroke-width="2.6"/>')
    b.append(f'<circle cx="{mx}" cy="{my}" r="17" fill="none" stroke="{t["amber"]}" stroke-width="1" stroke-dasharray="2 3"/>')
    b.append(f'<text x="{mx}" y="{my + 8}" font-size="23" font-weight="800" text-anchor="middle" fill="{t["amber"]}">3</text>')
    b.append(f'<text x="{mx + 32}" y="{my - 6}" font-size="18" font-weight="800">3rd place</text>')
    b.append(f'<text class="cap" x="{mx + 32}" y="{my + 11}" font-size="9.5">ASU Reverse the Future</text>')
    b.append(f'<text class="cap" x="{mx + 32}" y="{my + 25}" font-size="9.5" fill="{t["amber"]}">$3,000 prize · 2026</text>')
    b.append(f'<line x1="{rx_ + 20}" y1="170" x2="{rx_ + rw - 20}" y2="170" stroke="{t["line"]}"/>')
    b.append(f'<text x="{rx_ + 20}" y="218" font-size="40" font-weight="800" letter-spacing="-1.5" fill="{t["accent"]}">+6.3%</text>')
    b.append(f'<text class="cap" x="{rx_ + 20}" y="240" font-size="10.5" fill="{t["ink"]}">modeled fleet value</text>')
    b.append(f'<text class="cap" x="{rx_ + 20}" y="256" font-size="10.5">vs. the default routes,</text>')
    b.append(f'<text class="cap" x="{rx_ + 20}" y="272" font-size="10.5">$500K+ on 100 servers</text>')
    css = """
.rr{transform-box:fill-box;transform-origin:center;animation:rr 13s cubic-bezier(.3,1.4,.5,1) infinite both}
@keyframes rr{0%{opacity:0;transform:scale(.3) rotate(-90deg)}5%{opacity:1;transform:none}88%{opacity:1;transform:none}95%,100%{opacity:0;transform:none}}
.rb{transform-box:fill-box;transform-origin:left center;animation:rb 13s cubic-bezier(.2,.8,.2,1) infinite both}
@keyframes rb{0%{transform:scaleX(0)}10%{transform:scaleX(1)}88%{transform:scaleX(1);opacity:1}95%,100%{transform:scaleX(1);opacity:0}}
.medal{animation:medal 3s ease-in-out infinite}
@keyframes medal{0%,100%{stroke-opacity:1}50%{stroke-opacity:.45}}
"""
    return svg(W, H, t, css, "\n".join(b),
               "ReCompute: a grid of 100 retired GPU servers where 49 are rerouted to better routes, seven routes scored per "
               "machine, 6.3 percent more modeled value, and a 3rd place medal from ASU Reverse the Future with a $3,000 prize")



# ------------------------------------------------------------ pipeline
def pipeline(t):
    W, H = 840, 214
    stages = [
        ("01", "query", t["accent"], ["SQL", "PostgreSQL", "SQLite", "MySQL", "Parquet"]),
        ("02", "analyze", t["violet"], ["Python", "pandas", "NumPy", "time series", "NLP"]),
        ("03", "serve", t["green"], ["FastAPI", "SQLAlchemy", "REST", "Firebase", "Docker"]),
        ("04", "show", t["amber"], ["React", "TypeScript", "Power BI", "Three.js", "Figma"]),
    ]
    b = [f'<text class="cap" x="28" y="30">fig. 10 · the stack, in the order data moves through it</text>']
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


# ------------------------------------------------------------ activity
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
    b = [f'<text class="cap" x="28" y="30">commit signal, last 12 months · redrawn nightly by scripts/build.py</text>']
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
        "hero": hero, "highlights": highlights, "training": training_log,
        "blink-decode": blink_decode, "blink-energy": blink_energy, "recompute": recompute_fleet,
        "lifeops": strip_lifeops, "research": strip_research, "fairclaim": strip_fairclaim, "play": strip_play,
        "pipeline": pipeline,
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
