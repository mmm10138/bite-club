from flask import Flask, render_template, request 
#Flask is the python library that turns functions into web pages
#render_template allows us to use html files in our flask app
#request allows us to get information from the user (like search terms)
import nyc_data


app = Flask(__name__) #Create app 

@app.route("/") #When someone visists home page 
def index():
    term = request.args.get("term", "") #Get the search term from the user
    restaurants = nyc_data.search(term, limit=20)
    return render_template("index.html", restaurants=restaurants, term=term)

@app.route("/restaurant/<camis>")
def restaurant_detail(camis):
    restaurant = nyc_data.get_restaurant(camis)
    if restaurant is None:
        return "Restaurant not found", 404
    return render_template("restaurant.html", restaurant=restaurant)

if __name__ == "__main__":
    app.run(debug=True, port=5000) #Restarts server when you save a file 
