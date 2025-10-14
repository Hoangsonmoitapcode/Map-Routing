import requests
import pandas as pd
from datetime import datetime
from src.app.core.config import WEATHER_API_KEY, LATITUDE, LONGITUDE


def predict_flood(flood_model):
    """Get weather data and predict flood"""
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    weather_data = response.json()

    current_temp = weather_data['main']['temp']
    current_humidity = weather_data['main']['humidity']
    current_wind_speed = weather_data['wind']['speed']
    now = datetime.now()
    current_month = now.month
    current_hour = now.hour
    is_rainy = 1 if current_month in [6, 7, 8] else 0

    input_df = pd.DataFrame(
        [[current_temp, current_humidity, current_wind_speed, current_month, current_hour, is_rainy]],
        columns=['temp', 'humidity', 'wind_speed', 'month', 'hour', 'is_rainy_season']
    )

    is_flooded_prediction = flood_model.predict(input_df)[0]
    return is_flooded_prediction