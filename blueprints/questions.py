"""
Questions blueprint for question generation and review workflow.
"""
from flask import Blueprint, request, jsonify
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth, require_lecturer
from utils.question_generator import generate_questions_for_session, generate_reference_answers_for_questions
from extensions.llm import call_llm_json, prompt_generate_script
from config import BATCH_SIZE

questions_bp = Blueprint("questions", __name__)


@questions_bp.route("/generate", methods=["POST"])
@require_lecturer
def generate_questions():
    """Generate questions for a session (draft status)."""
    data = request.get_json()
    session_id = data.get("session_id")
    num_questions = data.get("num_questions")
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    user_id = request.user_id
    
    try:
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Verify user is creator
        if session["created_by"] != user_id:
            return jsonify({"error": "Only session creator can generate questions"}), 403
        
        # Update session status
        supabase.table("session").update({"status": "generating_questions"}).eq("session_id", session_id).execute()
        
        # Generate questions
        questions = generate_questions_for_session(
            session_id=session_id,
            material_id=session.get("material_id"),
            course_name=session.get("course_name"),
            difficulty_level=session.get("difficulty_level", "APPLY"),
            num_questions=num_questions or BATCH_SIZE
        )
        
        # Insert questions into database
        question_ids = []
        for question in questions:
            question["created_by"] = user_id
            question_response = supabase.table("question").insert(question).execute()
            if question_response.data:
                question_ids.append(question_response.data[0]["question_id"])
        
        # Update session status
        supabase.table("session").update({"status": "reviewing_questions"}).eq("session_id", session_id).execute()
        
        # Log AI request
        try:
            supabase.table("airequestlog").insert({
                "session_id": session_id,
                "request_type": "GENERATE_QUESTION",
                "request_payload": {"num_questions": len(question_ids)},
                "response_payload": {"question_ids": question_ids}
            }).execute()
        except:
            pass  # Logging is optional
        
        return jsonify({
            "question_ids": question_ids,
            "count": len(question_ids),
            "status": "draft",
            "next_step": "review_questions"
        }), 200
        
    except Exception as e:
        # Reset session status on error
        try:
            supabase.table("session").update({"status": "created"}).eq("session_id", session_id).execute()
        except:
            pass
        return jsonify({"error": f"Failed to generate questions: {str(e)}"}), 500


@questions_bp.route("/session/<int:session_id>", methods=["GET"])
@require_auth
def get_questions(session_id):
    """Get questions for a session, filtered by status."""
    status = request.args.get("status", "all")
    
    try:
        query = supabase.table("question").select("*").eq("session_id", session_id)
        
        if status != "all":
            query = query.eq("status", status)
        
        questions_response = query.order("question_id", desc=False).execute()
        
        if not questions_response.data:
            return jsonify([]), 200
        
        return jsonify(questions_response.data), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get questions: {str(e)}"}), 500


@questions_bp.route("/<int:question_id>", methods=["PUT"])
@require_lecturer
def update_question(question_id):
    """Update a question (Lecturer only)."""
    data = request.get_json()
    
    content = data.get("content")
    keywords = data.get("keywords")
    difficulty = data.get("difficulty")
    
    try:
        # Verify question exists
        question_response = supabase.table("question").select("*").eq("question_id", question_id).single().execute()
        
        if not question_response.data:
            return jsonify({"error": "Question not found"}), 404
        
        question = question_response.data
        
        # Verify user is session creator
        session_response = supabase.table("session").select("created_by").eq("session_id", question["session_id"]).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can edit questions"}), 403
        
        # Update question
        update_data = {}
        if content:
            update_data["content"] = content
        if keywords:
            update_data["keywords"] = keywords
        if difficulty:
            update_data["difficulty"] = difficulty
        
        if update_data:
            supabase.table("question").update(update_data).eq("question_id", question_id).execute()
        
        return jsonify({"message": "Question updated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update question: {str(e)}"}), 500


@questions_bp.route("/<int:question_id>", methods=["DELETE"])
@require_lecturer
def delete_question(question_id):
    """Delete a question (Lecturer only)."""
    try:
        # Verify question exists
        question_response = supabase.table("question").select("*").eq("question_id", question_id).single().execute()
        
        if not question_response.data:
            return jsonify({"error": "Question not found"}), 404
        
        question = question_response.data
        
        # Verify user is session creator
        session_response = supabase.table("session").select("created_by").eq("session_id", question["session_id"]).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can delete questions"}), 403
        
        # Delete question
        supabase.table("question").delete().eq("question_id", question_id).execute()
        
        return jsonify({"message": "Question deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete question: {str(e)}"}), 500


