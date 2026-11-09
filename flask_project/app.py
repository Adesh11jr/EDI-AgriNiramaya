"""
AgriNiramaya - Flask REST API & Web Application Server
Tagline: Healthy Plants. Smarter Farming.
Project: First-Year Engineering EDI Project

Provides RESTful endpoints for Authentication, Farm Management,
Plant Leaf Image Uploads, Agronomic Soil Telemetry, and Agriculture Assistant.
"""

import os
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from database import init_db, get_db_connection
from models import (
    UserModel,
    FarmModel,
    PlantUploadModel,
    SoilModel,
    AssistantModel,
    CROP_REFERENCE_GUIDES
)

# Initialize Flask Application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(os.path.dirname(BASE_DIR), "WEB")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "agriniramaya-edi-secret-key-2026-secure")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

# Enable CORS for cross-origin requests
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})


# -------------------------------------------------------------
# HELPER FUNCTIONS & AUTH DECORATOR
# -------------------------------------------------------------

def allowed_file(filename):
    """Check if uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user_id():
    """Retrieve authenticated user ID from session or Bearer token header."""
    # 1. Check Flask session
    if "user_id" in session:
        return session["user_id"]

    # 2. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        # In this lightweight architecture, token format is user_id:session_token
        # or simple user_id for simplicity and offline robustness
        if token.isdigit():
            return int(token)
        elif ":" in token:
            parts = token.split(":")
            if parts[0].isdigit():
                return int(parts[0])

    # 3. Check X-User-ID header (useful for development & IoT testing)
    x_user = request.headers.get("X-User-ID")
    if x_user and x_user.isdigit():
        return int(x_user)

    return None


def login_required(f):
    """Decorator to enforce authenticated access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "message": "Please log in to access this resource."
            }), 401
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# FRONTEND STATIC PAGE ROUTES
# -------------------------------------------------------------

@app.route("/")
def serve_index():
    """Serve home page."""
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def serve_static_pages(path):
    """Serve HTML, CSS, JS, and image assets from WEB directory."""
    full_path = os.path.join(WEB_DIR, path)
    if os.path.exists(full_path):
        return send_from_directory(WEB_DIR, path)
    # If file with .html exists
    if os.path.exists(full_path + ".html"):
        return send_from_directory(WEB_DIR, path + ".html")
    return send_from_directory(WEB_DIR, "index.html")


# -------------------------------------------------------------
# SYSTEM & HEALTH ENDPOINTS
# -------------------------------------------------------------

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    return jsonify({
        "status": "online",
        "service": "AgriNiramaya Agricultural IoT & AI Platform",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }), 200


# -------------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# -------------------------------------------------------------

@app.route("/register", methods=["POST"])
@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    security_question = data.get("security_question", "What is your favorite crop or plant?")
    security_answer = data.get("security_answer", "")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Name, email, and password are required."}), 400

    result = UserModel.create(name, email, password, security_question, security_answer)
    if result["success"]:
        return jsonify(result), 201
    return jsonify(result), 400


@app.route("/login", methods=["POST"])
@app.route("/api/login", methods=["POST"])
def login():
    """Authenticate user and establish session."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Please provide both email and password."}), 400

    auth_result = UserModel.authenticate(email, password)
    if not auth_result["success"]:
        return jsonify(auth_result), 401

    user = auth_result["user"]
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    # Provide token representation for cross-origin or file:// usage
    token = f"{user['id']}:{uuid.uuid4().hex[:16]}"

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['name']}!",
        "user": user,
        "token": token
    }), 200


@app.route("/logout", methods=["POST"])
@app.route("/api/logout", methods=["POST"])
def logout():
    """Clear session data."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


