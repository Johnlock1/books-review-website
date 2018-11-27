# Project 1: Books

This is the Project 1 of [CS50's Web Programming with Python and JavaScript](https://cs50.github.io/web/) course. It's a books' review website.

## Features

+ Registration
+ Login
+ Logout
+ Import database
+ Search by Book Title, Author or ISBN
+ Book Page
+ Review Submission
+ Goodreads Review Data:
+ API Access: If users make a GET request to your website’s /api/<isbn> route,
where <isbn> is an ISBN number, the website returns a JSON response.

## Known Issues

**Passwords are saved as plain text.**
I tried to hash the passwords by importing `from passlib.apps import custom_app_context` and using `hash` method, but I couldn't get it to work.

## Live site
You can check the site at https://johnlock1-cs50-project1.herokuapp.com

## Author

Christos Christou - https://github.com/Johnlock1/
