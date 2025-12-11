"""
Student sessions blueprint for student participation flow.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth, require_student
from utils.answer_evaluator import evaluate_answer, generate_overall_feedback

student_sessions_bp = Blueprint("student_sessions", __name__)


@student_sessions_bp.route("/join", methods=["POST"])
@require_student
def join_session():
    """Join a session (EXAM requires password)."""
    data = request.get_json()
    session_id = data.get("session_id")
    password = data.get("password", "")
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    student_id = request.user_id
    
    try:
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Check session status and password based on session type
        if session["session_type"] == "EXAM":
            # EXAM sessions must be ready
            if session["status"] != "ready":
                return jsonify({"error": "Session is not ready yet"}), 400
            
            # Check password for EXAM sessions
            if session.get("password"):
                if password != session["password"]:
                    return jsonify({"error": "Invalid password"}), 401
        elif session["session_type"] in ["PRACTICE", "INTERVIEW"]:
            # PRACTICE/INTERVIEW sessions can be started immediately (status: created)
            # No password required
            if session["status"] not in ["created", "ready"]:
                return jsonify({"error": "Session is not available"}), 400
        
        # Check if student has already joined
        existing_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session_id).eq("student_id", student_id).execute()
        
        if existing_response.data:
            student_session_id = existing_response.data[0]["student_session_id"]
            return jsonify({
                "student_session_id": student_session_id,
                "message": "Already joined this session"
            }), 200
        
        # Create student session
        student_session_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        
        student_session_response = supabase.table("studentsession").insert(student_session_data).execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Failed to join session"}), 500
        
        student_session_id = student_session_response.data[0]["student_session_id"]
        
        return jsonify({
            "student_session_id": student_session_id,
            "session_id": session_id,
            "message": "Joined session successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to join session: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/start", methods=["POST"])
@require_student
def start_session(student_session_id):
    """Start a student session."""
    student_id = request.user_id
    
    try:
        # Verify student session exists and belongs to student
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", student_session["session_id"]).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Check if session is ready (for EXAM) or created (for PRACTICE/INTERVIEW)
        if session["session_type"] == "EXAM" and session["status"] != "ready":
            return jsonify({"error": "Session is not ready"}), 400
        elif session["session_type"] in ["PRACTICE", "INTERVIEW"] and session["status"] not in ["created", "ready"]:
            return jsonify({"error": "Session is not available"}), 400
        
        interview_time_limit = None

        # For PRACTICE: generate questions if not already generated
        if session["session_type"] == "PRACTICE":
            # Check if questions exist
            questions_response = supabase.table("question").select("question_id").eq("session_id", session["session_id"]).execute()
            
            if not questions_response.data:
                # Generate questions on the fly
                from utils.question_generator import generate_questions_for_session
                
                try:
                    questions = generate_questions_for_session(
                        session_id=session["session_id"],
                        material_id=session.get("material_id"),
                        course_name=session.get("course_name"),
                        difficulty_level=session.get("difficulty_level", "APPLY"),
                        session_type=session.get("session_type")
                    )
                    
                    # Insert questions
                    for question in questions:
                        question["status"] = "approved"  # Auto-approve for practice/interview
                        question["reference_answer"] = None  # Will be generated when answer is submitted
                        supabase.table("question").insert(question).execute()
                except Exception as e:
                    print(f"Warning: Failed to generate PRACTICE questions on-the-fly: {e}")
                    # Continue anyway - questions might be generated later
        elif session["session_type"] == "INTERVIEW":
            # Generate interview questions on the fly using CV/JD (ephemeral, not persisted as materials)
            questions_response = supabase.table("question_interview").select("question_interview_id").eq("session_id", session["session_id"]).execute()
            if not questions_response.data:
                try:
                    # Load interview config for sources
                    config_response = supabase.table("interviewconfig").select("*").eq("session_id", session["session_id"]).single().execute()
                    config = config_response.data or {}
                    interview_time_limit = config.get("time_limit")
                    cv_url = config.get("cv_url")
                    jd_url = config.get("jd_url")
                    num_questions = config.get("num_questions") or 8
                    job_title = config.get("position") or session.get("course_name") or ""
                    if not cv_url:
                        return jsonify({"error": "Interview CV is missing"}), 400

                    from utils.question_generator import generate_interview_questions

                    questions = generate_interview_questions(
                        session_id=session["session_id"],
                        job_title=job_title,
                        cv_source=cv_url,
                        jd_source=jd_url,
                        num_questions=num_questions,
                    )

                    # Insert interview questions
                    creator_uuid = None
                    try:
                        creator_uuid = getattr(getattr(request, "current_user", None), "user", None).id  # type: ignore
                    except Exception:
                        creator_uuid = None
                    for question in questions:
                        if creator_uuid:
                            question["created_by"] = creator_uuid
                        else:
                            # Avoid inserting invalid uuid (fallback to null if schema allows)
                            question["created_by"] = None
                        supabase.table("question_interview").insert(question).execute()

                    # Refresh count after insert
                    questions_response = supabase.table("question_interview").select("question_interview_id").eq("session_id", session["session_id"]).execute()
                    if not questions_response.data:
                        return jsonify({"error": "Failed to generate interview questions"}), 500
                except Exception as e:
                    print(f"Warning: Failed to generate INTERVIEW questions on-the-fly: {e}")
                    return jsonify({"error": f"Failed to generate interview questions: {e}"}), 500
        
        # Get total questions count
        if session["session_type"] == "INTERVIEW":
            questions_response = (
                supabase.table("question_interview")
                .select("question_interview_id")
                .eq("session_id", session["session_id"])
                .execute()
            )
        else:
            # Questions can have status "approved" or "answers_approved" - both are valid for students
            questions_response = supabase.table("question").select("question_id").eq("session_id", session["session_id"]).in_("status", ["approved", "answers_approved"]).execute()
        total_questions = len(questions_response.data or [])
        
        if total_questions == 0:
            return jsonify({"error": "No questions available for this session"}), 400
        
        time_limit_value = session.get("time_limit") or interview_time_limit
        return jsonify({
            "student_session_id": student_session_id,
            "session_started": True,
            "total_questions": total_questions,
            "time_limit": time_limit_value
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to start session: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/question", methods=["GET"])
@require_student
def get_next_question(student_session_id):
    """Get next question for student session."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        session_id = student_session["session_id"]
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        session_data = session_response.data or {}
        if not session_data:
            return jsonify({"error": "Session not found"}), 404
        
        if session_data.get("session_type") == "INTERVIEW":
            # Interview flow uses question_interview & studentanswer_interview
            answered_response = (
                supabase.table("studentanswer_interview")
                .select("question_interview_id")
                .eq("student_session_id", student_session_id)
                .execute()
            )
            answered_question_ids = [a["question_interview_id"] for a in (answered_response.data or [])]

            all_questions_response = (
                supabase.table("question_interview")
                .select("*")
                .eq("session_id", session_id)
                .order("question_index", desc=False)
                .execute()
            )
            all_questions = all_questions_response.data or []
            if answered_question_ids:
                unanswered = [q for q in all_questions if q["question_interview_id"] not in answered_question_ids]
            else:
                unanswered = all_questions

            if not unanswered:
                return jsonify({"message": "No more questions", "completed": True}), 200

            question = unanswered[0]
            total_questions = len(all_questions)

            return jsonify({
                "question_interview_id": question["question_interview_id"],
                "question_id": question["question_interview_id"],  # alias for FE compatibility
                "question": question.get("content", ""),
                "question_number": len(answered_question_ids) + 1,
                "total_questions": total_questions,
                "question_type": question.get("question_type", ""),
                "category": question.get("category", ""),
                "purpose": question.get("purpose", ""),
            }), 200
        else:
            # Get all answered question IDs
            answered_response = supabase.table("studentanswer").select("question_id").eq("student_session_id", student_session_id).execute()
            answered_question_ids = [a["question_id"] for a in (answered_response.data or [])]
            
            # Get all approved questions (both "approved" and "answers_approved" status)
            all_questions_response = supabase.table("question").select("*").eq("session_id", session_id).in_("status", ["approved", "answers_approved"]).execute()
            all_questions = all_questions_response.data or []
            
            # Filter out already answered questions
            if answered_question_ids:
                unanswered = [q for q in all_questions if q["question_id"] not in answered_question_ids]
            else:
                unanswered = all_questions
            
            if not unanswered:
                return jsonify({
                    "message": "No more questions",
                    "completed": True
                }), 200
            
            # Get first unanswered question
            question = unanswered[0]
            
            # Get total questions count
            total_questions = len(all_questions)
            
            return jsonify({
                "question_id": question["question_id"],
                "question": question["content"],
                "question_number": len(answered_question_ids) + 1,
                "total_questions": total_questions,
                "question_type": question.get("question_type", "")
            }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get question: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/answer", methods=["POST"])
@require_student
def submit_answer(student_session_id):
    """Submit answer for a question (store only, AI evaluation deferred)."""
    data = request.get_json()
    question_id = data.get("question_id")
    question_interview_id = data.get("question_interview_id")
    answer_text = data.get("answer")
    
    if not (question_id or question_interview_id) or not answer_text:
        return jsonify({"error": "Question ID and answer are required"}), 400
    
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Decide branch by session type
        session_response = supabase.table("session").select("*").eq("session_id", student_session["session_id"]).single().execute()
        session = session_response.data if session_response.data else {}
        session_type = session.get("session_type")

        if session_type == "INTERVIEW":
            # Get interview question
            question_response = (
                supabase.table("question_interview")
                .select("*")
                .eq("question_interview_id", question_interview_id)
                .single()
                .execute()
            )
            if not question_response.data:
                return jsonify({"error": "Question not found"}), 404
            question = question_response.data

            # Check if already answered
            existing_answer_response = (
                supabase.table("studentanswer_interview")
                .select("answer_id")
                .eq("student_session_id", student_session_id)
                .eq("question_interview_id", question_interview_id)
                .execute()
            )
            existing_answer = existing_answer_response.data[0] if existing_answer_response.data else None

            if existing_answer:
                answer_id = existing_answer["answer_id"]
                supabase.table("studentanswer_interview").update({
                    "answer_text": answer_text,
                    "ai_score": None,
                    "ai_feedback": None
                }).eq("answer_id", answer_id).execute()
            else:
                answer_data = {
                    "student_session_id": student_session_id,
                    "question_interview_id": question_interview_id,
                    "answer_text": answer_text,
                    "ai_score": None,
                    "ai_feedback": None
                }
                answer_response = supabase.table("studentanswer_interview").insert(answer_data).execute()
                if not answer_response.data:
                    return jsonify({"error": "Failed to save answer"}), 500
                answer_id = answer_response.data[0]["answer_id"]

            # Progress counters
            answered_response = supabase.table("studentanswer_interview").select("question_interview_id").eq("student_session_id", student_session_id).execute()
            answered_count = len(answered_response.data or [])
            all_questions_response = supabase.table("question_interview").select("question_interview_id").eq("session_id", question["session_id"]).execute()
            total_questions = len(all_questions_response.data or [])

            response_payload = {
                "answer_id": answer_id,
                "next_question_available": answered_count < total_questions,
                "answered_count": answered_count,
                "total_questions": total_questions
            }
        else:
            # Get question
            question_response = supabase.table("question").select("*").eq("question_id", question_id).single().execute()
            
            if not question_response.data:
                return jsonify({"error": "Question not found"}), 404
            
            question = question_response.data
            
            # Check if already answered
            existing_answer_response = supabase.table("studentanswer").select("answer_id").eq("student_session_id", student_session_id).eq("question_id", question_id).execute()
            existing_answer = existing_answer_response.data[0] if existing_answer_response.data else None
            
            # Get reference answer (if available)
            reference_answer = question.get("reference_answer", "")
            
            # For PRACTICE sessions, generate reference answer on-the-fly if not available
            if not reference_answer and session.get("session_type") == "PRACTICE":
                try:
                    from utils.question_generator import generate_reference_answers_for_questions
                    answer_map = generate_reference_answers_for_questions(
                        session_id=question["session_id"],
                        question_ids=[question_id],
                        material_id=session.get("material_id"),
                        course_name=session.get("course_name"),
                        session_type=session.get("session_type")
                    )
                    reference_answer = answer_map.get(question_id, "")
                    
                    # Update question with reference answer
                    if reference_answer:
                        supabase.table("question").update({
                            "reference_answer": reference_answer
                        }).eq("question_id", question_id).execute()
                except Exception as e:
                    print(f"Warning: Failed to generate reference answer: {e}")
                    reference_answer = ""  # Continue without reference answer
            
            if existing_answer:
                answer_id = existing_answer["answer_id"]
                supabase.table("studentanswer").update({
                    "answer_text": answer_text,
                    "ai_score": None,
                    "ai_feedback": None
                }).eq("answer_id", answer_id).execute()
            else:
                answer_data = {
                    "student_session_id": student_session_id,
                    "question_id": question_id,
                    "answer_text": answer_text,
                    "ai_score": None,
                    "ai_feedback": None
                }
                
                answer_response = supabase.table("studentanswer").insert(answer_data).execute()
                
                if not answer_response.data:
                    return jsonify({"error": "Failed to save answer"}), 500
                
                answer_id = answer_response.data[0]["answer_id"]
            
            # Check if there are more questions
            answered_response = supabase.table("studentanswer").select("question_id").eq("student_session_id", student_session_id).execute()
            answered_count = len(answered_response.data or [])
            
            # Get total questions
            all_questions_response = supabase.table("question").select("question_id").eq("session_id", question["session_id"]).eq("status", "approved").execute()
            total_questions = len(all_questions_response.data or [])
            
            response_payload = {
                "answer_id": answer_id,
                "next_question_available": answered_count < total_questions,
                "answered_count": answered_count,
                "total_questions": total_questions
            }
        
        return jsonify(response_payload), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to submit answer: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/end", methods=["POST"])
@require_student
def end_session(student_session_id):
    """End student session and generate overall feedback."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        session_id = student_session["session_id"]
        
        session_response = supabase.table("session").select("session_type, material_id, course_name").eq("session_id", session_id).single().execute()
        session = session_response.data if session_response.data else {}
        session_type = session.get("session_type")
        
        if session_type == "INTERVIEW":
            # Interview answers flow
            answers_response = supabase.table("studentanswer_interview").select("*").eq("student_session_id", student_session_id).execute()
            if not answers_response.data:
                return jsonify({"error": "No answers found"}), 400
            answers = answers_response.data

            question_ids = [a["question_interview_id"] for a in answers]
            questions_response = supabase.table("question_interview").select("*").in_("question_interview_id", question_ids).execute()
            questions_dict = {q["question_interview_id"]: q for q in (questions_response.data or [])}

            requires_evaluation = any(answer.get("ai_score") is None for answer in answers)

            if requires_evaluation:
                # Load interview config for CV/JD sources
                config_response = supabase.table("interviewconfig").select("*").eq("session_id", session_id).single().execute()
                config = config_response.data or {}
                cv_url = config.get("cv_url")
                jd_url = config.get("jd_url")
                job_title = config.get("position") or session.get("course_name") or ""
                if not cv_url:
                    return jsonify({"error": "Interview CV is missing, cannot evaluate"}), 400

                # Generate missing reference answers
                missing_reference_ids = [
                    q_id for q_id, question in questions_dict.items()
                    if question and not question.get("reference_answer")
                ]
                if missing_reference_ids:
                    try:
                        from utils.question_generator import generate_reference_answers_for_interview

                        answer_map = generate_reference_answers_for_interview(
                            question_interview_ids=missing_reference_ids,
                            cv_source=cv_url,
                            jd_source=jd_url,
                            job_title=job_title,
                        )

                        for q_id, ref_answer in answer_map.items():
                            if ref_answer:
                                supabase.table("question_interview").update({
                                    "reference_answer": ref_answer
                                }).eq("question_interview_id", q_id).execute()
                                if questions_dict.get(q_id):
                                    questions_dict[q_id]["reference_answer"] = ref_answer
                    except Exception as e:
                        print(f"Warning: Failed to generate interview reference answers during evaluation: {e}")

                # Evaluate answers
                for answer in answers:
                    question = questions_dict.get(answer["question_interview_id"], {})
                    if not question:
                        continue
                    reference_answer = question.get("reference_answer") or "No reference answer available. Evaluate based on the question and student's answer."
                    evaluation = evaluate_answer(
                        question=question.get("content", ""),
                        student_answer=answer.get("answer_text", ""),
                        reference_answer=reference_answer,
                        difficulty=question.get("question_type", ""),
                        session_type=session_type
                    )
                    ai_score_payload = {"overall_score": evaluation.get("overall_score", 0.0), **(evaluation.get("scores") or {})}
                    ai_feedback_payload = {
                        "feedback": evaluation.get("feedback", ""),
                        "strengths": evaluation.get("strengths", []),
                        "weaknesses": evaluation.get("weaknesses", []),
                    }
                    supabase.table("studentanswer_interview").update({
                        "ai_score": ai_score_payload,
                        "ai_feedback": ai_feedback_payload
                    }).eq("answer_id", answer["answer_id"]).execute()

                    answer["ai_score"] = evaluation.get("overall_score", 0.0)
                    answer["ai_feedback"] = evaluation.get("feedback", "")
                    answer["ai_scores_breakdown"] = evaluation.get("scores", {})

                    # Log AI request
                    try:
                        supabase.table("airequestlog").insert({
                            "session_id": session_id,
                            "request_type": "EVALUATE_ANSWER_INTERVIEW",
                            "request_payload": {
                                "question_interview_id": answer["question_interview_id"],
                                "answer_length": len(answer.get("answer_text") or "")
                            },
                            "response_payload": {
                                "score": evaluation.get("overall_score", 0.0),
                                "feedback_length": len(evaluation.get("feedback") or "")
                            }
                        }).execute()
                    except Exception:
                        pass

            def _overall_from_score(value):
                if isinstance(value, dict):
                    return float(value.get("overall_score") or value.get("overall") or 0.0)
                if isinstance(value, (int, float)):
                    return float(value)
                return 0.0

            total_score = sum(_overall_from_score(a.get("ai_score")) for a in answers)
            answered_count = len(answers)
            overall_score = total_score / answered_count if answered_count else 0.0

            qa_pairs = []
            scores_summary = {
                "correctness": 0.0,
                "coverage": 0.0,
                "reasoning": 0.0,
                "creativity": 0.0,
                "communication": 0.0,
                "attitude": 0.0
            }

            for answer in answers:
                question = questions_dict.get(answer["question_interview_id"], {})
                score_value = _overall_from_score(answer.get("ai_score"))
                qa_pairs.append({
                    "question": question.get("content", ""),
                    "answer": answer.get("answer_text", ""),
                    "score": score_value,
                    "feedback": answer.get("ai_feedback", "")
                })

                breakdown_source = answer.get("ai_scores_breakdown")
                if not breakdown_source and isinstance(answer.get("ai_score"), dict):
                    breakdown_source = answer.get("ai_score")
                breakdown = breakdown_source or {}
                for criterion in scores_summary:
                    value = breakdown.get(criterion)
                    if isinstance(value, (int, float)):
                        scores_summary[criterion] += float(value)

            if answered_count:
                scores_summary = {k: v / answered_count for k, v in scores_summary.items()}

            overall_feedback_data = generate_overall_feedback(qa_pairs, scores_summary, session_type=session_type)

            supabase.table("studentsession").update({
                "score_total": overall_score,
                "ai_overall_feedback": overall_feedback_data["overall_feedback"]
            }).eq("student_session_id", student_session_id).execute()

            return jsonify({
                "student_session_id": student_session_id,
                "score_total": overall_score,
                "ai_overall_feedback": overall_feedback_data["overall_feedback"],
                "completed_at": datetime.now().isoformat()
            }), 200
        else:
            # Original PRACTICE/EXAM flow
            answers_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).execute()
            
            if not answers_response.data:
                return jsonify({"error": "No answers found"}), 400
            
            answers = answers_response.data
            
            # Get questions for each answer
            question_ids = [a["question_id"] for a in answers]
            questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
            questions_dict = {q["question_id"]: q for q in (questions_response.data or [])}
            
            # Determine if evaluation is needed
            requires_evaluation = any(answer.get("ai_score") is None for answer in answers)
            
            if requires_evaluation:
                # Generate reference answers for missing ones
                missing_reference_ids = [
                    q_id for q_id, question in questions_dict.items()
                    if question and not question.get("reference_answer")
                ]
                
                if missing_reference_ids and session_type in ["PRACTICE", "INTERVIEW"]:
                    try:
                        from utils.question_generator import generate_reference_answers_for_questions
                        answer_map = generate_reference_answers_for_questions(
                            session_id=session_id,
                            question_ids=missing_reference_ids,
                            material_id=session.get("material_id"),
                            course_name=session.get("course_name"),
                            session_type=session_type
                        )
                        
                        for q_id, ref_answer in answer_map.items():
                            if ref_answer:
                                supabase.table("question").update({
                                    "reference_answer": ref_answer
                                }).eq("question_id", q_id).execute()
                                if questions_dict.get(q_id):
                                    questions_dict[q_id]["reference_answer"] = ref_answer
                    except Exception as e:
                        print(f"Warning: Failed to generate reference answers during evaluation: {e}")
                
                # Evaluate each answer now that all are collected
                for answer in answers:
                    question = questions_dict.get(answer["question_id"], {})
                    
                    if not question:
                        continue
                    
                    reference_answer = question.get("reference_answer") or "No reference answer available. Evaluate based on the question and student's answer."
                    
                    evaluation = evaluate_answer(
                        question=question.get("content", ""),
                        student_answer=answer.get("answer_text", ""),
                        reference_answer=reference_answer,
                        difficulty=question.get("question_type", ""),
                        session_type=session_type
                    )
                    
                    supabase.table("studentanswer").update({
                        "ai_score": evaluation["overall_score"],
                        "ai_feedback": evaluation["feedback"]
                    }).eq("answer_id", answer["answer_id"]).execute()
                    
                    # Update local copy to include evaluation results
                    answer["ai_score"] = evaluation["overall_score"]
                    answer["ai_feedback"] = evaluation["feedback"]
                    answer["ai_scores_breakdown"] = evaluation.get("scores", {})
                    
                    # Log AI request
                    try:
                        supabase.table("airequestlog").insert({
                            "session_id": session_id,
                            "request_type": "EVALUATE_ANSWER",
                            "request_payload": {
                                "question_id": answer["question_id"],
                                "answer_length": len(answer.get("answer_text") or "")
                            },
                            "response_payload": {
                                "score": evaluation["overall_score"],
                                "feedback_length": len(evaluation.get("feedback") or "")
                            }
                        }).execute()
                    except Exception:
                        pass
            
            # Calculate overall score
            total_score = sum((a.get("ai_score") or 0.0) for a in answers)
            answered_count = len(answers)
            overall_score = total_score / answered_count if answered_count else 0.0
            
            # Prepare Q&A pairs for overall feedback
            qa_pairs = []
            scores_summary = {
                "correctness": 0.0,
                "coverage": 0.0,
                "reasoning": 0.0,
                "creativity": 0.0,
                "communication": 0.0,
                "attitude": 0.0
            }
            
            for answer in answers:
                question = questions_dict.get(answer["question_id"], {})
                qa_pairs.append({
                    "question": question.get("content", ""),
                    "answer": answer.get("answer_text", ""),
                    "score": answer.get("ai_score", 0.0),
                    "feedback": answer.get("ai_feedback", "")
                })
                
                breakdown = answer.get("ai_scores_breakdown") or {}
                for criterion in scores_summary:
                    value = breakdown.get(criterion)
                    if isinstance(value, (int, float)):
                        scores_summary[criterion] += float(value)
            
            if answered_count:
                scores_summary = {k: v / answered_count for k, v in scores_summary.items()}
            
            # Generate overall feedback
            overall_feedback_data = generate_overall_feedback(qa_pairs, scores_summary, session_type=session_type)
            
            # Update student session
            supabase.table("studentsession").update({
                "score_total": overall_score,
                "ai_overall_feedback": overall_feedback_data["overall_feedback"]
            }).eq("student_session_id", student_session_id).execute()
            
            return jsonify({
                "student_session_id": student_session_id,
                "score_total": overall_score,
                "ai_overall_feedback": overall_feedback_data["overall_feedback"],
                "completed_at": datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to end session: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>", methods=["GET"])
@require_student
def get_student_session(student_session_id):
    """Get student session results."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", student_session["session_id"]).single().execute()
        session = session_response.data if session_response.data else {}
        
        if session.get("session_type") == "INTERVIEW":
            answers_response = supabase.table("studentanswer_interview").select("*").eq("student_session_id", student_session_id).execute()
            answers = answers_response.data or []

            question_ids = [a["question_interview_id"] for a in answers]
            questions_response = supabase.table("question_interview").select("*").in_("question_interview_id", question_ids).execute()
            questions_dict = {q["question_interview_id"]: q for q in (questions_response.data or [])}

            formatted_answers = []
            for answer in answers:
                question = questions_dict.get(answer["question_interview_id"], {})
                formatted_answers.append({
                    "answer_id": answer["answer_id"],
                    "question_interview_id": answer["question_interview_id"],
                    "question": question.get("content", ""),
                    "answer": answer.get("answer_text", ""),
                    "ai_score": answer.get("ai_score"),
                    "ai_feedback": answer.get("ai_feedback")
                })
        else:
            # PRACTICE/EXAM
            answers_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).execute()
            answers = answers_response.data or []
            
            # Get questions
            question_ids = [a["question_id"] for a in answers]
            questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
            questions_dict = {q["question_id"]: q for q in (questions_response.data or [])}
            
            # Format answers
            formatted_answers = []
            for answer in answers:
                question = questions_dict.get(answer["question_id"], {})
                formatted_answers.append({
                    "answer_id": answer["answer_id"],
                    "question_id": answer["question_id"],
                    "question": question.get("content", ""),
                    "answer": answer.get("answer_text", ""),
                    "ai_score": answer.get("ai_score"),
                    "ai_feedback": answer.get("ai_feedback"),
                    "lecturer_score": answer.get("lecturer_score"),
                    "lecturer_feedback": answer.get("lecturer_feedback")
                })
        
        return jsonify({
            "student_session_id": student_session_id,
            "session_id": student_session["session_id"],
            "session_name": session.get("session_name", ""),
            "session_type": session.get("session_type", ""),
            "score_total": student_session.get("score_total"),
            "ai_overall_feedback": student_session.get("ai_overall_feedback"),
            "answers": formatted_answers,
            "join_time": student_session.get("join_time")
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get student session: {str(e)}"}), 500


@student_sessions_bp.route("/history", methods=["GET"])
@require_student
def get_history():
    """Get student's session history."""
    student_id = request.user_id
    
    try:
        # Get all student sessions
        student_sessions_response = supabase.table("studentsession").select("*").eq("student_id", student_id).order("join_time", desc=True).execute()
        
        if not student_sessions_response.data:
            return jsonify([]), 200
        
        # Format response with session details
        history = []
        for ss in student_sessions_response.data:
            # Get session details
            session_response = supabase.table("session").select("*").eq("session_id", ss["session_id"]).single().execute()
            session = session_response.data if session_response.data else {}
            
            history.append({
                "student_session_id": ss["student_session_id"],
                "session_id": ss["session_id"],
                "session_name": session.get("session_name", ""),
                "session_type": session.get("session_type", ""),
                "course_name": session.get("course_name", ""),
                "score_total": ss.get("score_total"),
                "join_time": ss.get("join_time")
            })
        
        return jsonify(history), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get history: {str(e)}"}), 500

