from flask import Flask, render_template, request, redirect, url_for 
#Flask is the python library that turns functions into web pages
#render_template allows us to use html files in our flask app
#request allows us to get information from the user (like search terms)
import nyc_data
import sqlite3 #sqlite3 is a library that allows us to use a database in our app
from datetime import datetime #datetime is a library that allows us to work with dates and times
from database import init_db
from seed import seed_if_empty


app = Flask(__name__) #Create app 
# Run on import, not just under __main__, because gunicorn imports the
# app rather than executing the file. On Render the filesystem is wiped
# on every restart, so both of these need to run each boot.
init_db()
seed_if_empty()

DATABASE="bite_club.db" #Database file name

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

@app.route("/") #When someone visists home page 
def index():
    term = request.args.get("term", "") #Get the search term from the user
    restaurants = nyc_data.search(term, limit=20)
    return render_template("index.html", restaurants=restaurants, term=term)

@app.route("/restaurant/<camis>")
def restaurant_detail(camis):
    restaurant, error = nyc_data.get_restaurant(camis)
    if error == "unavailable":
        return "City data is temporarily unavailable. Try again in a moment.", 503
    if error == "not_found":
        return "Restaurant not found", 404
    db = get_db()
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
    today = datetime.now().date().isoformat()

    visit_date = request.form.get("visit_date", "")
    if visit_date and visit_date > today:
        return "Visit date cannot be in the future.", 400

    ratings = {}
    for field in ("food", "atmosphere", "service", "overall"):
        try:
            value = int(request.form[field])
        except (KeyError, ValueError):
            return f"Missing or invalid {field} rating.", 400
        if value < 1 or value > 5:
            return f"{field} must be between 1 and 5.", 400
        ratings[field] = value

    username = request.form.get("username", "").strip()
    body = request.form.get("body", "").strip()
    if not username or not body:
        return "Name and review text are required.", 400
    db = get_db()
    db.execute(
        "INSERT INTO reviews"
        " (restaurant_id, username, food, atmosphere, service, overall,"
        "  ordered, would_return, visit_date, body, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            camis,
            request.form["username"],
            int(request.form["food"]),
            int(request.form["atmosphere"]),
            int(request.form["service"]),
            int(request.form["overall"]),
            request.form.get("ordered", ""),
            1 if request.form.get("would_return") else 0,
            request.form.get("visit_date", ""),
            request.form["body"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    db.close()
    return redirect(url_for("restaurant_detail", camis=camis))
    

if __name__ == "__main__":
    app.run(debug=True, port=5000) #Restarts server when you save a file 
