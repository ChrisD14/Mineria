# recommender/recommendation_engine.py
import re
import json
import time
import random
import logging # Asegúrate de importar logging

# Configura el logger para ver mensajes de depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Importa las funciones de NLP
from nlp.intent_recognizer import recognize_intent
from nlp.entity_extractor import extract_entities # Asegúrate de que este sea el archivo actualizado
from nlp.translator import translate_text_to_english # Asumiendo que esta función existe

from scrapers.la_ganga import LaGangaScraper
from scrapers.computron import ComputronScraper
from scrapers.novicompu import NovicompuScraper
from scrapers.mobilestore import MobilestoreScraper
from scrapers.bestcell import BestcellScraper
from config import RECOMMENDATION_THRESHOLDS 

class RecommendationEngine:
    def __init__(self):
        self.scrapers = {
            "la_ganga": LaGangaScraper(),
            "computron": ComputronScraper(),
            "novicompu": NovicompuScraper(),
            "mobilestore": MobilestoreScraper(),
            "bestcell": BestcellScraper(),
        }
        # Puedes añadir un mapeo de propósito a requisitos mínimos aquí
        self.purpose_requirements = {
            "estudio": {"min_ram_gb": 8, "min_storage_gb": 256, "storage_type": "SSD", "cpu_brand": None, "gpu_required": False},
            "gaming": {"min_ram_gb": 16, "min_storage_gb": 512, "storage_type": "SSD", "cpu_brand": None, "gpu_required": True},
            "diseño_grafico": {"min_ram_gb": 16, "min_storage_gb": 512, "storage_type": "SSD", "cpu_brand": None, "gpu_required": True}, # Ajustar a 32GB RAM en _recommend_computer
            "oficina": {"min_ram_gb": 8, "min_storage_gb": 256, "storage_type": "SSD", "cpu_brand": None, "gpu_required": False},
            "programacion": {"min_ram_gb": 16, "min_storage_gb": 512, "storage_type": "SSD", "cpu_brand": None, "gpu_required": False},
        }

    # --- NUEVA FUNCIÓN PARA GENERAR LA QUERY DE BÚSQUEDA ---\
    def _generate_search_query(self, user_intent, extracted_entities):
        query_parts = []

        # 1. Identificar el tipo principal de producto
        if user_intent == "computadora":
            if "portatil" in extracted_entities.get("modality", []):
                query_parts.append("laptop")
            elif "escritorio" in extracted_entities.get("modality", []):
                query_parts.append("computadora escritorio") # Más específico que solo "pc"
            else:
                # Si no se especifica modalidad pero la intención es computadora, default a laptop
                query_parts.append("laptop")

        # 2. Añadir especificaciones clave a la query
        specs = extracted_entities.get("specs", {})
        
        # RAM
        ram_gb = specs.get("ram_gb")
        if ram_gb:
            query_parts.append(f"{ram_gb}GB RAM") # Ahora se busca explícitamente "RAM"

        # Almacenamiento
        storage_gb = specs.get("storage_gb")
        storage_type = specs.get("storage_type")
        if storage_gb:
            if storage_type:
                query_parts.append(f"{storage_gb}GB {storage_type}")
            else:
                query_parts.append(f"{storage_gb}GB SSD") # Asumir SSD si no se especifica tipo para búsqueda

        # CPU
        cpu_brand = specs.get("cpu_brand")
        if cpu_brand:
            query_parts.append(cpu_brand)

        # GPU
        gpu_model = specs.get("gpu_model")
        if gpu_model:
            query_parts.append(gpu_model)
        elif specs.get("gpu_required"):
            query_parts.append("tarjeta grafica") # Si solo se requiere GPU sin modelo específico

        # 3. Añadir presupuesto (palabras clave genéricas para la búsqueda inicial)
        budget = extracted_entities.get("budget")
        if budget == "bajo":
            query_parts.append("economica")
        elif budget == "alto":
            query_parts.append("premium")
        
        # Unir todas las partes en una sola cadena de consulta
        # Limita la longitud de la query para evitar problemas con las URLs de búsqueda
        search_query = " ".join(query_parts).strip()
        if not search_query:
            search_query = user_intent if user_intent != "desconocido" else "producto tecnologico"

        logging.info(f"Query de búsqueda generada: '{search_query}'")
        return search_query.strip()
    
    def _get_specs(self, details: dict) -> dict:
        specs = details.get("specifications")
        if isinstance(specs, dict) and specs:
            return specs
        fallback = {}
        for k in ("ram_gb", "storage_gb", "storage_type", "cpu_brand", "gpu_required", "gpu_model"):
            if k in details:
                fallback[k] = details[k]
        return fallback

    def _recommend_computer(self, entities: dict, user_original_prompt: str) -> list:
        # Aquí consolidamos los requisitos del usuario
        # Inicializamos los requisitos con valores que no restrinjan si no se especifican
        requirements = {
            "min_ram_gb": 0,
            "min_storage_gb": 0,
            "cpu_brand": None,
            "gpu_required": entities["specs"].get("gpu_required", False), # Usar el GPU requerido extraído
            "desired_gpu_keyword": entities["specs"].get("gpu_model"), # Modelo de GPU deseado
            "storage_type": entities["specs"].get("storage_type"),
            "min_price": entities.get("min_price"),
            "max_price": entities.get("max_price"),
        }

        # Aplicar requisitos basados en el propósito
        for purpose in entities["purpose"]:
            if purpose in self.purpose_requirements:
                reqs = self.purpose_requirements[purpose]
                requirements["min_ram_gb"] = max(requirements["min_ram_gb"], reqs["min_ram_gb"])
                requirements["min_storage_gb"] = max(requirements["min_storage_gb"], reqs["min_storage_gb"])
                if reqs["cpu_brand"]:
                    requirements["cpu_brand"] = reqs["cpu_brand"]
                if reqs["gpu_required"]:
                    requirements["gpu_required"] = True
                if reqs["storage_type"] and not requirements["storage_type"]: # Si no se especificó y el propósito lo pide
                    requirements["storage_type"] = reqs["storage_type"]

        # Sobrescribir con especificaciones explícitas del usuario si existen
        if entities["specs"].get("ram_gb") is not None:
            requirements["min_ram_gb"] = max(requirements["min_ram_gb"], entities["specs"]["ram_gb"])
        if entities["specs"].get("storage_gb") is not None:
            requirements["min_storage_gb"] = max(requirements["min_storage_gb"], entities["specs"]["storage_gb"])
        if entities["specs"].get("storage_type") is not None:
             requirements["storage_type"] = entities["specs"]["storage_type"] # El tipo explícito del usuario es prioritario
        if entities["specs"].get("cpu_brand") is not None:
            requirements["cpu_brand"] = entities["specs"]["cpu_brand"]
        
        # Consideración especial para diseño gráfico: 32GB de RAM si no se especificó más
        if "diseño_grafico" in entities["purpose"] and requirements["min_ram_gb"] < 32:
            requirements["min_ram_gb"] = max(requirements["min_ram_gb"], 32)
            logging.info("Ajustando requisito de RAM a 32GB para diseño gráfico.")


        # Manejo del presupuesto cualitativo si no hay rangos de precio explícitos
        if not (requirements["min_price"] or requirements["max_price"]) and entities["budget"]:
            if entities["budget"] == "bajo":
                requirements["max_price"] = RECOMMENDATION_THRESHOLDS["low_budget_max_price"]
            elif entities["budget"] == "medio":
                requirements["max_price"] = RECOMMENDATION_THRESHOLDS["medium_budget_max_price"]
            elif entities["budget"] == "alto":
                requirements["min_price"] = RECOMMENDATION_THRESHOLDS["medium_budget_max_price"] # o un valor inicial más alto

        
        # Generar la query de búsqueda para los scrapers
        search_query = self._generate_search_query("computadora", entities)
        logging.info(f"Buscando computadoras con la query: '{search_query}' y requisitos: {requirements}")

        all_found_products = []
        for scraper_name, scraper_instance in self.scrapers.items():
            logging.info(f"Scraping en {scraper_name} para '{search_query}'...")
            try:
                # La función search_products debería devolver una lista de diccionarios
                # con 'name', 'price', 'url', 'store', 'image_url', 'description', 'specifications'
                store_products_basic = scraper_instance.search_products(search_query)
                logging.info(f"Se encontraron {len(store_products_basic)} productos básicos en {scraper_name}.")
                
                # Para cada producto básico, intentar obtener detalles completos
                for basic_product in store_products_basic:
                    if basic_product.get('url') and basic_product['url'] != '#':
                        detailed_product = scraper_instance.parse_product_page(basic_product['url'])
                        if detailed_product:
                            # Fusionar detalles básicos con los detallados
                            # Priorizar los detallados si hay superposición
                            merged_details = {**basic_product, **detailed_product}
                            # Asegurarse de que 'specifications' sea un diccionario
                            merged_details['specifications'] = {
                                **basic_product.get('specifications', {}), 
                                **detailed_product.get('specifications', {})
                            }
                            all_found_products.append({
                                'category': basic_product.get('category', 'Computadora'),
                                'description': merged_details.get('description', basic_product.get('name')),
                                'details': merged_details, # Contiene todos los detalles combinados
                                'score': 0 # El score se calculará después
                            })
                        else:
                            # Si no se pueden obtener detalles completos, usar solo los básicos
                            logging.warning(f"No se pudieron obtener detalles completos para {basic_product.get('name')} en {scraper_name}. Usando solo datos básicos.")
                            all_found_products.append({
                                'category': basic_product.get('category', 'Computadora'),
                                'description': basic_product.get('description', basic_product.get('name')),
                                'details': basic_product, # Usar solo los detalles básicos
                                'score': 0
                            })
                    else:
                        logging.warning(f"Producto sin URL o URL inválida en {scraper_name}: {basic_product.get('name')}. Omitiendo detalles.")
                        all_found_products.append({
                            'category': basic_product.get('category', 'Computadora'),
                            'description': basic_product.get('description', basic_product.get('name')),
                            'details': basic_product, # Usar solo los detalles básicos
                            'score': 0
                        })

            except Exception as e:
                logging.error(f"Error al scrapear en {scraper_name}: {e}", exc_info=True)
                continue # Continúa con el siguiente scraper
        
        logging.info(f"Total de productos encontrados después de scraping: {len(all_found_products)}")
        if not all_found_products:
            logging.warning("No se encontraron productos para recomendar.")
            return []


        # Filtrar y puntuar productos
        scored_recommendations = []
        for product_rec in all_found_products:
            score = 0
            details = product_rec.get("details", {})
            specs = details.get("specifications", {})
            product_price = details.get("price")
            
            # --- Criterios de puntuación ---

            # 1. Requisitos de RAM
            product_ram = specs.get("ram_gb")
            if product_ram and product_ram >= requirements["min_ram_gb"]:
                score += 0.30 # Alto peso para RAM

            # 2. Requisitos de Almacenamiento
            product_storage_gb = specs.get("storage_gb")
            product_storage_type = specs.get("storage_type")
            if product_storage_gb and product_storage_gb >= requirements["min_storage_gb"]:
                score += 0.20 # Peso para cantidad de almacenamiento
                if requirements["storage_type"] and product_storage_type and \
                   requirements["storage_type"].lower() == product_storage_type.lower():
                    score += 0.10 # Bono por tipo de almacenamiento (ej. SSD)

            # 3. Requisitos de CPU (si aplica)
            product_cpu = specs.get("cpu_brand")
            if requirements["cpu_brand"] and product_cpu and \
               requirements["cpu_brand"].lower() in product_cpu.lower():
                score += 0.15 # Peso para CPU

            # 4. Requisitos de GPU
            if requirements["gpu_required"]:
                if specs.get("gpu_model"): # Si tiene un modelo de GPU
                    score += 0.20
                    if requirements["desired_gpu_keyword"] and \
                       requirements["desired_gpu_keyword"].lower() in specs["gpu_model"].lower():
                       score += 0.05 # Bono si coincide con modelo deseado
            
            # 5. Rango de precios
            if product_price is not None:
                if requirements["min_price"] is not None and product_price < requirements["min_price"]:
                    score -= 0.20 # Penalizar si es muy barato/por debajo del mínimo
                if requirements["max_price"] is not None and product_price > requirements["max_price"]:
                    score -= 0.30 # Penalizar fuertemente si excede el presupuesto
                elif (requirements["min_price"] is None or product_price >= requirements["min_price"]) and \
                     (requirements["max_price"] is None or product_price <= requirements["max_price"]):
                    score += 0.10 # Bono por estar dentro del presupuesto

            # Asegurarse de que el score no sea negativo
            product_rec['score'] = max(0, score)
            scored_recommendations.append(product_rec)

        # Ordenar por puntuación (descendente) y luego por precio (ascendente)
        scored_recommendations.sort(key=lambda x: (x['score'], -x['details'].get('price', float('inf'))), reverse=True)

        # Limitar a las mejores recomendaciones
        final_recommendations = [
            rec for rec in scored_recommendations 
            if rec['score'] >= RECOMMENDATION_THRESHOLDS["min_score"] # Usa el umbral del config
        ][:RECOMMENDATION_THRESHOLDS["max_results_to_return"]]
        
        logging.info(f"Se encontraron {len(final_recommendations)} recomendaciones finales después de filtrar.")

        # Añadir la recomendación del experto de Gemini si hay resultados
        if final_recommendations:
            from nlp.gemini_recommender_assistant import get_gemini_expert_recommendation
            logging.info("Solicitando recomendación experta a Gemini...")
            gemini_advice = get_gemini_expert_recommendation(user_original_prompt, final_recommendations)
            
            # Añadir la recomendación de Gemini como el primer elemento si es relevante
            # O puedes añadirla como una propiedad especial de la lista de recomendaciones
            if gemini_advice:
                final_recommendations.insert(0, {
                    'category': 'Consejo de Experto',
                    'description': gemini_advice,
                    'details': {}, # No hay detalles de producto para el consejo
                    'score': 1.0 # Una puntuación alta para que aparezca primero
                })
        
        return final_recommendations


    def get_recommendations(self, user_original_prompt: str, translation_result: dict) -> list:
        logging.info(f"Solicitud del usuario original: '{user_original_prompt}'")

        # Paso 1: Usar el resultado de la traducción ya obtenido de app.py
        # translation_result ya contiene 'success', 'translated_text', 'error_message'
        if not translation_result['success']:
            logging.error(f"Error en la traducción: {translation_result['error_message']}")
            return [{'category': 'Error', 'description': 'No se pudo procesar tu solicitud debido a un problema de traducción.', 'details': {}}]
        
        translated_prompt = translation_result['translated_text']
        logging.info(f"Solicitud del usuario traducida (para NLP interno): '{translated_prompt}'")

        # Paso 2: Reconocer la intención y extraer entidades
        intent = recognize_intent(translated_prompt)
        entities = extract_entities(translated_prompt)
        
        # --- VERIFICACIÓN DE SEGURIDAD PARA ENTITIES ---
        if not isinstance(entities, dict):
            logging.error(f"extract_entities no devolvió un diccionario. Devolvió: {entities}. Asumiendo estructura vacía.")
            entities = {
                "purpose": [],
                "specs": {
                    "ram_gb": None,
                    "storage_gb": None,
                    "storage_type": None,
                    "cpu_brand": None,
                    "gpu_required": False,
                    "gpu_model": None
                },
                "budget": None,
                "modality": [],
                "min_price": None,
                "max_price": None
            }
        # ------------------------------------------------

        logging.info(f"Intención detectada: {intent}")
        logging.info(f"Entidades extraídas: {entities}")

        # Paso 3: Basado en la intención, llama a la función de recomendación apropiada
        if intent == "computadora":
            # Pasamos user_original_prompt para la recomendación experta de Gemini
            return self._recommend_computer(entities, user_original_prompt)
        else:
            return [{
                'category': 'Información',
                'description': 'Actualmente, solo puedo recomendar computadoras. ¿Hay algo más en lo que pueda ayudarte con laptops o PCs de escritorio?',
                'details': {}
            }]

