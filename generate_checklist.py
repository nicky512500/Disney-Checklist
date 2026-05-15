#!/usr/bin/env python3
"""
Read tmdb_data.json → generate DATA constant → write data.js.

disney-checklist.html loads data.js via <script src>; if you change keys here,
update the HTML accordingly.
"""
import json

raw = json.load(open('tmdb_data.json'))

ANIM_GENRE = 16


# ── Filtering / shaping ─────────────────────────────────────────────────────

def dedup_sort(movies, min_pop=0, min_year=1, max_year=2030,
               title_filter=None, id_blacklist=()):
    seen, out = set(), []
    blacklist = set(id_blacklist)
    for m in movies:
        if m['year'] < min_year or m['year'] > max_year:
            continue
        if m['popularity'] < min_pop:
            continue
        if title_filter and not title_filter(m):
            continue
        if m.get('id') in blacklist:
            continue
        key = m['title'].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        orig = m.get('original_title') or ''
        orig = orig if orig.lower().strip() != key else ''
        out.append({"title": m['title'], "year": m['year'], "orig": orig,
                    "id": m.get('id')})
    out.sort(key=lambda x: (x['year'], x['title']))
    return out


def yr(items, lo, hi):
    return [i for i in items if lo <= i['year'] <= hi]


def is_animated(m):
    return ANIM_GENRE in m.get('genre_ids', [])


def clean_tv(tv_list, min_pop=5, min_year=2021, title_filter=None):
    seen, out = set(), []
    for m in tv_list:
        if m['year'] < min_year or m['popularity'] < min_pop:
            continue
        if title_filter and not title_filter(m):
            continue
        k = m['title'].lower().strip()
        if k in seen:
            continue
        seen.add(k)
        out.append({'title': m['title'], 'year': m['year']})
    out.sort(key=lambda x: (x['year'], x['title']))
    return out


def include_by_id(source_pool, ids):
    """Force-include specific TMDb ids from a raw pool (used to rescue items
    that fall below the popularity threshold but are part of the canon)."""
    wanted = set(ids)
    return [m for m in source_pool if m['id'] in wanted]


# ── Group rules ──────────────────────────────────────────────────────────────
GROUP_RULES = [
    (["mater", "el materdor"],                         "Cars Toons"),
    (["prep & landing", "prep&landing"],               "Prep & Landing"),
    (["toy story of terror", "toy story that time",
      "lamp life", "partysaurus", "hawaiian vacation",
      "small fry"],                                    "Toy Story Shorts"),
    (["sparkshort", "purl", "smash and grab", "kitbull",
      "float", "loop (", "out (", "wind (", "burrow",
      "twenty something", "nona (", "adelaide ("],     "SparkShorts"),
    (["dug days", "dug's special"],                    "Dug Shorts"),
    (["frozen fever", "olaf", "雪寶", "once upon a snowman"], "Frozen Shorts"),
    (["jack-jack attack", "jack jack"],                "Incredibles Shorts"),
    (["cars on the road"],                             "Cars Shorts"),
    (["mike's new car"],                               "Monsters Shorts"),
]


def assign_group(item):
    t = (item.get('title', '') + ' ' + item.get('orig', '')).lower()
    for patterns, group in GROUP_RULES:
        if any(p in t for p in patterns):
            return group
    return ''


def js_items(items):
    lines = []
    for i in items:
        t = i['title'].replace("\\", "\\\\").replace('"', '\\"')
        orig = (i.get('orig') or '').replace("\\", "\\\\").replace('"', '\\"')
        group = assign_group(i).replace("\\", "\\\\").replace('"', '\\"')
        orig_field = f', orig: "{orig}"' if orig else ''
        group_field = f', group: "{group}"' if group else ''
        lines.append(f'          {{ title: "{t}", year: {i["year"]}{orig_field}{group_field} }},')
    return '\n'.join(lines)


