#!/usr/bin/env python3
"""
Dental Price Guide (dentalpriceguide.com) static site generator.

Inputs (all under _src/):
  content/<slug>.json   page specs written by the article machine (generate-dental.js)
  data/pages-index.json every planned page (slug, pillar, category, level, kind, primary, ...)
  data/publish.json     {slug: "YYYY-MM-DD"} -> pages that are LIVE. Only these are rendered,
                        linked, and listed in the sitemap. Links to not-yet-live pages are
                        rendered as plain text until the page is released.
Output: the repo root (one index.html per directory), plus sitemap.xml, robots.txt, llms.txt,
        ads.txt, .htaccess, 404.html, manifest.json, favicon.svg, IndexNow key file, assets/.

Usage:
  python3 _src/build.py                 build
  python3 _src/build.py --release 3     publish the next 3 queued pages (that have content), then build
  python3 _src/build.py --status        show live / queued / missing-content counts
"""
import os, re, sys, json, html, shutil, datetime

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(SRC)
CONTENT = os.path.join(SRC, "content")
DATA = os.path.join(SRC, "data")

SITE = "Dental Price Guide"
HOST = "https://www.dentalpriceguide.com"
TAGLINE = "What dental work really costs, from published claims and survey data"
BRAND = "#0f766e"
PUBLISHED = "2026-10-21"
REVIEWER = "Dr. Faisal Irshad"
REVIEWER_SUFFIX = "MBBS"
REVIEWER_TITLE = "Medical Doctor"
PMDC = "PMDC 54440-S"
CONTACT_EMAIL = "contact@dentalpriceguide.com"
AD_CLIENT = "ca-pub-8301212931863478"
GSC_VERIFY = ""            # meta-tag token, optional (HTML-file method used instead)
INDEXNOW_KEY = "b7d41e9c2a6f48e3a1c05d9e7f2b8a64"
OG_IMG = HOST + "/assets/img/og-default.png"
TODAY = datetime.date.today().isoformat()

CATEGORIES = [
    ("oral-surgery", "Oral Surgery", "Wisdom teeth, tooth extractions and gum grafts: what they cost, what recovery looks like, and how insurance treats them."),
    ("implants-tooth-replacement", "Implants & Tooth Replacement", "Dental implants, dentures and bridges compared on price, lifespan and what each involves."),
    ("braces-orthodontics", "Braces & Orthodontics", "Metal, ceramic, lingual and clear braces: prices, insurance, and living with braces."),
    ("cosmetic-dentistry", "Cosmetic Dentistry", "Veneers, teeth whitening and bonding: costs per tooth, what lasts, and what insurance skips."),
    ("restorative-dentistry", "Restorative Dentistry", "Root canals, crowns, fillings and abscess treatment: prices and what to expect."),
    ("preventive-care-insurance", "Preventive Care & Insurance", "Cleanings, exams, X-rays and how dental insurance pays for each type of treatment."),
]
CAT_NAME = {c[0]: c[1] for c in CATEGORIES}
PILLAR_ORDER = ["Dental Implants", "Dentures", "Dental Bridges", "Braces", "Veneers", "Teeth Whitening",
                "Dental Bonding", "Wisdom Teeth", "Tooth Extraction", "Gum Graft", "Root Canal", "Dental Crowns",
                "Fillings", "Tooth Abscess", "Dental Cleaning", "Dental Insurance"]
STATIC = ["about", "methodology", "editorial-policy", "privacy", "disclaimer", "contact"]

def esc(s): return html.escape(str(s or ""), quote=True)
def strip_tags(s): return re.sub(r"<[^>]+>", "", s or "")
def load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except FileNotFoundError: return default

# ---------------------------------------------------------------- data
INDEX = load(os.path.join(DATA, "pages-index.json"), [])
IDX = {p["slug"]: p for p in INDEX}
PUBLISH = load(os.path.join(DATA, "publish.json"), {})

def has_content(slug): return os.path.exists(os.path.join(CONTENT, slug + ".json"))

def release(n):
    queue = [p["slug"] for p in INDEX if p["slug"] not in PUBLISH and has_content(p["slug"])]
    picked = queue[:n]
    for s in picked: PUBLISH[s] = TODAY
    json.dump(PUBLISH, open(os.path.join(DATA, "publish.json"), "w"), indent=1, sort_keys=True)
    print(f"released {len(picked)}: {', '.join(picked) or '-'}  | still queued: {len(queue) - len(picked)}")
    return picked

if "--status" in sys.argv:
    live = [s for s in PUBLISH if has_content(s)]
    queued = [p["slug"] for p in INDEX if p["slug"] not in PUBLISH and has_content(p["slug"])]
    missing = [p["slug"] for p in INDEX if not has_content(p["slug"])]
    print(f"live {len(live)} | queued {len(queued)} | no content yet {len(missing)}")
    sys.exit(0)
if "--release" in sys.argv:
    release(int(sys.argv[sys.argv.index("--release") + 1]))

PAGES = {}
for s in PUBLISH:
    if has_content(s):
        PAGES[s] = json.load(open(os.path.join(CONTENT, s + ".json"), encoding="utf-8"))
LIVE = set(PAGES)
def live_path(path): return path.strip("/") in LIVE

