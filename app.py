"""Bite Club — restaurant discovery and reviews for New York City.

Three sources of data meet here:
  - nyc_data.py fetches restaurants from the city's open data API
  - bite_club.db holds reviews written by Bite Club users
  - the templates render both

The two are deliberately kept apart. City data is read-only and cached;
reviews are ours and are written locally. Nothing from the city is ever
stored, and nothing a user writes is ever sent anywhere.
"""

from flask import Flask, render_template, request, redirect, url_for
# Flask is the python library that turns functions into web pages
# render_template allows us to use html files in our flask app
# request allows us to get information from the user (like search terms)
# redirect and url_for send the browser to a different page after a POST

import nyc_data
import sqlite3  # sqlite3 is a library that allows us to use a database in our app
from datetime import datetime  # datetime is a library that allows us to work with dates and times
from database import init_db
from seed import seed_if_empty

app = Flask(__name__)   # Create app
DATABASE = "bite_club.db"   # Database file name

# These run on import rather than under __main__, because gunicorn (the
# production server) imports this file instead of executing it. Render's
# free tier also wipes the filesystem on every restart, so the database
# has to be rebuilt and reseeded each boot.
init_db()
seed_if_empty()


def get_db():
    """Open a connection to the reviews database.

    row_factory = sqlite3.Row makes rows behave like dictionaries, so
    templates can write review.username instead of review[2]. Without
    it every read would depend on column order, which breaks silently
    the moment the schema changes.
    """
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")   # When someone visits home page
def index():
    """Search page. Also the homepage, with an empty search term."""
    # request.args holds everything after the ? in the URL. The second
    # argument to .get() is the default, so a bare visit to / searches
    # for nothing and gets the most recently inspected restaurants.
    term = request.args.get("term", "")   # Get the search term from the user

    restaurants = nyc_data.search(term, limit=20)

    # term goes back into the template so the search box still shows
    # what was typed after the page reloads.
    return render_template("index.html", restaurants=restaurants, term=term)


@app.route("/restaurant/<camis>")
def restaurant_detail(camis):
    """One restaurant: city data on top, Bite Club reviews below.

    <camis> in the route makes that part of the URL a variable. Visiting
    /restaurant/50006232 calls this function with camis="50006232".
    """
    restaurant, error = nyc_data.get_restaurant(camis)

    # Two different failures that would otherwise look identical.
    # "unavailable" means the city's API failed; "not_found" means no
    # restaurant has that ID. Telling the user which one happened is
    # the difference between "try again" and "this doesn't exist".
    if error == "unavailable":
        return "City data is temporarily unavailable. Try again in a moment.", 503
    if error == "not_found":
        return "Restaurant not found", 404

    db = get_db()

    # Two queries rather than one, because they return different shapes:
    # the first gives many rows, the second gives a single row of
    # averages. Doing the arithmetic in SQL rather than Python also
    # means it stays correct if reviews are ever paginated.
    #
    # The ? is a placeholder. Values are passed separately from the SQL
    # so that a malicious restaurant ID is treated as text, never as
    # commands. Never build a query by joining strings.
    reviews = db.execute(
        "SELECT * FROM reviews WHERE restaurant_id = ? ORDER BY created_at DESC",
        (camis,),
    ).fetchall()

    averages = db.execute(
        "SELECT AVG(food) AS food, AVG(atmosphere) AS atmosphere,"
        " AVG(service) AS service, AVG(overall) AS overall, COUNT(*) AS count"
        " FROM reviews WHERE restaurant_id = ?",
        (camis,),
    ).fetchone()

    db.close()

    return render_template(
        "restaurant.html",
        restaurant=restaurant,
        reviews=reviews,
        averages=averages,
    )


@app.route("/restaurant/<camis>/review", methods=["POST"])
def add_review(camis):
    """Save a review.

    methods=["POST"] means this route only accepts form submissions.
    Searching uses GET because it only reads; writing uses POST so the
    data doesn't end up in the URL and a refresh doesn't resubmit it.

    Everything below re-checks what the HTML form already enforces with
    min, max and required. Those attributes are a convenience for honest
    users, not a control: anyone can send a request directly and skip
    the form entirely. Validation that matters happens on the server.
    """
    today = datetime.now().date().isoformat()

    # ISO dates compare correctly as plain strings, because the format
    # is year-month-day with zero padding. "2026-11-24" > "2026-11-23".
    visit_date = request.form.get("visit_date", "")
    if visit_date and visit_date > today:
        return "Visit date cannot be in the future.", 400

    # Each of the four scores has to be an integer from 1 to 5.
    # int() raises ValueError on anything that isn't a number, and
    # request.form[field] raises KeyError if the field is missing, so
    # both are caught.
    ratings = {}
    for field in ("food", "atmosphere", "service", "overall"):
        try:
            value = int(request.form[field])
        except (KeyError, ValueError):
            return f"Missing or invalid {field} rating.", 400
        if value < 1 or value > 5:
            return f"{field} must be between 1 and 5.", 400
        ratings[field] = value

    # .strip() removes surrounding whitespace, so a name of three
    # spaces counts as empty rather than passing as a username.
    username = request.form.get("username", "").strip()
    body = request.form.get("body", "").strip()
    if not username or not body:
        return "Name and review text are required.", 400

    # Only open the database once the input is known to be good.
    db = get_db()
    db.execute(
        "INSERT INTO reviews"
        " (restaurant_id, username, food, atmosphere, service, overall,"
        "  ordered, would_return, visit_date, body, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            camis,
            username,
            ratings["food"],
            ratings["atmosphere"],
            ratings["service"],
            ratings["overall"],
            request.form.get("ordered", "").strip(),
            # SQLite has no boolean type. An unchecked checkbox sends
            # nothing at all, so .get() returns None, which becomes 0.
            1 if request.form.get("would_return") else 0,
            visit_date,
            body,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    db.commit()   # without this, nothing is actually saved
    db.close()

    # Redirect rather than rendering the page directly. After a POST the
    # browser should end up on a GET URL, otherwise refreshing the page
    # submits the review a second time.
    return redirect(url_for("restaurant_detail", camis=camis))


if __name__ == "__main__":
    # Only runs when you execute this file directly. In production
    # gunicorn imports the app instead, so this is skipped.
    app.run(debug=True, port=5000)   # Restarts server when you save a file
    