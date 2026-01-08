from matchmaking_repository import get_all_students_from_matchmaking_queue, get_all_therapists_from_matchmaking_queue, delete_student_and_therapist_from_matchmaking_queue, add_student_and_therapist_to_matchmaking_results, get_match_id_based_on_pair, extract_topic_from_tags

def check_student_urgency(student):
    return True if student["urgency"] == 1 else False

def check_student_topic_with_therapist_expertise(student, therapist):
    student_topic = extract_topic_from_tags(student["topic"])
    therapist_expertise = extract_topic_from_tags(therapist["expertise"])
    if "General" in student_topic:
        return True
    return True if any(topic in therapist_expertise for topic in student_topic) else False

def write_matchmaking_result(student, therapist):
    return {
        "student_user_id": student["user_id"],
        "therapist_user_id": therapist["user_id"],
        "student_session_id": student["session_id"],
        "therapist_session_id": therapist["session_id"],
    }


# def run_matchmaking():
#     from socket_helperfuncs import notify_users_of_new_match
#     results = []
#     students = get_all_students_from_matchmaking_queue()
#     therapists = get_all_therapists_from_matchmaking_queue()

#     i = 0
#     while (i < len(students)) and (len(therapists) > 0):
#         student = students[i]
#         matched = False

#         if check_student_urgency(student):
#             therapist = therapists[0]
#             pair = write_matchmaking_result(student, therapist)
#             delete_student_and_therapist_from_matchmaking_queue(student, therapist)
#             results.append(pair)
#             students = get_all_students_from_matchmaking_queue()
#             therapists = get_all_therapists_from_matchmaking_queue()
#             matched = True

#         else:
#             for therapist in therapists:
#                 if check_student_topic_with_therapist_expertise(student, therapist):
#                     pair = write_matchmaking_result(student, therapist)
#                     delete_student_and_therapist_from_matchmaking_queue(student, therapist)
#                     results.append(pair)
#                     students = get_all_students_from_matchmaking_queue()
#                     therapists = get_all_therapists_from_matchmaking_queue()
#                     matched = True
#                     break

#         if not matched:
#             i += 1

#     for pair in results:
#         add_student_and_therapist_to_matchmaking_results(pair)
#         notify_users_of_new_match(pair["student_user_id"], pair["therapist_user_id"], pair["student_session_id"], pair["therapist_session_id"])
    
#     print("end matchmaking algo")
    


def run_matchmaking():
    from socket_helperfuncs import notify_users_of_new_match, generate_unique_code1 # Cần import generate_unique_code1
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
            
            # --- TẠO VÀ GÁN ROOMCODE NGAY TẠI ĐÂY ---
            room_code = generate_unique_code1(6) # Tạo mã phòng
            pair["roomcode"] = room_code        # Gán vào dictionary pair
            # ----------------------------------------
            
            delete_student_and_therapist_from_matchmaking_queue(student, therapist)
            results.append(pair)
            # ... (Truy vấn lại danh sách và matched = True) ...

        else:
            for therapist in therapists:
                if check_student_topic_with_therapist_expertise(student, therapist):
                    pair = write_matchmaking_result(student, therapist)
                    
                    # --- TẠO VÀ GÁN ROOMCODE NGAY TẠI ĐÂY ---
                    room_code = generate_unique_code1(6) # Tạo mã phòng
                    pair["roomcode"] = room_code        # Gán vào dictionary pair
                    # ----------------------------------------
                    
                    delete_student_and_therapist_from_matchmaking_queue(student, therapist)
                    results.append(pair)
                    # ... (Truy vấn lại danh sách, matched = True, break) ...

        if not matched:
            i += 1
            
    # Phần cuối hàm:
    for pair in results:
        # 1. TẠO PHÒNG TRONG BỘ NHỚ và Thông báo cho Client
        notify_users_of_new_match(pair["student_user_id"], pair["therapist_user_id"], pair["student_session_id"], pair["therapist_session_id"], pair["roomcode"])
        
        # 2. LƯU KẾT QUẢ VÀO DB (Bây giờ đã bao gồm roomcode)
        add_student_and_therapist_to_matchmaking_results(pair) 
        
    print("end matchmaking algo")