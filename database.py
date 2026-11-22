
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT    NOT NULL,
    username      TEXT    NOT NULL,
    food          INTEGER NOT NULL,
    atmosphere    INTEGER NOT NULL,
    service       INTEGER NOT NULL,
    overall       INTEGER NOT NULL,
    ordered       TEXT,
    would_return  INTEGER NOT NULL,
    visit_date    TEXT,
    body          TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);
"""

def init_db():
    connection = sqlite3.connect("bite_club.db")
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()
    print("Database ready.")

if __name__ == "__main__":
    init_db()
