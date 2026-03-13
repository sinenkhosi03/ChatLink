from flask import Blueprint, render_template, url_for, redirect, request, flash
from app.client_registry import clients
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.client_interface import client_application

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/signIn", methods=["GET","POST"])
def signin():
    if request.method=="POST":
        name = request.form.get("username")
        pw = request.form.get("password")

        client = client_application()

        success, err = client.login(name, pw)

        if not success:
            flash(err)
            return redirect(url_for("main.signin"))

        # CHANGED: store client
        clients[name] = client
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
        client = client_application()

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

@main.route("/logout")
@login_required
def logout():

    from app.client_registry import clients

    client = clients.pop(current_user.id, None)   # CHANGED

    if client:
        client.logout()

    logout_user()

    return redirect(url_for("main.signin"))


@main.route("/home")
@login_required
def chat_home():

    client = clients.get(current_user.id)   # CHANGED

    if not client:
        return redirect(url_for("main.signin"))

    online_users = client.view_online_users() or []

    # print(online_users)

    return render_template("chatHome.html", online_users=online_users)

@main.route("/chat/<friend>")
@login_required
def chat(friend, message=""):
    client = clients.get(current_user.id)   # CHANGED

    if not client:
        return redirect(url_for("main.signin"))

    online_users = client.view_online_users()

    if message != "":
        client.send

    return render_template("chatScreen.html", online_users=online_users, friend=friend)