import requests


WMO_RAIN_CODES = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
WMO_WIND_THRESHOLD_KMH = 50
WMO_HEAT_THRESHOLD_C = 38
WMO_FROST_THRESHOLD_C = 2


def get_user_location():
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data.get("latitude")), float(data.get("longitude"))
    except Exception:
        pass
    return None, None


def fetch_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "hourly": "precipitation_probability,temperature_2m,windspeed_10m",
        "forecast_days": 1,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


def parse_weather_conditions(weather_data):
    if not weather_data:
        return {}

    current = weather_data.get("current_weather", {})
    weathercode = current.get("weathercode")
    temperature = current.get("temperature")
    windspeed = current.get("windspeed")

    hourly = weather_data.get("hourly", {})
    precip_probs = hourly.get("precipitation_probability", [])
    max_precip_prob = max(precip_probs) if precip_probs else 0

    return {
        "weathercode": weathercode,
        "temperature": temperature,
        "windspeed": windspeed,
        "max_precipitation_probability": max_precip_prob,
        "rain_likely": weathercode in WMO_RAIN_CODES or max_precip_prob >= 60,
        "heat_alert": temperature is not None and temperature >= WMO_HEAT_THRESHOLD_C,
        "frost_alert": temperature is not None and temperature <= WMO_FROST_THRESHOLD_C,
        "wind_alert": windspeed is not None and windspeed >= WMO_WIND_THRESHOLD_KMH,
    }


def detect_language(text):
    if not text:
        return "french"
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > len(text) * 0.3:
        return "arabic"
    darija_keywords = ["wach", "bghit", "zwina", "mzyan", "nta", "hna", "daba", "rani", "makanch"]
    lower = text.lower()
    if any(k in lower for k in darija_keywords):
        return "darija"
    return "french"


def generate_intelligent_alert(crop, action_type, notes, weather_conditions, api_key):
    if not any([
        weather_conditions.get("rain_likely"),
        weather_conditions.get("heat_alert"),
        weather_conditions.get("frost_alert"),
        weather_conditions.get("wind_alert"),
    ]):
        return None

    language = detect_language(notes)

    language_instruction = {
        "french": "Réponds uniquement en français.",
        "arabic": "أجب باللغة العربية الفصحى فقط.",
        "darija": "جاوب بالدارجة الجزائرية فقط.",
    }.get(language, "Réponds uniquement en français.")

    weather_summary = []
    if weather_conditions.get("rain_likely"):
        weather_summary.append(f"pluie probable ({weather_conditions['max_precipitation_probability']}% de probabilité, code WMO {weather_conditions['weathercode']})")
    if weather_conditions.get("heat_alert"):
        weather_summary.append(f"chaleur extrême ({weather_conditions['temperature']}°C)")
    if weather_conditions.get("frost_alert"):
        weather_summary.append(f"risque de gel ({weather_conditions['temperature']}°C)")
    if weather_conditions.get("wind_alert"):
        weather_summary.append(f"vents forts ({weather_conditions['windspeed']} km/h)")

    prompt = f"""Tu es un agronome expert en agriculture algérienne. Un agriculteur vient de logger une intervention sur son champ.

Données de l'intervention :
- Culture : {crop}
- Action effectuée : {action_type}
- Notes de l'agriculteur : {notes if notes else 'aucune note'}

Conditions météo actuelles :
- {', '.join(weather_summary)}

Ta mission : génère une alerte agronomique courte, pratique et spécifique (2-3 phrases maximum) pour aider l'agriculteur à adapter son intervention en fonction de la météo. Sois concret et actionnable. Si aucune alerte n'est nécessaire, réponds avec le mot exact : NULL

{language_instruction}"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.4,
            },
            timeout=15,
        )

        if response.status_code == 200:
            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            if message.upper() == "NULL" or not message:
                return None
            return message
        return None

    except Exception:
        return None