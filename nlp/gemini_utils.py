# utils/gemini_utils.py
import os
import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyAhBimvlCXKuWEQslEWw-lV3vqEHJbh2Nw"

genai.configure(api_key=os.getenv(GEMINI_API_KEY))

model = genai.GenerativeModel("models/gemini-2.0-flash-001")

def classify_intent_with_gemini(prompt: str) -> str:
    full_prompt = (
        "You are an intent classifier. Based on the following user request, classify the intent as one of:\n"
        "- 'computadora' (if asking about laptops or desktop computers)\n"
        "- 'memoria_ram'\n"
        "- 'almacenamiento'\n"
        "- 'impresora'\n"
        "- 'desconocido'\n"
        "User request: " + prompt
    )

    response = model.generate_content(full_prompt)
    intent = response.text.strip().lower()
    
    if intent not in ["computadora", "memoria_ram", "almacenamiento", "impresora"]:
        return "desconocido"
    return intent
