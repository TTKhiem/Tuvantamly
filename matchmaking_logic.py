from matchmaking.matchmaking_repository import get_all_students_from_matchmaking_queue, get_all_therapists_from_matchmaking_queue, delete_student_and_therapist_from_matchmaking_queue, add_student_and_therapist_to_matchmaking_results, get_match_id_based_on_pair

def check_student_urgency(student):
    return True if student["urgency"] == 1 else False

def check_student_topic_with_therapist_expertise(student, therapist):
    return True if student["topic"] == therapist["expertise"] else False

def write_matchmaking_result(student, therapist):
    return {
        "student_user_id": student["user_id"],
        "therapist_user_id": therapist["user_id"],
        "student_session_id": student["session_id"],
        "therapist_session_id": therapist["session_id"],
    }

def run_matchmaking():
    from main import notify_users_of_new_match
    results = []
    students = get_all_students_from_matchmaking_queue()
    therapists = get_all_therapists_from_matchmaking_queue()

    i = 0
    while (i < len(students)) and (len(therapists) > 0):
        student = students[i]
        matched = False

        if check_student_urgency(student):
            therapist = therapists[0]
            pair = write_matchmaking_result(student, therapist)
            delete_student_and_therapist_from_matchmaking_queue(student, therapist)
            results.append(pair)
            students = get_all_students_from_matchmaking_queue()
            therapists = get_all_therapists_from_matchmaking_queue()
            matched = True

        else:
            for therapist in therapists:
                if check_student_topic_with_therapist_expertise(student, therapist):
                    pair = write_matchmaking_result(student, therapist)
                    delete_student_and_therapist_from_matchmaking_queue(student, therapist)
                    results.append(pair)
                    students = get_all_students_from_matchmaking_queue()
                    therapists = get_all_therapists_from_matchmaking_queue()
                    matched = True
                    break

        if not matched:
            i += 1

    for pair in results:
        add_student_and_therapist_to_matchmaking_results(pair)
        notify_users_of_new_match(pair["student_user_id"], pair["therapist_user_id"], pair["student_session_id"], pair["therapist_session_id"])
    
    print("end matchmaking algo")
    