from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.conf import settings
from .utils import generate_intelligent_alert


class GroqAPITest(TestCase):

    def setUp(self):
        self.api_key = settings.GROQ_API_KEY
        self.weather_conditions = {
            "rain_likely": True,
            "heat_alert": False,
            "frost_alert": False,
            "wind_alert": False,
            "max_precipitation_probability": 80,
            "weathercode": 61,
            "temperature": 22,
            "windspeed": 15,
        }
    def test_groq_full_debug(self):
        import requests
        from django.conf import settings

        prompt = """Tu es un agronome expert en agriculture algérienne. Un agriculteur vient de logger une intervention sur son champ.

    Données de l'intervention :
    - Culture : blé
    - Action effectuée : treatment
    - Notes de l'agriculteur : Application fongicide parcelle nord.

    Conditions météo actuelles :
    - pluie probable (80% de probabilité, code WMO 61)

    Ta mission : génère une alerte agronomique courte, pratique et spécifique (2-3 phrases maximum) pour aider l'agriculteur à adapter son intervention en fonction de la météo. Sois concret et actionnable. Si aucune alerte n'est nécessaire, réponds avec le mot exact : NULL

    Réponds uniquement en français."""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.4,
            },
            timeout=15,
        )
        print("\n--- Full Debug ---")
        print("Status:", response.status_code)
        data = response.json()
        message = data["choices"][0]["message"]["content"].strip()
        print("Raw message:", repr(message))
        print("------------------\n")
        self.assertEqual(response.status_code, 200)
        
    def test_groq_real_call(self):
        result = generate_intelligent_alert(
            crop="blé",
            action_type="treatment",
            notes="Application fongicide parcelle nord.",
            weather_conditions=self.weather_conditions,
            api_key=self.api_key,
        )
        print("\n--- Groq API Response ---")
        print(result)
        print("-------------------------\n")
        self.assertIsNotNone(result, "Groq returned None — check your API key or network.")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)

    def test_groq_arabic(self):
        result = generate_intelligent_alert(
            crop="طماطم",
            action_type="watering",
            notes="سقي الحقل الشمالي",
            weather_conditions=self.weather_conditions,
            api_key=self.api_key,
        )
        print("\n--- Groq Arabic Response ---")
        print(result)
        print("----------------------------\n")
        self.assertIsNotNone(result)

    def test_groq_darija(self):
        result = generate_intelligent_alert(
            crop="btatem",
            action_type="planting",
            notes="daba bghit nzra f had lard",
            weather_conditions=self.weather_conditions,
            api_key=self.api_key,
        )
        print("\n--- Groq Darija Response ---")
        print(result)
        print("----------------------------\n")
        self.assertIsNotNone(result)

    def test_no_alert_when_weather_is_fine(self):
        calm_conditions = {
            "rain_likely": False,
            "heat_alert": False,
            "frost_alert": False,
            "wind_alert": False,
            "max_precipitation_probability": 10,
            "weathercode": 1,
            "temperature": 24,
            "windspeed": 10,
        }
        result = generate_intelligent_alert(
            crop="blé",
            action_type="observation",
            notes="Tout va bien.",
            weather_conditions=calm_conditions,
            api_key=self.api_key,
        )
        print("\n--- No Alert Test ---")
        print(result)
        print("---------------------\n")
        self.assertIsNone(result, "Should return None when weather is fine — no alert needed.")

    def test_groq_invalid_key(self):
        result = generate_intelligent_alert(
            crop="blé",
            action_type="treatment",
            notes="Test avec clé invalide.",
            weather_conditions=self.weather_conditions,
            api_key="invalid_key_test",
        )
        print("\n--- Invalid Key Test ---")
        print(result)
        print("------------------------\n")
        self.assertIsNone(result, "Should return None gracefully when API key is wrong.")

    
    def test_groq_debug(self):
        import requests
        from django.conf import settings

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 50,
            },
            timeout=15,
        )
        print("\n--- Debug ---")
        print("Status:", response.status_code)
        print("Response:", response.json())
        print("-------------\n")
        self.assertEqual(response.status_code, 200)



