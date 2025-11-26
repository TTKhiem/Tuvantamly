from flask_socketio import SocketIO, join_room, leave_room, emit
from flask import session

# You should initialize socketio in main.py like this:
# socketio = SocketIO(app, cors_allowed_origins="*")

# Here we assume `socketio` is imported from main.py
from main import socketio  

@socketio.on("join_room")
def handle_join_room(data):
    # """
    # Event to join a chat room.
    # data: {"match_id": 5}
    # """
    match_id = data.get("match_id")
    if not match_id:
        return

    room_name = f"room_{match_id}"
    join_room(room_name)

    # Optionally, notify the room that a new user joined
    emit(
        "user_joined",
        {"message": f"User has joined room {match_id}"},
        room=room_name
    )


# Event: send message
@socketio.on("send_message")
def handle_send_message(data):
    # """
    # Broadcast a message to everyone in the room.
    # data: {
    #     "match_id": 5,
    #     "sender_id": 101,
    #     "message": "Hello!"
    # }
    # """
    match_id = data.get("match_id")
    sender_id = data.get("sender_id")
    message = data.get("message")

    if not match_id or not sender_id or message is None:
        return

    room_name = f"room_{match_id}"

    # Broadcast the message to all clients in the room
    emit(
        "receive_message",
        {
            "match_id": match_id,
            "sender_id": sender_id,
            "message": message
        },
        room=room_name
    )


@socketio.on("connect")
def handle_connect():
    user_id = session.get("user_id")  # Flask session
    if user_id:
        join_room(f"user_{user_id}")


def notify_users_of_new_match(student_user_id, therapist_user_id, match_id):
    # """
    # Emit a 'new_match' event to both student and therapist when a match is created.
    # Front-end can listen to this event to update sidebar and allow joining the room.
    # """
    room_name = f"room_{match_id}"  # optional, just for reference in event

    # Event payload
    data = {
        "match_id": match_id,
        "student_user_id": student_user_id,
        "therapist_user_id": therapist_user_id
    }

    # Emit to both users specifically (requires client to join a personal room)
    socketio.emit("new_match", data, room=f"user_{student_user_id}")
    socketio.emit("new_match", data, room=f"user_{therapist_user_id}")