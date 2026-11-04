"""Refresh the profile README from live GitHub data.

Run by .github/workflows/update-profile.yml once a day. It writes:
  assets/stats.svg       GitHub stats card
  assets/top-langs.svg   Most used languages card
  assets/activity.svg    Activity overview for the last year
and refreshes the "More projects" table and "Recently active" line in README.md.

Only the Python standard library is used, so the workflow needs no installs.
Set PROFILE_DATA=path/to/sample.json to render from a saved API response instead.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "mohammednaeemog-sys")
NAME = "Mohammed Naeem"
ROOT = Path(__file__).resolve().parent.parent

# Colours from the existing SVGs, so the new cards match the old look.
BG, GREEN, LIGHT, TEXT, MUTED, BORDER, DIM = (
    "#0d1117", "#3fb950", "#7ee787", "#c9d1d9", "#8b949e", "#30363d", "#6e7681")
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'
SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"

# Repos shown as cards under "Featured work" are left out of the auto table.
FEATURED = {
    "AI-Art-Style-Transfer",
    "Password-Strength-Classification-Using-Structural-Features",
    "skein-yarn-comparator",
    "rag-project-bluebook",
}
HIDDEN = {USER}  # the profile repo itself

# Hand-written text for repos whose GitHub description is empty or too short.
# Any new repo not listed here uses its own GitHub description and topics.
OVERRIDES = {
    "-Image-Classification-Using-Convolutional-Neural-Network": (
        "CNN Image Classification",
        "Image classifier built with a convolutional neural network.",
        "Deep Learning, Jupyter"),
    "Penetration-Testing-and-Remote-Access-Simulation-Using-Kali-Linux-and-Metasploit-Framework": (
        "Penetration Testing Simulation",
        "Simulated penetration test and remote access scenario in a controlled lab environment.",
        "Kali Linux, Metasploit"),
    "portfolio": (
        "Portfolio Website",
        "Personal portfolio with course materials, published to GitHub Pages by GitHub Actions.",
        "React, Vite, JavaScript"),
    "RRN-WORK": (
        "COVID-19 Forecasting with RNN, LSTM and GRU",
        "Exploratory analysis of a COVID-19 dataset and forecasting with recurrent neural networks.",
        "Deep Learning, Jupyter"),
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name url description isFork isArchived stargazerCount pushedAt
        primaryLanguage { name }
        repositoryTopics(first: 6) { nodes { topic { name } } }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    repositoriesContributedTo(first: 1, includeUserRepositories: true,
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch():
    sample = os.environ.get("PROFILE_DATA")
    if sample:
        return json.loads(Path(sample).read_text())["data"]["user"]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("No GH_TOKEN or GITHUB_TOKEN set.")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme-updater"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors") or not body.get("data", {}).get("user"):
        sys.exit(f"GitHub API error: {body.get('errors')}")
    return body["data"]["user"]


def fmt(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


# ---------------------------------------------------------------- stats card
ICONS = {  # 16px octicons
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}


def stats_svg(u, repos):
    c = u["contributionsCollection"]
    rows = [
        ("star", "Total Stars Earned", sum(r["stargazerCount"] for r in repos)),
        ("commit", "Total Commits (last year)", c["totalCommitContributions"]),
        ("pr", "Total PRs", c["totalPullRequestContributions"]),
        ("issue", "Total Issues", c["totalIssueContributions"]),
        ("repo", "Contributed to (last year)", u["repositoriesContributedTo"]["totalCount"]),
    ]
    total = c["contributionCalendar"]["totalContributions"]
    lines = []
    for i, (icon, label, value) in enumerate(rows):
        y = 25 * i
        lines.append(
            f'<g transform="translate(0,{y})"><g class="row" style="animation-delay:{450 + i * 150}ms">'
            f'<path transform="translate(0,-12)" fill="{GREEN}" d="{ICONS[icon]}"/>'
            f'<text x="25" y="0" class="lbl">{label}:</text>'
            f'<text x="235" y="0" class="val">{fmt(value)}</text></g></g>')
    circ = 2 * 3.14159 * 40
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="467" height="195" viewBox="0 0 467 195" role="img" aria-label="{escape(NAME)}'s GitHub stats">
  <style>
    .title {{ font: 600 18px {SANS}; fill: {GREEN}; animation: fade .8s ease-in-out forwards; }}
    .lbl {{ font: 600 14px {SANS}; fill: {TEXT}; }}
    .val {{ font: 700 14px {SANS}; fill: {TEXT}; }}
    .row {{ opacity: 0; animation: fade .3s ease-in-out forwards; }}
    .big {{ font: 800 22px {SANS}; fill: {TEXT}; }}
    .small {{ font: 600 11px {SANS}; fill: {MUTED}; }}
    .ring {{ stroke-dasharray: {circ:.1f}; stroke-dashoffset: {circ:.1f}; animation: draw 1.2s .4s ease-out forwards; }}
    @keyframes fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="466" height="194" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="title">{escape(NAME)}'s GitHub Stats</text>
  <g transform="translate(25,72)">
    {"".join(lines)}
  </g>
  <g transform="translate(390,112)">
    <circle r="40" fill="none" stroke="{GREEN}" stroke-opacity="0.2" stroke-width="6"/>
    <circle r="40" fill="none" stroke="{GREEN}" stroke-width="6" stroke-linecap="round" transform="rotate(-90)" class="ring"/>
    <text y="6" text-anchor="middle" class="big">{fmt(total)}</text>
    <text y="62" text-anchor="middle" class="small">contributions</text>
  </g>
</svg>
'''


# --------------------------------------------------------------- languages
def langs_svg(repos):
    sizes, colors = {}, {}
    for r in repos:
        if r["isFork"]:
            continue
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or MUTED
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:8]
    total = sum(s for _, s in top) or 1
    width, bar = 350, 300
    segs, x = [], 0.0
    for name, size in top:
        w = bar * size / total
        segs.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{colors[name]}"/>')
        x += w
    legend = []
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        legend.append(
            f'<g transform="translate({col * 150},{row * 25})"><g class="item" style="animation-delay:{450 + i * 150}ms">'
            f'<circle cx="5" cy="6" r="5" fill="{colors[name]}"/>'
            f'<text x="15" y="10" class="lang">{escape(name)} {100 * size / total:.1f}%</text></g></g>')
    if not top:
        legend.append(f'<text x="0" y="10" class="lang">No public code yet</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="195" viewBox="0 0 {width} 195" role="img" aria-label="Most used languages">
  <style>
    .title {{ font: 600 18px {SANS}; fill: {GREEN}; animation: fade .8s ease-in-out forwards; }}
    .lang {{ font: 400 12px {SANS}; fill: {TEXT}; }}
    .item {{ opacity: 0; animation: fade .3s ease-in-out forwards; }}
    .bar {{ animation: grow 1s .3s ease-out both; transform-origin: left; }}
    @keyframes fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="194" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="title">Most Used Languages</text>
  <mask id="m"><rect x="25" y="60" width="{bar}" height="8" rx="5" fill="#fff"/></mask>
  <g mask="url(#m)"><g transform="translate(25,60)"><g class="bar">{"".join(segs)}</g></g></g>
  <g transform="translate(25,86)">
    {"".join(legend)}
  </g>
</svg>
'''


# ---------------------------------------------------------------- activity
def activity_svg(u):
    c = u["contributionsCollection"]
    vals = {
        "commits": c["totalCommitContributions"],
        "prs": c["totalPullRequestContributions"],
        "issues": c["totalIssueContributions"],
        "reviews": c["totalPullRequestReviewContributions"],
    }
    total = sum(vals.values()) or 1
    pct = {k: v / total for k, v in vals.items()}
    R = 95
    # Commits left, code review top, issues right, pull requests bottom.
    pts = {
        "commits": (-R * pct["commits"], 0),
        "reviews": (0, -R * pct["reviews"]),
        "issues": (R * pct["issues"], 0),
        "prs": (0, R * pct["prs"]),
    }
    order = ["commits", "reviews", "issues", "prs"]
    poly = " ".join(f"{x:.1f},{y:.1f}".replace("-0.0", "0").replace("0.0", "0") for x, y in (pts[k] for k in order))
    dots = "".join(
        f'\n      <circle cx="{pts[k][0]:.1f}" cy="{pts[k][1]:.1f}" r="4.5" fill="{BG}" stroke="{LIGHT}" stroke-width="2"/>'
        for k in order if vals[k] > 0)

    def p(k):
        return f"{round(100 * pct[k])}%"

    def label(k, x, y, name, anchor):
        a = f' text-anchor="{anchor}"' if anchor else ""
        if vals[k] == 0:
            return f'\n      <text x="{x}" y="{y}"{a}>{name}</text>'
        return (f'\n      <text x="{x}" y="{y - 9}"{a} fill="{TEXT}">{p(k)}</text>'
                f'\n      <text x="{x}" y="{y + 9}"{a}>{name}</text>')

    labels = (
        (f'\n      <text x="0" y="-126" text-anchor="middle" fill="{TEXT}">{p("reviews")}</text>' if vals["reviews"] else "")
        + '\n      <text x="0" y="-108" text-anchor="middle">Code review</text>'
        + label("issues", 108, 5, "Issues", "")
        + label("commits", -108, 5, "Commits", "end")
        + (f'\n      <text x="0" y="116" text-anchor="middle" fill="{TEXT}">{p("prs")}</text>'
           '\n      <text x="0" y="134" text-anchor="middle">Pull requests</text>'
           if vals["prs"] else '\n      <text x="0" y="116" text-anchor="middle">Pull requests</text>'))

    def word(k, name):
        return f"{round(100 * pct[k])} percent {name}"
    aria = "Activity overview for the last year: " + ", ".join(
        word(k, n) for k, n in [("commits", "commits"), ("prs", "pull requests"),
                                ("issues", "issues"), ("reviews", "code reviews")])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 320" width="1000" height="320" role="img" aria-label="{aria}">
  <style>
    .mono {{ font-family: {MONO}; }}
  </style>
  <rect x="0.5" y="0.5" width="999" height="319" rx="10" fill="{BG}" stroke="{BORDER}"/>

  <!-- header -->
  <circle cx="24" cy="22" r="5" fill="#ff5f56"/><circle cx="42" cy="22" r="5" fill="#ffbd2e"/><circle cx="60" cy="22" r="5" fill="#27c93f"/>
  <text x="82" y="26" font-size="12" fill="{DIM}" class="mono">mohammed@dhaka: ~/activity</text>

  <!-- left: numbers (updated automatically every day) -->
  <text x="48" y="104" font-size="15" fill="{GREEN}" class="mono">$ activity --last-year</text>
  <g font-size="15" class="mono" fill="{TEXT}">
    <text x="48" y="144">commits</text><text x="228" y="144" text-anchor="end" fill="{LIGHT}">{vals["commits"]}</text>
    <text x="48" y="172">pull requests</text><text x="228" y="172" text-anchor="end" fill="{LIGHT}">{vals["prs"]}</text>
    <text x="48" y="200">issues</text><text x="228" y="200" text-anchor="end" fill="{LIGHT}">{vals["issues"]}</text>
    <text x="48" y="228">code review</text><text x="228" y="228" text-anchor="end" fill="{LIGHT}">{vals["reviews"]}</text>
  </g>

  <!-- chart -->
  <g transform="translate(560,168)">
    <!-- axes -->
    <g stroke="{GREEN}" stroke-opacity="0.55" stroke-width="2" stroke-linecap="round">
      <line x1="0" y1="-95" x2="0" y2="95"/>
      <line x1="-95" y1="0" x2="95" y2="0"/>
    </g>
    <!-- guide ring -->
    <path d="M0,-95 L95,0 L0,95 L-95,0 Z" fill="none" stroke="{BORDER}" stroke-dasharray="3 6" stroke-width="2"/>

    <!-- data shape grows in once -->
    <g>
      <animateTransform attributeName="transform" type="scale" from="0" to="1" dur="1.4s" begin="0s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>
      <polygon points="{poly}" fill="{GREEN}" fill-opacity="0.35" stroke="{GREEN}" stroke-width="2" stroke-linejoin="round"/>{dots}
    </g>

    <!-- labels -->
    <g font-size="13" class="mono" fill="{MUTED}">{labels}
    </g>
  </g>
</svg>
'''


# ------------------------------------------------------------------ README
def replace_block(text, key, body):
    pattern = re.compile(rf"(<!-- AUTO:{key}:START -->\n).*?(\n<!-- AUTO:{key}:END -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"README is missing the AUTO:{key} markers.")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ").strip()


def projects_table(repos):
    rows = ["| Project | Description | Technologies |", "|:--|:--|:--|"]
    for r in repos:
        if r["isFork"] or r["isArchived"] or r["name"] in FEATURED | HIDDEN:
            continue
        title, desc, tech = OVERRIDES.get(r["name"], (None, None, None))
        title = title or r["name"].strip("-").replace("-", " ").replace("_", " ")
        desc = desc or r["description"] or "No description yet."
        if not tech:
            tags = [r["primaryLanguage"]["name"]] if r["primaryLanguage"] else []
            tags += [t["topic"]["name"] for t in r["repositoryTopics"]["nodes"]]
            tech = ", ".join(dict.fromkeys(tags)) or "-"
        rows.append(f"| [**{cell(title)}**]({r['url']}) | {cell(desc)} | {cell(tech)} |")
    return "\n".join(rows)


def recent_line(repos):
    names = [r for r in repos if r["name"] not in HIDDEN][:3]
    links = [f'<a href="{r["url"]}">{escape(r["name"])}</a>' for r in names]
    joined = links[0] if len(links) == 1 else ", ".join(links[:-1]) + " and " + links[-1] if links else ""
    return f'<p align="center">\n  <sub>Recently active in {joined}</sub>\n</p>'


def main():
    u = fetch()
    repos = u["repositories"]["nodes"]
    assets = ROOT / "assets"
    (assets / "stats.svg").write_text(stats_svg(u, repos))
    (assets / "top-langs.svg").write_text(langs_svg(repos))
    (assets / "activity.svg").write_text(activity_svg(u))
    readme = ROOT / "README.md"
    text = readme.read_text()
    text = replace_block(text, "PROJECTS", projects_table(repos))
    text = replace_block(text, "RECENT", recent_line(repos))
    readme.write_text(text)
    print("Updated at", datetime.now(timezone.utc).isoformat(timespec="minutes"))


if __name__ == "__main__":
    main()
