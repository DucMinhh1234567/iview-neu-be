"""
Sessions blueprint for managing EXAM, PRACTICE, and INTERVIEW sessions.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth, require_lecturer, require_student
from utils.storage import StorageService
from utils.bloom_taxonomy import get_included_levels

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/exam", methods=["POST"])
@require_lecturer
def create_exam_session():
    """Create EXAM session (Lecturer only)."""
    data = request.get_json()
    
    session_name = data.get("session_name")
    course_name = data.get("course_name")
    material_id = data.get("material_id")
    difficulty_level = data.get("difficulty_level")
    password = data.get("password", "")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    time_limit = data.get("time_limit")  # Optional, in minutes
    
    if not all([session_name, course_name, difficulty_level]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if not material_id:
        return jsonify({"error": "Material ID is required"}), 400
    
    user_id = request.user_id
    
    try:
        # Verify material exists
        material_response = supabase.table("material").select("material_id").eq("material_id", material_id).single().execute()
        if not material_response.data:
            return jsonify({"error": "Material not found"}), 404
        
        # Create session
        session_data = {
            "session_name": session_name,
            "session_type": "EXAM",
            "course_name": course_name,
            "created_by": user_id,
            "material_id": material_id,
            "difficulty_level": difficulty_level,
            "password": password if password else None,
            "start_time": start_time,
            "end_time": end_time,
            "status": "created"
        }
        
        session_response = supabase.table("session").insert(session_data).execute()
        
        if not session_response.data:
            return jsonify({"error": "Failed to create session"}), 500
        
        session_id = session_response.data[0]["session_id"]
        
        return jsonify({
            "session_id": session_id,
            "message": "Exam session created successfully",
            "status": "created"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create exam session: {str(e)}"}), 500


@sessions_bp.route("/practice", methods=["POST"])
@require_student
def create_practice_session():
    """Create PRACTICE session (Student only)."""
    data = request.get_json()
    
    session_name = data.get("session_name")
    course_name = data.get("course_name")
    material_id = data.get("material_id")  # Optional
    difficulty_level = data.get("difficulty_level")
    time_limit = data.get("time_limit")  # Required, in minutes
    
    if not all([session_name, course_name, difficulty_level, time_limit]):
        return jsonify({"error": "Missing required fields"}), 400
    
    user_id = request.user_id
    
    try:
        # Verify material if provided
        if material_id:
            material_response = supabase.table("material").select("material_id").eq("material_id", material_id).single().execute()
            if not material_response.data:
                return jsonify({"error": "Material not found"}), 404
        
        # Create session
        session_data = {
            "session_name": session_name,
            "session_type": "PRACTICE",
            "course_name": course_name,
            "created_by": user_id,
            "material_id": material_id if material_id else None,
            "difficulty_level": difficulty_level,
            "status": "created"
        }
        
        session_response = supabase.table("session").insert(session_data).execute()
        
        if not session_response.data:
            return jsonify({"error": "Failed to create session"}), 500
        
        session_id = session_response.data[0]["session_id"]
        
        return jsonify({
            "session_id": session_id,
            "message": "Practice session created successfully",
            "status": "created"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create practice session: {str(e)}"}), 500


@sessions_bp.route("/interview", methods=["POST"])
@require_student
def create_interview_session():
    """Create INTERVIEW session (Student only)."""
    data = request.get_json()
    
    session_name = data.get("session_name")
    position = data.get("position")
    level = data.get("level")
    cv_url = data.get("cv_url")
    jd_url = data.get("jd_url", "")
    time_limit = data.get("time_limit")
    num_questions = data.get("num_questions")
    
    if not all([session_name, position, level, cv_url]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if not time_limit and not num_questions:
        return jsonify({"error": "Either time_limit or num_questions is required"}), 400
    
    user_id = request.user_id
    
    try:
        # Create session
        session_data = {
            "session_name": session_name,
            "session_type": "INTERVIEW",
            "created_by": user_id,
            "status": "created"
        }
        
        session_response = supabase.table("session").insert(session_data).execute()
        
        if not session_response.data:
            return jsonify({"error": "Failed to create session"}), 500
        
        session_id = session_response.data[0]["session_id"]
        
        # Create interview config
        config_data = {
            "session_id": session_id,
            "position": position,
            "level": level,
            "cv_url": cv_url,
            "jd_url": jd_url if jd_url else None,
            "time_limit": time_limit,
            "num_questions": num_questions
        }
        
        config_response = supabase.table("interviewconfig").insert(config_data).execute()
        
        if not config_response.data:
            # Delete session if config creation fails
            supabase.table("session").delete().eq("session_id", session_id).execute()
            return jsonify({"error": "Failed to create interview config"}), 500
        
        return jsonify({
            "session_id": session_id,
            "config_id": config_response.data[0]["config_id"],
            "message": "Interview session created successfully",
            "status": "created"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to create interview session: {str(e)}"}), 500


@sessions_bp.route("/interview/upload-cv", methods=["POST"])
@require_student
def upload_cv():
    """Upload CV for interview session."""
    file = request.files.get("file")
    session_id = request.form.get("session_id")
    
    if not file:
        return jsonify({"error": "CV file is required"}), 400
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Validate file type
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        return jsonify({"error": "Only PDF, PNG, JPG, JPEG files are allowed"}), 400
    
    try:
        # Upload file
        file_info = StorageService.upload_file(file, session_id, file_type="cv")
        
        return jsonify({
            "cv_url": file_info["url"],
            "file_path": file_info["file_path"],
            "storage_type": file_info["storage_type"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to upload CV: {str(e)}"}), 500


@sessions_bp.route("/interview/upload-jd", methods=["POST"])
@require_student
def upload_jd():
    """Upload JD (Job Description) for interview session (optional)."""
    file = request.files.get("file")
    session_id = request.form.get("session_id")
    
    if not file:
        return jsonify({"error": "JD file is required"}), 400
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Validate file type (mainly PDF)
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed for JD"}), 400
    
    try:
        # Upload file
        file_info = StorageService.upload_file(file, session_id, file_type="jd")
        
        return jsonify({
            "jd_url": file_info["url"],
            "file_path": file_info["file_path"],
            "storage_type": file_info["storage_type"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to upload JD: {str(e)}"}), 500


@sessions_bp.route("", methods=["GET"])
@require_auth
def get_sessions():
    """Get sessions based on user role and filters."""
    session_type = request.args.get("type")
    created_by = request.args.get("created_by")
    user_id = request.user_id
    user_role = request.user_role
    
    try:
        query = supabase.table("session").select("*")
        
        # Filter by type if provided
        if session_type:
            query = query.eq("session_type", session_type)
        
        # Filter by creator if provided or if user is lecturer
        if created_by:
            query = query.eq("created_by", created_by)
        elif user_role == "LECTURER":
            query = query.eq("created_by", user_id)
        
        # Order by created_at desc and limit to prevent timeout with too many sessions
        # Default limit to 100 sessions, can be increased if needed
        limit = request.args.get("limit", type=int)
        if limit:
            query = query.limit(limit)
        else:
            query = query.limit(100)  # Default limit to prevent timeout
        
        sessions_response = query.order("created_at", desc=True).execute()
        
        if not sessions_response.data:
            return jsonify([]), 200
        
        sessions = sessions_response.data
        session_ids = [s["session_id"] for s in sessions]
        
        # Optimize: Get all student counts in one query instead of per session
        # Get all student sessions for these session IDs
        student_counts = {}
        if session_ids:
            try:
                # Query all student sessions for these sessions at once
                student_sessions_response = supabase.table("studentsession").select("session_id").in_("session_id", session_ids).execute()
                
                # Count students per session
                if student_sessions_response.data:
                    for ss in student_sessions_response.data:
                        session_id = ss["session_id"]
                        student_counts[session_id] = student_counts.get(session_id, 0) + 1
            except Exception as e:
                # If batch query fails, fall back to 0 for all
                print(f"Warning: Failed to get student counts: {e}")
        
        # Add student count to each session
        sessions_with_counts = []
        for session in sessions:
            session_id = session["session_id"]
            sessions_with_counts.append({
                **session,
                "student_count": student_counts.get(session_id, 0)
            })
        
        return jsonify(sessions_with_counts), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get sessions: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>", methods=["GET"])
@require_auth
def get_session(session_id):
    """Get session details."""
    try:
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Get student count
        student_sessions_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session_id).execute()
        student_count = len(student_sessions_response.data or [])
        session["student_count"] = student_count
        
        # Get questions count
        questions_response = supabase.table("question").select("question_id").eq("session_id", session_id).execute()
        questions_count = len(questions_response.data or [])
        session["questions_count"] = questions_count
        
        # Get interview config if INTERVIEW session
        if session["session_type"] == "INTERVIEW":
            config_response = supabase.table("interviewconfig").select("*").eq("session_id", session_id).single().execute()
            if config_response.data:
                session["interview_config"] = config_response.data
        
        return jsonify(session), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get session: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>", methods=["PUT"])
@require_auth
def update_session(session_id):
    """Update session (only creator can update)."""
    data = request.get_json()
    user_id = request.user_id
    
    try:
        # Verify session exists and user is creator
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        if session["created_by"] != user_id:
            return jsonify({"error": "Only session creator can update"}), 403
        
        # Update session
        update_data = {}
        allowed_fields = ["session_name", "course_name", "difficulty_level", "password", "start_time", "end_time"]
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if update_data:
            supabase.table("session").update(update_data).eq("session_id", session_id).execute()
        
        return jsonify({"message": "Session updated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update session: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>", methods=["DELETE"])
@require_auth
def delete_session(session_id):
    """Delete session (only creator can delete, and only if no students have participated)."""
    user_id = request.user_id
    
    try:
        # Verify session exists and user is creator
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        if session["created_by"] != user_id:
            return jsonify({"error": "Only session creator can delete"}), 403
        
        # Check if any students have participated
        student_sessions_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session_id).limit(1).execute()
        
        if student_sessions_response.data:
            return jsonify({"error": "Cannot delete session with student participation"}), 400
        
        # Delete session (cascade will handle related records)
        supabase.table("session").delete().eq("session_id", session_id).execute()
        
        return jsonify({"message": "Session deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete session: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>/generate-script", methods=["POST"])
@require_lecturer
def generate_script(session_id):
    """Generate opening and closing script for session."""
    try:
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Verify user is creator
        if session["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can generate script"}), 403
        
        # Generate script using AI
        from extensions.llm import prompt_generate_script, call_llm_json
        
        prompt = prompt_generate_script(
            session_name=session["session_name"],
            course_name=session.get("course_name"),
            difficulty_level=session.get("difficulty_level"),
            session_type=session["session_type"]
        )
        
        response = call_llm_json(prompt)
        
        opening_script = response.get("opening_script", "")
        closing_script = response.get("closing_script", "")
        
        # Update session with scripts
        supabase.table("session").update({
            "opening_script": opening_script,
            "closing_script": closing_script,
            "status": "reviewing_script"
        }).eq("session_id", session_id).execute()
        
        return jsonify({
            "session_id": session_id,
            "opening_script": opening_script,
            "closing_script": closing_script,
            "status": "script_generated",
            "next_step": "review_script"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate script: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>/script", methods=["GET"])
@require_lecturer
def get_script(session_id):
    """Get opening and closing script for session."""
    try:
        session_response = supabase.table("session").select("opening_script, closing_script").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify(session_response.data), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get script: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>/script", methods=["PUT"])
@require_lecturer
def update_script(session_id):
    """Update opening and closing script for session."""
    data = request.get_json()
    opening_script = data.get("opening_script")
    closing_script = data.get("closing_script")
    
    try:
        # Verify session and user is creator
        session_response = supabase.table("session").select("created_by").eq("session_id", session_id).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can edit script"}), 403
        
        # Update script
        update_data = {}
        if opening_script:
            update_data["opening_script"] = opening_script
        if closing_script:
            update_data["closing_script"] = closing_script
        
        if update_data:
            supabase.table("session").update(update_data).eq("session_id", session_id).execute()
        
        return jsonify({"message": "Script updated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update script: {str(e)}"}), 500


@sessions_bp.route("/<int:session_id>/finalize", methods=["POST"])
@require_lecturer
def finalize_session(session_id):
    """Finalize session after all reviews are complete."""
    try:
        # Verify session and user is creator
        session_response = supabase.table("session").select("created_by").eq("session_id", session_id).single().execute()
        
        if session_response.data["created_by"] != request.user_id:
            return jsonify({"error": "Only session creator can finalize session"}), 403
        
        # Verify all requirements are met
        # Check if all questions have reference answers
        questions_response = supabase.table("question").select("question_id, reference_answer, status").eq("session_id", session_id).execute()
        
        if not questions_response.data:
            return jsonify({"error": "No questions found. Cannot finalize session without questions."}), 400
        
        questions = questions_response.data
        for q in questions:
            if not q.get("reference_answer") or q.get("status") != "answers_approved":
                return jsonify({"error": "All questions must have approved reference answers"}), 400
        
        # Check if scripts are present
        session_full = supabase.table("session").select("opening_script, closing_script").eq("session_id", session_id).single().execute()
        
        if not session_full.data.get("opening_script") or not session_full.data.get("closing_script"):
            return jsonify({"error": "Opening and closing scripts are required"}), 400
        
        # Update session status to ready
        supabase.table("session").update({
            "status": "ready"
        }).eq("session_id", session_id).execute()
        
        return jsonify({
            "session_id": session_id,
            "status": "ready",
            "questions_count": len(questions),
            "message": "Session finalized successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to finalize session: {str(e)}"}), 500

