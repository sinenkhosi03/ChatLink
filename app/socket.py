from flask_socketio import emit, join_room
from flask_login import current_user
from app import socketio

@socketio.on('connect')
def handle_connect(auth):
    join_room(current_user.id)
    print(f"{current_user.id} connected")

@socketio.on('receive_message')
def handle_message(data):
    emit('new_message', data, room=data['recipient'])