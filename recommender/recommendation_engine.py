# recommender/recommendation_engine.py
import re
import json
import time
import random
import logging # Asegúrate de importar logging

# Configura el logger para ver mensajes de depuración
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Importa las funciones de NLP
from nlp.intent_recognizer import recognize_intent
from nlp.entity_extractor import extract_entities
from scrapers.la_ganga import LaGangaScraper
from scrapers.computron import ComputronScraper
from scrapers.novicompu import NovicompuScraper
from config import RECOMMENDATION_THRESHOLDS 

class RecommendationEngine:
    def __init__(self):
        self.scrapers = {
            "novicompu": NovicompuScraper(),
            #"computron": ComputronScraper(),
            #"la_ganga": LaGangaScraper(),
            
            # Agrega otros scrapers aquí
        }

    # --- NUEVA FUNCIÓN PARA GENERAR LA QUERY DE BÚSQUEDA ---
    def _generate_search_query(self, user_intent, extracted_entities):
        query_parts = []

        # 1. Identificar el tipo principal de producto
        if user_intent == "computadora":
            if "portatil" in extracted_entities.get("modality", []):
                query_parts.append("laptop")
            elif "escritorio" in extracted_entities.get("modality", []):
                query_parts.append("computadora escritorio") # Más específico que solo "pc"
            else:
                query_parts.append("laptop")
        elif user_intent == "memoria_ram":
            query_parts.append("memoria RAM")
        elif user_intent == "almacenamiento":
            query_parts.append("disco duro") # Genérico para almacenamiento

        # 2. Añadir especificaciones clave de forma concisa (solo para productos principales como laptops)
        if user_intent == "computadora":
            specs = extracted_entities.get("specs", {})

            if specs.get("ram_gb"):
                query_parts.append(f"{specs['ram_gb']}GB RAM") 

            if specs.get("storage_gb"):
                storage_type = specs.get("storage_type", "SSD").upper() # Predeterminar a SSD
                query_parts.append(f"{specs['storage_gb']}GB {storage_type}")

            # CPU Brand
            if specs.get("cpu_brand"):
                query_parts.append(specs['cpu_brand'])

            # GPU Model o indicación de GPU
            if specs.get("gpu_model"):
                query_parts.append(specs['gpu_model'])
            elif specs.get("gpu_required"): # Si solo se requiere GPU pero no se especificó modelo
                query_parts.append("tarjeta grafica") 

            # 3. Añadir palabras clave relacionadas con el propósito/uso, pero con precaución
            purpose_keywords = extracted_entities.get("purpose", [])
            if "diseño grafico" in purpose_keywords:
                query_parts.append("profesional") # "profesional" puede ser mejor que "diseño" solo
            elif "gaming" in purpose_keywords:
                query_parts.append("gamer")
            
        # Para RAM y Almacenamiento, también añadimos specs
        elif user_intent == "memoria_ram":
            specs = extracted_entities.get("specs", {})
            if specs.get("ram_gb"):
                query_parts.append(f"{specs['ram_gb']}GB")
        
        elif user_intent == "almacenamiento":
            specs = extracted_entities.get("specs", {})
            if specs.get("storage_type"):
                query_parts.append(specs["storage_type"].upper())
            if specs.get("storage_gb"):
                query_parts.append(f"{specs['storage_gb']}GB")


        # Unir las partes, eliminando duplicados y espacios extra.
        # Usamos un set para eliminar duplicados y luego volvemos a lista para preservar el orden inicial.
        # Ordenamos para asegurar que las palabras más importantes (ej. "laptop", "32GB RAM") aparezcan primero.
        # Esto es una heurística y puede ser afinado.
        unique_query_parts = []
        seen = set()
        for part in query_parts:
            if part not in seen:
                unique_query_parts.append(part)
                seen.add(part)
        
        # Opcional: ordenar las palabras clave de forma estratégica.
        # Por ahora, el orden de adición es suficientemente bueno.

        final_query = " ".join(unique_query_parts).strip()
        
        # Fallback si la query queda vacía o muy genérica
        if not final_query:
            if "portatil" in extracted_entities.get("modality", []):
                final_query = "laptop"
            else:
                final_query = "computadora"

        return final_query
    # --- FIN NUEVA FUNCIÓN ---

    def _extract_gpu_info(self, specifications, description=None):
        """
        Intenta extraer la información de la GPU de las especificaciones y opcionalmente de la descripción.
        """
        if not specifications:
            specifications = {} # Asegura que sea un diccionario para evitar errores si es None

        # Palabras clave comunes para GPU (puedes expandir esto)
        gpu_keywords = [
            "tarjeta gráfica", "gráficos", "gpu", "vídeo", "video",
            "nvidia", "geforce", "rtx", "gtx", "quadro",
            "amd", "radeon", "rx", "vega",
            "intel iris", "intel uhd", "intel hd graphics", "intel graphics", # Gráficos integrados
            "iris xe", "uhd graphics" # Simplificaciones o variantes
        ]

        # Busca en las claves y valores de las especificaciones
        for key, value in specifications.items():
            key_lower = key.lower()
            value_lower = str(value).lower() # Asegurarse de que el valor sea string

            for keyword in gpu_keywords:
                if keyword in key_lower or keyword in value_lower:
                    # Si la clave es específica de GPU, devuelve su valor
                    if any(k in key_lower for k in ["gráfic", "gpu", "video"]):
                        return value
                    # Si la palabra clave se encontró en el valor, devuelve el valor.
                    return value # Puedes refinar esto con regex para extraer el modelo

        # Si no se encontró en las especificaciones estructuradas, busca en la descripción
        if description:
            description_lower = str(description).lower()
            for keyword in gpu_keywords:
                if keyword in description_lower:
                    # Si se encuentra en la descripción, puedes devolver la palabra clave o el segmento.
                    # Para ser más útil, puedes intentar extraer el texto alrededor del keyword.
                    # Por simplicidad, devolvemos el keyword.
                    return f"Mención en descripción: {keyword}"
        
        return None # No se encontró información de GPU

    def _parse_cpu_info(self, cpu_string):
        """Intenta extraer el fabricante de la CPU (Intel/AMD) y el modelo."""
        if not cpu_string:
            return None, None
        cpu_lower = cpu_string.lower()
        if "intel" in cpu_lower:
            return "Intel", cpu_string
        elif "amd" in cpu_lower:
            return "AMD", cpu_string
        return None, cpu_string # Fabricante desconocido, pero devolvemos el string

    def _parse_ram_info(self, ram_string):
        """Intenta extraer la cantidad de RAM en GB."""
        if not ram_string:
            return None
        # Busca números seguidos de GB o G
        match = re.search(r'(\d+)\s*(?:gb|g)', str(ram_string).lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def _parse_storage_info(self, storage_string):
        """Intenta extraer la cantidad de almacenamiento en GB/TB y el tipo."""
        if not storage_string:
            return None, None # cant_gb, type

        storage_lower = str(storage_string).lower()
        
        cant_gb = None
        # Busca TB y convierte a GB
        tb_match = re.search(r'(\d+)\s*tb', storage_lower)
        if tb_match:
            try:
                cant_gb = int(tb_match.group(1)) * 1024
            except ValueError:
                pass
        
        # Busca GB
        if not cant_gb: # Si no se encontró en TB, busca en GB
            gb_match = re.search(r'(\d+)\s*(?:gb|g)', storage_lower)
            if gb_match:
                try:
                    cant_gb = int(gb_match.group(1))
                except ValueError:
                    pass

        storage_type = None
        if "ssd" in storage_lower:
            storage_type = "SSD"
        elif "hdd" in storage_lower or "disco duro" in storage_lower:
            storage_type = "HDD"
        elif "nvme" in storage_lower:
            storage_type = "NVMe SSD" # Más específico

        return cant_gb, storage_type

    def _score_product(self, product_details, user_requirements):
        """
        Calcula un puntaje para un producto basado en los requisitos del usuario.
        """
        score = 0
        weights = user_requirements.get("weights", {
            "price": 0.25,
            "ram": 0.2,
            "cpu": 0.2,
            "gpu": 0.2,
            "storage": 0.15
        })

        # Asegurarse de que los campos existan y sean del tipo correcto
        # Aquí es crucial el manejo de errores si 'price' no es numérico o si falta
        price = float(product_details.get('price')) if product_details.get('price') is not None else 999999
        specs = product_details.get('specifications', {})
        description = product_details.get('description', '') 

        logging.debug(f"Puntuando producto: '{product_details.get('name', 'N/A')}' de {product_details.get('store', 'N/A')}")
        logging.debug(f"  URL: {product_details.get('url', 'N/A')}")
        logging.debug(f"  Precio del producto: {price}")
        logging.debug(f"  Specs extraídas del scraper: {specs}")
        logging.debug(f"  Requisitos del usuario: {user_requirements}")

        # Criterio 1: Precio
        max_price = user_requirements.get("max_price")
        if max_price is not None:
            if price == 999999 or price > max_price: # También considera si el precio es el valor por defecto
                logging.debug(f"  Producto {product_details['name']} (Precio: {price}) DESCARTADO: Excede el precio máximo ({max_price}) o precio no disponible.")
                return -1 # Descartar si excede el precio máximo o si el precio no se pudo parsear
            price_score = 1 - (price / max_price) if max_price > 0 else 0
            score += price_score * weights.get("price", 0)
            logging.debug(f"  Score Precio (max {max_price}): {price_score * weights.get('price', 0)}")
        elif price != 999999: # Si no hay precio maximo definido, pero el producto tiene precio real
            # Heurística para preferir precios más bajos si no hay máximo definido
            # Normalizar en un rango esperado, ej. hasta 2000
            price_normalized = min(price, 2000) / 2000 
            score += (1 - price_normalized) * weights.get("price", 0) 
            logging.debug(f"  Score Precio (sin max): {(1 - price_normalized) * weights.get('price', 0)}")

        # Criterio 2: RAM
        # Ahora, las specs ya vienen parseadas del scraper
        product_ram_gb = specs.get('ram_gb')
        
        min_ram_gb = user_requirements.get("min_ram_gb")
        if min_ram_gb is not None and min_ram_gb > 0: # Solo si hay un requisito de RAM mínimo
            if product_ram_gb is None or product_ram_gb < min_ram_gb:
                logging.debug(f"  Producto {product_details['name']} (RAM: {product_ram_gb}) DESCARTADO: No cumple con RAM mínima requerida ({min_ram_gb}).")
                return -1 # Descartar si no cumple con RAM mínima
            ram_score = (product_ram_gb / min_ram_gb) if min_ram_gb > 0 else 1
            score += min(ram_score, 1.0) * weights.get("ram", 0) # Normalizar a 1 si es mucho más
            logging.debug(f"  Score RAM ({product_ram_gb} vs {min_ram_gb}): {min(ram_score, 1.0) * weights.get('ram', 0)}")
        elif product_ram_gb: # Si no hay requisito mínimo pero el producto tiene RAM
            score += (product_ram_gb / 32) * weights.get("ram", 0) # Pequeño bonus, normalizar a un valor alto esperado, ej. 32GB

        # Criterio 3: CPU
        product_cpu_model = specs.get('cpu_model')
        cpu_brand_req = user_requirements.get("cpu_brand")

        if cpu_brand_req:
            # Revisa si la marca requerida está en el modelo del producto
            if product_cpu_model and cpu_brand_req.lower() in product_cpu_model.lower():
                score += 1 * weights.get("cpu", 0)
                logging.debug(f"  Score CPU (marca '{cpu_brand_req}' en '{product_cpu_model}'): {1 * weights.get('cpu', 0)}")
            else:
                logging.debug(f"  Producto {product_details['name']} (CPU: {product_cpu_model}) DESCARTADO: No coincide con marca de CPU requerida ({cpu_brand_req}).")
                return -1
        elif product_cpu_model: # Si no se requiere marca específica pero hay CPU
             score += 0.5 * weights.get("cpu", 0) # Pequeño bonus por tener CPU
             logging.debug(f"  Score CPU (generico, '{product_cpu_model}'): {0.5 * weights.get('cpu', 0)}")


        # Criterio 4: GPU
        product_gpu_model = specs.get('gpu_model')
        gpu_present = bool(product_gpu_model)

        gpu_required = user_requirements.get("gpu_required")
        if gpu_required is True and not gpu_present:
            logging.debug(f"  Producto {product_details['name']} DESCARTADO: Se requiere GPU dedicada y no se encontró.")
            return -1 # Descartar si se requiere GPU y no se encontró
        
        if gpu_present:
            # Si hay una GPU deseada específica, podemos dar más puntaje por coincidencia
            desired_gpu_keyword = user_requirements.get("desired_gpu_keyword")
            if desired_gpu_keyword and desired_gpu_keyword.lower() in str(product_gpu_model).lower():
                score += 2 * weights.get("gpu", 0) # Doble puntaje por coincidencia fuerte
                logging.debug(f"  Score GPU (coincidencia '{desired_gpu_keyword}' en '{product_gpu_model}'): {2 * weights.get('gpu', 0)}")
            else:
                score += 1 * weights.get("gpu", 0) # Puntaje base por tener GPU
                logging.debug(f"  Score GPU (presente, '{product_gpu_model}'): {1 * weights.get('gpu', 0)}")

        # Criterio 5: Almacenamiento (Storage)
        product_storage_gb = specs.get('storage_gb')
        product_storage_type = specs.get('storage_type')
        
        min_storage_gb = user_requirements.get("min_storage_gb")
        if min_storage_gb is not None and min_storage_gb > 0:
            if product_storage_gb is None or product_storage_gb < min_storage_gb:
                logging.debug(f"  Producto {product_details['name']} (Almacenamiento: {product_storage_gb}) DESCARTADO: No cumple con almacenamiento mínimo ({min_storage_gb}).")
                return -1 # Descartar si no cumple con almacenamiento mínimo
            storage_score = (product_storage_gb / min_storage_gb) if min_storage_gb > 0 else 1
            score += min(storage_score, 1.0) * weights.get("storage", 0)
            logging.debug(f"  Score Almacenamiento ({product_storage_gb} vs {min_storage_gb}): {min(storage_score, 1.0) * weights.get('storage', 0)}")
        elif product_storage_gb:
            score += (product_storage_gb / 1024) * weights.get("storage", 0) # Normalizar a 1TB

        # Criterio 6: Tienda preferida
        if user_requirements.get("prefer_store") and product_details.get("store") == user_requirements["prefer_store"]:
            score += 0.05 # Pequeño bonus por tienda preferida
            logging.debug(f"  Score Bonus Tienda Preferida: 0.05")

        logging.debug(f"  Producto {product_details['name']} (Computron): Score final: {score}")
        return score

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

    def _recommend_computer(self, entities, original_prompt): # Añadir original_prompt
        purpose = entities.get("purpose", [])
        specs_req = entities.get("specs", {}) # Renombrado para no confundir con specs del producto
        budget_str = entities.get("budget")
        modality = entities.get("modality", [])

        # --- POST-PROCESAMIENTO DE ENTIDADES (Asegurar inferencias importantes) ---
        # Si es para diseño gráfico o gaming, se asume GPU necesaria si no se especifica lo contrario
        if ("diseño grafico" in purpose or "gaming" in purpose) and specs_req.get("gpu_required") is None:
            specs_req["gpu_required"] = True
            entities["specs"]["gpu_required"] = True # Actualizar las entidades originales si es necesario

        # Mapeo de entidades a requisitos de usuario
        user_requirements = {}

        # Presupuesto
        max_price = None
        if budget_str == "bajo":
            max_price = RECOMMENDATION_THRESHOLDS["low_budget_max_price"]
        elif budget_str == "medio":
            max_price = RECOMMENDATION_THRESHOLDS["medium_budget_max_price"]
        elif budget_str == "alto":
            max_price = RECOMMENDATION_THRESHOLDS["high_budget_max_price"]
        if max_price:
            user_requirements["max_price"] = max_price

        # Propósito y especificaciones
        user_requirements["min_ram_gb"] = specs_req.get("ram_gb") or 0
        user_requirements["min_storage_gb"] = specs_req.get("storage_gb") or 0
        user_requirements["cpu_brand"] = specs_req.get("cpu_brand")
        user_requirements["gpu_required"] = specs_req.get("gpu_required") # Asumimos True/False directamente de extract_entities
        user_requirements["desired_gpu_keyword"] = specs_req.get("gpu_model")

        # Ajustes basados en propósito (sobrescribe o añade a specs_req)
        if "gaming" in purpose:
            user_requirements["gpu_required"] = True
            if not user_requirements.get("desired_gpu_keyword") and budget_str == "alto":
                user_requirements["desired_gpu_keyword"] = RECOMMENDATION_THRESHOLDS["gaming_gpu_min"]
            user_requirements["min_ram_gb"] = max(user_requirements.get("min_ram_gb", 0), RECOMMENDATION_THRESHOLDS["gaming_ram_min_gb"])
            user_requirements["min_storage_gb"] = max(user_requirements.get("min_storage_gb", 0), RECOMMENDATION_THRESHOLDS["gaming_storage_min_gb"])
            user_requirements["weights"] = {"price": 0.15, "ram": 0.15, "cpu": 0.2, "gpu": 0.4, "storage": 0.1} # Más peso a GPU
        elif "diseño" in purpose or "diseño grafico" in purpose: # Asegurarse de capturar "diseño grafico"
            user_requirements["min_ram_gb"] = max(user_requirements.get("min_ram_gb", 0), RECOMMENDATION_THRESHOLDS["design_ram_min_gb"])
            user_requirements["min_storage_gb"] = max(user_requirements.get("min_storage_gb", 0), RECOMMENDATION_THRESHOLDS["design_storage_min_gb"])
            user_requirements["gpu_required"] = user_requirements.get("gpu_required", True) # Asumir GPU si no se dijo lo contrario
            user_requirements["weights"] = {"price": 0.2, "ram": 0.3, "cpu": 0.25, "gpu": 0.15, "storage": 0.1}
        elif "estudio" in purpose or "oficina" in purpose:
            user_requirements["min_ram_gb"] = max(user_requirements.get("min_ram_gb", 0), RECOMMENDATION_THRESHOLDS["office_ram_min_gb"])
            user_requirements["min_storage_gb"] = max(user_requirements.get("min_storage_gb", 0), RECOMMENDATION_THRESHOLDS["office_storage_min_gb"])
            user_requirements["gpu_required"] = False # No requiere GPU dedicada
            user_requirements["weights"] = {"price": 0.4, "ram": 0.2, "cpu": 0.2, "gpu": 0.05, "storage": 0.15} # Menos peso a GPU


        # --- USAR LA NUEVA FUNCIÓN PARA GENERAR LA CONSULTA DE BÚSQUEDA ---
        search_query = self._generate_search_query("computadora", entities)
        logging.info(f"Buscando computadoras con la query: '{search_query}' y requisitos: {user_requirements}")
        # --- FIN DE USO DE LA NUEVA FUNCIÓN ---

        print(f"Buscando computadoras con la query: '{search_query}' y requisitos: {user_requirements}")

        all_detailed_products = []
        for store_name, scraper_instance in self.scrapers.items():
            logging.info(f"Scraping en {store_name} para '{search_query}'...")
            search_results = scraper_instance.search_products(search_query) 
            
            if search_results:
                for i, item_from_list in enumerate(search_results):
                    # Aquí puedes añadir un log para ver si los productos de Computron están siendo obtenidos en la lista de búsqueda
                    logging.debug(f"    Item listado {i+1}/{len(search_results)} de {store_name}: {item_from_list['name']} ({item_from_list['url']})")

                    if item_from_list['url'] and item_from_list['url'] != '#':
                        detailed_product = scraper_instance.parse_product_page(item_from_list['url'])
                        if detailed_product:
                            all_detailed_products.append(detailed_product)
                        time.sleep(random.uniform(0.5, 1.5)) # Ajusta la pausa si es necesario
                    else:
                        logging.warning(f"    Advertencia: URL de detalle no válida para '{item_from_list['name']}'. Se omite.")
            else:
                logging.info(f"    No se encontraron resultados para '{search_query}' en {store_name}.")
        
        logging.info(f"Total de productos detallados recopilados de todas las tiendas: {len(all_detailed_products)}")
        
        scored_products = []
        for product in all_detailed_products:
            score = self._score_product(product, user_requirements)
            if score >= 0: # Solo incluir productos que no fueron descartados
                scored_products.append({'product': product, 'score': score})

        scored_products.sort(key=lambda x: x['score'], reverse=True)
        
        # Devolver las mejores 10 recomendaciones (o las que existan)
        top_recommendations = []
        if scored_products:
            for rec in scored_products[:10]: # Mostrar los top 10
                top_recommendations.append({
                    'category': 'Computadora',
                    'description': f"Una excelente opción para tu necesidad: {rec['product']['name']} ({rec['product'].get('store', 'N/A')})",
                    'details': rec['product'],
                    'score': rec['score'] 
                })
        else:
            top_recommendations.append({
                'category': 'Computadora',
                'description': 'No se encontraron computadoras que cumplan con los criterios en las tiendas.',
                'details': {}
            })
        
        # Log final de las recomendaciones antes de devolverlas
        logging.info("--- Recomendaciones finales generadas por _recommend_computer ---")
        for rec in top_recommendations:
            logging.info(f"  Categoría: {rec['category']}, Descripción: {rec['description']}, Score: {rec.get('score', 'N/A')}")
            logging.debug(f"  Detalles completos: {json.dumps(rec['details'], indent=2)}") # Log de detalles completos

        return top_recommendations

    def _recommend_ram(self, entities, original_prompt): # Añadir original_prompt
        specs = entities["specs"]
        ram_gb_req = specs.get("ram_gb")
        
        # --- USAR LA NUEVA FUNCIÓN PARA GENERAR LA CONSULTA DE BÚSQUEDA ---
        search_query = self._generate_search_query("memoria_ram", entities)
        # --- FIN DE USO DE LA NUEVA FUNCIÓN ---

        print(f"Buscando RAM con la query: '{search_query}'")
        
        all_products = []
        for store_name, scraper_instance in self.scrapers.items():
            print(f"Scraping en {store_name} para '{search_query}'...")
            search_results = scraper_instance.search_products(search_query)
            if search_results:
                # Aquí, para RAM, puedes querer los detalles completos también
                for i, item_from_list in enumerate(search_results):
                    # Pausa importante aquí también
                    time.sleep(random.uniform(1, 2))
                    detailed_product = scraper_instance.parse_product_page(item_from_list['url'])
                    if detailed_product:
                        all_products.append(detailed_product)
                    

        # Puedes adaptar _score_product para RAM o hacer una lógica de filtrado simple
        filtered_products = []
        for prod in all_products:
            prod_ram_gb = self._parse_ram_info(prod.get('specifications', {}).get('Memoria RAM', prod.get('specifications', {}).get('RAM', '')))
            if ram_gb_req and prod_ram_gb and prod_ram_gb >= ram_gb_req:
                filtered_products.append(prod)
            elif not ram_gb_req: # Si no hay requisito de GB, cualquier RAM sirve
                filtered_products.append(prod)
        
        # Ordenar por precio para accesorios
        filtered_products.sort(key=lambda x: x.get('price', float('inf')))

        if not filtered_products:
            return [{
                'category': 'Memoria RAM',
                'description': 'No se encontraron módulos de RAM que cumplan con los criterios.',
                'details': {}
            }]
        
        top_recommendations = []
        for prod in filtered_products[:10]:
            top_recommendations.append({
                'category': 'Memoria RAM',
                'description': f"Considera este módulo de RAM: {prod['name']}",
                'details': prod
            })
        return top_recommendations

    def _recommend_storage(self, entities, original_prompt): # Añadir original_prompt
        specs = entities["specs"]
        storage_gb_req = specs.get("storage_gb")
        storage_type_req = specs.get("storage_type")

        # --- USAR LA NUEVA FUNCIÓN PARA GENERAR LA CONSULTA DE BÚSQUEDA ---
        search_query = self._generate_search_query("almacenamiento", entities)
        # --- FIN DE USO DE LA NUEVA FUNCIÓN ---

        print(f"Buscando almacenamiento con la query: '{search_query}'")

        all_products = []
        for store_name, scraper_instance in self.scrapers.items():
            print(f"Scraping en {store_name} para '{search_query}'...")
            search_results = scraper_instance.search_products(search_query)
            if search_results:
                # Aquí, para Almacenamiento, también necesitas los detalles completos
                for i, item_from_list in enumerate(search_results):
                    # Pausa importante aquí también
                    time.sleep(random.uniform(1, 2))
                    detailed_product = scraper_instance.parse_product_page(item_from_list['url'])
                    if detailed_product:
                        all_products.append(detailed_product)


        filtered_products = []
        for prod in all_products:
            prod_storage_gb, prod_storage_type = self._parse_storage_info(prod.get('specifications', {}).get('Almacenamiento', prod.get('specifications', {}).get('Disco Duro', prod.get('specifications', {}).get('SSD', ''))))
            
            meets_gb = True
            if storage_gb_req and (prod_storage_gb is None or prod_storage_gb < storage_gb_req):
                meets_gb = False
            
            meets_type = True
            if storage_type_req and prod_storage_type and storage_type_req.lower() not in prod_storage_type.lower():
                meets_type = False
            
            if meets_gb and meets_type:
                filtered_products.append(prod)
        
        filtered_products.sort(key=lambda x: x.get('price', float('inf')))

        if not filtered_products:
            return [{
                'category': 'Almacenamiento',
                'description': 'No se encontraron opciones de almacenamiento.',
                'details': {}
            }]
        
        top_recommendations = []
        for prod in filtered_products[:10]:
            top_recommendations.append({
                'category': 'Almacenamiento',
                'description': f"Una buena opción de almacenamiento: {prod['name']}",
                'details': prod
            })
        return top_recommendations

# Para probar directamente el RecommendationEngine
if __name__ == '__main__':
    # Este es solo un ejemplo de cómo se usaría en tu aplicación principal
    # Las funciones recognize_intent y extract_entities deben existir y funcionar
    # para que esto tenga sentido.

    # Simular funciones NLP (debes tenerlas implementadas en nlp/intent_recognizer.py y nlp/entity_extractor.py)
    # y que devuelvan el formato esperado por RecommendationEngine.

    # Ejemplo de cómo podrían ser (si no las tienes completas aún):
    def mock_recognize_intent(prompt):
        if "computadora" in prompt.lower() or "laptop" in prompt.lower() or "pc" in prompt.lower():
            return "computadora"
        elif "ram" in prompt.lower() or "memoria" in prompt.lower():
            return "memoria_ram"
        elif "disco" in prompt.lower() or "almacenamiento" in prompt.lower() or "ssd" in prompt.lower() or "hdd" in prompt.lower():
            return "almacenamiento"
        return "desconocido"

    def mock_extract_entities(prompt):
        entities = {
            "purpose": [], # gaming, diseño, estudio, oficina
            "specs": {
                "ram_gb": None,
                "storage_gb": None,
                "storage_type": None, # SSD, HDD
                "cpu_brand": None, # Intel, AMD
                "gpu_required": None, # True, False
                "gpu_model": None # Ej. RTX 3060
            },
            "budget": None, # bajo, medio, alto
            "modality": [] # portatil, escritorio
        }
        
        # Lógica muy básica para extraer entidades (sustituye por tu NLP real)
        prompt_lower = prompt.lower()
        if "gaming" in prompt_lower or "juegos" in prompt_lower:
            entities["purpose"].append("gaming")
            entities["specs"]["gpu_required"] = True
        # Asegúrate de que "diseño grafico" se capture como un solo propósito
        elif "diseño grafico" in prompt_lower: 
            entities["purpose"].append("diseño grafico") # Cambiado de "diseño" a "diseño grafico"
            entities["specs"]["gpu_required"] = True # Inferir GPU para diseño
        elif "estudio" in prompt_lower or "oficina" in prompt_lower:
            entities["purpose"].append("estudio")
            entities["specs"]["gpu_required"] = False # No requiere GPU dedicada por defecto

        if "portatil" in prompt_lower or "laptop" in prompt_lower:
            entities["modality"].append("portatil")
        elif "escritorio" in prompt_lower or "pc" in prompt_lower:
            entities["modality"].append("escritorio")

        # RAM
        ram_match = re.search(r'(\d+)\s*(?:gb|g)\s*(?:de)?\s*ram', prompt_lower)
        if ram_match:
            entities["specs"]["ram_gb"] = int(ram_match.group(1))

        # Almacenamiento
        # Mejorar la extracción de almacenamiento para que no capture RAM
        storage_match = re.search(r'(\d+)\s*(?:gb|g)(?=\s*(ssd|hdd|nvme|m\.2|tb|disco|solido))', prompt_lower)
        if storage_match:
            amount = int(storage_match.group(1))
            unit = storage_match.group(2)
            if unit.lower() == 'tb':
                entities["specs"]["storage_gb"] = amount * 1024 # Convertir TB a GB
            else:
                entities["specs"]["storage_gb"] = amount
            
        if "ssd" in prompt_lower:
            entities["specs"]["storage_type"] = "SSD"
        elif "hdd" in prompt_lower or "disco duro" in prompt_lower:
            entities["specs"]["storage_type"] = "HDD"
        elif "nvme" in prompt_lower:
            entities["specs"]["storage_type"] = "NVMe SSD"


        # CPU Brand (ej. "intel i5", "amd ryzen")
        if "intel" in prompt_lower:
            entities["specs"]["cpu_brand"] = "Intel"
        elif "amd" in prompt_lower:
            entities["specs"]["cpu_brand"] = "AMD"

        # GPU Model (ej. "rtx 3060", "gtx 1650")
        gpu_model_match = re.search(r'(rtx\s*\d{3,4}(?:[a-z]{0,2})?|gtx\s*\d{3,4}(?:[a-z]{0,2})?|radeon\s*rx\s*\d{3,4}|intel\s*iris\s*xe|uhd\s*graphics)', prompt_lower)
        if gpu_model_match:
            entities["specs"]["gpu_model"] = gpu_model_match.group(0).strip().upper()
            entities["specs"]["gpu_required"] = True # Si se menciona un modelo, se asume que se requiere

        # Presupuesto
        if "barato" in prompt_lower or "económico" in prompt_lower or "bajo presupuesto" in prompt_lower:
            entities["budget"] = "bajo"
        elif "medio" in prompt_lower or "presupuesto medio" in prompt_lower:
            entities["budget"] = "medio"
        elif "caro" in prompt_lower or "alto presupuesto" in prompt_lower:
            entities["budget"] = "alto"

        return entities

    # Guarda las funciones originales de nlp
    original_recognize_intent = recognize_intent
    original_extract_entities = extract_entities

    # Sobreescribir las funciones reales con los mocks para la prueba local del engine
    # Esto SOLO afecta el bloque if __name__ == '__main__':
    recognize_intent = mock_recognize_intent
    extract_entities = mock_extract_entities


    engine = RecommendationEngine()

    # Pruebas con prompts de usuario
    prompts = [
        "Quiero una laptop gaming con 16GB de RAM y una RTX 3060, con presupuesto medio.",
        "Necesito una computadora para oficina, algo básico y económico.",
        "Recomiéndame una memoria RAM de 8GB.",
        "Busco un disco duro SSD de 500GB.",
        "Laptop para diseño gráfico, con al menos 32GB de RAM."
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
                    print("    No se encontraron detalles específicos.")
        else:
            print("No se pudieron generar recomendaciones.")

    # Restaura las funciones originales de nlp después de la prueba
    recognize_intent = original_recognize_intent
    extract_entities = original_extract_entities