# --- Bloque de prueba (solo para ejecución directa de este archivo) ---
if __name__ == '__main__':
    # Esto es solo para propósitos de prueba y requiere que las claves API de Gemini estén configuradas
    # en `nlp/entity_extractor.py` y `nlp/gemini_recommender_assistant.py`
    # y también el `nlp/translation_service.py`
    try:
        from nlp.gemini_recommender_assistant import configure_gemini_api_for_recommender
        from nlp.entity_extractor import configure_gemini_api_for_extractor
        from nlp.translator import configure_gemini_api_for_translation # Asumiendo que existe
        
        configure_gemini_api_for_recommender()
        configure_gemini_api_for_extractor()
        configure_gemini_api_for_translation() # Asegura que la traducción también esté configurada
        logging.info("APIs de Gemini configuradas para pruebas.")
    except Exception as e:
        logging.warning(f"No se pudieron configurar las APIs de Gemini para pruebas: {e}. Las pruebas pueden fallar.")

    engine = RecommendationEngine()

    prompts = [
        "Laptop para diseño gráfico, con al menos 32GB de RAM.",
        "Busco una computadora para gaming, que tenga una NVIDIA RTX.",
        "Necesito una laptop económica para estudiar.",
        "PC de escritorio para programación con 16GB de RAM y 512GB SSD.",
        "Quiero una laptop con un presupuesto de 1000 a 1500 dólares.",
        "Dime la mejor laptop para el trabajo, con un Intel Core i7.",
        "Busco una computadora potente y barata."
    ]

    for prompt in prompts:
        print(f"\n--- Procesando consulta: '{prompt}' ---")
        # Pasa el prompt completo a get_recommendations
        recommendations = engine.get_recommendations(prompt) 

        if recommendations:
            for rec in recommendations:
                print(f"Categoría: {rec.get('category')}")
                print(f"Descripción: {rec.get('description')}")
                if rec.get('details'):
                    details = rec['details']
                    print(f"    Nombre: {details.get('name')}")
                    print(f"    Precio: ${details.get('price', 'N/A'):.2f}")
                    print(f"    Tienda: {details.get('store')}")
                    print(f"    URL: {details.get('url')}")
                    # Para evitar errores si la descripción es muy larga
                    print(f"    Descripción detallada: {details.get('description', 'N/A')[:100]}...")
                    print(f"    Especificaciones: {details.get('specifications', 'N/A')}")
                    print(f"    Score: {rec.get('score', 'N/A'):.2f}" if 'score' in rec else "")
                else:
                    print("    No se encontraron detalles específicos (posiblemente un consejo de experto).")
        else:
            print("No se pudieron generar recomendaciones.")