# ---------------------------------------------------------------- schema
ORG = {"@type": "Organization", "@id": HOST + "/#org", "name": SITE, "url": HOST + "/",
       "logo": {"@type": "ImageObject", "url": HOST + "/assets/img/logo.png", "width": 512, "height": 512},
       "description": "Independent guide to US dental procedure costs, built on published claims and survey data.",
       "email": CONTACT_EMAIL}
WEBSITE = {"@type": "WebSite", "@id": HOST + "/#website", "name": SITE, "url": HOST + "/",
           "publisher": {"@id": HOST + "/#org"}, "inLanguage": "en-US"}
AUTHOR = {"@type": "Person", "@id": HOST + "/#reviewer", "name": REVIEWER, "honorificSuffix": REVIEWER_SUFFIX,
          "jobTitle": REVIEWER_TITLE, "identifier": PMDC, "url": HOST + "/about/",
          "description": "Medical doctor (MBBS) with 18 years of clinical and laboratory-medicine experience. Reviews pages for medical accuracy; not a dentist."}

def graph(nodes):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": nodes}, ensure_ascii=False) + "</script>"

def crumbs_ld(trail):
    items = []
    for i, (n, u) in enumerate(trail, 1):
        it = {"@type": "ListItem", "position": i, "name": n}
        if u: it["item"] = HOST + u
        items.append(it)
    return {"@type": "BreadcrumbList", "itemListElement": items}

# ---------------------------------------------------------------- chrome
def head(title, desc, path, nodes, og_type="article", robots="index,follow,max-snippet:-1,max-image-preview:large"):
    canonical = HOST + path
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={AD_CLIENT}" crossorigin="anonymous"></script>\n' if AD_CLIENT else "")
    verify = f'<meta name="google-site-verification" content="{GSC_VERIFY}">\n' if GSC_VERIFY else ""
    return f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="{BRAND}">
{verify}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMG}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/img/icon-180.png">
<link rel="manifest" href="/manifest.json">
<link rel="stylesheet" href="/assets/css/style.css">
{ads}{graph([ORG, WEBSITE, AUTHOR] + nodes)}
</head>
"""

LOGO = f'<svg class="mark" viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><rect width="64" height="64" rx="14" fill="{BRAND}"/><path d="M20 16c-5 0-8 4-8 10 0 9 4 12 5 20 1 5 3 8 5 8s3-4 4-9c1-4 2-6 6-6s5 2 6 6c1 5 2 9 4 9s4-3 5-8c1-8 5-11 5-20 0-6-3-10-8-10-4 0-6 2-12 2s-8-2-12-2z" fill="#fff"/></svg>'

def header():
    nav = "".join(f'<a href="/{c[0]}/">{esc(c[1])}</a>' for c in CATEGORIES)
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap">
<a class="brand" href="/" aria-label="{SITE} home">{LOGO}<span>Dental&nbsp;Price&nbsp;Guide</span></a>
<button class="menu-btn" aria-label="Menu" aria-expanded="false" onclick="var n=document.getElementById('nav'),o=n.classList.toggle('open');this.setAttribute('aria-expanded',o)">&#9776;</button>
<nav class="nav" id="nav" aria-label="Primary">{nav}</nav>
</div></header>
"""

def footer():
    cats = "".join(f'<a href="/{c[0]}/">{esc(c[1])}</a>' for c in CATEGORIES)
    return f"""<footer class="site-foot"><div class="wrap">
<div class="foot-cols">
<div><p class="foot-brand"><strong>{SITE}</strong><br>{TAGLINE}.</p>
<p class="foot-rev">Medically reviewed by {REVIEWER}, {REVIEWER_SUFFIX} ({PMDC}).</p></div>
<nav class="foot-links" aria-label="Topics">{cats}</nav>
<nav class="foot-links" aria-label="Site">
<a href="/about/">About us</a><a href="/methodology/">How we price procedures</a><a href="/editorial-policy/">Editorial policy</a>
<a href="/disclaimer/">Medical disclaimer</a><a href="/privacy/">Privacy policy</a><a href="/contact/">Contact</a></nav>
</div>
<p class="foot-note">{SITE} publishes general cost and health information for US readers. Prices are national averages from the published sources named on each page; your dentist's fee, your location and your insurance plan will change what you pay. This site does not give dental or medical advice. For severe pain, facial swelling, fever or bleeding that will not stop, contact a dentist or urgent care now.</p>
<p class="copyright">&copy; 2026 {SITE}. Prices last checked October 2026.</p>
</div></footer>
</body>
</html>"""

def page_shell(title, desc, path, nodes, body, og_type="article", robots=None):
    h = head(title, desc, path, nodes, og_type) if robots is None else head(title, desc, path, nodes, og_type, robots)
    return h + header() + f'<main id="main" class="wrap">{body}</main>\n' + footer()

def breadcrumbs(trail):
    parts = []
    for n, u in trail:
        parts.append(f'<a href="{u}">{esc(n)}</a>' if u else f'<span aria-current="page">{esc(n)}</span>')
    return '<nav class="crumbs" aria-label="Breadcrumb">' + ' <span class="sep">&rsaquo;</span> '.join(parts) + "</nav>"

