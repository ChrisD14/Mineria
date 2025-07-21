# nlp/gemini_recommender_assistant.py
import os
import google.generativeai as genai
import logging
import json # Para serializar los detalles de los productos si es necesario

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ¡IMPORTANTE!
# Por favor, asegúrate de que tu clave API esté configurada de forma segura
# Se recomienda usar variables de entorno para las claves de API en producción.
# Para este ejemplo y pruebas rápidas, la ponemos aquí directamente,
# pero en un entorno real, NO es la mejor práctica.
GEMINI_API_KEY_RECOMMENDER = "AIzaSyAhBimvlCXKuWEQslEWw-lV3vqEHJbh2Nw" 

def configure_gemini_api_for_recommender():
    """Configura la clave API de Gemini directamente."""
    if not GEMINI_API_KEY_RECOMMENDER:
        logging.error("La clave API de Gemini para el recomendador no está configurada (está vacía).")
        raise ValueError("GEMINI_API_KEY_RECOMMENDER no configurada correctamente en el código (vacía).")
    genai.configure(api_key=GEMINI_API_KEY_RECOMMENDER)
    logging.info("API de Gemini configurada exitosamente para el asistente recomendador.")


def get_gemini_expert_recommendation(user_original_prompt: str, found_laptops: list) -> str:
    """
    Genera una recomendación experta utilizando la API de Google Gemini,
    basándose en la solicitud original del usuario y las laptops encontradas.
    """
    try:
        # Asegúrate de que la API de Gemini ya ha sido configurada
        # (Esto se debería hacer una vez al inicio de la aplicación, por ejemplo en app.py)
        
        model = genai.GenerativeModel('models/gemini-2.0-flash-001') # O 'models/gemini-1.5-flash-latest' u otro modelo

        # Prepara los datos de las laptops para el modelo
        # Queremos enviar solo los detalles relevantes que el modelo necesita para la recomendación
        laptops_for_gemini = []
        for rec in found_laptops:
            if rec and rec.get('details'):
                details = rec['details']
                # Simplificamos las especificaciones para el prompt, incluyendo storage_gb y storage_type
                specs_summary = {
                    "RAM": f"{details['specifications'].get('ram_gb')}GB" if details['specifications'].get('ram_gb') else 'N/A',
                    "Almacenamiento": f"{details['specifications'].get('storage_gb')}GB {details['specifications'].get('storage_type')}" if details['specifications'].get('storage_gb') and details['specifications'].get('storage_type') else 'N/A',
                    "CPU": details['specifications'].get('cpu_brand', 'N/A'),
                    "GPU": details['specifications'].get('gpu_model', 'N/A')
                }
                laptops_for_gemini.append({
                    "nombre": details.get('name'),
                    "precio": details.get('price'),
                    "tienda": details.get('store'),
                    "url": details.get('url'),
                    "especificaciones": specs_summary,
                    "descripcion_corta": details.get('description', '')[:150] + '...' if details.get('description') else ''
                })
        
        # Construye el prompt para el modelo de Gemini
        # Es crucial instruir al modelo sobre su rol y el idioma de la respuesta.
        prompt_to_gemini = f"""
Eres un experto en tecnología altamente cualificado y tu objetivo es proporcionar recomendaciones claras y concisas a los usuarios.
Analiza la solicitud original del usuario y la lista de laptops encontradas.
Tu respuesta debe ser SIEMPRE en español.

1.  **Evalúa si las laptops encontradas se ajustan a la solicitud del usuario.**
2.  **Destaca la(s) mejor(es) opción(es)** que cumplan con los requisitos, explicando por qué.
3.  **Si hay alguna inconsistencia o dato inusual en las especificaciones** (ej. si se esperaría un SSD pero se reporta HDD para alta gama, o si faltan datos importantes), menciona esta observación.
4.  **No inventes especificaciones.** Si un dato es N/A o no está claro, indícalo.
5.  **Proporciona un consejo final conciso y útil.**

---
**Solicitud original del usuario:** "{user_original_prompt}"

---
**Laptops encontradas y sus detalles:**
{json.dumps(laptops_for_gemini, indent=2, ensure_ascii=False)}
---

Por favor, proporciona un consejo experto basado en esta información, y asegúrate de que la respuesta sea en español.
"""
        logging.info("Enviando prompt a Gemini para recomendación experta...")
        logging.debug(f"Prompt enviado: {prompt_to_gemini}")

        response = model.generate_content(prompt_to_gemini)
        
        # Accede al texto generado por el modelo
        gemini_advice = response.text
        logging.info("Recomendación de Gemini recibida.")
        return gemini_advice

    except Exception as e:
        logging.error(f"Error al obtener la recomendación del experto de Gemini: {e}", exc_info=True)
        return "Lo siento, no pude generar una recomendación experta en este momento. Por favor, inténtalo de nuevo más tarde."

