"""Seed demo reviews.

Render's free tier has an ephemeral filesystem, so bite_club.db is
wiped on every restart. This runs at startup and refills it when the
reviews table is empty, so the deployed app is never bare.

The reviews below are invented demo content, not real user submissions.
They exist so the app has something to show. Anything a real visitor
writes is stored the same way, through the normal form.

Restaurant IDs are fetched live rather than hardcoded, because a
hardcoded camis might not appear in current search results.
"""

import sqlite3
from datetime import datetime, timedelta

import nyc_data

DATABASE = "bite_club.db"

# Each tuple is one review, in the order the INSERT below expects:
# (username, food, atmosphere, service, overall, ordered, would_return, body)
#
# Scores deliberately vary, including some low ones. A seed where every
# restaurant averages 5.0 looks fake and makes the averages meaningless.
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
    """True if the reviews table already has rows.

    Assumes init_db() has already created the table. app.py calls that
    first, so by the time this runs the table exists but may be empty.
    """
    connection = sqlite3.connect(DATABASE)
    # fetchone() returns a one-item tuple like (12,), so [0] takes the number.
    count = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    connection.close()
    return count > 0


def seed():
    """Write demo reviews across the first few restaurants currently returned."""
    # Fetched live rather than hardcoded. The city's dataset is ordered
    # by inspection date, so which restaurants appear changes daily. A
    # hardcoded ID could point at a restaurant nobody can find.
    restaurants = nyc_data.search("", limit=6)

    # If the API is down there's nothing to attach reviews to. Skip
    # quietly rather than crashing the whole app on startup.
    if not restaurants:
        print("Seed skipped: no restaurants returned from the API.")
        return

    connection = sqlite3.connect(DATABASE)
    today = datetime.now()

    # enumerate() gives both the position and the item, and the position
    # is used below for both the restaurant and the date offset.
    for index, review in enumerate(DEMO_REVIEWS):
        # Modulo cycles through the restaurants, so 12 reviews across
        # 6 restaurants gives 2 each. Two is enough for an average to
        # mean something without looking padded.
        restaurant = restaurants[index % len(restaurants)]

        # Unpacking the tuple into named variables, so the INSERT below
        # reads properly instead of being review[0], review[1] and so on.
        username, food, atmos, service, overall, ordered, would_return, body = review

        # Stagger the dates backwards from today, three days apart, so
        # the reviews look accumulated over time rather than all posted
        # in the same second. Visits are dated two days before the
        # review was written.
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
    """Seed only when the table is empty, so real reviews are never overwritten.

    Called on every startup. On a fresh deploy it fills the database; on
    a running instance it does nothing.
    """
    if not has_reviews():
        seed()


if __name__ == "__main__":
    # Running this file directly seeds unconditionally, for testing.
    seed()