"""
Dashboard blueprint for statistics and summaries.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth, require_student, require_lecturer

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/students/<int:student_id>", methods=["GET"])
@require_student
def get_student_dashboard(student_id):
    """Get student dashboard with statistics."""
    current_user_id = request.user_id
    
    # Verify student can only view their own dashboard
    if student_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    
    try:
        # Get user info
        user_response = supabase.table("User").select("*").eq("user_id", student_id).single().execute()
        
        if not user_response.data:
            return jsonify({"error": "User not found"}), 404
        
        user_data = user_response.data
        
        # Get student info
        student_response = supabase.table("student").select("*").eq("student_id", student_id).single().execute()
        student_data = student_response.data if student_response.data else {}
        
        # Get all student sessions
        student_sessions_response = supabase.table("studentsession").select("*").eq("student_id", student_id).execute()
        student_sessions = student_sessions_response.data or []
        
        # Get session details for each student session
        session_ids = [ss["session_id"] for ss in student_sessions]
        sessions_dict = {}
        if session_ids:
            sessions_response = supabase.table("session").select("*").in_("session_id", session_ids).execute()
            sessions_dict = {s["session_id"]: s for s in (sessions_response.data or [])}
        
        # Calculate statistics
        total_sessions = len(student_sessions)
        total_exam_sessions = 0
        total_interview_sessions = 0
        total_practice_sessions = 0
        
        for ss in student_sessions:
            session = sessions_dict.get(ss["session_id"], {})
            session_type = session.get("session_type", "")
            if session_type == "EXAM":
                total_exam_sessions += 1
            elif session_type == "INTERVIEW":
                total_interview_sessions += 1
            elif session_type == "PRACTICE":
                total_practice_sessions += 1
        
        # Calculate average score
        scores = [ss.get("score_total") for ss in student_sessions if ss.get("score_total")]
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        # Get recent sessions (last 5)
        recent_sessions = sorted(
            student_sessions,
            key=lambda x: x.get("join_time", ""),
            reverse=True
        )[:5]
        
        recent_sessions_formatted = []
        for ss in recent_sessions:
            session = sessions_dict.get(ss["session_id"], {})
            recent_sessions_formatted.append({
                "student_session_id": ss["student_session_id"],
                "session_name": session.get("session_name", ""),
                "session_type": session.get("session_type", ""),
                "score_total": ss.get("score_total"),
                "join_time": ss.get("join_time")
            })
        
        # Get sessions by day (last 7 days)
        sessions_by_day = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            sessions_by_day[date] = 0
        
        for ss in student_sessions:
            join_time = ss.get("join_time")
            if join_time:
                try:
                    if isinstance(join_time, str):
                        date = datetime.fromisoformat(join_time.replace("Z", "+00:00")).date().isoformat()
                    else:
                        date = join_time.date().isoformat()
                    if date in sessions_by_day:
                        sessions_by_day[date] += 1
                except:
                    pass
        
        return jsonify({
            "user": {
                "user_id": user_data["user_id"],
                "full_name": user_data["full_name"],
                "email": user_data["email"],
                "student_code": student_data.get("student_code", ""),
                "class_name": student_data.get("class_name", ""),
                "course_year": student_data.get("course_year")
            },
            "statistics": {
                "total_sessions": total_sessions,
                "average_score": round(average_score, 2),
                "total_exam_sessions": total_exam_sessions,
                "total_interview_sessions": total_interview_sessions,
                "total_practice_sessions": total_practice_sessions
            },
            "recent_sessions": recent_sessions_formatted,
            "sessions_by_day": sessions_by_day
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get dashboard: {str(e)}"}), 500


@dashboard_bp.route("/lecturers/<int:lecturer_id>", methods=["GET"])
@require_lecturer
def get_lecturer_dashboard(lecturer_id):
    """Get lecturer dashboard with statistics."""
    current_user_id = request.user_id
    
    # Verify lecturer can only view their own dashboard
    if lecturer_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    
    try:
        # Get user info
        user_response = supabase.table("User").select("*").eq("user_id", lecturer_id).single().execute()
        
        if not user_response.data:
            return jsonify({"error": "User not found"}), 404
        
        user_data = user_response.data
        
        # Get lecturer info
        lecturer_response = supabase.table("lecturer").select("*").eq("lecturer_id", lecturer_id).single().execute()
        lecturer_data = lecturer_response.data if lecturer_response.data else {}
        
        # Get all sessions created by lecturer
        sessions_response = supabase.table("session").select("*").eq("created_by", lecturer_id).execute()
        sessions = sessions_response.data or []
        
        # Get all materials uploaded by lecturer
        materials_response = supabase.table("material").select("material_id").eq("uploaded_by", lecturer_id).execute()
        materials = materials_response.data or []
        
        # Calculate statistics
        total_sessions = len(sessions)
        total_materials = len(materials)
        
        # Count students who have participated
        total_students = 0
        sessions_need_review = 0
        
        for session in sessions:
            student_sessions_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session["session_id"]).execute()
            student_count = len(student_sessions_response.data or [])
            total_students += student_count
            
            # Count sessions that need review (EXAM sessions with students but not reviewed)
            if session["session_type"] == "EXAM" and student_count > 0:
                # Check if any student sessions are not reviewed
                # Get all student sessions and check which ones are not reviewed
                all_student_sessions = student_sessions_response.data or []
                unreviewed = [ss for ss in all_student_sessions if not ss.get("reviewed_by")]
                if unreviewed:
                    sessions_need_review += 1
        
        # Get recent sessions (last 5)
        recent_sessions = sorted(
            sessions,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[:5]
        
        recent_sessions_formatted = []
        for session in recent_sessions:
            # Get student count
            student_sessions_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session["session_id"]).execute()
            student_count = len(student_sessions_response.data or [])
            
            recent_sessions_formatted.append({
                "session_id": session["session_id"],
                "session_name": session.get("session_name", ""),
                "session_type": session.get("session_type", ""),
                "status": session.get("status", ""),
                "student_count": student_count,
                "created_at": session.get("created_at")
            })
        
        return jsonify({
            "user": {
                "user_id": user_data["user_id"],
                "full_name": user_data["full_name"],
                "email": user_data["email"],
                "lecturer_code": lecturer_data.get("lecturer_code", ""),
                "department": lecturer_data.get("department", "")
            },
            "statistics": {
                "total_sessions": total_sessions,
                "total_materials": total_materials,
                "total_students": total_students,
                "sessions_need_review": sessions_need_review
            },
            "recent_sessions": recent_sessions_formatted
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get dashboard: {str(e)}"}), 500

