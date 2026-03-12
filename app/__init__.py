import os
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from app.storage import user_exist
from app.models import User
from flask_socketio import SocketIO


login_manager = LoginManager()
login_manager.login_view = "main.signin" # tells Flask where to redirect users if they aren't logged in

@login_manager.user_loader
def load_user(username):
    return User(username) #return the User session object

socketio = SocketIO()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

    login_manager.init_app(app)
    socketio.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    from app import socket

    return app