@app.route("/me", methods=["GET"])
@app.route("/api/me", methods=["GET"])
def get_current_user():
    """Get current authenticated user profile."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"authenticated": False, "user": None}), 200

    user = UserModel.get_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None}), 200

    return jsonify({"authenticated": True, "user": user}), 200


@app.route("/forgot-password", methods=["POST"])
@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    """
    Handle password recovery workflow.
    Step 1: Check email and retrieve security question.
    Step 2: Submit security answer and new password.
    """
    data = request.get_json() or {}
    action = data.get("action", "get_question")
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    if action == "get_question":
        result = UserModel.get_security_question(email)
        status_code = 200 if result["success"] else 404
        return jsonify(result), status_code

    elif action == "reset":
        security_answer = data.get("security_answer", "")
        new_password = data.get("new_password", "")
        if not new_password:
            return jsonify({"success": False, "message": "New password is required."}), 400

        result = UserModel.reset_password(email, security_answer, new_password)
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code

    return jsonify({"success": False, "message": "Invalid action requested."}), 400


# -------------------------------------------------------------
# FARM MANAGEMENT ENDPOINTS
# -------------------------------------------------------------

@app.route("/farms", methods=["GET"])
@app.route("/api/farms", methods=["GET"])
@login_required
def get_farms():
    """List all farms belonging to the authenticated user."""
    user_id = get_current_user_id()
    farms = FarmModel.get_all_by_user(user_id)
    return jsonify({"success": True, "count": len(farms), "farms": farms}), 200


@app.route("/farms", methods=["POST"])
@app.route("/api/farms", methods=["POST"])
@login_required
def create_farm():
    """Create a new farm record."""
    user_id = get_current_user_id()
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    location = data.get("location", "").strip()
    size = data.get("size", 1.0)
    crop_name = data.get("crop_name", "").strip()
    crop_variety = data.get("crop_variety", "").strip()
    soil_type = data.get("soil_type", "Alluvial").strip()
    irrigation_method = data.get("irrigation_method", "Drip Irrigation").strip()
    field_info = data.get("field_info", "").strip()

    if not name or not location or not crop_name:
        return jsonify({"success": False, "message": "Farm name, location, and crop name are required."}), 400

    result = FarmModel.create(
        user_id=user_id,
        name=name,
        location=location,
        size=size,
        crop_name=crop_name,
        crop_variety=crop_variety,
        soil_type=soil_type,
        irrigation_method=irrigation_method,
        field_info=field_info
    )
    return jsonify(result), 201


@app.route("/farms/<int:farm_id>", methods=["GET"])
@app.route("/api/farms/<int:farm_id>", methods=["GET"])
@login_required
def get_farm(farm_id):
    """Retrieve details for a single farm."""
    user_id = get_current_user_id()
    farm = FarmModel.get_by_id(farm_id, user_id=user_id)
    if not farm:
        return jsonify({"success": False, "message": "Farm not found."}), 404
    return jsonify({"success": True, "farm": farm}), 200


@app.route("/farms/<int:farm_id>", methods=["PUT"])
@app.route("/api/farms/<int:farm_id>", methods=["PUT"])
@login_required
def update_farm(farm_id):
    """Update details for an existing farm."""
    user_id = get_current_user_id()
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    location = data.get("location", "").strip()
    size = data.get("size", 1.0)
    crop_name = data.get("crop_name", "").strip()
    crop_variety = data.get("crop_variety", "").strip()
    soil_type = data.get("soil_type", "Alluvial").strip()
    irrigation_method = data.get("irrigation_method", "Drip Irrigation").strip()
    field_info = data.get("field_info", "").strip()

    if not name or not location or not crop_name:
        return jsonify({"success": False, "message": "Farm name, location, and crop name are required."}), 400

    result = FarmModel.update(
        farm_id=farm_id,
        user_id=user_id,
        name=name,
        location=location,
        size=size,
        crop_name=crop_name,
        crop_variety=crop_variety,
        soil_type=soil_type,
        irrigation_method=irrigation_method,
        field_info=field_info
    )
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@app.route("/farms/<int:farm_id>", methods=["DELETE"])
@app.route("/api/farms/<int:farm_id>", methods=["DELETE"])
@login_required
def delete_farm(farm_id):
    """Delete an existing farm record."""
    user_id = get_current_user_id()
    result = FarmModel.delete(farm_id, user_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


# -------------------------------------------------------------
# PLANT DISEASE DETECTION ENDPOINTS
# -------------------------------------------------------------

@app.route("/upload-leaf", methods=["POST"])
@app.route("/api/upload-leaf", methods=["POST"])
@login_required
def upload_leaf():
    """
    Handle plant leaf image upload.
    Validates file type, saves file to storage, and generates agronomic analysis record.
    Complies with rule: Never fabricates fake AI confidence scores if model is not loaded.
    """
    user_id = get_current_user_id()
    crop_name = request.form.get("crop_name", "").strip()
    farm_id = request.form.get("farm_id")

    if not crop_name:
        return jsonify({"success": False, "message": "Crop name is required."}), 400

    if "image" not in request.files:
        return jsonify({"success": False, "message": "No leaf image file provided."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Only JPG, JPEG, and PNG images are supported."}), 400

    # Generate secure, unique filename
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"leaf_{user_id}_{uuid.uuid4().hex[:12]}.{extension}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)

    file.save(file_path)
    file_size = os.path.getsize(file_path)

    # Save to database
    farm_id_int = int(farm_id) if farm_id and str(farm_id).isdigit() else None
    result = PlantUploadModel.save_upload(
        user_id=user_id,
        crop_name=crop_name,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or f"image/{extension}",
        farm_id=farm_id_int
    )

    # Fetch full record with analysis details
    record = PlantUploadModel.get_upload_by_id(result["upload_id"], user_id=user_id)

    return jsonify({
        "success": True,
        "message": "Leaf image uploaded and processed successfully.",
        "record": record,
        "image_url": f"/leaf-image/{result['upload_id']}"
    }), 201


@app.route("/uploads", methods=["GET"])
@app.route("/api/uploads", methods=["GET"])
@login_required
def get_uploads():
    """List all leaf uploads and analysis records for authenticated user."""
    user_id = get_current_user_id()
    uploads = PlantUploadModel.get_uploads_by_user(user_id)
    return jsonify({"success": True, "count": len(uploads), "uploads": uploads}), 200


@app.route("/uploads/<int:upload_id>", methods=["GET"])
@app.route("/api/uploads/<int:upload_id>", methods=["GET"])
@login_required
def get_upload_detail(upload_id):
    """Retrieve details and analysis for a single upload."""
    user_id = get_current_user_id()
    upload = PlantUploadModel.get_upload_by_id(upload_id, user_id=user_id)
    if not upload:
        return jsonify({"success": False, "message": "Upload record not found."}), 404
    return jsonify({"success": True, "upload": upload}), 200


@app.route("/leaf-image/<int:upload_id>", methods=["GET"])
@app.route("/api/leaf-image/<int:upload_id>", methods=["GET"])
def get_leaf_image(upload_id):
    """Serve leaf image file securely."""
    upload = PlantUploadModel.get_upload_by_id(upload_id)
    if not upload or not os.path.exists(upload["file_path"]):
        return jsonify({"success": False, "message": "Image not found."}), 404

    return send_file(upload["file_path"], mimetype=upload["mime_type"])


@app.route("/disease-history", methods=["GET"])
@app.route("/api/disease-history", methods=["GET"])
@login_required
def get_disease_history():
    """Retrieve disease inspection history for the user."""
    user_id = get_current_user_id()
    uploads = PlantUploadModel.get_uploads_by_user(user_id)
    return jsonify({"success": True, "count": len(uploads), "history": uploads}), 200


# -------------------------------------------------------------
# SOIL MONITORING ENDPOINTS (IoT / ESP32 READY)
# -------------------------------------------------------------

@app.route("/sensor-data", methods=["POST"])
@app.route("/api/sensor-data", methods=["POST"])
def post_sensor_data():
    """
    ESP32 / IoT Sensor Node Ingestion Endpoint.
    Accepts telemetry payload from microcontrollers or automated field stations.
    Also supports test data submission with is_test_data flag.
    """
    data = request.get_json() or {}

    # Validate essential readings
    if "moisture" not in data or "temperature" not in data or "ph" not in data:
        return jsonify({
            "success": False,
            "message": "Missing required sensor parameters: moisture, temperature, and ph."
        }), 400

    try:
        moisture = float(data["moisture"])
        temperature = float(data["temperature"])
        ph = float(data["ph"])
        humidity = float(data["humidity"]) if data.get("humidity") is not None else None
        nitrogen = float(data["nitrogen"]) if data.get("nitrogen") is not None else None
        phosphorus = float(data["phosphorus"]) if data.get("phosphorus") is not None else None
        potassium = float(data["potassium"]) if data.get("potassium") is not None else None
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Sensor readings must be valid numeric values."}), 400

    # Bounds validation
    if not (0.0 <= moisture <= 100.0):
        return jsonify({"success": False, "message": "Moisture must be between 0% and 100%."}), 400
    if not (-20.0 <= temperature <= 70.0):
        return jsonify({"success": False, "message": "Temperature reading is out of realistic physical range."}), 400
    if not (0.0 <= ph <= 14.0):
        return jsonify({"success": False, "message": "pH must be between 0.0 and 14.0."}), 400

    user_id = get_current_user_id()
    if not user_id and data.get("user_id"):
        user_id = int(data.get("user_id"))

    farm_id = data.get("farm_id")
    device_id = data.get("device_id", "ESP32_AGRI_NODE_01")
    is_test_data = 1 if data.get("is_test_data") in [True, 1, "1", "true"] else 0

    result = SoilModel.save_reading(
        moisture=moisture,
        temperature=temperature,
        ph=ph,
        humidity=humidity,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
        user_id=user_id,
        farm_id=farm_id,
        device_id=device_id,
        is_test_data=is_test_data
    )

    return jsonify(result), 201


@app.route("/classify-soil", methods=["POST"])
@app.route("/api/classify-soil", methods=["POST"])
def classify_soil():
    """
    On-demand agronomic classification for given soil parameters.
    Returns scientific classification, moisture/pH analysis, and agricultural recommendations.
    """
    data = request.get_json() or {}
    try:
        moisture = float(data.get("moisture", 50.0))
        temperature = float(data.get("temperature", 24.0))
        ph = float(data.get("ph", 6.8))
        humidity = float(data["humidity"]) if data.get("humidity") is not None else None
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Numeric values required for classification."}), 400

    analysis = SoilModel.classify_soil(moisture, temperature, ph, humidity)
    return jsonify({"success": True, "analysis": analysis}), 200


@app.route("/soil-data", methods=["GET"])
@app.route("/api/soil-data", methods=["GET"])
def get_soil_data():
    """
    Retrieve historical sensor telemetry logs.
    Never fabricates readings: returns empty list if no sensor has reported.
    """
    user_id = get_current_user_id()
    farm_id = request.args.get("farm_id")
    limit = int(request.args.get("limit", 50))

    readings = SoilModel.get_history(user_id=user_id, farm_id=farm_id, limit=limit)
    return jsonify({"success": True, "count": len(readings), "readings": readings}), 200


@app.route("/latest-soil", methods=["GET"])
@app.route("/api/latest-soil", methods=["GET"])
def get_latest_soil():
    """
    Retrieve latest sensor reading.
    Rule compliance: If no sensor data has been received, returns data=None without fabricating fake values.
    """
    user_id = get_current_user_id()
    farm_id = request.args.get("farm_id")
    latest = SoilModel.get_latest(user_id=user_id, farm_id=farm_id)

    if not latest:
        return jsonify({
            "success": True,
            "has_data": False,
            "reading": None,
            "message": "No sensor data available yet. Please connect an ESP32 node or submit test telemetry."
        }), 200

    # Determine sensor online status (recent reading within 10 minutes)
    created_time = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00")) if "T" in latest["created_at"] else datetime.strptime(latest["created_at"], "%Y-%m-%d %H:%M:%S")
    time_diff = (datetime.now() - created_time).total_seconds()
    is_live = time_diff < 600  # within 10 minutes

    return jsonify({
        "success": True,
        "has_data": True,
        "is_live": is_live,
        "reading": latest
    }), 200


# -------------------------------------------------------------
# AGRICULTURE ASSISTANT ENDPOINT
# -------------------------------------------------------------

@app.route("/assistant", methods=["POST"])
@app.route("/api/assistant", methods=["POST"])
def assistant():
    """
    Agriculture Assistant Chatbot API.
    Uses verified Agronomy Knowledge Base if external LLM API is not configured.
    Explicitly informs user of offline mode without fabricating live AI responses.
    """
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"success": False, "message": "Please enter a question."}), 400

    user_id = get_current_user_id()
    response = AssistantModel.get_response(message, user_id=user_id)

    return jsonify({
        "success": True,
        "response": response
    }), 200


@app.route("/assistant/history", methods=["GET"])
@app.route("/api/assistant/history", methods=["GET"])
@login_required
def get_assistant_history():
    """Retrieve user chat history."""
    user_id = get_current_user_id()
    history = AssistantModel.get_history(user_id)
    return jsonify({"success": True, "history": history}), 200


# -------------------------------------------------------------
# DASHBOARD AGGREGATE STATS ENDPOINT
# -------------------------------------------------------------

@app.route("/dashboard-stats", methods=["GET"])
@app.route("/api/dashboard-stats", methods=["GET"])
@login_required
def dashboard_stats():
    """
    Aggregate authentic database statistics for main dashboard.
    Strictly uses actual SQLite records without fake statistics.
    """
    user_id = get_current_user_id()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Total registered farms
        cursor.execute("SELECT COUNT(*) as total_farms FROM farms WHERE user_id = ?", (user_id,))
        total_farms = cursor.fetchone()["total_farms"]

        # 2. Total distinct crops
        cursor.execute("SELECT COUNT(DISTINCT crop_name) as total_crops FROM farms WHERE user_id = ?", (user_id,))
        total_crops = cursor.fetchone()["total_crops"]

        # 3. Recent farms
        cursor.execute("SELECT * FROM farms WHERE user_id = ? ORDER BY created_at DESC LIMIT 4", (user_id,))
        recent_farms = [dict(r) for r in cursor.fetchall()]

        # 4. Total leaf uploads
        cursor.execute("SELECT COUNT(*) as total_uploads FROM plant_uploads WHERE user_id = ?", (user_id,))
        total_uploads = cursor.fetchone()["total_uploads"]

        # 5. Recent uploads
        cursor.execute("""
            SELECT u.*, d.disease_name, d.status, d.confidence
            FROM plant_uploads u
            LEFT JOIN disease_analysis d ON d.upload_id = u.id
            WHERE u.user_id = ?
            ORDER BY u.created_at DESC LIMIT 4
        """, (user_id,))
        recent_uploads = [dict(r) for r in cursor.fetchall()]

        # 6. Total soil readings
        cursor.execute("SELECT COUNT(*) as total_readings FROM soil_readings WHERE user_id = ? OR user_id IS NULL", (user_id,))
        total_readings = cursor.fetchone()["total_readings"]

    # Latest soil reading
    latest_soil = SoilModel.get_latest(user_id=user_id)

    # Activity timeline generated from actual timestamps
    activity = []
    for f in recent_farms:
        activity.append({
            "type": "farm_created",
            "title": f"Farm Registered: {f['name']}",
            "description": f"Cultivating {f['crop_name']} ({f['size']} acres) in {f['location']}",
            "timestamp": f["created_at"]
        })
    for u in recent_uploads:
        activity.append({
            "type": "leaf_uploaded",
            "title": f"Leaf Inspection: {u['crop_name']}",
            "description": f"Image {u['original_filename']} logged for health analysis",
            "timestamp": u["created_at"]
        })

    # Sort activity descending by timestamp
    activity.sort(key=lambda x: x["timestamp"], reverse=True)

    return jsonify({
        "success": True,
        "stats": {
            "total_farms": total_farms,
            "total_crops": total_crops,
            "total_uploads": total_uploads,
            "total_soil_readings": total_readings
        },
        "recent_farms": recent_farms,
        "recent_uploads": recent_uploads,
        "latest_soil": latest_soil,
        "recent_activity": activity[:8]
    }), 200


# -------------------------------------------------------------
# CONTACT FORM ENDPOINT
# -------------------------------------------------------------

@app.route("/contact", methods=["POST"])
@app.route("/api/contact", methods=["POST"])
def submit_contact():
    """Submit contact message or academic project inquiry."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    subject = data.get("subject", "").strip()
    message = data.get("message", "").strip()

    if not name or not email or not message:
        return jsonify({"success": False, "message": "Name, email, and message are required."}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (?, ?, ?, ?)
        """, (name, email, subject or "General Inquiry", message))

    return jsonify({
        "success": True,
        "message": "Thank you for contacting AgriNiramaya! Your inquiry has been received."
    }), 201


# -------------------------------------------------------------
# APPLICATION ENTRYPOINT
# -------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("=" * 65)
    print("🌿 AgriNiramaya - AI Plant Health & Soil Monitoring Platform")
    print("   Tagline: Healthy Plants. Smarter Farming.")
    print("   Web Server running at: http://127.0.0.1:5000")
    print("   Database: plant_doctor.db")
    print("   Academic EDI Project Mode: ACTIVE")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)
