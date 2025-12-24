"""Application package init."""

# Expose app/socketio so run.py can import cleanly
from app.app_factory import create_app, socketio  # noqa: F401


