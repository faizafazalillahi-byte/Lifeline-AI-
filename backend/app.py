"""
app.py
------
LifeLine AI backend entry point.

Run with:
    python app.py

Blueprints are registered incrementally as modules are built:
  Module 1 -> auth_bp        (DONE)
  Module 3 -> user_bp        (contacts, profile, history)
  Module 5 -> emergency_bp, facility_bp
  Module 7 -> admin_bp
"""

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from routes.auth_routes import auth_bp

# NOTE: the following imports are added module by module. Each is wrapped
# in a try/except ImportError purely so app.py runs even before later
# modules exist yet (useful while following this build step by step).
# Once all modules are delivered, these will always succeed.
try:
    from routes.user_routes import user_bp
except ImportError:
    user_bp = None

try:
    from routes.emergency_routes import emergency_bp
except ImportError:
    emergency_bp = None

try:
    from routes.facility_routes import facility_bp
except ImportError:
    facility_bp = None

try:
    from routes.admin_routes import admin_bp
except ImportError:
    admin_bp = None


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Allow the static frontend (served separately, e.g. Live Server /
    # any static host) to call this API.
    CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_ORIGIN}})

    # ---- Register blueprints ----
    app.register_blueprint(auth_bp)
    if user_bp:
        app.register_blueprint(user_bp)
    if emergency_bp:
        app.register_blueprint(emergency_bp)
    if facility_bp:
        app.register_blueprint(facility_bp)
    if admin_bp:
        app.register_blueprint(admin_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"success": True, "message": "LifeLine AI backend is running"}), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5000)