def js_section(key, label, icon, cat, subsections, extra_cats=None):
    all_cats = [cat] + (extra_cats or [])
    cats_js = '[' + ', '.join(f'"{c}"' for c in all_cats) + ']'
    parts = [f'  {key}: {{',
             f'    label: "{label}",',
             f'    icon: "{icon}",',
             f'    cat: "{cat}",',
             f'    cats: {cats_js},',
             '    subsections: [']
    for sub in subsections:
        if not sub['items']:
            continue
        lbl = sub['label'].replace('"', '\\"')
        parts.append('      {')
        parts.append(f'        label: "{lbl}",')
        parts.append('        items: [')
        parts.append(js_items(sub['items']))
        parts.append('        ]')
        parts.append('      },')
    parts.append('    ]')
    parts.append('  },')
    return '\n'.join(parts)


# ── Disney Animation ─────────────────────────────────────────────────────────
# Merge WDAS/WDFA/WDP classic (under 'disney_animation') with Touchstone
# animated features (Nightmare Before Christmas, Roger Rabbit, Gnomeo).
da_pool = raw['disney_animation'] + raw.get('touchstone_animation', [])

# Hand-pick features that live below the popularity threshold but are part of
# the canon (Rescuers Down Under, Make Mine Music, So Dear to My Heart, etc.).
# IDs are stable; verified against tmdb_data.json.
DA_FORCE_IDS = [
    11135,   # The Rescuers Down Under (1990)
    20343,   # Make Mine Music (1946)
    29682,   # So Dear to My Heart (1948)
    22752,   # The Reluctant Dragon (1941)
    11114,   # Pete's Dragon (1977)
]
da = dedup_sort(da_pool, min_pop=2, min_year=1937, title_filter=is_animated)
forced = dedup_sort(include_by_id(da_pool, DA_FORCE_IDS), title_filter=is_animated)
da_titles = {i['title'].lower() for i in da}
da.extend(m for m in forced if m['title'].lower() not in da_titles)
da.sort(key=lambda x: (x['year'], x['title']))

disney_js = js_section('disney', 'Disney 動畫', '🏰', 'disney', [
    {'label': '黃金時代 1937–1959', 'items': yr(da, 1937, 1959)},
    {'label': '銀幕時代 1960–1988',  'items': yr(da, 1960, 1988)},
    {'label': '文藝復興 1989–1999',  'items': yr(da, 1989, 1999)},
    {'label': '2000–2009',           'items': yr(da, 2000, 2009)},
    {'label': '2010–今',             'items': yr(da, 2010, 2030)},
])

# ── Pixar features ───────────────────────────────────────────────────────────
px = dedup_sort(raw['pixar'], min_pop=4, min_year=1995)
pixar_js = js_section('pixar', 'Pixar', '💡', 'pixar', [
    {'label': '1995–2010', 'items': yr(px, 1995, 2010)},
    {'label': '2011–2019', 'items': yr(px, 2011, 2019)},
    {'label': '2020–今',   'items': yr(px, 2020, 2030)},
])

# ── Pixar shorts ─────────────────────────────────────────────────────────────
px_all   = dedup_sort(raw['pixar'], min_pop=0.3, min_year=1986)
feat_set = {i['title'].lower() for i in px}
px_shorts = [i for i in px_all if i['title'].lower() not in feat_set]
pixar_shorts_js = js_section('shorts_pixar', 'Pixar 短篇', '💫', 'shorts', [
    {'label': '早期短片 1986–1999', 'items': yr(px_shorts, 1986, 1999)},
    {'label': '劇院附映 2000–2015', 'items': yr(px_shorts, 2000, 2015)},
    {'label': '近期短片 2016–今',   'items': yr(px_shorts, 2016, 2030)},
], extra_cats=['pixar'])

# ── Disney Animation shorts ──────────────────────────────────────────────────
da_all   = dedup_sort(da_pool, min_pop=1.0, min_year=1928, title_filter=is_animated)
feat_da  = {i['title'].lower() for i in da}
da_shorts = [i for i in da_all if i['title'].lower() not in feat_da]
disney_shorts_js = js_section('shorts_disney', 'Disney 動畫短篇', '🎞️', 'shorts', [
    {'label': '早期短片 1928–1999', 'items': yr(da_shorts, 1928, 1999)},
    {'label': '2000–2015',          'items': yr(da_shorts, 2000, 2015)},
    {'label': '2016–今',            'items': yr(da_shorts, 2016, 2030)},
], extra_cats=['disney'])

