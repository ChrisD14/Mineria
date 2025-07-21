# nlp/translator.py (Este es tu archivo existente, actualizado)
import os
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ¡IMPORTANTE!
# Por favor, asegúrate de que tu clave API esté configurada de forma segura.
# Se recomienda usar variables de entorno para las claves de API en producción.
# Para este ejemplo y pruebas rápidas, se define aquí, pero NO es la mejor práctica para producción.
# Puedes usar la misma clave que usas para el recomendador o extractor.
GEMINI_API_KEY_TRANSLATION = "AIzaSyAhBimvlCXKuWEQslEWw-lV3vqEHJbh2Nw" 

def configure_gemini_api_for_translation():
    if not GEMINI_API_KEY_TRANSLATION:
            logging.error("La clave API de Gemini para la traducción no está configurada (está vacía).")
            raise ValueError("GEMINI_API_KEY_TRANSLATION no configurada correctamente en el código (vacía).")
    genai.configure(api_key=GEMINI_API_KEY_TRANSLATION)
    logging.info("API de Gemini configurada exitosamente para el servicio de traducción.")

def translate_text_to_english(text: str) -> dict:
    """
    Traduce el texto dado del español al inglés utilizando la API de Google Gemini.
    Siempre traduce a inglés para mantener la consistencia con el motor de recomendación.

    Args:
        text (str): El texto a traducir.

    Returns:
        dict: Un diccionario con 'success' (bool), 'translated_text' (str) y 'error_message' (str, opcional).
              Si hay un error, 'translated_text' contendrá el texto original.
    """
    configure_gemini_api_for_translation() # Asegura que la API esté configurada

    model = genai.GenerativeModel('models/gemini-2.0-flash-001') # O un modelo más adecuado para traducción

    # Ajustamos el prompt para que sea explícito en traducir de español a inglés
    prompt = f"Translate the following text from Spanish to English. Provide only the translated text, without any additional comments or formatting:\n\n'{text}'"

    try:
        logging.info(f"Iniciando traducción de texto a inglés: '{text}'")
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        logging.info(f"Texto traducido a inglés: '{translated_text}'")
        return {'success': True, 'translated_text': translated_text}
    except Exception as e:
        logging.error(f"Error al traducir texto con Gemini: {e}", exc_info=True)
        # En caso de error, devolver el texto original para que el proceso no falle
        return {'success': False, 'translated_text': text, 'error_message': str(e)}

# --- Bloque de prueba (solo para ejecución directa de este archivo) ---
if __name__ == '__main__':
    configure_gemini_api_for_translation() # Configura la API para la prueba

    test_phrases = [
        "Hola, necesito una laptop para estudiar.",
        "Busco un PC de gaming con 32GB de RAM.",
        "¿Me puedes recomendar algo barato?",
        "Quiero una computadora con más de 1000 dólares.",
        "Este es un texto de prueba."
    ]

    for phrase in test_phrases:
        result = translate_text_to_english(phrase)
        if result['success']:
            print(f"Original: '{phrase}'\nTraducido: '{result['translated_text']}'\n---")
        else:
            print(f"Original: '{phrase}'\nError: {result['error_message']}\n---")