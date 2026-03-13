from flask_socketio import emit, join_room
from flask_login import current_user
from app import socketio

@socketio.on('connect')
def handle_connect(auth):
    if current_user.is_authenticated:
        join_room(str(current_user.id))
    else:
        print("Unauthenticated socket connection rejected")
        return False

@socketio.on('receive_message')
def handle_message(data):
    emit('new_message', data, room=data['recipient'])