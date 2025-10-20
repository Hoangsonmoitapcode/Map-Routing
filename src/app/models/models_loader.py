# src/app/core/load_model.py
import joblib
import os
from src.app.core.config import MODEL_PATH


def load_flood_model():
    """Tải model AI dự đoán ngập"""
    print("Loading AI model...")

    if not os.path.exists(MODEL_PATH):
        print(f"Model không tồn tại tại: {MODEL_PATH}")
        print("Chỉ sử dụng chế độ định tuyến tiêu chuẩn.")
        return None

    try:
        flood_model = joblib.load(MODEL_PATH)
        print("AI model loaded successfully.")
        return flood_model
    except Exception as e:
        print(f"Lỗi khi load model: {e}")
        return None
