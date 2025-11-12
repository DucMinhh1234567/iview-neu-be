"""
Authentication blueprint with Supabase Auth.
Handles user registration, login, logout, and user info.
"""
from flask import Blueprint, request, jsonify
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()
    
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")
    role = data.get("role", "STUDENT")  # Default to STUDENT
    username = data.get("username")
    
    # Additional fields based on role
    lecturer_code = data.get("lecturer_code")
    department = data.get("department")
    student_code = data.get("student_code")
    class_name = data.get("class_name")
    course_year = data.get("course_year")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    if not full_name:
        return jsonify({"error": "Full name is required"}), 400
    
    # Validate role-specific fields
    if role == "LECTURER":
        if not lecturer_code:
            return jsonify({"error": "Lecturer code is required for lecturers"}), 400
    elif role == "STUDENT":
        if not student_code:
            return jsonify({"error": "Student code is required for students"}), 400
    else:
        return jsonify({"error": "Invalid role. Must be LECTURER or STUDENT"}), 400
    
    try:
        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "role": role
                }
            }
        })
        
        if not auth_response.user:
            return jsonify({"error": "Failed to create user"}), 500
        
        user_id = auth_response.user.id
        
        # Create user record in PostgreSQL
        # Link via email (Supabase Auth UUID stored separately if needed)
        user_data = {
            "username": username or email.split("@")[0],
            "email": email,
            "full_name": full_name,
            "role": role,
            "password_hash": ""  # Password is handled by Supabase Auth
        }
        
        # Insert into User table
        user_response = supabase.table("User").insert(user_data).execute()
        
        if not user_response.data:
            # If user creation fails, try to delete auth user
            # Note: Admin delete requires service role key
            try:
                # We can't easily delete without admin access, so just return error
                pass
            except:
                pass
            return jsonify({"error": "Failed to create user record"}), 500
        
        pg_user_id = user_response.data[0]["user_id"]
        
        # Create role-specific record
        if role == "LECTURER":
            lecturer_data = {
                "lecturer_id": pg_user_id,
                "lecturer_code": lecturer_code,
                "department": department
            }
            supabase.table("lecturer").insert(lecturer_data).execute()
        elif role == "STUDENT":
            student_data = {
                "student_id": pg_user_id,
                "student_code": student_code,
                "class_name": class_name,
                "course_year": course_year
            }
            supabase.table("student").insert(student_data).execute()
        
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "user_id": pg_user_id,
                "email": email,
                "full_name": full_name,
                "role": role
            }
        }), 201
        
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            return jsonify({"error": "Email already registered"}), 409
        return jsonify({"error": f"Registration failed: {error_msg}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Sign in user and return JWT token."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user or not auth_response.session:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Get user info from PostgreSQL
        user_response = supabase.table("User").select("*").eq("email", email).single().execute()
        
        if not user_response.data:
            return jsonify({"error": "User not found in database"}), 404
        
        user_data = user_response.data
        
        # Get role-specific info
        role_info = {}
        if user_data["role"] == "LECTURER":
            lecturer_response = supabase.table("lecturer").select("*").eq("lecturer_id", user_data["user_id"]).single().execute()
            if lecturer_response.data:
                role_info = lecturer_response.data
        elif user_data["role"] == "STUDENT":
            student_response = supabase.table("student").select("*").eq("student_id", user_data["user_id"]).single().execute()
            if student_response.data:
                role_info = student_response.data
        
        return jsonify({
            "message": "Signed in successfully",
            "token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "user": {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "role": user_data["role"],
                **role_info
            }
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "wrong" in error_msg.lower():
            return jsonify({"error": "Invalid email or password"}), 401
        return jsonify({"error": f"Login failed: {error_msg}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Sign out user."""
    # With Supabase Auth, we typically sign out on the client side
    # But we can also invalidate the session on the server
    try:
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Sign out with Supabase Auth
            supabase.auth.sign_out()
        
        return jsonify({"message": "Signed out successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500


@auth_bp.route("/user", methods=["GET"])
@require_auth
def get_current_user():
    """Get current user information."""
    try:
        user_id = request.user_id
        email = request.user_email
        
        if not user_id or not email:
            return jsonify({"error": "User information not found"}), 404
        
        # Get user from database
        user_response = supabase.table("User").select("*").eq("email", email).single().execute()
        
        if not user_response.data:
            return jsonify({"error": "User not found"}), 404
        
        user_data = user_response.data
        
        # Get role-specific info
        role_info = {}
        if user_data["role"] == "LECTURER":
            lecturer_response = supabase.table("lecturer").select("*").eq("lecturer_id", user_data["user_id"]).single().execute()
            if lecturer_response.data:
                role_info = lecturer_response.data
        elif user_data["role"] == "STUDENT":
            student_response = supabase.table("student").select("*").eq("student_id", user_data["user_id"]).single().execute()
            if student_response.data:
                role_info = student_response.data
        
        return jsonify({
            "user": {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "role": user_data["role"],
                **role_info
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get user: {str(e)}"}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh JWT token."""
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400
    
    try:
        # Refresh session with Supabase Auth
        auth_response = supabase.auth.refresh_session(refresh_token)
        
        if not auth_response.session:
            return jsonify({"error": "Invalid refresh token"}), 401
        
        return jsonify({
            "token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Token refresh failed: {str(e)}"}), 401

