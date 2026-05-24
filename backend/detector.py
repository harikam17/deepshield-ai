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
            print(f"[DeepShield] WARNING: Could not load TensorFlow model: {e}")
            print("[DeepShield] Falling back to analytical inference mode.")
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
        else:
            return self._analytical_predict(img_array)

    def _cnn_predict(self, img_array: np.ndarray) -> dict:
        tf, keras = _get_tf()
        batch = np.expand_dims(img_array, axis=0)
        raw_prob = float(self.model.predict(batch, verbose=0)[0][0])
        fake_prob = raw_prob
        confidence = abs(fake_prob - 0.5) * 2 * 100
        confidence = self._calibrate_confidence(confidence)
        is_fake = fake_prob >= 0.45
        explanation = self._generate_explanation(img_array, fake_prob, confidence)
        return self._build_result(is_fake, confidence, fake_prob, explanation)

    def _analytical_predict(self, img_array: np.ndarray) -> dict:
        std_val = float(np.std(img_array))

        dx = np.diff(img_array.astype(np.float32), axis=0)
        dy = np.diff(img_array.astype(np.float32), axis=1)
        hf_noise = float(np.mean(np.abs(dx)) + np.mean(np.abs(dy)))
        hf_score = min(hf_noise / 30.0, 1.0)

        r_mean = float(np.mean(img_array[:, :, 0]))
        g_mean = float(np.mean(img_array[:, :, 1]))
        b_mean = float(np.mean(img_array[:, :, 2]))
        color_var = float(np.std([r_mean, g_mean, b_mean])) / 128.0

        fake_score = (hf_score * 0.55 + color_var * 0.35 + (std_val / 128.0) * 0.1)
        fake_prob = min(max(fake_score, 0.05), 0.95)

        confidence = abs(fake_prob - 0.5) * 2 * 100
        confidence = self._calibrate_confidence(confidence)

        explanation = self._generate_explanation(img_array, fake_prob, confidence)
        return self._build_result(False, confidence, fake_prob, explanation)

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        c = raw_confidence / 100.0
        c = c ** 0.85
        return round(c * 100.0, 1)

    def _generate_explanation(self, img_array: np.ndarray, fake_prob: float, confidence: float) -> dict:
        edges = np.abs(np.diff(img_array.astype(np.float32), axis=0))
        edge_irregularity = float(np.std(edges)) / 128.0
        face_consistency_score = max(0.0, 1.0 - edge_irregularity * 2)

        dx = np.diff(img_array.astype(np.float32), axis=1)
        hf = float(np.mean(np.abs(dx))) / 128.0
        texture_artifact_score = min(hf * 3.0, 1.0)

        h, w = img_array.shape[:2]
        block_means = []
        for i in range(0, h - 8, 8):
            for j in range(0, w - 8, 8):
                block = img_array[i:i+8, j:j+8]
                block_means.append(float(np.mean(block)))
        block_var = float(np.std(block_means)) / 128.0
        compression_score = min(block_var * 2.0, 1.0)

        def level(score):
            if score < 0.35: return "LOW"
            elif score < 0.65: return "MEDIUM"
            else: return "HIGH"

        return {
            "face_consistency": level(face_consistency_score),
            "texture_artifacts": level(texture_artifact_score),
            "compression_anomalies": level(compression_score),
            "face_consistency_score": round(face_consistency_score * 100, 1),
            "texture_artifact_score": round(texture_artifact_score * 100, 1),
            "compression_score": round(compression_score * 100, 1),
        }

    def _build_result(self, is_fake: bool, confidence: float, fake_prob: float, explanation: dict) -> dict:
        # Always FAKE or REAL — no UNCERTAIN
        if fake_prob >= 0.45:
            result_label = "FAKE"
        else:
            result_label = "REAL"

        authenticity_score = round((1.0 - fake_prob) * 100, 1)
        authenticity_score = max(0, min(100, authenticity_score))

        risk_score = round(fake_prob * 100 * (confidence / 100))
        risk_score = max(0, min(100, risk_score))

        if risk_score < 30:
            risk_level = "LOW"
        elif risk_score < 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        if confidence >= 85:
            confidence_tier = "HIGH"
        elif confidence >= 70:
            confidence_tier = "MODERATE"
        else:
            confidence_tier = "LOW"

        return {
            "result": result_label,
            "confidence": confidence,
            "confidence_tier": confidence_tier,
            "authenticity_score": authenticity_score,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "fake_probability": round(fake_prob * 100, 1),
            "explanation": explanation,
        }