@questions_bp.route("/approve", methods=["POST"])
@require_lecturer
def approve_questions():
    """Approve questions (move from draft to approved)."""
    data = request.get_json()
    session_id = data.get("session_id")
    question_ids = data.get("question_ids")  # Optional: specific questions to approve
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    try:
        # Verify session and user is creator
        session_response = supabase.table("session").select("created_by").eq("session_id", session_id).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can approve questions"}), 403
        
        # Update questions status
        query = supabase.table("question").update({"status": "approved"}).eq("session_id", session_id).eq("status", "draft")
        
        if question_ids:
            query = query.in_("question_id", question_ids)
        
        query.execute()
        
        # Update session status
        supabase.table("session").update({"status": "generating_answers"}).eq("session_id", session_id).execute()
        
        return jsonify({
            "message": "Questions approved successfully",
            "status": "generating_answers",
            "next_step": "generate_reference_answers"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to approve questions: {str(e)}"}), 500


@questions_bp.route("/generate-answers", methods=["POST"])
@require_lecturer
def generate_answers():
    """Generate reference answers for approved questions."""
    data = request.get_json()
    session_id = data.get("session_id")
    question_ids = data.get("question_ids")  # Optional: specific questions
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    try:
        # Verify session and user is creator
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can generate answers"}), 403
        
        session = session_response.data
        
        # Get approved questions
        query = supabase.table("question").select("*").eq("session_id", session_id).eq("status", "approved")
        
        if question_ids:
            query = query.in_("question_id", question_ids)
        
        questions_response = query.execute()
        
        if not questions_response.data:
            return jsonify({"error": "No approved questions found"}), 400
        
        questions = questions_response.data
        question_ids_list = [q["question_id"] for q in questions]
        
        # Generate reference answers
        answer_map = generate_reference_answers_for_questions(
            session_id=session_id,
            question_ids=question_ids_list,
            material_id=session.get("material_id"),
            course_name=session.get("course_name")
        )
        
        # Update questions with reference answers
        for question_id, reference_answer in answer_map.items():
            supabase.table("question").update({
                "reference_answer": reference_answer,
                "status": "answers_generated"
            }).eq("question_id", question_id).execute()
        
        # Update session status
        supabase.table("session").update({"status": "reviewing_answers"}).eq("session_id", session_id).execute()
        
        return jsonify({
            "question_ids": question_ids_list,
            "answers_generated": len(answer_map),
            "status": "answers_generated",
            "next_step": "review_answers"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate reference answers: {str(e)}"}), 500


@questions_bp.route("/<int:question_id>/answer", methods=["PUT"])
@require_lecturer
def update_reference_answer(question_id):
    """Update reference answer for a question."""
    data = request.get_json()
    reference_answer = data.get("reference_answer")
    
    if not reference_answer:
        return jsonify({"error": "Reference answer is required"}), 400
    
    try:
        # Verify question exists
        question_response = supabase.table("question").select("*").eq("question_id", question_id).single().execute()
        
        if not question_response.data:
            return jsonify({"error": "Question not found"}), 404
        
        question = question_response.data
        
        # Verify user is session creator
        session_response = supabase.table("session").select("created_by").eq("session_id", question["session_id"]).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can edit answers"}), 403
        
        # Update reference answer
        supabase.table("question").update({
            "reference_answer": reference_answer,
            "status": "answers_generated"
        }).eq("question_id", question_id).execute()
        
        return jsonify({"message": "Reference answer updated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update reference answer: {str(e)}"}), 500


@questions_bp.route("/approve-answers", methods=["POST"])
@require_lecturer
def approve_answers():
    """Approve reference answers (move to answers_approved)."""
    data = request.get_json()
    session_id = data.get("session_id")
    question_ids = data.get("question_ids")  # Optional
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    try:
        # Verify session and user is creator
        session_response = supabase.table("session").select("created_by").eq("session_id", session_id).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can approve answers"}), 403
        
        # Update questions status
        query = supabase.table("question").update({"status": "answers_approved"}).eq("session_id", session_id).eq("status", "answers_generated")
        
        if question_ids:
            query = query.in_("question_id", question_ids)
        
        query.execute()
        
        # Update session status
        supabase.table("session").update({"status": "generating_script"}).eq("session_id", session_id).execute()
        
        return jsonify({
            "message": "Reference answers approved successfully",
            "status": "answers_approved",
            "next_step": "generate_script"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to approve answers: {str(e)}"}), 500