def write(path, text):
    d = os.path.join(OUT, path.strip("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(text)

# ---------------------------------------------------------------- helpers
def fix_links(h):
    """Unwrap internal links to pages that are not live yet; harden external links."""
    def rep(m):
        href, inner = m.group(1), m.group(2)
        if href.startswith("/"):
            return f'<a href="{href}">{inner}</a>' if (href == "/" or live_path(href) or href.strip("/") in CAT_NAME or href.strip("/") in STATIC) else inner
        return f'<a href="{href}" rel="noopener" target="_blank">{inner}</a>'
    return re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', rep, h or "", flags=re.S)

def clean_html(h):
    h = re.sub(r"</?(h1|h2|h3|table|img|script|style)[^>]*>", "", h or "", flags=re.I)
    return fix_links(h)

def pillar_slug(pillar):
    for p in INDEX:
        if p["pillar"] == pillar and p["level"] == "Pillar Page": return p["slug"]

def lead_figure(slug):
    sp = PAGES.get(slug) or {}
    f = (sp.get("facts") or [{}])[0]
    return f.get("value", ""), f.get("source", "")

def h1_short(sp):
    return sp.get("h1") or sp.get("title") or sp.get("primary", "")

# ---------------------------------------------------------------- article pages
def render_article(slug):
    sp = PAGES[slug]; meta = IDX.get(slug, {})
    path = f"/{slug}/"
    cat_slug = sp.get("category_slug") or meta.get("category_slug")
    cat = CAT_NAME.get(cat_slug, "Dental costs")
    trail = [("Home", "/"), (cat, f"/{cat_slug}/")]
    ps = pillar_slug(sp["pillar"])
    if sp.get("level") != "Pillar Page" and ps in LIVE:
        trail.append((PAGES[ps].get("h1", sp["pillar"]).split(":")[0], f"/{ps}/"))
    trail.append((h1_short(sp).split(":")[0], None))
    updated = PUBLISH.get(slug, TODAY)

    qa = sp.get("quick_answer", "")
    qa_html = f'<div class="answer"><div class="answer-k">Quick answer</div>{clean_html(qa)}</div>' if qa else ""
    kt = sp.get("key_takeaways") or []
    kt_html = ('<div class="takeaways"><div class="tk-k">Key takeaways</div><ul>' + "".join(f"<li>{esc(x)}</li>" for x in kt) + "</ul></div>") if kt else ""

    table_html = ""
    ct = sp.get("cost_table")
    if isinstance(ct, dict) and ct.get("rows"):
        ths = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in ct.get("headers", []))
        trs = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in ct["rows"])
        table_html = (f'<div class="tbl"><table><caption>{esc(ct.get("caption", ""))}</caption>'
                      f"<thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>")

    secs = sp.get("sections") or []
    toc = ""
    if len(secs) >= 3:
        toc = ('<nav class="toc" aria-label="On this page"><div class="toc-k">On this page</div><ol>'
               + "".join(f'<li><a href="#{esc(s.get("id"))}">{esc(s.get("h2"))}</a></li>' for s in secs)
               + ('<li><a href="#faq">Frequently asked questions</a></li>' if sp.get("faq") else "") + "</ol></nav>")
    body_parts = []
    for i, s in enumerate(secs):
        body_parts.append(f'<section id="{esc(s.get("id"))}"><h2>{esc(s.get("h2"))}</h2>{clean_html(s.get("html"))}</section>')
        if i == 0 and table_html:
            body_parts.append(table_html); table_html = ""
    if table_html: body_parts.insert(0, table_html)

    faq = sp.get("faq") or []
    faq_html = ""
    if faq:
        faq_html = ('<section class="faq" id="faq"><h2>Frequently asked questions</h2>'
                    + "".join(f'<details><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>' for f in faq) + "</section>")

    rel = [r for r in (sp.get("related") or []) if live_path(r["url"]) and r["url"] != path]
    rel_html = ""
    if rel:
        rel_html = ('<section class="related"><h2>Related cost guides</h2><ul class="cards">'
                    + "".join(f'<li><a href="{r["url"]}">{esc(PAGES[r["url"].strip("/")].get("h1", r["title"]))}</a></li>' for r in rel[:8]) + "</ul></section>")

    var = [v for v in (sp.get("variations") or [])][:12]
    also = f'<p class="also"><span>People also search:</span> {esc(", ".join(var))}.</p>' if var else ""

    srcs = sp.get("sources") or []
    src_html = ('<section class="sources"><h2>Sources</h2><ol>'
                + "".join(f'<li><a href="{esc(s["url"])}" rel="noopener nofollow" target="_blank">{esc(s["name"])}</a></li>' for s in srcs)
                + f'</ol><p class="src-note">Prices are national figures from the sources above, checked October 2026. See <a href="/methodology/">how we price procedures</a>.</p></section>')

    byline = (f'<div class="byline"><span>Medically reviewed by <a href="/about/"><strong>{REVIEWER}, {REVIEWER_SUFFIX}</strong></a></span>'
              f'<span>Updated <time datetime="{updated}">{datetime.date.fromisoformat(updated).strftime("%B %-d, %Y")}</time></span>'
              f'<span><a href="/methodology/">{len([s for s in srcs if "carecredit" in s["url"] or "deltadental" in s["url"] or "goodrx" in s["url"] or "pearl" in s["url"] or "healthline" in s["url"]])} price sources</a></span></div>')

    body = (breadcrumbs(trail)
            + f'<article class="post"><header class="post-head"><h1>{esc(sp.get("h1"))}</h1>{byline}</header>'
            + qa_html + kt_html + toc + "".join(body_parts) + faq_html + also
            + '<div class="callout disclaimer"><p>This page is general information, not dental advice. Ask your dentist for a written treatment plan and cost estimate, and ask your insurer for a pre-treatment estimate before major work.</p></div>'
            + src_html + "</article>" + rel_html)

    procedure = {"@type": "MedicalProcedure", "name": sp["pillar"]}
    nodes = [{"@type": "MedicalWebPage", "@id": HOST + path + "#webpage", "url": HOST + path, "name": sp.get("title"),
              "headline": sp.get("h1"), "description": sp.get("description"), "inLanguage": "en-US",
              "datePublished": PUBLISH.get(slug, PUBLISHED), "dateModified": updated, "lastReviewed": updated,
              "isPartOf": {"@id": HOST + "/#website"}, "publisher": {"@id": HOST + "/#org"},
              "author": {"@id": HOST + "/#org"}, "reviewedBy": {"@id": HOST + "/#reviewer"},
              "about": procedure, "keywords": sp.get("meta_keywords", ""),
              "medicalAudience": {"@type": "MedicalAudience", "audienceType": "Patient"},
              "breadcrumb": {"@id": HOST + path + "#crumbs"},
              "citation": [s["url"] for s in srcs]},
             dict(crumbs_ld(trail), **{"@id": HOST + path + "#crumbs"})]
    if faq:
        nodes.append({"@type": "FAQPage", "@id": HOST + path + "#faq", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]})
    write(path, page_shell(sp.get("title"), sp.get("description"), path, nodes, body))