# --- Bloque de prueba (solo para ejecución directa de este archivo) ---
if __name__ == '__main__':
    # Configura la API de Gemini para la prueba
    configure_gemini_api_for_recommender()

    # Ejemplo de uso
    test_prompt = "Necesito una laptop para diseño gráfico con al menos 32GB de RAM."
    
    # Simula la lista de laptops que vendría del recommendation_engine
    # ¡Asegúrate de que tus scrapers (base_scrapers.py y computron.py)
    # estén extrayendo correctamente 'storage_gb' como 1024 (para 1TB) y 'storage_type' como 'SSD'!
    test_laptops_data = [
        {
            'category': 'Computadora',
            'description': 'Laptop potente para diseño y juegos.',
            'details': {
                'name': 'ASUS ROG Zephyrus G16',
                'price': 1800.0,
                'store': 'Computron',
                'url': 'http://computron.com.ec/asus-rog-g16',
                'image_url': 'some_image_url.jpg',
                'specifications': {
                    'ram_gb': 32,
                    'storage_gb': 1024, # 1TB
                    'storage_type': 'SSD',
                    'cpu_brand': 'Intel Core i9',
                    'gpu_model': 'NVIDIA GeForce RTX 4070'
                }
            },
            'score': 0.95
        },
        {
            'category': 'Computadora',
            'description': 'Laptop premium con doble pantalla.',
            'details': {
                'name': 'ASUS ZenBook Duo',
                'price': 2200.0,
                'store': 'Computron',
                'url': 'http://computron.com.ec/zenbook-duo',
                'image_url': 'another_image.jpg',
                'specifications': {
                    'ram_gb': 32,
                    'storage_gb': 1024, # 1TB
                    'storage_type': 'SSD',
                    'cpu_brand': 'Intel Core i9',
                    'gpu_model': 'NVIDIA GeForce RTX 4060'
                }
            },
            'score': 0.92
        },
        {
            'category': 'Computadora',
            'description': 'Laptop de alto rendimiento para profesionales.',
            'details': {
                'name': 'HP OMEN 16',
                'price': 1650.0,
                'store': 'Computron',
                'url': 'http://computron.com.ec/hp-omen-16',
                'image_url': 'hp_omen_image.jpg',
                'specifications': {
                    'ram_gb': 32,
                    'storage_gb': 512,
                    'storage_type': 'SSD',
                    'cpu_brand': 'AMD Ryzen 9',
                    'gpu_model': 'AMD Radeon RX 7800M'
                }
            },
            'score': 0.88
        },
         {
            'category': 'Computadora',
            'description': 'Laptop para juegos y multitarea. (Este sería un ejemplo con datos incorrectos si no se corrige el scraper)',
            'details': {
                'name': 'Laptop Incorrecta',
                'price': 1000.0,
                'store': 'La Ganga',
                'url': 'http://laganga.com/incorrecta',
                'image_url': 'incorrecta_image.jpg',
                'specifications': {
                    'ram_gb': 16, # No cumple con 32GB RAM
                    'storage_gb': 32, # Dato incorrecto simulado para HDD
                    'storage_type': 'HDD', # Tipo incorrecto simulado
                    'cpu_brand': 'Intel Core i5',
                    'gpu_model': 'NVIDIA GeForce RTX 3050'
                }
            },
            'score': 0.40 # Baja puntuación por no cumplir requisitos
        }
    ]
    

    print(f"\n--- Probando recomendación experta para: '{test_prompt}' ---")
    gemini_rec = get_gemini_expert_recommendation(test_prompt, test_laptops_data)
    print("\n--- Recomendación de Experto de Gemini ---\n")
    print(gemini_rec)

    print("\n--- Prueba con sin laptops (simulando que no se encontraron) ---")
    gemini_rec_no_laptops = get_gemini_expert_recommendation("Necesito una laptop barata para estudiar.", [])
    print("\n--- Recomendación de Experto de Gemini (sin laptops) ---\n")
    print(gemini_rec_no_laptops)