#Định nghĩa và tải các biến môi trường quan trọng như chuỗi kết nối database (DATABASE_URL), API key..

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/map_route_dtb")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "d4b84d495c4303582c5835a354d9b3c9")
LATITUDE = float(os.getenv("LATITUDE", "21.0245"))
LONGITUDE = float(os.getenv("LONGITUDE", "105.8412"))
MODEL_PATH = os.getenv("MODEL_PATH", "src/app/models/flood_model.joblib")