# ---------------------------------------------------------------- hubs
def pillars_in(cat_slug):
    ps = [p for p in INDEX if p["category_slug"] == cat_slug and p["level"] == "Pillar Page"]
    return sorted(ps, key=lambda p: PILLAR_ORDER.index(p["pillar"]) if p["pillar"] in PILLAR_ORDER else 99)

def render_hub(cat_slug, name, intro):
    path = f"/{cat_slug}/"
    blocks = []
    item_list = []
    for p in pillars_in(cat_slug):
        members = [x for x in INDEX if x["pillar"] == p["pillar"] and x["slug"] in LIVE]
        if not members: continue
        pil = p["slug"] if p["slug"] in LIVE else None
        subs = [x for x in members if x["slug"] != p["slug"]]
        fig, src = lead_figure(p["slug"]) if pil else ("", "")
        head_html = (f'<h2><a href="/{pil}/">{esc(PAGES[pil]["h1"])}</a></h2>' if pil else f"<h2>{esc(p['pillar'])}</h2>")
        lead = f'<p class="lead-fig"><strong>{esc(fig)}</strong> <span>({esc(src.split(" — ")[0])})</span></p>' if fig else ""
        lis = "".join(f'<li><a href="/{x["slug"]}/">{esc(PAGES[x["slug"]]["h1"])}</a></li>' for x in subs)
        blocks.append(f'<section class="hub-group">{head_html}{lead}<ul class="cards">{lis}</ul></section>')
        for x in members: item_list.append(HOST + f"/{x['slug']}/")
    body = (breadcrumbs([("Home", "/"), (name, None)]) + f'<header class="hub-head"><h1>{esc(name)} costs</h1><p class="lede">{esc(intro)}</p></header>'
            + "".join(blocks))
    nodes = [{"@type": "CollectionPage", "@id": HOST + path + "#webpage", "url": HOST + path, "name": f"{name} costs",
              "description": intro, "isPartOf": {"@id": HOST + "/#website"}, "inLanguage": "en-US",
              "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": u} for i, u in enumerate(item_list)]}},
             crumbs_ld([("Home", "/"), (name, None)])]
    write(path, page_shell(f"{name} Costs (2026) | {SITE}", f"{name} prices in the US: {intro}"[:155], path, nodes, body, "website"))