# ── Marvel MCU ───────────────────────────────────────────────────────────────
# Exclude pre-MCU films TMDb mis-tags under Marvel Studios.
MCU_EXCLUDE_IDS = {
    13056,  # Punisher: War Zone (2008, Lionsgate)
    1250,   # Ghost Rider (2007, Sony/Columbia)
    1979,   # Fantastic Four: Rise of the Silver Surfer (2007, Fox)
    559,    # Spider-Man 3 (2007, Sony)
}
# Rescue MCU Disney+ specials that fall below the pop=8 threshold.
MCU_FORCE_IDS = [
    894205,  # Werewolf by Night (2022)
    774752,  # The Guardians of the Galaxy Holiday Special (2022)
]
mcu_main = dedup_sort(raw['marvel'], min_pop=8, min_year=2008,
                      id_blacklist=MCU_EXCLUDE_IDS)
mcu_extra = dedup_sort(include_by_id(raw['marvel'], MCU_FORCE_IDS))
mcu_titles = {i['title'].lower() for i in mcu_main}
mcu = mcu_main + [m for m in mcu_extra if m['title'].lower() not in mcu_titles]
mcu.sort(key=lambda x: (x['year'], x['title']))

marvel_js = js_section('marvel', 'Marvel (MCU)', '🦸', 'marvel', [
    {'label': 'Phase 1 (2008–2012)',   'items': yr(mcu, 2008, 2012)},
    {'label': 'Phase 2 (2013–2015)',   'items': yr(mcu, 2013, 2015)},
    {'label': 'Phase 3 (2016–2019)',   'items': yr(mcu, 2016, 2019)},
    {'label': 'Phase 4 (2021–2022)',   'items': yr(mcu, 2020, 2022)},
    {'label': 'Phase 5–6 (2023–今)',   'items': yr(mcu, 2023, 2030)},
])

# ── Marvel TV ────────────────────────────────────────────────────────────────
mv_tv = clean_tv(raw['marvel_tv'], min_pop=5, min_year=2021)
marvel_tv_js = js_section('series_marvel', 'Marvel 劇集 (Disney+)', '📺', 'series', [
    {'label': '2021–2022', 'items': yr(mv_tv, 2021, 2022)},
    {'label': '2023–今',   'items': yr(mv_tv, 2023, 2030)},
])

# ── Star Wars films ──────────────────────────────────────────────────────────
SW_KW = ['星際大戰', 'star wars', 'rogue one', 'solo:', 'clone wars']
def is_sw(m):
    return any(k in m['title'].lower() for k in SW_KW)

sw_all = dedup_sort(raw['lucasfilm'], min_pop=5, min_year=1977, title_filter=is_sw)

# Classify each SW film explicitly so spin-offs don't leak into the trilogies.
ORIGINAL_KW = ['四部曲', '五部曲', '六部曲']
PREQUEL_KW  = ['首部曲', '二部曲', '三部曲']
SEQUEL_KW   = ['七部曲', '最後的絕地武士', '天行者的崛起']
SPINOFF_KW  = ['外傳', 'rogue one', 'solo']

def classify_sw(m):
    t = m['title'].lower()
    if any(k in m['title'] for k in ORIGINAL_KW): return 'original'
    if any(k in m['title'] for k in PREQUEL_KW):  return 'prequel'
    if any(k in m['title'] for k in SEQUEL_KW):   return 'sequel'
    if any(k in t           for k in SPINOFF_KW): return 'spinoff'
    return 'spinoff'

sw_buckets = {'original': [], 'prequel': [], 'sequel': [], 'spinoff': []}
for m in sw_all:
    sw_buckets[classify_sw(m)].append(m)

starwars_js = js_section('starwars', 'Star Wars', '⭐', 'starwars', [
    {'label': '原三部曲 Original Trilogy',  'items': sw_buckets['original']},
    {'label': '前傳三部曲 Prequel Trilogy', 'items': sw_buckets['prequel']},
    {'label': '後傳三部曲 Sequel Trilogy',  'items': sw_buckets['sequel']},
    {'label': '外傳 & 電影特輯',            'items': sw_buckets['spinoff']},
])

