"""
Authentication middleware and decorators for JWT token verification.
"""
from functools import wraps
from flask import request, jsonify
from extensions.supabase_client import supabase
from config import SUPABASE_ANON_KEY


def get_user_from_token(token: str):
    """
    Get user information from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (auth_user, pg_user_data) if valid, (None, None) otherwise
    """
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Verify token with Supabase Auth
        auth_user = supabase.auth.get_user(token)
        
        if not auth_user or not auth_user.user:
            return None, None
        
        # Get user from PostgreSQL using email
        email = auth_user.user.email
        user_response = supabase.table("User").select("*").eq("email", email).single().execute()
        
        if not user_response.data:
            return None, None
        
        return auth_user, user_response.data
        
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None, None


def require_auth(f):
    """
    Decorator to require authentication for an endpoint.
    
    Usage:
        @require_auth
        def my_endpoint():
            user_id = request.user_id
            user_email = request.user_email
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return jsonify({"error": "No authorization token provided"}), 401
        
        # Verify token and get user data
        auth_user, pg_user = get_user_from_token(auth_header)
        
        if not auth_user or not pg_user:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Attach user data to request object
        request.current_user = auth_user
        request.pg_user = pg_user
        request.user_id = pg_user.get("user_id")
        request.user_email = pg_user.get("email")
        request.user_role = pg_user.get("role")
        
        return f(*args, **kwargs)
    
    return decorated


def require_role(role: str):
    """
    Decorator to require specific role for an endpoint.
    
    Args:
        role: Required role ('LECTURER' or 'STUDENT')
        
    Usage:
        @require_role('LECTURER')
        def lecturer_only_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            # User role is already attached by require_auth
            user_role = request.user_role
            
            if not user_role:
                return jsonify({"error": "User role not found"}), 404
            
            if user_role != role:
                return jsonify({"error": f"Access denied. Required role: {role}"}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def require_lecturer(f):
    """Convenience decorator for lecturer-only endpoints."""
    return require_role('LECTURER')(f)


def require_student(f):
    """Convenience decorator for student-only endpoints."""
    return require_role('STUDENT')(f)