# ---------------------------------------------------------------- home
def render_home():
    rows = []
    for name in PILLAR_ORDER:
        s = pillar_slug(name)
        if s in LIVE:
            fig, src = lead_figure(s)
            rows.append(f'<tr><td><a href="/{s}/">{esc(name)}</a></td><td>{esc(PAGES[s]["facts"][0]["label"])}</td><td><strong>{esc(fig)}</strong></td><td>{esc(src.split(" — ")[0])}</td></tr>')
    table = ('<div class="tbl"><table><caption>US dental procedure costs at a glance (national figures, no insurance)</caption>'
             '<thead><tr><th scope="col">Procedure</th><th scope="col">What is priced</th><th scope="col">Typical cost</th><th scope="col">Source</th></tr></thead><tbody>'
             + "".join(rows) + "</tbody></table></div>")
    cats = "".join(f'<li><a href="/{c[0]}/"><span class="card-t">{esc(c[1])}</span><span class="card-d">{esc(c[2])}</span></a></li>' for c in CATEGORIES)
    body = (f'<section class="hero"><h1>What does dental work cost in the US?</h1>'
            f'<p class="lede">Plain-English price guides for {len(PILLAR_ORDER)} common dental procedures, with every figure taken from published claims data and national cost surveys, and named on the page. Medically reviewed by {REVIEWER}, {REVIEWER_SUFFIX}.</p></section>'
            + '<div class="answer"><div class="answer-k">Quick answer</div><p>Most routine dental work costs between about <strong>$85 and $160 for a cleaning</strong> and <strong>$1,100 to $2,000 for a crown</strong>, while a single dental implant runs <strong>$2,800 to $5,600</strong> without insurance (Delta Dental claims data). Insurance usually pays 100% of preventive care, 80% of basic work and 50% of major work, up to an annual maximum.</p></div>'
            + table + f'<h2>Browse by treatment area</h2><ul class="cards cats">{cats}</ul>'
            + '<section class="method"><h2>Where our prices come from</h2><p>We use out-of-network claims data published by Delta Dental, the Synchrony / CareCredit Average Procedural Cost Study (2023–2024), GoodRx and dental-fee data based on the ADA Survey of Dental Fees. When two sources disagree we show both and explain why. <a href="/methodology/">Read the full methodology</a>.</p></section>')
    nodes = [{"@type": "WebPage", "@id": HOST + "/#webpage", "url": HOST + "/", "name": SITE,
              "description": "US dental procedure costs from published claims and survey data.", "isPartOf": {"@id": HOST + "/#website"},
              "about": {"@type": "Thing", "name": "Dental procedure costs in the United States"}, "inLanguage": "en-US"}]
    write("/", page_shell(f"{SITE}: What Dental Work Costs in the US (2026)",
                          "How much dental implants, braces, veneers, root canals, crowns, dentures and wisdom teeth removal cost in the US, from published claims and survey data.",
                          "/", nodes, body, "website"))

