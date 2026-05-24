import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from detector import DeepfakeDetector
from preprocess import preprocess_image
from utils import compute_stats, save_history_entry, load_history

app = Flask(__name__)
CORS(app, origins="*")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

detector = DeepfakeDetector()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": detector.model_loaded, "timestamp": datetime.utcnow().isoformat()})


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported image format. Use PNG, JPG, JPEG, WEBP, or BMP."}), 415

    try:
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        img_array = preprocess_image(filepath)
        result = detector.predict(img_array)

        entry = {
            "id": uuid.uuid4().hex[:8],
            "result": result["result"],
            "confidence": result["confidence"],
            "risk_score": result["risk_score"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        save_history_entry(entry)

        try:
            os.remove(filepath)
        except Exception:
            pass

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/history", methods=["GET"])
def history():
    try:
        data = load_history()
        return jsonify({"history": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stats", methods=["GET"])
def stats():
    try:
        data = load_history()
        stats_data = compute_stats(data)
        return jsonify(stats_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clear-history", methods=["DELETE"])
def clear_history():
    try:
        with open("history.json", "w") as f:
            json.dump([], f)
        return jsonify({"message": "History cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
