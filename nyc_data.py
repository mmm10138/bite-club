import requests 

BASE_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

def search(term="", limit=20):
    params = {
        "$where": "inspection_date > '2020-01-01'",
        "$order": "inspection_date DESC",
        "$limit": 200,
    }
    if term:
        params["$q"] = term

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    rows = response.json()

    seen = {}
    for row in rows:
        camis = row.get("camis")
        if camis and camis not in seen:
            seen[camis] = row

    return [clean(row) for row in list(seen.values())[:limit]]
def clean(row):
    return {
        "id": row.get("camis", ""),
        "name": row.get("dba", "").title(),
        "cuisine": row.get("cuisine_description", ""),
        "address": f"{row.get('building', '')} {row.get('street', '')}".strip().title(),
        "boro": row.get("boro", ""),
        "zipcode": row.get("zipcode", ""),
        "phone": row.get("phone", ""),
        "grade": row.get("grade", ""),
        "score": row.get("score", ""),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
    }