# ── Indiana Jones ────────────────────────────────────────────────────────────
IJ_KW = ['法櫃奇兵', 'indiana jones', '魔宮傳奇', '聖戰奇兵', '水晶', '命運輪盤']
def is_ij(m):
    return any(k in m['title'].lower() for k in IJ_KW)
ij = dedup_sort(raw['lucasfilm'], min_pop=5, min_year=1981, title_filter=is_ij)
ij_js = js_section('indiana_jones', 'Indiana Jones', '🤠', 'liveaction', [
    {'label': '全系列', 'items': ij},
])

# ── Star Wars TV ─────────────────────────────────────────────────────────────
SW_TV_KW = ['星際大戰', 'star wars', '曼達洛', '波巴費特', '歐比王', '安道爾',
            '亞蘇卡', '瑕疵小隊', '視界', '抵抗勢力', '反抗軍', 'clone wars',
            '絕地傳奇', '帝國傳說', '骨幹小隊', '侍者', '暗影']
def is_sw_tv(m):
    return any(k in m['title'].lower() for k in SW_TV_KW)

sw_tv = clean_tv(raw['lucasfilm_tv'], min_pop=4, min_year=2003, title_filter=is_sw_tv)
sw_tv_js = js_section('series_starwars', 'Star Wars 劇集', '🌌', 'series', [
    {'label': '動畫劇集', 'items': [m for m in sw_tv if m['year'] <= 2018]},
    {'label': '真人劇集', 'items': [m for m in sw_tv if m['year'] >= 2019]},
])

# ── Disney live-action (Disney Pictures + Touchstone + Hollywood Pictures) ──
# Lowered min_pop from 8 → 6 so National Treasure, Pearl Harbor, Enchanted,
# Prince of Persia, Jungle Cruise etc. no longer get filtered out.
live_pool = (raw['disney_pictures_liveaction']
             + raw.get('touchstone_liveaction', [])
             + raw.get('hollywood_pictures', []))
la = dedup_sort(live_pool, min_pop=6, min_year=1950)
liveaction_js = js_section('liveaction', 'Disney 真人電影', '🎭', 'liveaction', [
    {'label': '1950–1989', 'items': yr(la, 1950, 1989)},
    {'label': '1990–2009', 'items': yr(la, 1990, 2009)},
    {'label': '2010–今',   'items': yr(la, 2010, 2030)},
])

# ── Disney live-action remakes ───────────────────────────────────────────────
# disney_pictures_animation is the remake-source pool (animation-genre-tagged
# titles distributed by WDP that aren't actually WDAS originals — e.g. Lion King
# 2019). Pixar films sneak in here because WDP also distributes Pixar — filter.
pixar_all_titles = {m['title'].lower() for m in dedup_sort(raw['pixar'], min_pop=0)}
NON_REMAKE_KW = ['葛瑞', 'diary of a wimpy', 'planes', '飛機總動員', 'recess', 'doug']

la2_raw = dedup_sort(raw['disney_pictures_animation'], min_pop=5, min_year=2010)
la2 = [m for m in la2_raw
       if m['title'].lower() not in pixar_all_titles
       and not any(k in m['title'].lower() for k in NON_REMAKE_KW)]

REMAKE_KW = ['仙履奇緣', '小美人魚', '阿拉丁', '花木蘭', '白雪公主',
             '星際寶貝：史迪奇', '美女與野獸', '彼得潘', '時尚惡女',
             '黑魔女', '魔境夢遊']
la_extra = [m for m in la if any(k in m['title'] for k in REMAKE_KW)]
la2_titles = {x['title'] for x in la2}
la2_all = la2 + [m for m in la_extra if m['title'] not in la2_titles]
la2_all.sort(key=lambda x: (x['year'], x['title']))

remake_js = js_section('liveaction_remake', 'Disney 真人版翻拍', '🎬', 'liveaction', [
    {'label': '2010–2019', 'items': yr(la2_all, 2010, 2019)},
    {'label': '2020–今',   'items': yr(la2_all, 2020, 2030)},
])

