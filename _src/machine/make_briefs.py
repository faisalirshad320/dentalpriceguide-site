import json, re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from facts import S, P, CATEGORY

pages = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'dental_pages.json')))

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('$', '')).strip('-')

# fix URLs: flat, keyword-bearing
for o in pages:
    if o['url'] and o['url'] != '/':
        o['slug'] = o['url'].strip('/')
    else:
        o['slug'] = slugify(o['page'])
SLUG_FIX={'how-long-does-a-filling-take':'cavity-filling','braces-cost-with-insurance':'braces-cost-insurance','is-teeth-whitening-covered-by-insurance':'teeth-whitening-insurance','does-insurance-cover-wisdom-teeth-removal':'wisdom-teeth-removal-insurance'}
for o in pages: o['slug']=SLUG_FIX.get(o['slug'],o['slug'])
# ensure unique
seen = set()
for o in pages:
    s = o['slug']; i = 2
    while s in seen: s = f"{o['slug']}-{i}"; i += 1
    o['slug'] = s; seen.add(s)

by_pillar = {}
for o in pages: by_pillar.setdefault(o['pillar'], []).append(o)

def is_cost(o):
    return bool(re.search(r'cost|price|how much|insurance|\$|cheap|afford|free|grant', o['page'] + ' ' + o['main']))

def page_kind(o):
    p = o['page']
    if o['level'] == 'Pillar Page': return 'pillar'
    if ' vs ' in p: return 'comparison'
    if p.startswith('best '): return 'bestof'
    if is_cost(o): return 'cost'
    return 'info'

# launch tranche = all pillars + top 30 subs by cluster volume
pillars = [o for o in pages if o['level'] == 'Pillar Page']
subs = sorted([o for o in pages if o['level'] != 'Pillar Page'], key=lambda o: -o['vol'])
launch = set(o['slug'] for o in pillars) | set(o['slug'] for o in subs[:30])

def related_for(o):
    sib = [x for x in by_pillar[o['pillar']] if x is not o]
    pil = [x for x in sib if x['level'] == 'Pillar Page']
    others = sorted([x for x in sib if x['level'] != 'Pillar Page'], key=lambda x: -x['vol'])
    rel = pil + others[: (6 if o['level'] == 'Pillar Page' else 3)]
    if o['level'] == 'Pillar Page':
        rel = sorted(sib, key=lambda x: -x['vol'])  # pillar links to ALL its subs
    return [{"title": x['page'][0].upper() + x['page'][1:], "url": "/" + x['slug'] + "/", "anchor": x['main']} for x in rel]

items = []
for o in pages:
    pf = P[o['pillar']]
    cite_keys = list(dict.fromkeys([k for _, _, k in pf['facts']] + pf['cite']))
    sources = [{"key": k, "url": S[k][0], "name": S[k][1]} for k in cite_keys]
    facts = [{"label": l, "value": v, "source": S[k][1], "url": S[k][0]} for l, v, k in pf['facts']]
    kind = page_kind(o)
    variations = o['variations']
    questions = [v for v in variations if re.match(r'^(how|what|when|why|can|do|does|is|are|should|will|where|which)\b', v)]
    cat, catslug = CATEGORY[o['pillar']]
    items.append({
        "slug": o['slug'], "path": "/" + o['slug'] + "/",
        "primary": o['main'], "primary_volume": o['main_vol'], "kd": int(o['main_kd'] or 0),
        "topic": ('what is a cavity filling and how long it takes' if o['slug']=='cavity-filling' else o['page']), "pillar": o['pillar'], "level": o['level'], "kind": kind,
        "category": cat, "category_slug": catslug,
        "variations": variations[:40], "question_variations": questions[:15],
        "cluster_volume": o['vol'], "why": o['why'],
        "facts": facts, "sources": sources,
        "related": related_for(o),
        "launch": o['slug'] in launch,
        "word_target": "1800-2400" if o['level'] == 'Pillar Page' else "1000-1500",
    })

items.sort(key=lambda t: (not t['launch'], t['level'] != 'Pillar Page', -t['cluster_volume']))
out = os.path.join(os.path.dirname(__file__), 'out'); os.makedirs(out, exist_ok=True)
json.dump([t for t in items if t['launch']], open(os.path.join(out, 'dental-input-launch.json'), 'w'), indent=1)
json.dump([t for t in items if not t['launch']], open(os.path.join(out, 'dental-input-rest.json'), 'w'), indent=1)
json.dump(items, open(os.path.join(out, 'pages-index.json'), 'w'), indent=1)
print('launch', sum(t['launch'] for t in items), 'rest', sum(not t['launch'] for t in items))
from collections import Counter
print(Counter(t['kind'] for t in items))
