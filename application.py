#!/usr/bin/python3
import os
import requests
import credentials

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from helpers import *

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
@login_required
def index():
    """Home page"""

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User Register"""

    username = request.form.get("username")
    password = request.form.get("password")
    confirmPassword = request.form.get("confirmPassword")

    if request.method == "POST":

        if not username:
            return render_template("error.html", message="Must provide username")

        elif not password:
            return render_template("error.html", message="Must provide password")

        elif password != confirmPassword:
            return render_template("error.html", message="Passwords don't match")

        elif db.execute("SELECT * FROM users WHERE username = :username",
                        {"username": username}).rowcount != 0:
            return render_template("error.html", message="Username already exists. Please pick another one.")

        db.execute("INSERT INTO users (username, password) \
                            VALUES (:username, :password)",
                   {"username": username, "password": password})

        db.commit()

        session["user_id"] = db.execute("SELECT id FROM users \
                            WHERE (username=:username) AND \
                            (password=:password)",
                                        {"username": username, "password": password}).fetchone().id
        session["logged_in"] = True

        return redirect(url_for("index"))

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User Login"""

    # forget any user_id
    session.clear()

    # If user submited a form
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return render_template("error.html", message="Must provide username")

        elif not password:
            return render_template("error.html", message="Must provide password.")

        result = db.execute("SELECT * FROM users WHERE username = :username AND password=:password",
                            {"username": username, "password": password}).fetchone()

        if result == None:
            return render_template("error.html", message="Invalid username and/or password.")

        flash("You were logged in")
        session["logged_in"] = True
        session["user_id"] = result[0]

        return redirect(url_for("index"))

    # If user got in page via GET method
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """User Logout"""

    session["logged_in"] = False
    session.clear()

    return redirect(url_for("login"))


@app.route("/books", methods=["POST"])
@login_required
def search():
    """Search results"""

    input = request.form.get("search")

    books = db.execute("SELECT * FROM books \
        JOIN authors ON books.author_id=authors.id \
        WHERE (isbn LIKE :input) OR (title LIKE :input) OR (name LIKE :input)",
                       {"input": f"%{input}%"}).fetchall()

    # If no books in database, I display a message instead of a table
    if len(books) == 0:
        books = None

    return render_template("results.html", books=books)


@app.route("/books/<int:book_id>")
@login_required
def book(book_id):
    """Book page"""

    book = db.execute(
        "SELECT * FROM books JOIN authors ON books.author_id=authors.id WHERE books.id=:id", {"id": book_id}).fetchone()

    # Get a JSON from Goodreads containing book's review
    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": credentials.goodreads_API_KEY, "isbns": book.isbn})

        json = res.json()["books"][0]

    # If no JSON is returned, show a custom message
    except:
        json = {}
        json["average_rating"] = "Review not available"
        json["work_ratings_count"] = "Review not available"

    # Get review count and avg rating from my database
    try:
        result = db.execute("SELECT COUNT(rating), AVG(rating) FROM reviews \
                            WHERE book_id=:book_id GROUP BY book_id", {"book_id": book_id}).fetchone()

        json["reviews_count"] = result[0]
        json["avg_rating"] = float("%.1f" % result[1])

    # If no available ratings in database, show a custom message
    except:
        json["reviews_count"] = "Review not available"
        json["avg_rating"] = "Review not available"

    # Get user's own review
    myreview = db.execute("SELECT * FROM reviews WHERE (user_id=:user_id) AND (book_id=:book_id)",
                          {"user_id": session["user_id"], "book_id": book_id}).fetchone()

    # Get Community's reviews
    reviews = db.execute("SELECT * FROM reviews WHERE book_id=:book_id",
                         {"book_id": book_id}).fetchall()

    # If no reviews in database, I display a message instead of a table
    if len(reviews) == 0:
        reviews = None

    return render_template("book.html", book=book, json=json, myreview=myreview, reviews=reviews)


@app.route("/books/<int:book_id>/review", methods=["POST"])
@login_required
def review(book_id):
    """Submit a review"""

    rating = request.form.get("rating")
    review = request.form.get("review")

    review = db.execute("INSERT INTO reviews (book_id, user_id, rating, review) \
                        VALUES (:book_id, :user_id, :rating, :review)",
                        {"book_id": book_id, "user_id": session["user_id"],
                         "rating": rating, "review": review})

    db.commit()

    return redirect(url_for("book", book_id=book_id))


@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    """Get stats via API"""

    try:

        # Get Title, Author, Year and ISBN
        result = db.execute("SELECT books.title, authors.name, books.year, books.isbn\
                        FROM books \
                            JOIN authors ON books.author_id=authors.id \
                        WHERE isbn=:isbn", {"isbn": isbn}).fetchone()

        # Get review count and avg rating
        result2 = db.execute("SELECT COUNT(rating), AVG(rating) FROM reviews \
                            JOIN books ON reviews.book_id=books.id \
                            WHERE books.isbn=:isbn GROUP BY book_id", {"isbn": isbn}).fetchone()

        if result2 == None:
            review_count = 0
            average_score = 0
        else:
            review_count = int(result2[0])
            average_score = float("%.1f" % result2[1])

        return jsonify(
            title=result.title,
            author=result.name,
            year=result.year,
            isbn=result.isbn,
            review_count=review_count,
            average_score=average_score,
        )

    # If the requested ISBN number isn’t in the database, return 404 error
    except:
        abort(404)
