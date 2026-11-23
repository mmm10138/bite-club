from flask import Flask #Flask is the python library that turns functions into web pages
import nyc_data
import render_template #Render_template allows us to use html files in our flask app

app = Flask(__name__) #Create app 

@app.route("/") #When someone visists home page 
def index():
    restaurants = nyc_data.search("", limit=20)
    return render_template("index.html", restaurants=restaurants)

if __name__ == "__main__":
    app.run(debug=True, port=5000) #Restarts server when you save a file 
