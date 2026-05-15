#!/usr/bin/env python3
"""
Fetch Disney-family studio movie/TV lists from TMDb and write tmdb_data.json.
generate_checklist.py reads that file and injects DATA into data.js.
"""

import json
import os
import time
import urllib.parse
import urllib.request

API_KEY = open(os.path.join(os.path.dirname(__file__), '.env')).read().strip().split('=')[1]
BASE = "https://api.themoviedb.org/3"
ANIMATION_GENRE = 16


def get(path, params=None):
    p = {"api_key": API_KEY, "language": "zh-TW"}
    if params:
        p.update(params)
    url = f"{BASE}{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def fetch_by_company(company_ids, media_type="movie", date_windows=None, max_pages=500):
    """
    Fetch and merge results across one or more company IDs.

    TMDb caps pagination at 500; for companies that exceed that (e.g. WDP id=3166
    with decades of content), pass `date_windows=[(start, end), ...]` so each window
    paginates independently.
    """
    if isinstance(company_ids, int):
        company_ids = [company_ids]
    endpoint = "/discover/movie" if media_type == "movie" else "/discover/tv"
    sort_field = "release_date.asc" if media_type == "movie" else "first_air_date.asc"
    date_field = "primary_release_date" if media_type == "movie" else "first_air_date"

    merged = {}
    for cid in company_ids:
        windows = date_windows or [(None, None)]
        for lo, hi in windows:
            page = 1
            while True:
                params = {"with_companies": cid, "sort_by": sort_field, "page": page}
                if lo: params[f"{date_field}.gte"] = lo
                if hi: params[f"{date_field}.lte"] = hi
                data = get(endpoint, params)
                for it in data.get("results", []):
                    merged[it["id"]] = it
                total = data.get("total_pages", 1)
                if page >= total or page >= max_pages:
                    break
                page += 1
                time.sleep(0.2)
    return list(merged.values())


def normalize_movies(items):
    """Dedupe + project movie fields used downstream, sorted by year."""
    seen, out = set(), []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        date = it.get("release_date", "") or ""
        out.append({
            "id": it["id"],
            "title": it.get("title") or it.get("name") or "",
            "original_title": it.get("original_title") or "",
            "year": int(date[:4]) if date[:4].isdigit() else 0,
            "genre_ids": it.get("genre_ids", []),
            "vote_average": it.get("vote_average", 0),
            "popularity": it.get("popularity", 0),
        })
    out.sort(key=lambda x: (x["year"], x["title"]))
    return out


def normalize_tv(items):
    """Same projection but for TV items (uses name + first_air_date)."""
    seen, out = set(), []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        date = it.get("first_air_date", "") or ""
        out.append({
            "id": it["id"],
            "title": it.get("name") or it.get("original_name") or "",
            "year": int(date[:4]) if date[:4].isdigit() else 0,
            "popularity": it.get("popularity", 0),
        })
    out.sort(key=lambda x: (x["year"], x["title"]))
    return out


def split_by_genre(items, genre_id):
    """Returns (with_genre, without_genre)."""
    yes = [m for m in items if genre_id in m["genre_ids"]]
    no = [m for m in items if genre_id not in m["genre_ids"]]
    return yes, no


# ── Sources ──────────────────────────────────────────────────────────────────
# TMDb company IDs (verified live).
#   Walt Disney umbrella spans several legal entities across decades; we merge
#   all of them and dedupe by TMDb movie id.
SOURCES = {
    "disney_animation": {
        "ids": [3166, 171656, 6125],        # WDP classic / WDFA / WDAS
        "date_windows": [                    # WDP (3166) exceeds 500-page cap
            ("1900-01-01", "1953-12-31"),
            ("1954-01-01", "1985-12-31"),
            ("1986-01-01", None),
        ],
    },
    "pixar":             {"ids": [3]},
    "marvel":            {"ids": [420]},
    "lucasfilm":         {"ids": [1]},
    "disney_pictures":   {"ids": [2]},       # split into animation/liveaction below
    "touchstone":        {"ids": [9195]},    # split into animation/liveaction below
    "searchlight":       {"ids": [43, 127929]},  # legacy + current names
    "hollywood_pictures":{"ids": [915]},
    "disneynature":      {"ids": [4436]},
    "fox":               {"ids": [25, 127928, 11749, 141821, 9383]},  # 20th Century group + Blue Sky
    "disney_channel":    {"ids": [240533, 241787]},  # HSM / Camp Rock / Descendants etc.
}

TV_SOURCES = {
    "marvel_tv":    [420],
    "lucasfilm_tv": [1],
}

