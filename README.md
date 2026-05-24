# 🛡 DeepShield AI — Deepfake Risk Intelligence Platform

A production-ready deepfake detection web application using EfficientNetB0 CNN with Explainable AI, analytics dashboard, and risk scoring.

---

## ✨ Features

- **Real CNN Inference** — EfficientNetB0 (transfer learning, ImageNet weights)
- **Explainable AI** — Face consistency, texture artifact, and compression anomaly scores
- **Confidence Calibration** — Never overconfident; UNCERTAIN when confidence < 70%
- **Risk Intelligence** — Authenticity score (0–100) + Risk level (LOW / MEDIUM / HIGH)
- **Analytics Dashboard** — Real-time pie, line, and bar charts via Chart.js
- **Prediction History** — Persisted in localStorage + backend JSON
- **Offline Mode** — Falls back to client-side analytical inference if backend is down
- **Camera Capture** — Use your webcam directly
- **Premium UI** — Dark glassmorphism, animated scan effects, toast notifications

---

## 🗂 Project Structure

```
deepshield/
├── backend/
│   ├── app.py          # Flask REST API
│   ├── detector.py     # EfficientNetB0 CNN detector
│   ├── preprocess.py   # Image preprocessing pipeline
│   ├── utils.py        # History & stats utilities
│   ├── requirements.txt
│   ├── history.json    # Auto-created on first run
│   └── model/
│       └── model.h5    # Auto-built on first startup
├── frontend/
│   └── index.html      # Complete self-contained frontend
├── render.yaml         # Render.com backend deployment
├── vercel.json         # Vercel frontend deployment
├── .gitignore
└── README.md
```

---

## 🚀 Local Development

### 1. Clone & navigate

```bash
git clone https://github.com/your-username/deepshield-ai.git
cd deepshield-ai
```

### 2. Set up Python backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The first run will **automatically build and save** the EfficientNetB0 model (requires internet for ImageNet weights, ~25MB download).

Backend runs at: `http://127.0.0.1:5000`

### 3. Open the frontend

Simply open `frontend/index.html` in your browser. No build step needed.

Or use a local server:
```bash
cd frontend
python -m http.server 8080
# Open http://localhost:8080
```

The frontend auto-detects `localhost` and connects to `http://127.0.0.1:5000`.

---

## 🌐 Deployment

### Backend → Render.com

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Render auto-reads `render.yaml` — no manual config needed
5. Note your Render URL: `https://deepshield-ai-backend.onrender.com`

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   ```
   DEEPSHIELD_API_URL = https://your-backend.onrender.com
   ```
5. Or edit `frontend/index.html` line ~240:
   ```js
   const API_BASE_URL = 'https://your-backend.onrender.com';
   ```

### Frontend → Netlify

1. Go to [netlify.com](https://netlify.com) → New Site
2. Drag-and-drop the `frontend/` folder
3. Done — static hosting, instant deploy

---

## 🧠 Model Architecture

```
Input (224×224×3)
      ↓
EfficientNetB0 (ImageNet weights, last 20 layers unfrozen)
      ↓
GlobalAveragePooling2D
      ↓
BatchNormalization
      ↓
Dense(256, ReLU)
      ↓
Dropout(0.4)
      ↓
Dense(64, ReLU)
      ↓
Dropout(0.2)
      ↓
Dense(1, Sigmoid)  →  [0,1] fake probability
```

### Fine-tuning on real data

```python
from tensorflow.keras.preprocessing.image import ImageDataGenerator

train_gen = ImageDataGenerator(
    rescale=1./255, rotation_range=20,
    horizontal_flip=True, zoom_range=0.2
).flow_from_directory(
    'data/train/',           # real/ and fake/ subfolders
    target_size=(224, 224),
    batch_size=32,
    class_mode='binary'
)

model.fit(train_gen, epochs=10, validation_data=val_gen)
model.save('backend/model/model.h5')
```

Recommended datasets: **FaceForensics++**, **DFDC**, **Celeb-DF**

---

## 🔌 API Reference

### `GET /health`
```json
{ "status": "ok", "model_loaded": true, "timestamp": "2024-01-01T00:00:00" }
```

### `POST /predict`
- Body: `multipart/form-data` with field `image`
- Response:
```json
{
  "result": "FAKE",
  "confidence": 87.3,
  "confidence_tier": "HIGH",
  "authenticity_score": 11,
  "risk_score": 76,
  "risk_level": "HIGH",
  "fake_probability": 88.5,
  "explanation": {
    "face_consistency": "LOW",
    "texture_artifacts": "HIGH",
    "compression_anomalies": "MEDIUM",
    "face_consistency_score": 22.1,
    "texture_artifact_score": 78.4,
    "compression_score": 54.2
  }
}
```

### `GET /history`
```json
{ "history": [ { "id": "abc123", "result": "FAKE", "confidence": 87.3, ... } ] }
```

### `GET /stats`
```json
{ "total_scans": 42, "fake_rate": 38.1, "avg_confidence": 81.2, ... }
```

### `DELETE /clear-history`
```json
{ "message": "History cleared" }
```

---

## ⚡ Performance Tips

- Use `tensorflow-lite` for 3–5× faster inference on CPU
- Enable GPU by installing `tensorflow-gpu` and CUDA
- Cache the model in memory (already done in `detector.py`)
- Use `gunicorn --workers 2` for concurrent requests on Render
- Compress images to < 2MB before upload for faster transfers

---

## 📄 License

MIT License — free to use, modify, and deploy.
