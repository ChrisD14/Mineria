# scrapers/computron.py
from scrapers.base_scrapers import BaseScraper
from config import STORE_SELECTORS, STORE_URLS
import re
import time 
import random
import logging

# Configura el logger para que puedas ver los mensajes de depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComputronScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_URLS["computron"], STORE_SELECTORS["computron"])
        self.store_name = "Computron"

    def _clean_price(self, price_str):
        if not price_str:
            return None
        
        # Elimina símbolos de moneda, espacios extra
        cleaned_price = price_str.replace('$', '').replace('USD', '').replace('S/', '').strip()
        # Elimina separadores de miles (punto)
        cleaned_price = cleaned_price.replace('.', '')
        # Reemplaza coma por punto para decimales
        cleaned_price = cleaned_price.replace(',', '.')
        
        try:
            return float(cleaned_price)
        except ValueError:
            logging.warning(f"No se pudo limpiar el precio '{price_str}' a un flotante.")
            return None 

    def search_products(self, query):
        search_url = f"{self.base_url}/?s={query.replace(' ', '+')}"
        logging.info(f"Buscando en Computron: {search_url}")
        soup = self._fetch_page(search_url)
        if not soup:
            return []

        products_found = []
        
        product_listings = soup.select(self.selectors["search_item_container"])

        if not product_listings:
            logging.warning(f"No se encontraron elementos de lista de productos en Computron con el selector '{self.selectors['search_item_container']}'.")
            return []

        irrelevant_keywords = ["forro", "sleeve", "mochila", "maleta", "cable", "adaptador", "mouse", "audifono"]
        
        for item in product_listings:
            if len(products_found) >= 10: # Limitar a 10 productos como en tu snippet original
                break
            try:
                name_tag = item.select_one(self.selectors["search_item_name"])
                link_tag = item.select_one(self.selectors["search_item_link"])
                img_tag = item.select_one(self.selectors["search_item_image"])

                name = name_tag.get_text(strip=True) if name_tag else 'N/A'
                
                price = None # Precio es None en la búsqueda

                product_url = link_tag['href'] if link_tag and 'href' in link_tag.attrs else '#'
                if product_url.startswith('/'): 
                    product_url = self.base_url + product_url

                image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else '#'
                if image_url == '#' and img_tag and 'data-src' in img_tag.attrs:
                    image_url = img_tag['data-src']
                if image_url.startswith('//'): 
                    image_url = "https:" + image_url
                elif image_url.startswith('/'):
                    image_url = self.base_url + image_url

                name_lower = name.lower()
                
                # *** LÓGICA DE FILTRADO MEJORADA ***
                is_laptop = "laptop" in name_lower or "notebook" in name_lower
                
                if not is_laptop and any(keyword in name_lower for keyword in irrelevant_keywords):
                    logging.info(f"Producto omitido por ser accesorio: '{name}'")
                    continue
                
                if not product_url.startswith(f"{self.base_url}/producto/") and not is_laptop:
                     logging.info(f"Producto omitido por URL o nombre sospechoso: '{name}' - {product_url}")
                     continue

                products_found.append({
                    'name': name,
                    'price': price, 
                    'url': product_url,
                    'image_url': image_url,
                    'store': self.store_name 
                })
                
            except Exception as e:
                logging.error(f"Error al parsear un item de producto en Computron (search_products): {e}. Item HTML (primeras 200 chars): {str(item)[:200]}...")
                continue
        return products_found

    def parse_product_page(self, url):
        logging.info(f"Scraping página de detalle de Computron: {url}")
        soup = self._fetch_page(url)
        if not soup:
            logging.warning(f"No se pudo obtener la página de detalle de {url} en Computron.")
            return None

        name_tag = soup.select_one(self.selectors["product_name"])
        price_tag = soup.select_one(self.selectors["product_price"])
        img_tag = soup.select_one(self.selectors["product_image"])
        # Asumiendo que la descripción está en el tab de descripción
        description_tag = soup.select_one(self.selectors.get("product_description_text", 'div.woocommerce-Tabs-panel--description p'))
        
        name = name_tag.get_text(strip=True) if name_tag else 'Nombre no encontrado'
        
        raw_price = price_tag.get_text(strip=True) if price_tag else None
        price = self._clean_price(raw_price)

        image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else '#'
        if image_url == '#' and img_tag and 'data-src' in img_tag.attrs:
            image_url = img_tag['data-src']
        if image_url.startswith('//'):
            image_url = "https:" + image_url
        elif image_url.startswith('/'):
            image_url = self.base_url + image_url
            
        description = description_tag.get_text(strip=True) if description_tag else 'Descripción no disponible.'

        # Extracción de especificaciones desde el nombre y la descripción
        specifications = self._extract_specs_from_text(name, description)

        # Aquí puedes añadir la extracción de specs desde una tabla si Computron la tiene
        # specs_container = soup.select_one(self.selectors.get("product_specs_list"))
        # if specs_container:
        #     # Lógica para parsear tabla de specs si existe y está en el HTML
        #     # Esto sobrescribiría o complementaría las specs extraídas del texto
        #     pass

        product_details = {
            'name': name,
            'price': price, 
            'url': url,
            'image_url': image_url,
            'store': self.store_name, 
            'description': description,
            'specifications': specifications
        }
        logging.info(f"Detalles extraídos para {name}: {product_details}")
        return product_details

    def _extract_specs_from_text(self, name, description):
        """
        Intenta extraer especificaciones (RAM, almacenamiento, CPU, GPU)
        del nombre y la descripción del producto.
        """
        combined_text = (name + " " + description).lower()
        specs = {
            "ram_gb": None,
            "storage_gb": None,
            "storage_type": None,
            "cpu_model": None,
            "gpu_model": None
        }

        # RAM
        ram_match = re.search(r'(\d+)\s*gb(?:\s*ram)?', combined_text, re.IGNORECASE)
        if ram_match:
            specs["ram_gb"] = int(ram_match.group(1))

        # Almacenamiento (SSD/HDD y GB/TB)
        storage_match = re.search(r'(\d+)\s*(?:gb|tb)\s*(ssd|hdd|nvme)?', combined_text, re.IGNORECASE)
        if storage_match:
            amount = int(storage_match.group(1))
            unit = storage_match.group(2).lower() if storage_match.group(2) else ''
            
            if 'tb' in unit: # Si la unidad es TB, convierte a GB
                specs["storage_gb"] = amount * 1024
            elif 'gb' in storage_match.group(0).lower(): # Si la unidad explícitamente es GB
                specs["storage_gb"] = amount
            else: # Si solo se encontró el número, asume GB si no hay TB
                specs["storage_gb"] = amount 
                
            if 'ssd' in unit or 'nvme' in unit or 'solid state' in combined_text:
                specs["storage_type"] = "SSD"
            elif 'hdd' in unit or 'disco duro' in combined_text:
                specs["storage_type"] = "HDD"
            
        # CPU
        # Patrones para Intel y AMD
        intel_cpu_pattern = r'intel\s*(?:core\s*(?:i(?:3|5|7|9)|ultra\s*\d+))(?:\s*-\s*\d+[a-z]{0,2})?'
        amd_cpu_pattern = r'amd\s*ryzen\s*(?:(?:3|5|7|9)|threadripper|athlon)(?:\s*mobile)?(?:\s*\d+[a-z]{0,2})?'
        
        cpu_match_intel = re.search(intel_cpu_pattern, combined_text, re.IGNORECASE)
        cpu_match_amd = re.search(amd_cpu_pattern, combined_text, re.IGNORECASE)

        if cpu_match_intel:
            specs["cpu_model"] = cpu_match_intel.group(0).strip()
        elif cpu_match_amd:
            specs["cpu_model"] = cpu_match_amd.group(0).strip()
        
        # GPU
        # Modelos comunes de GPUs dedicadas e integradas
        gpu_pattern = r'(nvidia\s*geforce\s*(?:rtx|gtx)\s*\d{3,4}[a-z]?|amd\s*radeon\s*rx\s*\d{3,4}[a-z]?|intel\s*(?:iris\s*xe|uhd\s*graphics))'
        gpu_match = re.search(gpu_pattern, combined_text, re.IGNORECASE)
        if gpu_match:
            specs["gpu_model"] = gpu_match.group(0).strip()

        return specs