# ── 20th Century Studios (Fox) ───────────────────────────────────────────────
fox_anim_pool = raw.get('fox_animation', [])
fox_live_pool = raw.get('fox_liveaction', [])

fox_anim = dedup_sort(fox_anim_pool, min_pop=5, min_year=1990, title_filter=is_animated)
fox_live = dedup_sort(fox_live_pool, min_pop=10, min_year=1970)

fox_js = js_section('fox', '20th Century 動畫', '🦊', 'shorts', [
    {'label': '冰原歷險記 / Blue Sky', 'items': [m for m in fox_anim if 'ice age' in (m.get('orig','').lower()) or '冰原' in m['title']]},
    {'label': '其他動畫',              'items': [m for m in fox_anim if not ('ice age' in (m.get('orig','').lower()) or '冰原' in m['title'])]},
], extra_cats=['disney'])

fox_live_js = js_section('fox_live', '20th Century 真人', '🎞️', 'liveaction', [
    {'label': '1970–1999', 'items': yr(fox_live, 1970, 1999)},
    {'label': '2000–2014', 'items': yr(fox_live, 2000, 2014)},
    {'label': '2015–今',   'items': yr(fox_live, 2015, 2030)},
])

# ── Searchlight ──────────────────────────────────────────────────────────────
sl = dedup_sort(raw.get('searchlight', []), min_pop=8, min_year=1995)
searchlight_js = js_section('searchlight', 'Searchlight Pictures', '🔦', 'liveaction', [
    {'label': '1995–2009', 'items': yr(sl, 1995, 2009)},
    {'label': '2010–今',   'items': yr(sl, 2010, 2030)},
])

# ── Disneynature ─────────────────────────────────────────────────────────────
dn = dedup_sort(raw.get('disneynature', []), min_pop=1, min_year=2007)
disneynature_js = js_section('disneynature', 'Disneynature 紀錄片', '🌍', 'liveaction', [
    {'label': '全系列', 'items': dn},
])

# ── Disney Channel TV movies ─────────────────────────────────────────────────
# Lower threshold than theatrical (TV movies are intrinsically less "popular").
dch_pool = raw.get('disney_channel_liveaction', []) + raw.get('disney_channel_animation', [])
dch = dedup_sort(dch_pool, min_pop=1.5, min_year=1997)
dch_js = js_section('disney_channel', 'Disney Channel 電視電影', '📡', 'liveaction', [
    {'label': '1997–2009', 'items': yr(dch, 1997, 2009)},
    {'label': '2010–今',   'items': yr(dch, 2010, 2030)},
])

# ── Assemble DATA object ─────────────────────────────────────────────────────
all_sections = '\n\n'.join([
    disney_js,
    pixar_js,
    marvel_js,
    marvel_tv_js,
    starwars_js,
    sw_tv_js,
    remake_js,
    liveaction_js,
    ij_js,
    fox_js,
    fox_live_js,
    searchlight_js,
    disneynature_js,
    dch_js,
    disney_shorts_js,
    pixar_shorts_js,
])

# data.js: window.DATA so the page can load it via <script src> (works under
# file://, which fetch() would not).
with open('data.js', 'w', encoding='utf-8') as f:
    f.write(f"window.DATA = {{\n{all_sections}\n}};\n")

print("✅ data.js 已產生")

# Summary
totals = {
    'disney': da, 'pixar': px, 'marvel': mcu,
    'marvel_tv': mv_tv, 'starwars': sw_all, 'sw_tv': sw_tv,
    'liveaction_remake': la2_all, 'liveaction': la,
    'indiana_jones': ij,
    'fox_animation': fox_anim, 'fox_liveaction': fox_live,
    'searchlight': sl, 'disneynature': dn, 'disney_channel': dch,
    'disney_shorts': da_shorts, 'pixar_shorts': px_shorts,
}
print("\n📊 各分類筆數：")
for k, v in totals.items():
    print(f"   {k:25s}  {len(v):4d} 筆")
print(f"\n   {'總計':25s}  {sum(len(v) for v in totals.values()):4d} 筆")
