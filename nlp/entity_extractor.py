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
    
    # Mueve la inicialización de initial_entities_structure fuera del try-except
    initial_entities_structure = {
        "purpose": [],
        "specs": {
            "ram_gb": None,
            "storage_gb": None,
            "storage_type": None,
            "cpu_brand": None,
            "gpu_required": None,
            "gpu_model": None
        },
        "budget": None,
        "modality": [],
        "min_price": None,
        "max_price": None
    }

    prompt = f"""
    Eres un experto en extracción de entidades para hardware de computadoras.
    Extrae las siguientes entidades de la solicitud del usuario. Si un valor no es especificado directamente,
    intenta inferirlo basándote en el contexto y palabras clave, especialmente para el 'purpose', 'ram_gb' y 'cpu_brand'.

    Las entidades a extraer son:
    - purpose: (string, uno de: 'gaming', 'graphic_design', 'programming', 'office', 'studying', 'general_use', 'workstation', o null si no se puede inferir)
        * Inferir 'gaming' si se menciona "juegos", "gaming", "tarjeta gráfica potente".
        * Inferir 'graphic_design' o 'workstation' si se menciona "diseño gráfico", "edición de video", "renderizado", "gran procesamiento", "potente".
        * Inferir 'programming' si se menciona "programación", "desarrollo", "máquinas virtuales".
        * Inferir 'office' o 'studying' si se menciona "trabajo de oficina", "clases", "escuela", "universidad", "tareas básicas".
        * Inferir 'general_use' si es para uso diario sin especificaciones de alto rendimiento.
    - specs: (object)
        - ram_gb: (integer, GB de RAM, o null si no se especifica y no se puede inferir. Si se menciona "mucha RAM", "gran RAM" o "alto rendimiento", inferir 16 o 32)
        - storage_gb: (integer, GB de almacenamiento, o null)
        - storage_type: (string, 'SSD', 'HDD', 'NVMe', o null)
        - cpu_brand: (string, 'Intel', 'AMD', 'Apple', o null. Si se menciona "gran procesamiento" o "alto rendimiento", inferir 'Intel' o 'AMD' si no se especifica uno, sugiriendo un chip de alta gama.)
        - gpu_required: (boolean, true si se menciona "tarjeta gráfica", "GPU", "gaming"; false si se menciona "gráficos integrados" o no es relevante, o null)
        - gpu_model: (string, modelo específico de GPU, o null)
    - budget: (string, 'low', 'medium', 'high', o null. Inferir 'high' si se menciona "alto rendimiento", "gran procesamiento", "gaming de gama alta".)
    - modality: (array of strings, ej. ["laptop", "desktop"], o null si no se especifica)
    - min_price: (number, precio mínimo, o null)
    - max_price: (number, precio máximo, o null)

    La respuesta debe ser solo un objeto JSON. Si un campo no es aplicable o no se puede inferir, usa null.

    Ejemplos de inferencia:
    - "Necesito una laptop para jugar" -> {{"purpose": "gaming", "specs": {{"gpu_required": true}}, "modality": ["laptop"]}}
    - "Busco una computadora con mucha ram y gran procesamiento" -> {{"purpose": "workstation", "specs": {{"ram_gb": 32, "cpu_brand": "Intel", "gpu_required": null}}, "modality": ["computer"], "budget": "high"}}
    - "Laptop para diseño gráfico con tarjeta de video" -> {{"purpose": "graphic_design", "specs": {{"gpu_required": true}}, "ram_gb": 32, "modality": ["laptop"], "budget": "high"}}
    - "Computadora barata para la universidad" -> {{"purpose": "studying", "budget": "low", "modality": ["computer"]}}
    - "Laptop 32gb ram" -> {{"purpose": "general_use", "specs": {{"ram_gb": 32}}, "modality": ["laptop"]}}
    
    Solicitud del usuario: '{user_prompt}'
    """

    logging.info(f"Enviando consulta a Gemini para extracción de entidades: '{user_prompt}'")
    try:
        response = model.generate_content(prompt)
        gemini_raw_text = response.text.strip()

        # *** CÓDIGO CORREGIDO AQUÍ: Elimina los delimitadores de bloque de código Markdown ***
        if gemini_raw_text.startswith('```json') and gemini_raw_text.endswith('```'):
            json_string = gemini_raw_text[len('```json'):-len('```')].strip()
        else:
            json_string = gemini_raw_text.strip() # En caso de que no use el formato de markdown

        extracted_data = json.loads(json_string) # Carga el JSON limpio

        # Copia los valores extraídos a la estructura final, manejando los que pueden faltar
        entities = initial_entities_structure.copy()
        
        # 'purpose' puede ser una cadena o una lista, o null. Asegúrate de que siempre sea una lista.
        if "purpose" in extracted_data and extracted_data["purpose"] is not None:
            if isinstance(extracted_data["purpose"], str):
                entities["purpose"] = [extracted_data["purpose"]]
            elif isinstance(extracted_data["purpose"], list):
                entities["purpose"] = extracted_data["purpose"]

        if "specs" in extracted_data and isinstance(extracted_data["specs"], dict):
            specs = entities["specs"] # Trabaja directamente en el sub-diccionario 'specs'

            if "ram_gb" in extracted_data["specs"]:
                specs["ram_gb"] = extracted_data["specs"]["ram_gb"]
            if "storage_gb" in extracted_data["specs"]:
                specs["storage_gb"] = extracted_data["specs"]["storage_gb"]
            if "storage_type" in extracted_data["specs"]:
                specs["storage_type"] = extracted_data["specs"]["storage_type"]
            if "cpu_brand" in extracted_data["specs"]:
                specs["cpu_brand"] = extracted_data["specs"]["cpu_brand"]
            
            # Ajuste para gpu_required si viene como True/False o null
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
        return initial_entities_structure # Ahora initial_entities_structure siempre estará definida
    except Exception as e:
        logging.error(f"Error inesperado durante la extracción de entidades: {e}", exc_info=True)
        return initial_entities_structure # Ahora initial_entities_structure siempre estará definida