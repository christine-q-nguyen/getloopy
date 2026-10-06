#!/usr/bin/env python3
"""Point the site at the address it is served from.

The site is static and every link in it is relative, so it runs anywhere. The only
things that depend on the final address are the canonical URL, the Open Graph URL,
the JSON-LD, sitemap.xml, and robots.txt. This script (re)writes all of them.

    python3 tools/set-site-url.py https://christine-q-nguyen.github.io/getloopy/
    python3 tools/set-site-url.py https://www.yourdomain.com/

Run it from the repository root (the folder that holds index.html). It is idempotent:
each page carries one block between <!-- seo:start --> and <!-- seo:end --> that is
replaced on every run. Titles and descriptions are read from each page's own
<title> and <meta name="description">.
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    "index.html", "work.html", "approach.html", "writing.html", "research.html", "about.html",
    "work/case-intake.html", "work/case-taxonomy.html", "work/case-classification.html",
    "work/case-editorial.html", "work/case-platform.html", "work/case-artifact.html",
    "work/case-training.html", "work/case-meta.html", "work/case-portfolio-method.html",
]
# Kept for canonical/OG when opened directly, but noindex and out of the sitemap while the nav skips them.
HIDDEN = ("work.html", "approach.html", "writing.html", "research.html")
PERSON = {
    "@type": "Person",
    "name": "Christine Nguyen",
    "givenName": "Christine",
    "familyName": "Nguyen",
    "jobTitle": "AI Enablement, Transformation, and Adoption Lead",
    "description": "Enterprise AI enablement, transformation, and adoption lead who translates between the people doing the work, leaders making the decision, and engineers building the system. Turns fuzzy AI asks into clear choices, testable workflows, trusted model decisions, and capabilities teams can own.",
    "address": {"@type": "PostalAddress", "addressLocality": "Austin", "addressRegion": "TX", "addressCountry": "US"},
    "email": "mailto:christineqnguyen@gmail.com",
    "sameAs": ["https://www.linkedin.com/in/christinenguyen7/", "https://github.com/christine-q-nguyen"],
    "knowsAbout": [
        "AI enablement", "AI transformation", "AI adoption", "AI Center of Excellence", "AI portfolio prioritization",
        "agentic workflows", "applied machine learning", "AI platform strategy", "human-in-the-loop design",
        "responsible AI", "LLM evaluation", "Model Context Protocol (MCP)",
        "use-case prioritization", "service design", "user research", "product management",
    ],
    "alumniOf": [
        {"@type": "CollegeOrUniversity", "name": "New York University, Interactive Telecommunications Program"},
        {"@type": "CollegeOrUniversity", "name": "The University of Texas at Dallas"},
    ],
}


def seo_block(base: str, rel: str, title: str, desc: str, is_home: bool) -> str:
    url = base + ("" if rel == "index.html" else rel)
    og_image = base + "assets/img/og.png"
    graph = [dict(PERSON, **{"@id": base + "#person", "url": base})]
    page = {
        "@type": "ProfilePage" if is_home else "WebPage",
        "@id": url,
        "url": url,
        "name": title,
        "description": desc,
        "isPartOf": {"@type": "WebSite", "@id": base + "#site", "url": base, "name": "christine.nguyen — Let's get loopy"},
        "about": {"@id": base + "#person"},
    }
    if is_home:
        page["mainEntity"] = {"@id": base + "#person"}
    graph.append(page)
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=0).replace("</", "<\\/")
    lines = [
        "<!-- seo:start (managed by tools/set-site-url.py) -->",
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:type" content="{"profile" if is_home else "article"}">',
        f'<meta property="og:site_name" content="christine.nguyen">',
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">',
        f'<meta property="og:description" content="{html.escape(desc, quote=True)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{og_image}">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{html.escape(title, quote=True)}">',
        f'<meta name="twitter:description" content="{html.escape(desc, quote=True)}">',
        f'<meta name="twitter:image" content="{og_image}">',
        f'<script type="application/ld+json">{ld}</script>',
        "<!-- seo:end -->",
    ]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    base = sys.argv[1].rstrip("/") + "/"
    for rel in PAGES:
        path = ROOT / rel
        src = path.read_text(encoding="utf-8")
        title = html.unescape(re.search(r"<title>(.*?)</title>", src, re.S).group(1).strip())
        m = re.search(r'<meta name="description" content="([^"]*)">', src)
        desc = html.unescape(m.group(1)) if m else title
        block = seo_block(base, rel, title, desc, rel == "index.html")
        if "<!-- seo:start" in src:
            src = re.sub(r"<!-- seo:start.*?<!-- seo:end -->", lambda _: block, src, flags=re.S)
        else:
            src = src.replace("</head>", block + "\n</head>", 1)
        path.write_text(src, encoding="utf-8")
    today = date.today().isoformat()
    sitemap_pages = [p for p in PAGES if p not in HIDDEN]
    urls = "".join(
        f"  <url><loc>{base + ('' if p == 'index.html' else p)}</loc><lastmod>{today}</lastmod>"
        f"<priority>{'1.0' if p == 'index.html' else '0.8' if '/' not in p else '0.6'}</priority></url>\n"
        for p in sitemap_pages
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
        encoding="utf-8",
    )
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n", encoding="utf-8")
    print(f"site url set to {base} on {len(PAGES)} pages; sitemap.xml and robots.txt written")


if __name__ == "__main__":
    main()