# ---------------------------------------------------------------- static pages
def static_pages():
    src_rows = "".join(
        f'<tr><td><a href="{u}" rel="noopener" target="_blank">{esc(n)}</a></td><td>{esc(w)}</td></tr>' for n, u, w in [
            ("Delta Dental cost guides", "https://www.deltadental.com/protect-my-smile/procedures/", "Average out-of-network charges from Delta Dental's internal claims data (2021–2025, year stated on each page)."),
            ("CareCredit dentist price list", "https://www.carecredit.com/dentistry/costs/", "Synchrony Average Procedural Cost Study, ASQ360° Market Research, 2023–2024, all 50 states and DC."),
            ("GoodRx procedure guides", "https://www.goodrx.com/health-topic/oral/cost-of-dentures", "Dentist-reviewed cost guides; used for denture types not covered elsewhere."),
            ("Pearl dental cost data", "https://dentalcosts.hellopearl.com/procedure/braces", "Population-weighted national averages based on ADA fee survey data (May 2026)."),
            ("Healthline", "https://www.healthline.com/health/dental-and-oral-health/teeth-bonding", "Dentist-reviewed articles; used for bonding and braces ranges."),
        ])
    pages = {
        "about": ("About Dental Price Guide", "Who runs Dental Price Guide, who reviews it, and why the site exists.",
            f"""<h1>About {SITE}</h1>
<p class="lede">{SITE} explains what common dental treatments cost in the United States, what changes the price, and how insurance and payment options affect what you pay.</p>
<h2>Why this site exists</h2><p>Dental prices are hard to find before you sit in the chair. Most dental offices do not publish fees, and insurers publish their data in different places with different definitions. We collect published cost data in one place, label where each number comes from, and explain it in plain English.</p>
<h2>Medical review</h2><p>Pages are medically reviewed by <strong>{REVIEWER}, {REVIEWER_SUFFIX}</strong> ({PMDC}), a medical doctor with 18 years of clinical and laboratory-medicine experience. Dr. Irshad checks pages for medical accuracy and safety advice. He is a physician, not a dentist, and he does not set or verify individual dental fees; prices come from the published sources listed on our <a href="/methodology/">methodology page</a>.</p>
<h2>What we do not do</h2><ul><li>We do not accept payment from dentists, clinics or product makers to appear on the site.</li><li>We do not recommend individual dentists.</li><li>We do not diagnose or give individual treatment advice.</li></ul>
<p>The site is supported by display advertising. Advertisers have no say in what we publish. Questions or corrections: <a href="/contact/">contact us</a>.</p>"""),
        "methodology": ("How We Price Dental Procedures", "Where every dental price on this site comes from, how we handle conflicting numbers, and how often we check them.",
            f"""<h1>How we price dental procedures</h1>
<p class="lede">Every dollar figure on {SITE} comes from a published, named source. We never estimate a price ourselves, and each page lists its sources at the bottom.</p>
<h2>Our sources</h2><div class="tbl"><table><thead><tr><th scope="col">Source</th><th scope="col">What it measures</th></tr></thead><tbody>{src_rows}</tbody></table></div>
<h2>Why two numbers sometimes differ</h2><p>Delta Dental reports what out-of-network dentists charged on real claims. The CareCredit study surveys practice prices. The two measure different things, so their averages can differ by a few hundred dollars. When they differ, we show both and say which is which.</p>
<h2>What our prices do not include</h2><p>National averages do not reflect your city, your dentist, your insurance plan or the complexity of your case. A root canal price, for example, usually does not include the crown that follows. Each page says what is and is not included where the source makes it clear.</p>
<h2>How often we check</h2><p>Prices were last checked in October 2026. We review sources at least twice a year and update a page's date when its figures change.</p>"""),
        "editorial-policy": ("Editorial Policy", "How Dental Price Guide researches, writes, reviews and corrects its pages.",
            f"""<h1>Editorial policy</h1>
<h2>Research</h2><p>Each page starts from a fixed set of sourced price facts. Writers may use only those figures. Clinical guidance follows mainstream sources such as the American Dental Association, specialty associations and major academic medical centers.</p>
<h2>Writing</h2><p>Pages answer the reader's question in the first sentence, use plain English, and say when something varies or is uncertain. We use AI-assisted drafting tools under these rules, and every page is checked against its source list before publishing.</p>
<h2>Review</h2><p>Pages are medically reviewed by {REVIEWER}, {REVIEWER_SUFFIX}. The review date appears at the top of each page.</p>
<h2>Corrections</h2><p>If you find an error, <a href="/contact/">tell us</a>. We correct factual errors promptly and update the page date.</p>
<h2>Independence</h2><p>We do not accept payment for coverage. Ads are served by Google AdSense and are labelled as ads by Google.</p>"""),
        "privacy": ("Privacy Policy", "How Dental Price Guide handles data, cookies and advertising.",
            f"""<h1>Privacy policy</h1><p>Last updated October 21, 2026.</p>
<h2>What we collect</h2><p>We do not ask you to create an account and we do not collect your name, email address or health information through the site. Our web server keeps standard access logs (IP address, browser type, pages requested, time) for security and troubleshooting.</p>
<h2>Advertising and cookies</h2><p>We use Google AdSense to show ads. Google and its partners use cookies to serve ads based on your visits to this and other websites. You can opt out of personalized advertising at <a href="https://www.google.com/settings/ads" rel="noopener" target="_blank">Google Ads Settings</a> or <a href="https://www.aboutads.info/choices/" rel="noopener" target="_blank">aboutads.info</a>. See <a href="https://policies.google.com/technologies/partner-sites" rel="noopener" target="_blank">how Google uses data from partner sites</a>.</p>
<h2>Your rights</h2><p>Residents of California, the EU and the UK have rights over personal data, including access and deletion. Because we do not hold personal data beyond server logs and ad cookies, most requests are handled through Google's controls above. For anything else, <a href="/contact/">contact us</a>.</p>
<h2>Children</h2><p>This site is intended for adults and does not knowingly collect data from children under 13.</p>"""),
        "disclaimer": ("Medical Disclaimer", "Dental Price Guide provides general information only and is not dental or medical advice.",
            f"""<h1>Medical and cost disclaimer</h1>
<p>{SITE} provides general information about dental procedures and their typical costs. It is not dental, medical, financial or insurance advice, and it does not create a doctor-patient relationship.</p>
<p>Prices are national averages from the sources named on each page. Your actual cost depends on your dentist, your location, your treatment plan and your insurance. Always get a written estimate from your dentist and a pre-treatment estimate from your insurer.</p>
<p><strong>Seek care promptly</strong> if you have facial or neck swelling, fever, trouble swallowing or breathing, bleeding that will not stop, or severe pain. These can be signs of a spreading infection.</p>"""),
        "contact": ("Contact Dental Price Guide", "How to contact Dental Price Guide with corrections, questions or data suggestions.",
            f"""<h1>Contact us</h1><p>For corrections, data sources we should consider, or general questions, email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</p>
<p>We cannot answer questions about your own treatment or give a price for your specific case; your dentist and your insurer are the right people for that.</p>
<p>{SITE} is published by Omnia Ventures.</p>"""),
    }
    for slug, (title, desc, html_body) in pages.items():
        path = f"/{slug}/"
        trail = [("Home", "/"), (title, None)]
        nodes = [{"@type": "AboutPage" if slug == "about" else "WebPage", "@id": HOST + path + "#webpage", "url": HOST + path,
                  "name": title, "description": desc, "isPartOf": {"@id": HOST + "/#website"}, "inLanguage": "en-US"}, crumbs_ld(trail)]
        write(path, page_shell(f"{title} | {SITE}", desc, path, nodes, breadcrumbs(trail) + f'<article class="post static">{html_body}</article>', "website"))

