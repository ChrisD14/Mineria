# app.py
from flask import Flask, render_template, request, jsonify
from nlp.entity_extractor import extract_entities
from nlp.intent_recognizer import recognize_intent
from recommender.recommendation_engine import RecommendationEngine
from nlp.translator import translate_text_to_english # Importa la función actualizada
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
recommender = RecommendationEngine() # Instancia el motor de recomendación

# Ruta principal que renderiza el formulario
@app.route('/')
def index():
    return render_template('index.html')



# Ruta para manejar las solicitudes de recomendación
@app.route('/recommend', methods=['POST'])
def recommend():
    user_prompt = request.form.get('prompt') # Usar .get() para evitar KeyError si no existe

    if not user_prompt:
        return render_template('index.html', error="Por favor, ingresa una solicitud.", recommendations=[])

    logging.info(f"Solicitud del usuario original: '{user_prompt}'")
    
    try:
        # Paso 1: Traducir la consulta del usuario a inglés para el procesamiento NLP
        translation_result = translate_text_to_english(user_prompt)
        
        if not translation_result['success']:
            logging.error(f"Error en la traducción: {translation_result['error_message']}")
            return render_template('index.html', user_prompt=user_prompt, recommendations=[{
                'category': 'Error',
                'description': f"No se pudo procesar tu solicitud debido a un problema de traducción: {translation_result['error_message']}. Por favor, intenta de nuevo.",
                'details': {}
            }])
        
        # El motor de recomendación espera el objeto `translation_result`
        # para acceder a `translated_text` y `success`
        recommendations = recommender.get_recommendations(user_prompt, translation_result) 
    
    except Exception as e:
        logging.error(f"Error general en el proceso de recomendación o con Gemini: {e}", exc_info=True)
        recommendations = [{
            'category': 'Error',
            'description': 'Hubo un problema al procesar tu solicitud. Intenta de nuevo más tarde.',
            'details': {}
        }]

    return render_template('index.html', user_prompt=user_prompt, recommendations=recommendations)

if __name__ == '__main__':
    # Importante: para producción, usa un servidor WSGI como Gunicorn o Waitress
    app.run(debug=True) # En producción, cambia debug=False y usa un servidor WSGI