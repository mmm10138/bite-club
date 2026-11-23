"""Seed demo reviews.

Render's free tier has an ephemeral filesystem, so bite_club.db is
wiped on every restart. This runs at startup and refills it when the
reviews table is empty, so the deployed app is never bare.

Restaurant IDs are fetched live rather than hardcoded, because a
hardcoded camis might not appear in current search results.
"""

import sqlite3
from datetime import datetime, timedelta

import nyc_data

DATABASE = "bite_club.db"

# (username, food, atmosphere, service, overall, ordered, would_return, body)
DEMO_REVIEWS = [
    ("maria_m", 5, 3, 4, 4, "Açai bowl", 1,
     "Best açai in the neighbourhood. Seating is an afterthought but I don't come here to sit."),
    ("dkim", 4, 5, 4, 4, "Iced oat latte", 1,
     "Came for a coffee, stayed two hours. Nobody rushed me once."),
    ("j.alvarez", 3, 2, 2, 2, "Chicken over rice", 0,
     "Fine at 2am. Would not plan an evening around it."),
    ("sasha.p", 5, 4, 5, 5, "Whatever the counter recommends", 1,
     "Asked what was good and got the right answer. That's the whole review."),
    ("tomwrites", 2, 4, 3, 3, "Lunch special", 0,
     "Room is lovely, food was lukewarm. Felt like I'd ordered at the wrong time."),
    ("nnguyen", 5, 5, 4, 5, "Pork belly bun, twice", 1,
     "Ordered seconds before finishing firsts. No regrets."),
    ("ellawrites", 4, 3, 5, 4, "Shared plates", 1,
     "Service made this. Our server noticed we were splitting everything and brought extra plates unasked."),
    ("marcus.t", 3, 3, 1, 2, "Breakfast sandwich", 0,
     "Twenty minutes for a bacon egg and cheese. It was a good one, but still."),
    ("priya_r", 5, 4, 4, 5, "Thali", 1,
     "Everything on the tray earned its place. Bringing my parents."),
    ("owen.b", 4, 4, 4, 4, "Slice and a seltzer", 1,
     "Does one thing properly. No notes."),
    ("lucia.v", 2, 3, 3, 2, "Pasta of the day", 0,
     "Underseasoned. Bread was excellent, which somehow made it worse."),
    ("samkeller", 5, 5, 5, 5, "Tasting menu", 1,
     "Expensive and worth it. Go hungry."),
]


def has_reviews():
    connection = sqlite3.connect(DATABASE)
    count = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    connection.close()
    return count > 0


def seed():
    """Write demo reviews across the first few restaurants currently returned."""
    restaurants = nyc_data.search("", limit=6)
    if not restaurants:
        print("Seed skipped: no restaurants returned from the API.")
        return

    connection = sqlite3.connect(DATABASE)
    today = datetime.now()

    for index, review in enumerate(DEMO_REVIEWS):
        # Spread reviews across the restaurants, 2 each.
        restaurant = restaurants[index % len(restaurants)]
        username, food, atmos, service, overall, ordered, would_return, body = review

        # Stagger the dates so they don't all land on the same day.
        visited = (today - timedelta(days=index * 3 + 2)).date().isoformat()
        created = (today - timedelta(days=index * 3)).isoformat(timespec="seconds")

        connection.execute(
            "INSERT INTO reviews"
            " (restaurant_id, username, food, atmosphere, service, overall,"
            "  ordered, would_return, visit_date, body, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (restaurant["id"], username, food, atmos, service, overall,
             ordered, would_return, visited, body, created),
        )

    connection.commit()
    connection.close()
    print(f"Seeded {len(DEMO_REVIEWS)} reviews across {len(restaurants)} restaurants.")


def seed_if_empty():
    if not has_reviews():
        seed()


if __name__ == "__main__":
    seed()