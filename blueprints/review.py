"""
Review blueprint for lecturer review and scoring.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_lecturer

review_bp = Blueprint("review", __name__)


@review_bp.route("/sessions", methods=["GET"])
@require_lecturer
def get_sessions_to_review():
    """Get list of sessions to review (Lecturer only)."""
    lecturer_id = request.user_id
    
    try:
        # Get all EXAM sessions created by lecturer
        sessions_response = supabase.table("session").select("*").eq("created_by", lecturer_id).eq("session_type", "EXAM").order("created_at", desc=True).execute()
        
        if not sessions_response.data:
            return jsonify([]), 200
        
        # Get student count for each session
        sessions_with_counts = []
        for session in sessions_response.data:
            # Count students who have completed
            student_sessions_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session["session_id"]).execute()
            student_count = len(student_sessions_response.data or [])
            
            sessions_with_counts.append({
                **session,
                "student_count": student_count
            })
        
        return jsonify(sessions_with_counts), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get sessions: {str(e)}"}), 500


@review_bp.route("/sessions/<int:session_id>/students", methods=["GET"])
@require_lecturer
def get_session_students(session_id):
    """Get list of students who participated in a session."""
    lecturer_id = request.user_id
    
    try:
        # Verify session exists and lecturer is creator
        session_response = supabase.table("session").select("created_by").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        if session_response.data["created_by"] != lecturer_id:
            return jsonify({"error": "Only session creator can view students"}), 403
        
        # Get all student sessions
        student_sessions_response = supabase.table("studentsession").select("*").eq("session_id", session_id).order("join_time", desc=True).execute()
        
        if not student_sessions_response.data:
            return jsonify([]), 200
        
        # Format response with student info
        students = []
        for ss in student_sessions_response.data:
            # Get student info
            student_response = supabase.table("student").select("*, User(*)").eq("student_id", ss["student_id"]).single().execute()
            
            student_data = {}
            user_data = {}
            if student_response.data:
                student_data = student_response.data
                user_data = student_data.get("User", {}) if isinstance(student_data.get("User"), dict) else {}
            
            students.append({
                "student_session_id": ss["student_session_id"],
                "student_id": ss["student_id"],
                "student_name": user_data.get("full_name", "") if user_data else "",
                "student_code": student_data.get("student_code", ""),
                "score_total": ss.get("score_total"),
                "join_time": ss.get("join_time"),
                "reviewed_by": ss.get("reviewed_by"),
                "reviewed_at": ss.get("reviewed_at")
            })
        
        return jsonify(students), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get students: {str(e)}"}), 500


@review_bp.route("/student-sessions/<int:student_session_id>", methods=["GET"])
@require_lecturer
def get_student_session_details(student_session_id):
    """Get detailed student session for review."""
    lecturer_id = request.user_id
    
    try:
        # Get student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        ss = student_session_response.data
        
        # Get session info
        session_response = supabase.table("session").select("*").eq("session_id", ss["session_id"]).single().execute()
        session = session_response.data if session_response.data else {}
        
        # Get student info
        student_response = supabase.table("student").select("*, User(*)").eq("student_id", ss["student_id"]).single().execute()
        student_data = student_response.data if student_response.data else {}
        user_data = student_data.get("User", {}) if isinstance(student_data.get("User"), dict) else {}
        
        # Verify lecturer is session creator
        if session.get("created_by") != lecturer_id:
            return jsonify({"error": "Only session creator can view student session"}), 403
        
        # Get all answers
        answers_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).execute()
        answers = answers_response.data or []
        
        # Get questions
        question_ids = [a["question_id"] for a in answers] if answers else []
        questions_dict = {}
        if question_ids:
            questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
            questions_dict = {q["question_id"]: q for q in (questions_response.data or [])}
        
        # Format answers
        formatted_answers = []
        scores_breakdown = {
            "correctness": 0.0,
            "coverage": 0.0,
            "reasoning": 0.0,
            "creativity": 0.0,
            "communication": 0.0,
            "attitude": 0.0
        }
        
        for answer in answers:
            question = questions_dict.get(answer["question_id"], {})
            
            # Get scores from AI feedback if available
            # Note: We might need to parse scores from feedback or store separately
            # For now, we'll use ai_score as the main score
            
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
            "student_name": user_data.get("full_name", "") if user_data else "",
            "student_id": student_data.get("student_code", ""),
            "session_name": session.get("session_name", ""),
            "session_type": session.get("session_type", ""),
            "score_total": ss.get("score_total"),
            "ai_overall_feedback": ss.get("ai_overall_feedback"),
            "answers": formatted_answers,
            "scores_breakdown": scores_breakdown,
            "join_time": ss.get("join_time"),
            "reviewed_by": ss.get("reviewed_by"),
            "reviewed_at": ss.get("reviewed_at")
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get student session: {str(e)}"}), 500


@review_bp.route("/answers/<int:answer_id>/score", methods=["PUT"])
@require_lecturer
def edit_answer_score(answer_id):
    """Edit score for an answer."""
    data = request.get_json()
    lecturer_score = data.get("lecturer_score")
    
    if lecturer_score is None:
        return jsonify({"error": "Lecturer score is required"}), 400
    
    if not (0 <= lecturer_score <= 10):
        return jsonify({"error": "Score must be between 0 and 10"}), 400
    
    lecturer_id = request.user_id
    
    try:
        # Get answer
        answer_response = supabase.table("studentanswer").select("*").eq("answer_id", answer_id).single().execute()
        
        if not answer_response.data:
            return jsonify({"error": "Answer not found"}), 404
        
        answer = answer_response.data
        
        # Get student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", answer["student_session_id"]).single().execute()
        student_session = student_session_response.data if student_session_response.data else {}
        
        # Get session
        session_response = supabase.table("session").select("*").eq("session_id", student_session.get("session_id")).single().execute()
        session = session_response.data if session_response.data else {}
        
        # Verify lecturer is session creator
        if session.get("created_by") != lecturer_id:
            return jsonify({"error": "Only session creator can edit scores"}), 403
        
        # Get old score for logging
        old_score = answer.get("lecturer_score") or answer.get("ai_score")
        
        # Update answer
        supabase.table("studentanswer").update({
            "lecturer_score": lecturer_score
        }).eq("answer_id", answer_id).execute()
        
        # Log review action
        try:
            supabase.table("reviewlog").insert({
                "answer_id": answer_id,
                "reviewer_id": lecturer_id,
                "old_score": old_score,
                "new_score": lecturer_score
            }).execute()
        except:
            pass
        
        # Recalculate overall score
        student_session_id = answer["student_session_id"]
        recalculate_overall_score(student_session_id)
        
        return jsonify({
            "answer_id": answer_id,
            "lecturer_score": lecturer_score,
            "message": "Score updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update score: {str(e)}"}), 500


@review_bp.route("/answers/<int:answer_id>/feedback", methods=["PUT"])
@require_lecturer
def edit_answer_feedback(answer_id):
    """Edit feedback for an answer."""
    data = request.get_json()
    lecturer_feedback = data.get("lecturer_feedback")
    
    if lecturer_feedback is None:
        return jsonify({"error": "Lecturer feedback is required"}), 400
    
    lecturer_id = request.user_id
    
    try:
        # Get answer
        answer_response = supabase.table("studentanswer").select("*").eq("answer_id", answer_id).single().execute()
        
        if not answer_response.data:
            return jsonify({"error": "Answer not found"}), 404
        
        answer = answer_response.data
        
        # Get student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", answer["student_session_id"]).single().execute()
        student_session = student_session_response.data if student_session_response.data else {}
        
        # Get session
        session_response = supabase.table("session").select("*").eq("session_id", student_session.get("session_id")).single().execute()
        session = session_response.data if session_response.data else {}
        
        # Verify lecturer is session creator
        if session.get("created_by") != lecturer_id:
            return jsonify({"error": "Only session creator can edit feedback"}), 403
        
        # Get old feedback for logging
        old_feedback = answer.get("lecturer_feedback") or answer.get("ai_feedback", "")
        
        # Update answer
        supabase.table("studentanswer").update({
            "lecturer_feedback": lecturer_feedback
        }).eq("answer_id", answer_id).execute()
        
        # Log review action
        try:
            supabase.table("reviewlog").insert({
                "answer_id": answer_id,
                "reviewer_id": lecturer_id,
                "old_feedback": old_feedback,
                "new_feedback": lecturer_feedback
            }).execute()
        except:
            pass
        
        return jsonify({
            "answer_id": answer_id,
            "lecturer_feedback": lecturer_feedback,
            "message": "Feedback updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update feedback: {str(e)}"}), 500


@review_bp.route("/student-sessions/<int:student_session_id>/overall", methods=["PUT"])
@require_lecturer
def edit_overall_feedback(student_session_id):
    """Edit overall feedback for a student session."""
    data = request.get_json()
    lecturer_feedback = data.get("lecturer_feedback")
    
    if lecturer_feedback is None:
        return jsonify({"error": "Lecturer feedback is required"}), 400
    
    lecturer_id = request.user_id
    
    try:
        # Get student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        ss = student_session_response.data
        
        # Get session
        session_response = supabase.table("session").select("*").eq("session_id", ss["session_id"]).single().execute()
        session = session_response.data if session_response.data else {}
        
        # Verify lecturer is session creator
        if session.get("created_by") != lecturer_id:
            return jsonify({"error": "Only session creator can edit overall feedback"}), 403
        
        # Update student session
        # Note: We might want to add a separate lecturer_feedback field
        # For now, we'll update ai_overall_feedback
        supabase.table("studentsession").update({
            "ai_overall_feedback": lecturer_feedback,
            "reviewed_by": lecturer_id,
            "reviewed_at": datetime.now().isoformat()
        }).eq("student_session_id", student_session_id).execute()
        
        return jsonify({
            "student_session_id": student_session_id,
            "lecturer_feedback": lecturer_feedback,
            "message": "Overall feedback updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update overall feedback: {str(e)}"}), 500


def recalculate_overall_score(student_session_id: int):
    """Recalculate overall score for a student session."""
    try:
        # Get all answers
        answers_response = supabase.table("studentanswer").select("lecturer_score, ai_score").eq("student_session_id", student_session_id).execute()
        
        if not answers_response.data:
            return
        
        answers = answers_response.data
        scores = []
        
        for answer in answers:
            # Use lecturer_score if available, otherwise use ai_score
            score = answer.get("lecturer_score") or answer.get("ai_score")
            if score:
                scores.append(float(score))
        
        if scores:
            overall_score = sum(scores) / len(scores)
            
            # Update student session
            supabase.table("studentsession").update({
                "score_total": overall_score
            }).eq("student_session_id", student_session_id).execute()
            
    except Exception as e:
        print(f"Error recalculating overall score: {e}")

