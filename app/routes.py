from flask import Blueprint, render_template, url_for, redirect
import time

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/signIn", methods=["GET", "POST"])
def signin():
    return render_template("signIn.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")


def chat():
    return render_template("chatScreen.html")
