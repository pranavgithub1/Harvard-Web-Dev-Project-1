import os

from flask import Flask, session, render_template, request ,redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
KEY = "cIL3fKUTriBGePdAliQA"

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    session.clear()
    return render_template("index.html")

@app.route("/login", methods=['POST'])
def login():
    # get the username and password
    username = request.form.get("username")
    password = request.form.get("password")
    #check if the user exists via the username
    if db.execute("SELECT * FROM users WHERE username = :username",{"username":username}).rowcount == 0:
        error = "user does not exist"
        return render_template("index.html",error=error)
    else:
        session["admin"] = username
        return redirect(url_for("home"))

@app.route("/register")
def register():
    return render_template("register.html")
    
@app.route("/newuser", methods=['POST'])
def newuser():
    # get potential username and password
    potential_new_username = request.form.get("username")
    newpassword = request.form.get("password")
    # check if potential username already exists
    if db.execute("SELECT * FROM users WHERE username = :username",{"username":potential_new_username}).rowcount != 0:
        # the username is taken
        # return render_template(usernameTaken.html)
        error = "username not available"
        return render_template("register.html",error=error)
    else:  
        # the username is available
        db.execute("INSERT INTO users (username,password) VALUES (:username,:password)",{"username":potential_new_username,"password":newpassword})
        db.commit()
        return render_template("registration_success.html")

@app.route("/home",methods=["POST","GET"])
def home():
    if "admin" not in session:
        return redirect(url_for("index"))
    else:
        return render_template("home.html",username=session["admin"])

@app.route("/search",methods=["POST"])
def search():
    author = request.form.get("author")

    """
    if isbn:
        results = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchall()
        if results==False:
            results = db.execute("SELECT * FROM books WHERE author LIKE :author",{"author":author}).fetchall()
            return render_template("search.html")
        return render_template("search.html")
    else:
        results = db.execute("SELECT * FROM books WHERE author LIKE :author",{"author":author}).fetchall()
        return render_template("search.html")
    if results==False:
        return("no results")
    """
    results = db.execute("SELECT * FROM books WHERE author LIKE :author",{"author":r"%{}%".format(author)}).fetchall()
    if results==False:
        return("no results")
    else:
        return render_template("home.html",username=session["admin"],results=results)

@app.route("/search/<string:title>",methods=["GET","POST"])
def bookpage(title):
    print("bookpage called with: ",title)
    result = db.execute("SELECT * FROM books WHERE title = :title",{"title":title}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE title = :title",{"title":title}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": result.isbn})
    print(res.json()["books"][0]["average_rating"])
    average_rating = res.json()["books"][0]["average_rating"]
    ratings_count = res.json()["books"][0]["ratings_count"]
    return render_template("bookpage.html",title=title,author=result.author,isbn=result.isbn,year=result.year,reviews=reviews,average_rating=average_rating,ratings_count=ratings_count)

@app.route("/search/<string:title>/review",methods=["POST"])
def review(title):
    print("review called with: ",title)
    review = request.form.get("review")
    rating = request.form.get("rating")
    if review:
        if (db.execute("SELECT * FROM reviews WHERE author = :author AND title=:title",{"author":session["admin"],"title":title}).rowcount==0):
            db.execute("INSERT INTO reviews (review,title,author,rating) VALUES (:review,:title,:author,:rating)",{"review":review,"title":title,"author":session["admin"],"rating":rating})
            db.commit()
        else:
            db.execute("UPDATE reviews SET review=:review,rating=:rating WHERE author=:author",{"review":review,"author":session["admin"],"rating":rating})
            db.commit()
    return redirect(url_for("bookpage",title=title))

@app.route("/api")
def api():
    isbn = request.args.get("isbn")
    return redirect(url_for("isbn",isbn=isbn))

@app.route("/api/<string:isbn>")
def isbn(isbn):
    results = result = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
    average_rating = res.json()["books"][0]["average_rating"]
    ratings_count = res.json()["books"][0]["ratings_count"]
    return jsonify(title=result.title,author=result.author,year=result.year,isbn=isbn,review_count=ratings_count,average_score=average_rating)