# Rescue list: titles TMDb fails to tag under any Disney company.
# Each entry fetches /movie/{id} directly and appends to the named bucket.
RESCUE_MOVIE_IDS = {
    "disney_channel_liveaction": [
        10947,  # High School Musical (2006) — TMDb only credits Salty Pictures
        11887,  # High School Musical 3: Senior Year (2008) — pop too low for theatrical bucket
    ],
}


def fetch_movie_by_id(movie_id):
    """Fetch a single movie's full record, shaped like /discover results."""
    d = get(f"/movie/{movie_id}")
    return {
        "id": d["id"],
        "title": d.get("title") or d.get("original_title", ""),
        "original_title": d.get("original_title", ""),
        "release_date": d.get("release_date", ""),
        "genre_ids": [g["id"] for g in d.get("genres", [])],
        "vote_average": d.get("vote_average", 0),
        "popularity": d.get("popularity", 0),
    }

# ── Fetch ────────────────────────────────────────────────────────────────────

print("🎬 Fetching movie sources…")
raw_movies = {}
for key, cfg in SOURCES.items():
    print(f"   • {key} (ids={cfg['ids']})")
    items = fetch_by_company(cfg["ids"], date_windows=cfg.get("date_windows"))
    raw_movies[key] = normalize_movies(items)
    print(f"     → {len(raw_movies[key])} 部")

print("\n📺 Fetching TV sources…")
raw_tv = {}
for key, ids in TV_SOURCES.items():
    items = fetch_by_company(ids, media_type="tv")
    raw_tv[key] = normalize_tv(items)
    print(f"   • {key}: {len(raw_tv[key])} 部")

# ── Post-processing ──────────────────────────────────────────────────────────

# WDP (id=2) contains both animation (mostly remake live-action like 2019 Lion King
# which TMDb still tags as animation) and pure live-action. Split by genre.
wdp_anim, wdp_live = split_by_genre(raw_movies["disney_pictures"], ANIMATION_GENRE)

# Dedupe WDP-animation against disney_animation (avoid Lion King appearing twice).
disney_ids = {m["id"] for m in raw_movies["disney_animation"]}
wdp_anim = [m for m in wdp_anim if m["id"] not in disney_ids]

# Pixar films are also distributed by WDP — keep them out of WDP-liveaction.
pixar_ids = {m["id"] for m in raw_movies["pixar"]}
wdp_live = [m for m in wdp_live if m["id"] not in pixar_ids]

touch_anim, touch_live = split_by_genre(raw_movies["touchstone"],      ANIMATION_GENRE)
fox_anim,   fox_live   = split_by_genre(raw_movies["fox"],             ANIMATION_GENRE)
dch_anim,   dch_live   = split_by_genre(raw_movies["disney_channel"],  ANIMATION_GENRE)

# Rescue: pull individual movies by id and merge into named buckets.
print("\n🩹 Fetching rescue ids…")
buckets = {
    "disney_channel_liveaction": dch_live,
    "disney_channel_animation":  dch_anim,
}
for bucket_key, ids in RESCUE_MOVIE_IDS.items():
    existing = {m["id"] for m in buckets.get(bucket_key, [])}
    for mid in ids:
        if mid in existing:
            continue
        raw_item = fetch_movie_by_id(mid)
        normalized = normalize_movies([raw_item])[0]
        buckets[bucket_key].append(normalized)
        print(f"   • {normalized['year']} {normalized['title']} → {bucket_key}")
    buckets[bucket_key].sort(key=lambda x: (x["year"], x["title"]))

output = {
    "disney_animation":           raw_movies["disney_animation"],
    "pixar":                      raw_movies["pixar"],
    "marvel":                     raw_movies["marvel"],
    "lucasfilm":                  raw_movies["lucasfilm"],
    "disney_pictures_animation":  wdp_anim,
    "disney_pictures_liveaction": wdp_live,
    "touchstone_animation":       touch_anim,
    "touchstone_liveaction":      touch_live,
    "fox_animation":              fox_anim,
    "fox_liveaction":             fox_live,
    "disney_channel_animation":   dch_anim,
    "disney_channel_liveaction":  dch_live,
    "searchlight":                raw_movies["searchlight"],
    "hollywood_pictures":         raw_movies["hollywood_pictures"],
    "disneynature":               raw_movies["disneynature"],
    "marvel_tv":                  raw_tv["marvel_tv"],
    "lucasfilm_tv":               raw_tv["lucasfilm_tv"],
}

with open("tmdb_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n✅ tmdb_data.json updated\n")
print("📊 摘要：")
for key, items in output.items():
    print(f"   {key:30s} {len(items):4d} 筆")
