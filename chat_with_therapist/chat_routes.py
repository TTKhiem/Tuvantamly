from flask import Blueprint, render_template, session
from matchmaking.matchmaking_repository import get_matches_for_user
from decorators import student_required, therapist_required

# Create a Blueprint for chat-related routes
chat_bp = Blueprint('chat', __name__, url_prefix='/chat_with_therapist')


@chat_bp.route("/student")
@student_required
def student_chat():
    # """
    # Render the student chat page with a sidebar listing all their chat rooms (matches).
    # """
    user_id = session.get("user_id")

    # Fetch all match IDs for this student
    matches = get_matches_for_user(user_id)

    return render_template("chat_student.html", matches=matches)


@chat_bp.route("/therapist")
@therapist_required
def therapist_chat():
    # """
    # Render the therapist chat page with a sidebar listing all their chat rooms (matches).
    # """
    user_id = session.get("user_id")

    # Fetch all match IDs for this therapist
    matches = get_matches_for_user(user_id)

    return render_template("chat_student.html", match_ids=matches)


