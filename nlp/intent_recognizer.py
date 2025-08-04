# nlp/intent_recognizer.py
import logging
import os

from nlp.gemini_utils import classify_intent_with_gemini

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

EXCLUDE_CONTEXT_KEYWORDS = ["libro", "book", "review", "reseña", "article", "artículo", "manual", "documental"]

def recognize_intent(user_prompt: str, use_gemini: bool = True) -> str:
    """
    Reconoce la intención principal de la consulta del usuario. 
    Si no hay certeza, puede usar Gemini para ayudar a clasificar.
    """
    prompt_lower = user_prompt.lower()
    logging.debug(f"Reconociendo intención para: '{prompt_lower}'")

    # 🛑 Paso 1: Evitar consultas que no impliquen búsqueda de productos
    if any(word in prompt_lower for word in EXCLUDE_CONTEXT_KEYWORDS):
        logging.info("Detectado contenido informativo (libros, artículos, etc.) → Intención: desconocido")
        return "desconocido"

    # ✅ Paso 2: Detectar intención por palabras clave específicas
    if any(word in prompt_lower for word in ["computer", "laptop", "pc", "desktop", "workstation"]):
        logging.info("Intención detectada: computadora")
        return "computadora"
    
    if "ram" in prompt_lower or "memory" in prompt_lower:
        logging.info("Intención detectada: memoria_ram")
        return "memoria_ram"
    
    if any(word in prompt_lower for word in ["storage", "disk", "ssd", "hdd", "nvme"]):
        logging.info("Intención detectada: almacenamiento")
        return "almacenamiento"
    
    if "printer" in prompt_lower:
        logging.info("Intención detectada: impresora")
        return "impresora"

    # 🔮 Paso 3: Si no se puede determinar, usar Gemini
    if use_gemini:
        logging.info("Usando Gemini para clasificación semántica...")
        return classify_intent_with_gemini(user_prompt)

    # 🚫 Por defecto
    logging.info("Intención no reconocida → Intención: desconocido")
    return "desconocido"
