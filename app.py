from flask import Flask, jsonify
from flask_cors import CORS
from config import DEBUG, CORS_ORIGINS, validate_config
from extensions.supabase_client import check_supabase_health

def create_app():
    try:
        validate_config()
    except ValueError as e:
        print(f"Configuration validation failed: {e}")
    
    app = Flask(__name__)
    app.config["DEBUG"] = DEBUG
    
    # CORS configuration
    CORS(app, origins=CORS_ORIGINS, supports_credentials=True)
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.materials import materials_bp
    from blueprints.sessions import sessions_bp
    from blueprints.questions import questions_bp
    from blueprints.student_sessions import student_sessions_bp
    from blueprints.review import review_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.files import files_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(materials_bp, url_prefix="/api/materials")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(questions_bp, url_prefix="/api/questions")
    app.register_blueprint(student_sessions_bp, url_prefix="/api/student-sessions")
    app.register_blueprint(review_bp, url_prefix="/api/review")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    
    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "message": "AI Interview Backend System",
            "status": "running",
            "version": "2.0.0",
            "database": "Supabase (PostgreSQL)"
        }), 200
    
    @app.route("/health", methods=["GET"])
    def health():
        supabase_status = "connected" if check_supabase_health() else "disconnected"
        return jsonify({
            "status": "healthy" if supabase_status == "connected" else "degraded",
            "supabase": supabase_status,
            "message": "Backend is running"
        }), 200
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request"}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)

