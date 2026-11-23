import time
import requests  # library for making web requests to other servers

# The NYC Open Data endpoint for restaurant inspections.
# 43nn-pn8j is the dataset ID. One row per inspection, ~297,000 rows.
BASE_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

# ---------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------
# Every page load would otherwise hit the city's API, which rate-limits
# anonymous requests. Results are held in memory for an hour.
# Restaurant inspections update daily at most, so this costs nothing
# in freshness.

_cache = {}
CACHE_SECONDS = 3600  # 1 hour


def _cache_get(key):
    entry = _cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.time() - stored_at > CACHE_SECONDS:
        return None          # expired, treat as a miss
    return value


def _cache_set(key, value):
    _cache[key] = (time.time(), value)


# ---------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------
# The city's grade column mixes actual grades with status codes.
# A, B and C are grades. N, Z and P mean an inspection happened but no
# grade was issued, so showing them raw next to an A would mislead.

GRADE_LABELS = {
    "A": "A",
    "B": "B",
    "C": "C",
    "N": "Not yet graded",
    "Z": "Grade pending",
    "P": "Grade pending",
}

REAL_GRADES = ("A", "B", "C")


def clean(row):
    """Turn one raw city row into the fields Bite Club uses.

    The city uses its own column names (dba, camis). Templates shouldn't
    have to know those, so everything gets renamed here, in one place.
    """
    grade = row.get("grade", "")

    return {
        # camis is the city's permanent ID for a restaurant.
        # Used as restaurant_id in the reviews table.
        "id": row.get("camis", ""),

        # dba = "doing business as", the trading name.
        # City data is ALL CAPS, so .title() makes it readable.
        "name": row.get("dba", "").title(),

        "cuisine": row.get("cuisine_description", ""),

        # Address arrives split across two columns. f"" joins them,
        # .strip() drops a stray space when one is missing.
        "address": f"{row.get('building', '')} {row.get('street', '')}".strip().title(),

        "boro": row.get("boro", ""),
        "zipcode": row.get("zipcode", ""),
        "phone": row.get("phone", ""),

        # Raw code, readable label, and whether it's a real grade.
        # Templates use is_graded to decide whether to show a badge.
        "grade": grade,
        "grade_label": GRADE_LABELS.get(grade, ""),
        "is_graded": grade in REAL_GRADES,
        "score": row.get("score", ""),

        # Coordinates, for the directions link.
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),

        # Derive a stable tile color from the cuisine name.
        # Same cuisine always maps to the same number, so Pizza is
        # always the same green. sum() of character codes is a crude
        # hash, but it's deterministic and good enough for 8 buckets.
        "tile": sum(ord(c) for c in row.get("cuisine_description", "x")) % 8,

        # First letters of the first two words, for the tile.
        "initials": "".join(w[0] for w in row.get("dba", "?").split()[:2]).upper(),
    }
    # .get(key, "") returns "" when a field is missing instead of
    # crashing. City data has gaps, so every field uses it.


def search(term="", limit=20):
    """Search restaurants. Returns a list of cleaned dicts, possibly empty."""

    # Check the cache before doing anything else.
    key = f"search:{term}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    # Socrata query parameters. The $ prefix marks them as query
    # operators rather than column filters.
    params = {
        # Skip placeholder rows. Never-inspected restaurants carry a
        # date of 1900-01-01 and have no cuisine or grade.
        "$where": "inspection_date > '2020-01-01'",

        # Newest first. This is what makes deduping work below:
        # the first row seen for a restaurant is its latest inspection.
        "$order": "inspection_date DESC",

        # Ask for 200 rows to get ~20 restaurants, since the same
        # restaurant appears once per inspection.
        "$limit": 200,
    }

    # $q is full-text search. Only added when there's a term, because
    # an empty $q returns nothing instead of everything.
    if term:
        params["$q"] = term

    try:
        # timeout=10 so a hanging city server doesn't hang Bite Club.
        response = requests.get(BASE_URL, params=params, timeout=10)
        # Raises an error on 4xx/5xx instead of silently returning junk.
        response.raise_for_status()
        rows = response.json()
    except requests.RequestException:
        # The city is down, slow, or rate-limiting. Return nothing
        # rather than crashing the page. A failed API call should
        # never take the site with it. Not cached, so the next
        # request retries rather than serving an empty list for an hour.
        return []

    # Dedupe. The dataset is one row per inspection, so a restaurant
    # inspected eight times appears eight times. Keep the first
    # occurrence of each camis, which is the most recent inspection.
    seen = {}
    for row in rows:
        camis = row.get("camis")
        if not camis:
            continue
        if camis not in seen:
            seen[camis] = dict(row)          # copy, so we can edit safely
        elif not seen[camis].get("grade") and row.get("grade"):
            seen[camis]["grade"] = row["grade"]
            seen[camis]["score"] = row.get("score", "")
    # Trim to the requested count, then clean each one.
    results = [clean(row) for row in list(seen.values())[:limit]]
    _cache_set(key, results)
    return results


def get_restaurant(camis):
    """Fetch one restaurant by its city ID.

    Returns (restaurant, error). error is None on success, or
    'unavailable' when the API failed, or 'not_found' when no such
    restaurant exists. Those two are different situations and the
    route shows different messages for each.
    """
    key = f"restaurant:{camis}"
    cached = _cache_get(key)
    if cached is not None:
        return cached, None

    params = {
        # No $ prefix: this filters on the camis column directly.
        "camis": camis,
        "$order": "inspection_date DESC",
        "$limit": 1,  # only need the latest inspection
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        rows = response.json()
    except requests.RequestException:
        return None, "unavailable"

    # No rows means no restaurant with that ID.
    if not rows:
        return None, "not_found"

    restaurant = clean(rows[0])
    _cache_set(key, restaurant)
    return restaurant, None