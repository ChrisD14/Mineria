import re
import json
import os
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GEMINI_API_KEY_EXTRACTOR = "AIzaSyAhBimvlCXKuWEQslEWw-lV3vqEHJbh2Nw"

def configure_gemini_api_for_extractor():
    if not GEMINI_API_KEY_EXTRACTOR:
        logging.error("La clave API de Gemini para el extractor no está configurada (está vacía).")
        raise ValueError("GEMINI_API_KEY_EXTRACTOR no configurada correctamente en el código (vacía).")
    genai.configure(api_key=GEMINI_API_KEY_EXTRACTOR)
    logging.info("API de Gemini configurada exitosamente para el extractor de entidades.")

def extract_entities(user_prompt: str) -> dict:
    configure_gemini_api_for_extractor()

    model = genai.GenerativeModel('models/gemini-2.0-flash-001')
    prompt = f"""
    Extract the following entities from the user's prompt: purpose (e.g., graphic_design, gaming, office, programming, studying, general_use), specs (ram_gb, storage_gb, storage_type (SSD, HDD, NVMe), cpu_brand (Intel, AMD, Apple), gpu_required (boolean), gpu_model), budget (low, medium, high), modality (laptop, desktop), min_price, max_price.

    User prompt: "{user_prompt}"

    Respond only with a JSON object. If a field is not mentioned, set its value to null or its default (e.g., gpu_required: false, empty list for purpose/modality).
    Example: {{"purpose": ["graphic_design"], "specs": {{"ram_gb": 32, "storage_gb": null, "storage_type": null, "cpu_brand": null, "gpu_required": true, "gpu_model": null}}, "budget": null, "modality": ["laptop"], "min_price": null, "max_price": null}}
    """

    initial_entities_structure = {
        "purpose": [],
        "specs": {
            "ram_gb": None,
            "storage_gb": None,
            "storage_type": None,
            "cpu_brand": None,
            "gpu_required": False, # Default to False
            "gpu_model": None
        },
        "budget": None,
        "modality": [],
        "min_price": None,
        "max_price": None
    }

    try:
        logging.info(f"Enviando consulta a Gemini para extracción de entidades: '{user_prompt}'")
        response = model.generate_content(prompt)
        gemini_raw_text = response.text.strip()
        logging.info(f"Respuesta cruda de Gemini: '{gemini_raw_text}'")

        # --- MODIFICACIÓN CLAVE AQUÍ: Limpiar la respuesta de Gemini ---
        if gemini_raw_text.startswith('```json') and gemini_raw_text.endswith('```'):
            gemini_raw_text = gemini_raw_text[7:-3].strip() # Elimina '```json' y '```'
        # -----------------------------------------------------------

        extracted_data = json.loads(gemini_raw_text)

        # Mapeo y validación de los datos extraídos
        # ... (el resto de tu lógica de mapeo de entidades sigue aquí) ...

        # Tu lógica existente para procesar `extracted_data` e `initial_entities_structure`
        # Deberías tener algo como esto para actualizar `entities` con los valores de `extracted_data`
        entities = initial_entities_structure.copy()

        if "purpose" in extracted_data and isinstance(extracted_data["purpose"], list):
            entities["purpose"] = extracted_data["purpose"]

        if "specs" in extracted_data and isinstance(extracted_data["specs"], dict):
            specs = entities["specs"]
            if "ram_gb" in extracted_data["specs"]:
                specs["ram_gb"] = extracted_data["specs"]["ram_gb"]
            if "storage_gb" in extracted_data["specs"]:
                specs["storage_gb"] = extracted_data["specs"]["storage_gb"]
            if "storage_type" in extracted_data["specs"]:
                specs["storage_type"] = extracted_data["specs"]["storage_type"]
            if "cpu_brand" in extracted_data["specs"]:
                specs["cpu_brand"] = extracted_data["specs"]["cpu_brand"]
            if "gpu_required" in extracted_data["specs"]:
                specs["gpu_required"] = extracted_data["specs"]["gpu_required"]
            if "gpu_model" in extracted_data["specs"]:
                specs["gpu_model"] = extracted_data["specs"]["gpu_model"]

        if "budget" in extracted_data:
            entities["budget"] = extracted_data["budget"]
        if "modality" in extracted_data and isinstance(extracted_data["modality"], list):
            entities["modality"] = extracted_data["modality"]
        if "min_price" in extracted_data:
            entities["min_price"] = extracted_data["min_price"]
        if "max_price" in extracted_data:
            entities["max_price"] = extracted_data["max_price"]

        logging.info(f"Entidades extraídas: {entities}")
        return entities

    except json.JSONDecodeError as e:
        logging.error(f"Error al decodificar la respuesta JSON de Gemini: {e}", exc_info=True)
        logging.error(f"Respuesta de Gemini que causó el error: '{gemini_raw_text}'")
        return initial_entities_structure
    except Exception as e:
        logging.error(f"Error inesperado al extraer entidades con Gemini: {e}", exc_info=True)
        return initial_entities_structure