from flask import Blueprint, render_template, url_for, redirect, request, flash

from flask_login import login_user, logout_user, login_required
from app.models import User
from app.client_interface import client_application

main = Blueprint("main", __name__)

client = client_application()

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/signIn", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        name = request.form["username"]
        pw = request.form["password"]

        login, err_msg = client.login(name, pw)
        if not login:
            flash("Incorrect login details or server timeout, try again.", category="message")
            print(err_msg)
            return redirect(url_for("main.signin"))
        
        # print("log in was a success.")
        # print(f"welcome: {name}")
        print(name)
        user = User(name)
        login_user(user)

        return redirect(url_for("main.chat_home"))
    return render_template("signIn.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_pw = request.form["confirm-password"]
        # print(username, password, confirm_pw)
 
        if confirm_pw != password:
            flash("passwords do not match")
            return redirect(url_for("main.register"))
        
        registration = client.register(username, password)
        if not registration:
            flash("Error occured, try again or try a different username.")
            return redirect(url_for("main.register")) 
        
        # print(username, password, confirm_pw)
        return redirect(url_for("main.signin"))
        
        
        
    return render_template("register.html")

@main.route("/home")
@login_required
def chat_home():

    return render_template("chatHome.html")

@main.route("/chat")
@login_required
def chat():
    return render_template("chatScreen.html")


# @main.route("/chat/fileshare", methods=["GET", "POST"])
# def file_share():
#     if request.method=="POST":
#         file = request.form["file-upload"]
#         print(file)
#     return redirect(url_for("main.chat"))


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.signin"))