# ---------------------------------------------------------------- site files
def site_files():
    urls = [("/", TODAY, "1.0")] + [(f"/{c[0]}/", TODAY, "0.8") for c in CATEGORIES] + [(f"/{s}/", PUBLISH[s], "0.9" if IDX.get(s, {}).get("level") == "Pillar Page" else "0.7") for s in sorted(LIVE)] + [(f"/{s}/", PUBLISHED, "0.3") for s in STATIC]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d, pr in urls:
        sm.append(f"<url><loc>{HOST}{u}</loc><lastmod>{d}</lastmod><priority>{pr}</priority></url>")
    sm.append("</urlset>")
    open(os.path.join(OUT, "sitemap.xml"), "w").write("\n".join(sm))

    bots = ["*", "Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-Web", "anthropic-ai",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "Amazonbot", "Bytespider", "Meta-ExternalAgent", "cohere-ai"]
    rb = ["# Dental Price Guide — all search and AI answer-engine crawlers are welcome."]
    for b in bots:
        rb += [f"User-agent: {b}", "Allow: /", "Disallow: /_src/", "Disallow: /.github/", ""]
    rb.append(f"Sitemap: {HOST}/sitemap.xml")
    open(os.path.join(OUT, "robots.txt"), "w").write("\n".join(rb) + "\n")

    ll = [f"# {SITE}", "", f"> Independent guide to what dental procedures cost in the United States. Every price is a national figure taken from a named, published source (Delta Dental out-of-network claims data 2021–2025; Synchrony/CareCredit Average Procedural Cost Study 2023–2024; GoodRx; Pearl dental cost data based on the ADA fee survey). Pages are medically reviewed by {REVIEWER}, {REVIEWER_SUFFIX}. Prices last checked October 2026.", "",
          "## About", f"- [Methodology: where our prices come from]({HOST}/methodology/)", f"- [About and medical review]({HOST}/about/)", ""]
    for c in CATEGORIES:
        mem = [p for p in INDEX if p["category_slug"] == c[0] and p["slug"] in LIVE]
        if not mem: continue
        ll.append(f"## {c[1]}")
        for p in sorted(mem, key=lambda p: (p["level"] != "Pillar Page", p["pillar"])):
            sp = PAGES[p["slug"]]
            ll.append(f"- [{sp['h1']}]({HOST}/{p['slug']}/): {sp.get('description', '')}")
        ll.append("")
    open(os.path.join(OUT, "llms.txt"), "w").write("\n".join(ll))

    open(os.path.join(OUT, "ads.txt"), "w").write(f"google.com, {AD_CLIENT.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
    open(os.path.join(OUT, f"{INDEXNOW_KEY}.txt"), "w").write(INDEXNOW_KEY)
    open(os.path.join(OUT, "manifest.json"), "w").write(json.dumps({"name": SITE, "short_name": "Dental Prices", "start_url": "/", "display": "standalone",
        "background_color": "#ffffff", "theme_color": BRAND, "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"}]}))
    open(os.path.join(OUT, "favicon.svg"), "w").write(LOGO.replace(' class="mark"', ' xmlns="http://www.w3.org/2000/svg"').replace(' width="30" height="30" aria-hidden="true"', ''))
    open(os.path.join(OUT, ".htaccess"), "w").write(HTACCESS)
    open(os.path.join(OUT, "index.php"), "w").write("<?php http_response_code(404); readfile(__DIR__.'/404.html');\n")
    nf = page_shell(f"Page not found | {SITE}", "This page does not exist.", "/404/", [],
                    '<article class="post static"><h1>Page not found</h1><p>That page does not exist or has moved. Try the <a href="/">home page</a> or one of these sections:</p><ul>'
                    + "".join(f'<li><a href="/{c[0]}/">{esc(c[1])}</a></li>' for c in CATEGORIES) + "</ul></article>", "website", "noindex,follow")
    open(os.path.join(OUT, "404.html"), "w").write(nf)

HTACCESS = r"""# Dental Price Guide — Apache config for Cloudways
DirectoryIndex index.html index.php
RewriteEngine On
RewriteCond %{HTTPS} !=on
RewriteCond %{HTTP:X-Forwarded-Proto} !=https
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
RewriteCond %{HTTP_HOST} ^dentalpriceguide\.com$ [NC]
RewriteRule ^ https://www.dentalpriceguide.com%{REQUEST_URI} [L,R=301]
RewriteCond %{THE_REQUEST} \s/(.*/)?index\.html[\s?] [NC]
RewriteRule ^(.*/)?index\.html$ /%1 [R=301,L]
RewriteRule ^(_src|\.github|\.git)(/|$) - [F,L]
RewriteRule ^(README\.md|\.gitignore)$ - [F,L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} !/$
RewriteCond %{REQUEST_URI} !\.[a-z0-9]+$ [NC]
RewriteRule ^(.*)$ /$1/ [R=301,L]
ErrorDocument 404 /404.html
<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Strict-Transport-Security "max-age=31536000"
  <FilesMatch "\.(css|svg|png|ico|woff2)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\.(html|xml|txt)$">
    Header set Cache-Control "public, max-age=3600"
  </FilesMatch>
</IfModule>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/xml application/json image/svg+xml
</IfModule>
"""

