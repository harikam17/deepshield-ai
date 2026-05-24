import os
import numpy as np

_tf = None
_keras = None

def _get_tf():
    global _tf, _keras
    if _tf is None:
        import tensorflow as tf
        _tf = tf
        _keras = tf.keras
    return _tf, _keras

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "model.h5")

class DeepfakeDetector:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._load_or_build_model()

    def _load_or_build_model(self):
        try:
            tf, keras = _get_tf()
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            if os.path.exists(MODEL_PATH):
                print("[DeepShield] Loading existing model...")
                self.model = keras.models.load_model(MODEL_PATH)
                self.model_loaded = True
                print("[DeepShield] Model loaded successfully.")
            else:
                print("[DeepShield] Building new EfficientNetB0 model...")
                self.model = self._build_model(keras)
                self.model.save(MODEL_PATH)
                self.model_loaded = True
                print("[DeepShield] Model built and saved.")
        except Exception as e:
            print(f"[DeepShield] WARNING: TensorFlow not available: {e}")
            print("[DeepShield] Using analytical inference mode.")
            self.model = None
            self.model_loaded = False

    def _build_model(self, keras):
        from tensorflow.keras.applications import EfficientNetB0
        from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout, BatchNormalization
        from tensorflow.keras import Model, Input
        inputs = Input(shape=(224, 224, 3))
        base = EfficientNetB0(include_top=False, weights="imagenet", input_tensor=inputs)
        for layer in base.layers[:-20]:
            layer.trainable = False
        x = base.output
        x = GlobalAveragePooling2D()(x)
        x = BatchNormalization()(x)
        x = Dense(256, activation="relu")(x)
        x = Dropout(0.4)(x)
        x = Dense(64, activation="relu")(x)
        x = Dropout(0.2)(x)
        output = Dense(1, activation="sigmoid")(x)
        model = Model(inputs=inputs, outputs=output)
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return model

    def predict(self, img_array: np.ndarray) -> dict:
        if self.model is not None:
            return self._cnn_predict(img_array)
        return self._analytical_predict(img_array)

    def _cnn_predict(self, img_array: np.ndarray) -> dict:
        batch = np.expand_dims(img_array, axis=0)
        raw_prob = float(self.model.predict(batch, verbose=0)[0][0])
        fake_prob = raw_prob
        confidence = abs(fake_prob - 0.5) * 2 * 100
        confidence = self._calibrate(confidence)
        explanation = self._explain(img_array, fake_prob)
        return self._build(confidence, fake_prob, explanation)

    def _analytical_predict(self, img_array: np.ndarray) -> dict:
        # --- feature 1: high-frequency noise (GAN artifacts) ---
        dx = np.diff(img_array.astype(np.float32), axis=1)
        dy = np.diff(img_array.astype(np.float32), axis=0)
        hf = float(np.mean(np.abs(dx)) + np.mean(np.abs(dy))) / 2.0
        hf_score = min(hf / 0.15, 1.0)  # normalised

        # --- feature 2: colour channel imbalance ---
        r = float(np.mean(img_array[:, :, 0]))
        g = float(np.mean(img_array[:, :, 1]))
        b = float(np.mean(img_array[:, :, 2]))
        color_var = float(np.std([r, g, b])) / 128.0

        # --- feature 3: local variance (smooth = suspicious) ---
        local_var = float(np.var(img_array)) / (128.0 ** 2)
        smoothness = max(0.0, 1.0 - local_var)

        # --- feature 4: block artifact (compression) ---
        h, w = img_array.shape[:2]
        block_means = []
        for i in range(0, h - 8, 8):
            for j in range(0, w - 8, 8):
                block_means.append(float(np.mean(img_array[i:i+8, j:j+8])))
        block_score = min(float(np.std(block_means)) / 30.0, 1.0)

        # --- combine: weighted fake score ---
        fake_score = (
            hf_score    * 0.35 +
            color_var   * 0.25 +
            smoothness  * 0.25 +
            block_score * 0.15
        )
        # Push toward fake end — default assumption is suspicious
        fake_prob = min(max(fake_score + 0.08, 0.05), 0.97)

        confidence = abs(fake_prob - 0.5) * 2 * 100
        confidence = self._calibrate(confidence)

        explanation = self._explain(img_array, fake_prob)
        return self._build(confidence, fake_prob, explanation)

    def _calibrate(self, raw: float) -> float:
        c = (raw / 100.0) ** 0.82
        return round(c * 100.0, 1)

    def _explain(self, img_array: np.ndarray, fake_prob: float) -> dict:
        edges = np.abs(np.diff(img_array.astype(np.float32), axis=0))
        face_score = max(0.0, 1.0 - float(np.std(edges)) / 128.0 * 2)

        dx = np.diff(img_array.astype(np.float32), axis=1)
        texture_score = min(float(np.mean(np.abs(dx))) / 128.0 * 3.0, 1.0)

        h, w = img_array.shape[:2]
        bm = []
        for i in range(0, h - 8, 8):
            for j in range(0, w - 8, 8):
                bm.append(float(np.mean(img_array[i:i+8, j:j+8])))
        comp_score = min(float(np.std(bm)) / 128.0 * 2.0, 1.0)

        def lvl(s):
            if s < 0.35: return "LOW"
            if s < 0.65: return "MEDIUM"
            return "HIGH"

        return {
            "face_consistency":        lvl(face_score),
            "texture_artifacts":       lvl(texture_score),
            "compression_anomalies":   lvl(comp_score),
            "face_consistency_score":  round(face_score  * 100, 1),
            "texture_artifact_score":  round(texture_score * 100, 1),
            "compression_score":       round(comp_score   * 100, 1),
        }

    def _build(self, confidence: float, fake_prob: float, explanation: dict) -> dict:
        # Simple binary — no UNCERTAIN
        result_label = "FAKE" if fake_prob >= 0.45 else "REAL"

        authenticity = round(max(0, min(100, (1.0 - fake_prob) * 100)), 1)
        risk_score   = round(max(0, min(100, fake_prob * 100 * (confidence / 100))))

        risk_level = "LOW" if risk_score < 30 else "MEDIUM" if risk_score < 60 else "HIGH"
        conf_tier  = "HIGH" if confidence >= 85 else "MODERATE" if confidence >= 70 else "LOW"

        return {
            "result":            result_label,
            "confidence":        confidence,
            "confidence_tier":   conf_tier,
            "authenticity_score": authenticity,
            "risk_score":        risk_score,
            "risk_level":        risk_level,
            "fake_probability":  round(fake_prob * 100, 1),
            "explanation":       explanation,
        }
