from flask import Flask, render_template, request
from datetime import date
import requests

app = Flask(__name__)

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_info(code):
    if code == 0:
        return "☀️", "Ясно", "sun"
    if code <= 3:
        return "⛅", "Облачно", "cloud"
    if code <= 48:
        return "🌫️", "Туман", "cloud"
    if code <= 67:
        return "🌧️", "Дождь", "rain"
    if code <= 77:
        return "❄️", "Снег", "snow"
    if code <= 82:
        return "🌦️", "Ливень", "rain"
    if code <= 86:
        return "❄️", "Снегопад", "snow"
    return "⛈️", "Гроза", "storm"


@app.route("/", methods=["GET", "POST"])
def index():
    city = ""
    days = []
    now = {}
    error = ""

    if request.method == "POST":
        city = request.form["city"]

        url_city = "https://geocoding-api.open-meteo.com/v1/search"
        answer = requests.get(url_city, params={"name": city, "count": 1, "language": "ru"})
        data = answer.json()

        if "results" not in data:
            error = "Такой город не найден :("
        else:
            place = data["results"][0]
            city = place["name"]

            url_weather = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": 7,
                "timezone": "auto",
            }
            result = requests.get(url_weather, params=params).json()

            current = result["current"]
            icon, text, kind = get_info(current["weather_code"])
            now = {
                "temp": round(current["temperature_2m"]),
                "wind": round(current["wind_speed_10m"]),
                "icon": icon,
                "text": text,
                "kind": kind,
            }

            weather = result["daily"]
            for i in range(7):
                d = date.fromisoformat(weather["time"][i])
                icon, text, kind = get_info(weather["weather_code"][i])
                day = {
                    "name": "Сегодня" if i == 0 else WEEKDAYS[d.weekday()],
                    "icon": icon,
                    "max": round(weather["temperature_2m_max"][i]),
                    "min": round(weather["temperature_2m_min"][i]),
                    "rain": weather["precipitation_sum"][i],
                }
                days.append(day)

    return render_template("index.html", city=city, days=days, now=now, error=error)


app.run(debug=True)