CSS = """
:root{--b:#0f766e;--bd:#115e59;--ink:#1f2937;--mut:#5b6472;--line:#e5e7eb;--bg:#fff;--soft:#f0fdfa;--warn:#fff7ed}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;font:17px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--bd)}a:hover{color:var(--b)}
.wrap{max-width:780px;margin:0 auto;padding:0 18px}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px}
.site-head{border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:5}
.site-head .wrap{display:flex;align-items:center;gap:14px;max-width:1100px;min-height:58px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:8px;font-weight:700;color:var(--ink);text-decoration:none;font-size:18px}
.menu-btn{margin-left:auto;border:1px solid var(--line);background:#fff;border-radius:8px;font-size:20px;min-width:44px;min-height:44px}
.nav{display:none;width:100%;flex-direction:column;padding:6px 0 10px}.nav.open{display:flex}
.nav a{padding:10px 4px;text-decoration:none;color:var(--ink);border-top:1px solid var(--line)}
@media(min-width:1000px){.menu-btn{display:none}.nav{display:flex;flex-direction:row;width:auto;margin-left:auto;padding:0;gap:14px}.nav a{border:0;font-size:14.5px;padding:6px 0}}
main{padding:14px 18px 40px}
.crumbs{font-size:14px;color:var(--mut);margin:6px 0 14px}.crumbs a{color:var(--mut)}.sep{margin:0 4px}
h1{font-size:clamp(28px,5vw,38px);line-height:1.2;margin:.2em 0 .4em}
h2{font-size:clamp(22px,3.6vw,27px);line-height:1.3;margin:1.8em 0 .5em}
.byline{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:14px;color:var(--mut);margin-bottom:18px}
.answer{background:var(--soft);border-left:4px solid var(--b);padding:14px 18px;border-radius:8px;margin:16px 0}
.answer-k,.tk-k,.toc-k{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--bd);margin-bottom:4px}
.answer p{margin:.2em 0}
.takeaways{border:1px solid var(--line);border-radius:8px;padding:12px 18px;margin:16px 0}.takeaways ul{margin:.3em 0;padding-left:20px}
.toc{border:1px solid var(--line);border-radius:8px;padding:12px 18px;margin:18px 0;background:#fafafa}.toc ol{margin:.3em 0;padding-left:20px}.toc a{text-decoration:none}
.tbl{overflow-x:auto;margin:18px 0;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:15.5px}caption{text-align:left;padding:10px 12px;font-weight:600}
th,td{padding:9px 12px;border-top:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f8fafc}
.callout{background:var(--warn);border-left:4px solid #f59e0b;padding:10px 16px;border-radius:8px;margin:16px 0}
.callout.disclaimer{background:#f8fafc;border-color:#94a3b8;font-size:15px}
.faq details{border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:10px 14px}.faq summary{font-weight:600;cursor:pointer;min-height:28px}
.also{font-size:14.5px;color:var(--mut)}.also span{font-weight:600}
.sources{font-size:14.5px}.sources ol{padding-left:20px}.src-note{color:var(--mut)}
.cards{list-style:none;padding:0;display:grid;grid-template-columns:1fr;gap:10px}
@media(min-width:640px){.cards{grid-template-columns:1fr 1fr}}
.cards a{display:block;border:1px solid var(--line);border-radius:10px;padding:12px 14px;text-decoration:none;color:var(--ink);min-height:44px}
.cards a:hover{border-color:var(--b)}.card-t{display:block;font-weight:600}.card-d{display:block;font-size:14.5px;color:var(--mut);margin-top:4px}
.hero{padding:10px 0}.lede{font-size:18.5px;color:#374151}.lead-fig{margin:.2em 0 .6em}.lead-fig span{color:var(--mut);font-size:14px}
.hub-group h2 a{text-decoration:none}
.site-foot{border-top:1px solid var(--line);background:#f8fafc;margin-top:30px;font-size:14.5px;color:var(--mut)}
.site-foot .wrap{max-width:1100px;padding:24px 18px}
.foot-cols{display:grid;gap:18px}@media(min-width:800px){.foot-cols{grid-template-columns:2fr 1fr 1fr}}
.foot-links{display:flex;flex-direction:column;gap:6px}.foot-links a{color:var(--mut)}
"""

def assets():
    d = os.path.join(OUT, "assets", "css"); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "style.css"), "w").write(re.sub(r"\n+", "\n", CSS).strip())
    img = os.path.join(OUT, "assets", "img"); os.makedirs(img, exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        def font(sz):
            for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
                if os.path.exists(f): return ImageFont.truetype(f, sz)
            return ImageFont.load_default()
        og = Image.new("RGB", (1200, 630), "#0f766e"); dr = ImageDraw.Draw(og)
        dr.text((80, 210), SITE, fill="white", font=font(78)); dr.text((80, 330), "What dental work really costs in the US", fill="#ccfbf1", font=font(40))
        dr.text((80, 420), "Implants · Braces · Veneers · Root canals · Crowns · Dentures", fill="#ccfbf1", font=font(30))
        og.save(os.path.join(img, "og-default.png"), optimize=True)
        for sz, name in [(180, "icon-180.png"), (192, "icon-192.png"), (512, "icon-512.png"), (512, "logo.png")]:
            ic = Image.new("RGB", (sz, sz), "#0f766e"); di = ImageDraw.Draw(ic)
            r = sz * 0.28; cx = sz / 2
            di.ellipse([cx - r * 1.1, sz * .22, cx + r * 1.1, sz * .62], fill="white")
            di.rectangle([cx - r * .95, sz * .42, cx - r * .25, sz * .80], fill="white"); di.rectangle([cx + r * .25, sz * .42, cx + r * .95, sz * .80], fill="white")
            ic.save(os.path.join(img, name), optimize=True)
    except ImportError:
        print("Pillow not installed: skipping PNG assets")

# ---------------------------------------------------------------- clean + build
MANIFEST = os.path.join(SRC, ".built.json")
def clean():
    prev = load(MANIFEST, [])
    for d in prev:
        p = os.path.join(OUT, d)
        if os.path.isdir(p) and not d.startswith((".", "_")): shutil.rmtree(p)

def main():
    clean()
    built = []
    for s in sorted(LIVE): render_article(s); built.append(s)
    for c in CATEGORIES: render_hub(*c); built.append(c[0])
    static_pages(); built += STATIC
    render_home(); assets(); built.append("assets")
    site_files()
    json.dump(sorted(built), open(MANIFEST, "w"), indent=0)
    print(f"built {len(LIVE)} articles + {len(CATEGORIES)} hubs + {len(STATIC)} static pages | queued {len([p for p in INDEX if p['slug'] not in PUBLISH])}")

main()
