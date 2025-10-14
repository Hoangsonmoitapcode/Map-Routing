#tải file .joblib lên và chuẩn bị sẵn sàng để các service khác sử dụng.

import joblib
from src.app.core.config import MODEL_PATH
import os

def load_flood_model():
    """Load AI model"""
    print("Loading AI model...")

    if not os.path.exists(MODEL_PATH):
        print(f"WARNING: Flood model not found at {MODEL_PATH}")
        print("Smart routing will be disabled. Only standard routing available.")
        return None  # ← Returns None instead of crashing

    try:
        flood_model = joblib.load(MODEL_PATH)
        print("AI model loaded.")
        return flood_model
    except Exception as e:
        print(f"ERROR loading flood model: {e}")
        return None  # ← Returns None on error