# Para probar este scraper directamente:
if __name__ == '__main__':
    scraper = ComputronScraper()
    # Usamos una query que sabemos que tiene laptops con 32GB RAM para una prueba más relevante
    # Asegúrate de que los selectores en config.py para Computron sean correctos.
    # Por ejemplo:
    # STORE_SELECTORS = {
    #    "computron": {
    #        "search_item_container": "li.product", # O el selector correcto para la lista de productos
    #        "search_item_name": "h2.woocommerce-loop-product__title",
    #        "search_item_link": "a.woocommerce-LoopProduct-link",
    #        "search_item_image": "img.wp-post-image",
    #        "product_name": "h1.product_title",
    #        "product_price": "p.price",
    #        "product_image": "div.woocommerce-product-gallery__image img",
    #        "product_description_text": "div.woocommerce-Tabs-panel--description p",
    #        # "product_specs_list": "table.shop_attributes" # Si hay una tabla de especificaciones
    #    },
    #    "la_ganga": { ... }
    # }

    search_query_test = "laptop 32GB RAM" # O tu query de prueba
    search_results = scraper.search_products(search_query_test) 
    logging.info(f"\n--- Resultados de búsqueda en Computron para '{search_query_test}' ---")
    if search_results:
        for product in search_results:
            logging.info(f"    Nombre: {product['name']}, Precio: {product['price']}, URL: {product['url']}, Imagen: {product['image_url']}")
        
        # Solo intentar parsear detalle si hay productos relevantes
        laptops_found = [p for p in search_results if "laptop" in p['name'].lower() or "notebook" in p['name'].lower()]
        if laptops_found and laptops_found[0]['url'] != '#':
            first_product_url = laptops_found[0]['url']
            logging.info(f"\n--- Probando parseo de detalle del primer producto relevante: {first_product_url} ---")
            detailed_product = scraper.parse_product_page(first_product_url)
            if detailed_product:
                logging.info("\n--- Detalles del producto completo ---")
                for key, value in detailed_product.items():
                    # Para 'specifications', imprime cada item en una nueva línea para mayor claridad
                    if key == 'specifications' and isinstance(value, dict):
                        logging.info(f"    {key}:")
                        for spec_key, spec_value in value.items():
                            logging.info(f"        {spec_key}: {spec_value}")
                    else:
                        logging.info(f"    {key}: {value}")
            else:
                logging.info("    No se pudieron obtener detalles del producto.")
        else:
            logging.info("No se encontraron productos relevantes para probar el parseo de detalle o la URL no es válida.")
    else:
        logging.info("No se encontraron productos para la búsqueda.")