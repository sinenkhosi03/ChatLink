from flask import Blueprint, render_template, url_for, redirect, request, flash
import time
from app.storage import add_user, user_exist

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/signIn", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        name = request.form["username"]
        pw = request.form["password"]
        #print(name, pw)
        # if name==username:
        #     print("right name")
        #     if pw == password:
        #        logedin = True
        #        print("log in was a success.")
        #        print(f"welcome: {name}")
        #        return render_template("chatHome.html")
    return render_template("signIn.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_pw = request.form["confirm-password"]
        # print(username, password, confirm_pw)
        if not user_exist(username):
            
            if confirm_pw == password:
                print(username, password, confirm_pw)
                add_user(username, password)
                print("it works")
                redirect(url_for("main.signin"))
            else:
                flash("passwords do not match")
                redirect(url_for("main.register"))
        else:
            flash("username exists, try a different one.")
            redirect(url_for("main.register"))
        
        
    return render_template("register.html")

@main.route("/chat")
def chat():
    return render_template("chatScreen.html")
