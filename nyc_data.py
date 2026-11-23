import time
import requests  # library for making web requests to other servers

# The NYC Open Data endpoint for restaurant inspections.
# 43nn-pn8j is the dataset ID. One row per inspection, ~297,000 rows.
BASE_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

_cache = {}
CACHE_SECONDS = 300  # 5 minutes


def _cache_get(key):
    entry = _cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.time() - stored_at > CACHE_SECONDS:
        return None
    return value


def _cache_set(key, value):
    _cache[key] = (time.time(), value)

def clean(row):
    """Turn one raw city row into the fields Bite Club uses.

    The city uses its own column names (dba, camis). Templates shouldn't
    have to know those, so everything gets renamed here, in one place.
    """
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

        # Health grade (A/B/C) and numeric score. Often empty:
        # not every inspection produces a grade.
        "grade": row.get("grade", ""),
        "score": row.get("score", ""),

        # Coordinates, for the directions link.
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
    }
    # .get(key, "") returns "" when a field is missing instead of
    # crashing. City data has gaps, so every field uses it.


def search(term="", limit=20):
    """Search restaurants. Returns a list of cleaned dicts, possibly empty."""

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

    key = f"search:{term}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

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
        # never take the site with it.
        return []

    # Dedupe. The dataset is one row per inspection, so a restaurant
    # inspected eight times appears eight times. Keep the first
    # occurrence of each camis, which is the most recent inspection.
    seen = {}
    for row in rows:
        camis = row.get("camis")
        if camis and camis not in seen:
            seen[camis] = row

        results = [clean(row) for row in list(seen.values())[:limit]]
    _cache_set(key, results)
    return results

    # Trim to the requested count, then clean each one.
    return [clean(row) for row in list(seen.values())[:limit]]


def get_restaurant(camis):
    """Returns (restaurant, error). error is None, 'unavailable', or 'not_found'."""
    params = {
        "camis": camis,
        "$order": "inspection_date DESC",
        "$limit": 1,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        rows = response.json()
    except requests.RequestException:
        return None, "unavailable"

    if not rows:
        return None, "not_found"

    return clean(rows[0]), None

    return clean(rows[0])