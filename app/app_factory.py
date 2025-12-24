"""Lightweight app factory to initialize Flask and extensions."""
import os

from app import chatbot, database, globals as global_state

# Expose socketio instance for runner
socketio = global_state.socketio


def create_app():
    """Return the configured Flask app."""
    app = global_state.app

    # Initialize chatbot clients (idempotent)
    chatbot.init_gemini_clients(
        os.getenv("GOOGLE_CHATBOT_API_KEY"),
        os.getenv("GOOGLE_PETBOT_API_KEY"),
    )

    database.init_app(app)

    # Register routes/handlers (imports attach routes/events)
    from app import main  # noqa: F401
    from app.sockets import handlers  # noqa: F401

    return app


