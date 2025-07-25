# scrapers/la_ganga.py
from scrapers.base_scrapers import BaseScraper
from config import STORE_SELECTORS, STORE_URLS
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LaGangaScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_URLS["la_ganga"], STORE_SELECTORS["la_ganga"])
        self.store_name = "La Ganga"

    def _clean_price(self, price_str):
        if not price_str:
            return None
        cleaned_price = price_str.replace('$', '').replace('USD', '').replace('S/', '').strip()
        cleaned_price = cleaned_price.replace('.', '').replace(',', '.')
        try:
            return float(cleaned_price)
        except ValueError:
            logging.warning(f"No se pudo limpiar el precio '{price_str}' a un flotante.")
            return None

    def search_products(self, query):
        search_url = f"{self.base_url}/catalogsearch/result/?q={query.replace(' ', '+')}"
        logging.info(f"Buscando en {self.store_name}: {search_url}")
        soup = self._fetch_page(search_url)
        products = []
        if soup:
            product_listings = soup.select(self.selectors["search_item_container"])
            logging.info(f"Se encontraron {len(product_listings)} productos básicos en {self.store_name}.")
            for product_elem in product_listings:
                name_elem = product_elem.select_one(self.selectors["search_item_name"])
                price_elem = product_elem.select_one(self.selectors["search_item_price"])
                url_elem = product_elem.select_one(self.selectors["search_item_link"])
                image_elem = product_elem.select_one(self.selectors["search_item_image"])

                name = name_elem.text.strip() if name_elem else "N/A"
                price_str = price_elem.text.strip() if price_elem else None
                price = self._clean_price(price_str)
                url = url_elem['href'] if url_elem else "#"
                image_url = image_elem['src'] if image_elem else "#"

                products.append({
                    'name': name,
                    'price': price,
                    'url': url,
                    'image_url': image_url,
                    'store': self.store_name
                })
        return products

    def parse_product_page(self, product_url):
        logging.info(f"Scraping página de detalle de {self.store_name}: {product_url}")
        soup = self._fetch_page(product_url)
        if not soup:
            logging.error(f"No se pudo obtener la página de detalle para {product_url}")
            return None

        product_details = {}
        # Extraer nombre, precio, etc. con los selectores del config
        name_elem = soup.select_one(self.selectors["product_name"])
        product_details['name'] = name_elem.text.strip() if name_elem else "N/A"

        price_elem = soup.select_one(self.selectors["product_price"])
        price_str = price_elem.text.strip() if price_elem else None
        product_details['price'] = self._clean_price(price_str)

        image_elem = soup.select_one(self.selectors["product_image"])
        product_details['image_url'] = image_elem['src'] if image_elem else "#"

        product_details['url'] = product_url
        product_details['store'] = self.store_name

        # Extraer descripción (ajusta el selector si es necesario)
        description_elem = soup.select_one(self.selectors["product_description_text"])
        product_details['description'] = description_elem.text.strip() if description_elem else "Sin descripción detallada."

        specs = self._parse_specifications(soup, product_details['name'], product_details['description'])
        product_details['specifications'] = specs
        # -----------------------------------------------------------------

        logging.info(f"Detalles extraídos para {product_details['name']}: {product_details}")
        return product_details

    def _parse_specifications(self, soup, name, description):
        specs = {
            'ram_gb': None,
            'storage_gb': None,
            'storage_type': None,
            'cpu_model': None,
            'gpu_model': None
        }

        # Combinar nombre y descripción para una búsqueda más completa
        full_text = f"{name} {description}".lower()

        # --- Extracción de RAM (ejemplos: "16GB RAM", "16 GB de RAM", "Memoria: 8GB") ---
        # Prioriza "GB RAM" luego "GB de RAM" y finalmente "GB" con palabra clave "memoria"
        ram_match = re.search(r'(\d+)\s*gb\s*ram', full_text)
        if not ram_match:
            ram_match = re.search(r'(\d+)\s*gb\s*de\s*ram', full_text)
        if not ram_match:
            ram_match = re.search(r'memoria\s*:\s*(\d+)\s*gb', full_text)
        if ram_match:
            try:
                specs['ram_gb'] = int(ram_match.group(1))
            except ValueError:
                pass

        # --- Extracción de Almacenamiento (GB/TB y tipo SSD/HDD/NVMe) ---
        # Busca patrones como "512 GB SSD", "1TB HDD", "256GB NVMe"
        storage_match = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme)', full_text)
        if storage_match:
            amount = int(storage_match.group(1))
            unit = storage_match.group(2).upper()
            storage_type = storage_match.group(3).upper()
            if unit == 'TB':
                amount *= 1024 # Convertir TB a GB
            specs['storage_gb'] = amount
            specs['storage_type'] = storage_type
        else:
            # Si no se encuentra el tipo, buscar solo la cantidad y el tipo por separado
            storage_amount_match = re.search(r'(\d+)\s*(gb|tb)', full_text)
            if storage_amount_match:
                amount = int(storage_amount_match.group(1))
                unit = storage_amount_match.group(2).upper()
                if unit == 'TB':
                    amount *= 1024
                specs['storage_gb'] = amount

            storage_type_match = re.search(r'(ssd|hdd|nvme)', full_text)
            if storage_type_match:
                specs['storage_type'] = storage_type_match.group(1).upper()

        # --- Extracción de Procesador (CPU) ---
        # Patrones para Intel Core iX, AMD Ryzen X, Apple M
        cpu_match = re.search(r'(intel\\s+core\\s+i[3579]|amd\\s+ryzen\\s*[3579]|apple\\s+m[123](?:\\s+pro|\\s+max|\\s+ultra)?)', full_text)
        if cpu_match:
            specs['cpu_model'] = cpu_match.group(0).replace('intel core', 'Intel Core').replace('amd ryzen', 'AMD Ryzen').replace('apple', 'Apple').title()

        # --- Extracción de Tarjeta Gráfica (GPU) ---
        # Patrones para NVIDIA GeForce RTX/GTX, AMD Radeon RX, Intel Iris/UHD
        gpu_match = re.search(r'(nvidia\\s+geforce\\s+(?:rtx|gtx)\\s*\\d+|amd\\s+radeon\\s*rx\\s*\\d+|intel\\s+(?:iris|uhd)\\s*(?:graphics)?(?:\\s*xe)?)', full_text)
        if gpu_match:
            specs['gpu_model'] = gpu_match.group(0).replace('nvidia geforce', 'NVIDIA GeForce').replace('amd radeon', 'AMD Radeon').replace('intel', 'Intel').title()

        return specs