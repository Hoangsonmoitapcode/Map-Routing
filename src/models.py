import joblib
from .config import MODEL_PATH

def load_flood_model():
    """Load AI model"""
    print("Loading AI model...")
    flood_model = joblib.load(MODEL_PATH)
    print("AI model loaded.")
    return flood_model