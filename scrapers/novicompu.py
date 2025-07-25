# scrapers/novicompu.py

from scrapers.base_scrapers import BaseScraper
from bs4 import BeautifulSoup
import re
import logging
from config import STORE_SELECTORS
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException # Importa NoSuchElementException

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class NovicompuScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url=STORE_SELECTORS["novicompu"]["base_url"],
                         selectors=STORE_SELECTORS["novicompu"])
        self.store_name = "Novicompu"
        self.currency_pattern = re.compile(r'[^\\d.,]+') # Re-inicializar para scraper específico si es necesario

    # El método _clean_price de BaseScraper debería ser suficiente.
    # Si Novicompu tiene un formato de precio muy único, puede ser sobrescrito aquí.

    def search_products(self, query):
        search_url = self.selectors["search_url_format"].format(query.replace(' ', '%20'), query.replace(' ', '+'))
        logging.info(f"[{self.store_name}] Buscando productos en: {search_url}")

        # Usar Selenium para obtener la página y esperar a que el enlace principal del producto cargue
        soup = self._fetch_page(search_url,
                                use_selenium=True,
                                wait_for_selector=self.selectors["wait_for_listing_product_card"])

        products_data = []
        if soup:
            # Seleccionar los enlaces principales de los productos (etiquetas a)
            product_links = soup.select(self.selectors["listing_product_link_card"])
            logging.info(f"[{self.store_name}] Encontrados {len(product_links)} enlaces de productos.")

            if not product_links:
                logging.info(f"No se encontraron productos para la búsqueda '{query}' en Novicompu.")
                # Comprobar mensajes de 404 o "producto no encontrado"
                if "404" in soup.get_text() or "producto no encontrado" in soup.get_text().lower():
                    logging.warning(f"La página de búsqueda de Novicompu para '{query}' devolvió un error 404 o producto no encontrado.")
                return []

            for link_element in product_links:
                name = None
                product_url = None
                image_url = None
                price = None
                
                # Obtener la URL del producto directamente del atributo href del <a>
                product_url = link_element.get('href')
                if product_url and product_url.startswith('/'):
                    product_url = self.base_url + product_url

                # Al estar el <article> dentro del <a>, usamos eso para seguir extrayendo datos
                article_element = link_element.select_one("article.vtex-product-summary-2-x-element")

                if article_element:
                    # Nombre
                    name_element = article_element.select_one("div.vtex-product-summary-2-x-nameContainer, h1.vtex-store-components-3-x-productNameContainer")
                    if name_element:
                        name = name_element.get_text(strip=True)

                    # Imagen
                    image_element = article_element.select_one("img.vtex-product-summary-2-x-image")
                    if image_element:
                        image_url = image_element.get("src") or image_element.get("data-src")

                    # Precio
                    price_element = article_element.select_one("span.vtex-product-price-1-x-sellingPrice")
                    if price_element:
                        price_text = price_element.get_text(strip=True)
                        price = self._clean_price(price_text)

                if name and product_url and price is not None: # Asegurarse de que la información básica esté presente
                    products_data.append({
                        'name': name,
                        'url': product_url,
                        'image_url': image_url,
                        'price': price,
                        'store': self.store_name
                    })
                else:
                    logging.debug(f"[{self.store_name}] Producto incompleto detectado y omitido en listado: Nombre='{name}', URL='{product_url}', Precio='{price}'")
        else:
            logging.error(f"No se pudo obtener la página de búsqueda para {query} en {self.store_name}.")
        
        logging.info(f"[{self.store_name}] Productos encontrados en la búsqueda de {self.store_name}: {len(products_data)}")
        return products_data

    def parse_product_page(self, product_url):
        logging.info(f"[{self.store_name}] Parseando página de producto: {product_url}")
        
        # Esperamos por el nombre del producto en la página de detalle
        # Usar un tiempo de espera más largo para la carga inicial de la página si es necesario, pero 30s suele ser suficiente.
        soup = self._fetch_page(product_url,
                                use_selenium=True,
                                wait_for_selector=self.selectors["wait_for_product_name"])
        
        product_details = {}
        if soup:
            # Nombre del producto
            name_element = soup.select_one(self.selectors["product_name"])
            if name_element:
                product_details['name'] = name_element.get_text(strip=True)
            else:
                logging.warning(f"Nombre del producto no encontrado para {product_url} en {self.store_name}")
                product_details['name'] = "N/A"

            # --- Extracción y espera del Precio (Enfoque robusto) ---
            price = None
            if self.driver: # Asegurarse de que el driver de Selenium esté inicializado
                try:
                    # Esperar a que el contenedor del precio sea visible
                    logging.info(f"[{self.store_name}] Esperando que el contenedor del precio sea visible con selector: {self.selectors['wait_for_product_price']}")
                    WebDriverWait(self.driver, 3).until( # Tiempo de espera más corto para visibilidad
                        EC.visibility_of_element_located((By.CSS_SELECTOR, self.selectors["wait_for_product_price"]))
                    )

                    # Definir una función de condición personalizada para WebDriverWait para verificar texto de precio válido
                    def price_has_valid_text(driver_instance):
                        try:
                            # Obtener el elemento que contiene el precio
                            # Usar el mismo selector que wait_for_product_price para consistencia
                            price_container_element = driver_instance.find_element(By.CSS_SELECTOR, self.selectors["product_price"])
                            
                            # Obtener su outerHTML para un parseo robusto con BeautifulSoup
                            outer_html_price = price_container_element.get_attribute('outerHTML')
                            soup_price = BeautifulSoup(outer_html_price, 'html.parser')
                            
                            # Extraer el texto del objeto BeautifulSoup. Esto maneja mejor los spans/divs anidados.
                            text = soup_price.get_text(strip=True)
                            
                            logging.debug(f"## DEBUG PRICE CHECK ({self.store_name}) - Selector de precio (contenedor): '{self.selectors['product_price']}'")
                            logging.debug(f"## DEBUG PRICE CHECK ({self.store_name}) - outerHTML del contenedor de precio: {outer_html_price}")
                            logging.debug(f"## DEBUG PRICE CHECK ({self.store_name}) - Texto extraído de BeautifulSoup (contenedor): '{text}'")
                            
                            cleaned_price_value = self._clean_price(text)
                            
                            logging.debug(f"## DEBUG PRICE CHECK ({self.store_name}) - Valor de precio limpio: {cleaned_price_value}")
                            
                            # Retornar True solo si el precio limpio es un número positivo válido
                            return cleaned_price_value is not None and cleaned_price_value > 0.0
                        except NoSuchElementException:
                            logging.debug(f"Elemento de precio no encontrado con selector: {self.selectors['product_price']}")
                            return False # El elemento aún no se encuentra
                        except Exception as e:
                            logging.debug(f"Excepción durante la verificación de price_has_valid_text ({self.store_name}): {e}")
                            return False

                    # Espera principal para que el precio se cargue y sea válido
                    logging.info(f"[{self.store_name}] Esperando que el precio tenga un valor válido...")
                    WebDriverWait(self.driver, 3).until(price_has_valid_text) # Tiempo de espera más largo para el valor del precio
                    
                    # Una vez que la condición se cumple, obtener el texto final del precio del elemento web
                    final_price_element = self.driver.find_element(By.CSS_SELECTOR, self.selectors["product_price"])
                    price_text_final = final_price_element.text.strip()
                    price = self._clean_price(price_text_final)
                    logging.info(f"[{self.store_name}] Precio encontrado y válido. Texto crudo: '{price_text_final}', Limpio: {price}")

                except TimeoutException as e:
                    logging.warning(f"[{self.store_name}] Tiempo de espera agotado para el elemento de precio o valor válido para {product_url}: {e}")
                    price = None # Dejar el precio como None si hay tiempo de espera agotado
                except Exception as e:
                    logging.error(f"[{self.store_name}] Error al extraer el precio para {product_url}: {e}", exc_info=True)
                    price = None # Dejar el precio como None en caso de otros errores

            product_details['price'] = price
            
            # Imagen del producto
            image_element = soup.select_one(self.selectors["product_image"])
            if image_element:
                product_details['image_url'] = image_element.get('src') or image_element.get('data-src')

            # Descripción
            description_container = soup.select_one(self.selectors["product_description_container"])
            if description_container:
                paragraphs = description_container.select(self.selectors["product_description_text"])
                if paragraphs:
                    description_text = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    product_details['description'] = description_text
                else:
                    product_details['description'] = description_container.get_text(strip=True)
            else:
                logging.debug(f"[{self.store_name}] Contenedor de descripción no encontrado para {product_url}.")
            
            # Extraer especificaciones usando _extract_specs_from_text (más general)
            # o _extract_specs si hay una tabla clara.
            # Para Novicompu, _extract_specs_from_text podría ser más fiable dado el contenido dinámico de VTEX.
            product_details['specifications'] = self._extract_specifications(soup)


            product_details['url'] = product_url
            product_details['store'] = self.store_name
        else:
            logging.error(f"[{self.store_name}] No se pudo obtener la página de detalle para {product_url}.")
        
        logging.debug(f"[{self.store_name}] Detalles del producto parseados: {product_details}")
        print(f"## DEBUG PRINT: _extract_specifications - Final specs: {product_details.get('specifications', {})}")
        return product_details

    def _extract_specifications(self, soup):
        specs = {
            'ram_gb': None,
            'storage_gb': None,
            'storage_type': None,
            'cpu_brand': None,
            'cpu_model': None,
            'gpu_model': None,
            'gpu_required': False
        }

        # Extraer solo el texto de la sección descripción para evitar ruido
        description_container = soup.select_one(self.selectors.get("product_description_container", ""))
        if description_container:
            full_text = description_container.get_text(separator=' ', strip=True)
        else:
            # Fallback a todo el texto visible
            full_text = soup.get_text(separator=' ', strip=True)

        # --- RAM ---
        ram_match = re.search(
            r'Memoria\s*ram\s*[:\-]?\s*(\d+)\s*GB', full_text, re.IGNORECASE)
        if not ram_match:
            # Intento alternativo solo número + GB + RAM
            ram_match = re.search(r'(\d+)\s*GB\s*ram', full_text, re.IGNORECASE)

        if ram_match:
            specs['ram_gb'] = int(ram_match.group(1))
        
        # --- Almacenamiento ---
        # Se aceptan formatos tipo "Almacenamiento 256GB SSD", "Almacenamiento: SSD de 256GB", "Almacenamiento 1Tb"
        storage_match = re.search(
            r'Almacenamiento[:\s]*((SSD|HDD)\s*(de)?\s*(\d+)\s*(TB|GB))', full_text, re.IGNORECASE)
        if storage_match:
            storage_str = storage_match.group(1)
            # Extraer número y unidad
            value_match = re.search(r'(\d+)', storage_str)
            unit_match = re.search(r'(TB|GB)', storage_str, re.IGNORECASE)
            type_match = re.search(r'(SSD|HDD)', storage_str, re.IGNORECASE)

            if value_match and unit_match and type_match:
                value = int(value_match.group(1))
                unit = unit_match.group(1).upper()
                storage_type = type_match.group(1).upper()

                if unit == 'TB':
                    specs['storage_gb'] = value * 1024
                else:
                    specs['storage_gb'] = value
                specs['storage_type'] = storage_type
        else:
            # Alternativa: "Almacenamiento 1Tb"
            alt_storage_match = re.search(
                r'Almacenamiento[:\s]*([\d]+)\s*(TB|GB)', full_text, re.IGNORECASE)
            if alt_storage_match:
                value = int(alt_storage_match.group(1))
                unit = alt_storage_match.group(2).upper()
                specs['storage_type'] = None
                specs['storage_gb'] = value * 1024 if unit == 'TB' else value

        # --- CPU ---
        # Extraer procesador, buscando el texto que empiece con "Procesador" o "Modelo" seguido de CPU
        cpu_match = re.search(
            r'(Procesador|Modelo)\s*[:\-]?\s*([A-Za-z0-9\-\™\s]+)', full_text, re.IGNORECASE)
        if cpu_match:
            cpu_str = cpu_match.group(2).strip()
            # Intentar separar marca y modelo para CPU
            if re.search(r'Intel', cpu_str, re.IGNORECASE):
                specs['cpu_brand'] = 'Intel'
            elif re.search(r'AMD', cpu_str, re.IGNORECASE):
                specs['cpu_brand'] = 'AMD'
            else:
                specs['cpu_brand'] = None

            specs['cpu_model'] = cpu_str

        # --- GPU ---
        # GPU puede estar en "Gráficos: ..." o "Gráficos ... integrados" o marca dedicada NVIDIA/AMD
        gpu_dedicated_match = re.search(
            r'(NVIDIA\s*GeForce\s*\w*|AMD\s*Radeon\s*\w*)', full_text, re.IGNORECASE)
        if gpu_dedicated_match:
            specs['gpu_model'] = gpu_dedicated_match.group(1).strip()
            specs['gpu_required'] = True
        else:
            gpu_integrated_match = re.search(
                r'Gráficos\s*[:\-]?\s*(Intel\s*integrados|Gráficos Intel integrados|Intel Iris Xe|AMD Radeon Graphics)', full_text, re.IGNORECASE)
            if gpu_integrated_match:
                specs['gpu_model'] = gpu_integrated_match.group(1).strip()
                specs['gpu_required'] = False
            else:
                specs['gpu_model'] = None
                specs['gpu_required'] = False

        return specs

# Para que el RecommendationEngine pueda encontrar este scraper
if __name__ == '__main__':
    print("Este módulo contiene el scraper de Novicompu. No está diseñado para ejecutarse directamente.")