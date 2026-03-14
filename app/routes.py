from flask import Blueprint, render_template, url_for, redirect, request, flash
from app.client_registry import clients
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.client_interface import client_application
from app import socketio


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


@main.route("/create-group", methods=["GET", "POST"])
@login_required
def create_group():
    client = clients.get(current_user.id)

    available_grps = client.view_groups() or []

    if request.method == "POST":
        print("Method >>> Post")
        grp_name = request.form["gname"]
        grp_members = request.form["members"]

        # print(grp_name, grp_members)

        grp_members = grp_members.split(", ")
        # print(grp_name, grp_members)

        status = client.create_group(grp_name, grp_members)
        if status:
            return redirect(url_for("main.group_home"))
        else:
            flash("An error occured. Group was not created")
    return render_template("group_form.html", available_grps = available_grps)

@main.route("/home")
@login_required
def chat_home():

    client = clients.get(current_user.id)   # CHANGED

    if not client:
        return redirect(url_for("main.signin"))

    online_users = client.view_online_users() or []

    # print(online_users)

    return render_template("chatHome.html", online_users=online_users)


@main.route("/groups", methods=["GET", "POST"])
@login_required
def group_home():
    client = clients.get(current_user.id)

    if not client:
        return redirect(url_for("main.signin"))

    available_grps = client.view_groups() or []

    print(available_grps)

    return render_template("groups.html", available_grps=available_grps)


@main.route("/chat/<friend>")
@login_required
def chat(friend):
    client = clients.get(current_user.id)   # CHANGED

    if not client:
        return redirect(url_for("main.signin"))

    online_users = client.view_online_users()
    connection_status = client.one_on_one_chat_connection(friend)
    if not connection_status:
        return redirect(url_for("main.chat_home"))
    return render_template("chatScreen.html", online_users=online_users, friend=friend)


@main.route("/send_message", methods=["POST"])
@login_required
def send_message():

    client = clients.get(current_user.id)

    if not client:
        return {"status": "error"}, 400

    data = request.json
    friend = data.get("friend")
    message = data.get("message")
    file_data = data.get("file")

    print(message)
    if message != "":
        sent_status = client.send_message_121(message, friend)
    # if not sent_status:
    #     print("Msg not sent")
    #     return {"status":"failed"}
    
    if file_data:
        client.send_file(file_data["url"], file_data["filename"], file_data["type"], file_data["size"], friend)
        print("sending file...")

    return {"status": "ok"}


import os
import time
from flask import request, jsonify

UPLOAD_FOLDER = "app/static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
@main.route("/upload_file", methods=["POST"])
@login_required
def upload_file():
    file = request.files["file"]

    # create unique filename
    filename = f"{int(time.time())}_{file.filename}"

    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    return jsonify({
        "url": f"app/static/uploads/{filename}"
    })