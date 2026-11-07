from flask import Flask, render_template, request
from datetime import date, datetime
import requests

app = Flask(__name__)

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

POPULAR_CITIES = ["Алматы", "Астана", "Москва", "Санкт-Петербург", "Токио", "Лондон"]


def get_info(code):
    if code == 0:
        return "☀️", "Ясно", "sun"
    if code == 1:
        return "🌤️", "Преимущественно ясно", "sun"
    if code == 2:
        return "⛅", "Переменная облачность", "cloud"
    if code == 3:
        return "☁️", "Пасмурно", "cloud"
    if code <= 48:
        return "🌫️", "Туман", "fog"
    if code <= 57:
        return "🌦️", "Морось", "rain"
    if code <= 67:
        return "🌧️", "Дождь", "rain"
    if code <= 77:
        return "❄️", "Снег", "snow"
    if code <= 82:
        return "🌧️", "Ливень", "rain"
    if code <= 86:
        return "🌨️", "Снегопад", "snow"
    return "⛈️", "Гроза", "storm"


def get_uv_label(uv):
    if uv <= 2:
        return "Низкий"
    if uv <= 5:
        return "Средний"
    if uv <= 7:
        return "Высокий"
    if uv <= 10:
        return "Очень высокий"
    return "Экстремальный"


def get_advice(kind, temp, wind, uv):
    if kind == "storm":
        return "Ожидается гроза — лучше остаться в помещении ⚡"
    if kind == "rain":
        return "Захвати зонт или дождевик, возможны осадки ☔"
    if kind == "snow":
        return "На улице снежно и скользко — одевайся теплее 🧣"
    if temp < 0:
        return "Морозная погода! Не забудь шапку и перчатки 🧤"
    if temp < 12:
        return "Довольно прохладно — куртка или худи будут кстати 🧥"
    if temp > 28:
        return "Жаркая погода! Пей больше воды и берегись солнца 🥤"
    if wind > 30:
        return "Сильный ветер — выбирай непродуваемую одежду 💨"
    if uv >= 6:
        return "Высокий УФ-индекс — используй защиту от солнца 🕶️"
    return "Отличная погода для прогулки на свежем воздухе ✨"


@app.route("/", methods=["GET", "POST"])
def index():
    city = request.values.get("city", "").strip()
    lat = request.values.get("lat", "").strip()
    lon = request.values.get("lon", "").strip()

    country = ""
    days = []
    hourly = []
    now = {}
    error = ""

    if city or (lat and lon):
        try:
            if lat and lon and not city:
                latitude = float(lat)
                longitude = float(lon)
                geo_url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
                geo_res = requests.get(
                    geo_url,
                    params={"latitude": latitude, "longitude": longitude, "localityLanguage": "ru"},
                    timeout=5,
                ).json()
                city = geo_res.get("city") or geo_res.get("locality") or "Моё место"
                country = geo_res.get("countryName", "")
            else:
                url_city = "https://geocoding-api.open-meteo.com/v1/search"
                answer = requests.get(
                    url_city,
                    params={"name": city, "count": 1, "language": "ru"},
                    timeout=5,
                )
                data = answer.json()

                if "results" not in data:
                    error = "Такой город не найден :("
                    return render_template(
                        "index.html",
                        city=city,
                        country=country,
                        days=days,
                        hourly=hourly,
                        now=now,
                        error=error,
                        popular=POPULAR_CITIES,
                    )

                place = data["results"][0]
                city = place["name"]
                country = place.get("country", "")
                latitude = place["latitude"]
                longitude = place["longitude"]

            url_weather = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "is_day,precipitation,weather_code,surface_pressure,"
                    "wind_speed_10m,wind_gusts_10m"
                ),
                "hourly": "temperature_2m,weather_code,precipitation_probability",
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,precipitation_probability_max,"
                    "sunrise,sunset,uv_index_max"
                ),
                "forecast_days": 7,
                "timezone": "auto",
            }
            result = requests.get(url_weather, params=params, timeout=5).json()

            current = result["current"]
            daily = result["daily"]
            hourly_data = result["hourly"]

            icon, text, kind = get_info(current["weather_code"])
            temp_val = round(current["temperature_2m"])
            wind_val = round(current["wind_speed_10m"])
            uv_val = round(daily["uv_index_max"][0])

            sunrise_str = daily["sunrise"][0].split("T")[1] if "T" in daily["sunrise"][0] else daily["sunrise"][0]
            sunset_str = daily["sunset"][0].split("T")[1] if "T" in daily["sunset"][0] else daily["sunset"][0]

            now = {
                "temp": temp_val,
                "feels_like": round(current["apparent_temperature"]),
                "humidity": round(current["relative_humidity_2m"]),
                "pressure": round(current["surface_pressure"] * 0.750062),
                "wind": wind_val,
                "gusts": round(current["wind_gusts_10m"]),
                "uv": uv_val,
                "uv_label": get_uv_label(uv_val),
                "sunrise": sunrise_str,
                "sunset": sunset_str,
                "is_day": current.get("is_day", 1),
                "icon": icon,
                "text": text,
                "kind": kind,
                "advice": get_advice(kind, temp_val, wind_val, uv_val),
                "today_max": round(daily["temperature_2m_max"][0]),
                "today_min": round(daily["temperature_2m_min"][0]),
                "rain_prob": daily["precipitation_probability_max"][0] or 0,
            }

            current_hour_prefix = current["time"][:13]
            start_idx = 0
            for idx, t_str in enumerate(hourly_data["time"]):
                if t_str.startswith(current_hour_prefix):
                    start_idx = idx
                    break

            for i in range(start_idx, min(start_idx + 24, len(hourly_data["time"]))):
                t_raw = hourly_data["time"][i]
                hour_label = "Сейчас" if i == start_idx else t_raw.split("T")[1]
                h_icon, _, _ = get_info(hourly_data["weather_code"][i])
                hourly.append(
                    {
                        "time": hour_label,
                        "icon": h_icon,
                        "temp": round(hourly_data["temperature_2m"][i]),
                        "prob": hourly_data["precipitation_probability"][i] or 0,
                    }
                )

            week_min = min(round(x) for x in daily["temperature_2m_min"])
            week_max = max(round(x) for x in daily["temperature_2m_max"])
            span = max(week_max - week_min, 1)

            for i in range(7):
                d = date.fromisoformat(daily["time"][i])
                d_icon, d_text, _ = get_info(daily["weather_code"][i])
                d_max = round(daily["temperature_2m_max"][i])
                d_min = round(daily["temperature_2m_min"][i])
                bar_left = round((d_min - week_min) / span * 100)
                bar_width = max(round((d_max - d_min) / span * 100), 8)

                days.append(
                    {
                        "name": "Сегодня" if i == 0 else WEEKDAYS[d.weekday()],
                        "date": d.strftime("%d.%m"),
                        "icon": d_icon,
                        "text": d_text,
                        "max": d_max,
                        "min": d_min,
                        "rain": round(daily["precipitation_sum"][i], 1),
                        "prob": daily["precipitation_probability_max"][i] or 0,
                        "bar_left": bar_left,
                        "bar_width": bar_width,
                    }
                )
        except Exception:
            error = "Ошибка соединения с погодным сервером. Попробуйте снова."

    return render_template(
        "index.html",
        city=city,
        country=country,
        days=days,
        hourly=hourly,
        now=now,
        error=error,
        popular=POPULAR_CITIES,
    )


if __name__ == "__main__":
    app.run(debug=True)