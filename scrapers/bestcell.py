# scrapers/bestcell.py

from scrapers.base_scrapers import BaseScraper
from bs4 import BeautifulSoup
import re
import logging
from config import STORE_SELECTORS
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class BestcellScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url=STORE_SELECTORS["bestcell"]["base_url"],
                         selectors=STORE_SELECTORS["bestcell"])
        self.store_name = "Bestcell"
        self.currency_pattern = re.compile(r'[^\d.,]+')

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

        desc_selector = self.selectors.get("product_description_container")
        desc_tag = soup.select_one(desc_selector)
        if not desc_tag:
            logging.warning(f"[{self.store_name}] No se encontró la descripción para extraer especificaciones.")
            return specs

        full_text = desc_tag.get_text(separator=' ').strip()

        # RAM
        ram_match = re.search(r'(?:Memoria\s*RAM|RAM)[\s:]*?(\d+)\s*GB', full_text, re.IGNORECASE)
        if ram_match:
            specs['ram_gb'] = int(ram_match.group(1))

        # Almacenamiento
        storage_match = re.search(r'(?:Almacenamiento:?\s*)?(\d+)\s*(TB|GB)\s*(SSD|HDD)', full_text, re.IGNORECASE)
        if storage_match:
            size = int(storage_match.group(1))
            unit = storage_match.group(2).upper()
            stype = storage_match.group(3).upper()
            specs['storage_gb'] = size * 1024 if unit == 'TB' else size
            specs['storage_type'] = stype

        # CPU
        cpu_match = re.search(r'(Intel|AMD)[\s®™]*?(Core|Ryzen)[\s®™]*([iIrR]?\d{1,4}[A-Za-z]*)', full_text, re.IGNORECASE)
        if cpu_match:
            specs['cpu_brand'] = cpu_match.group(1)
            # Protege contra grupos opcionales faltantes
            cpu_type = cpu_match.group(2) if cpu_match.lastindex >= 2 else ''
            cpu_model = cpu_match.group(3) if cpu_match.lastindex >= 3 else ''
            specs['cpu_model'] = f"{specs['cpu_brand']} {cpu_type} {cpu_model}".strip()
            logging.debug(f"CPU extraída: {specs['cpu_model']} de '{cpu_match.group(0)}'")
        else:
            logging.debug("No se pudo extraer el CPU del texto completo.")

        # GPU dedicada
        dedicated_gpu_match = re.search(r'(NVIDIA\s*GeForce\s*(?:RTX|GTX|MX)\s*\d{3,4}[A-Z]?|AMD\s*Radeon\s*RX\s*\d{3,4}[A-Z]?)', full_text, re.IGNORECASE)
        if dedicated_gpu_match:
            specs['gpu_model'] = dedicated_gpu_match.group(1).strip()
            specs['gpu_required'] = True
        else:
            # GPU integrada
            integrated_gpu_match = re.search(r'(intel\s+iris\s+xe|intel\s+uhd\s+graphics|amd\s+radeon\s+graphics)', full_text, re.IGNORECASE)
            if integrated_gpu_match:
                name = integrated_gpu_match.group(1).replace('intel', 'Intel').replace('amd', 'AMD').title()
                specs['gpu_model'] = name
                specs['gpu_required'] = False

        logging.debug(f"[{self.store_name}] Especificaciones extraídas: {specs}")
        return specs

    def search_products(self, query):
        search_url = self.selectors["search_url_format"].format(query.replace(' ', '%20'))
        logging.info(f"[{self.store_name}] Buscando productos en: {search_url}")

        soup = self._fetch_page(search_url,
                                use_selenium=True,
                                wait_for_selector=self.selectors["wait_for_listing_product_card"])

        products_data = []
        if soup:
            product_cards = soup.select(self.selectors["product_container"])
            logging.info(f"[{self.store_name}] Encontrados {len(product_cards)} productos.")

            if not product_cards:
                logging.info(f"No se encontraron productos para la búsqueda '{query}' en {self.store_name}.")
                return []

            for card in product_cards:
                try:
                    name_el = card.select_one(self.selectors["name"])
                    price_el = card.select_one(self.selectors["price"])
                    image_el = card.select_one(self.selectors["image"])
                    link_el = card.select_one(self.selectors["name"])

                    name = name_el.get_text(strip=True) if name_el else None
                    price_text = price_el.get_text(strip=True) if price_el else None
                    price = self._clean_price(price_text) if price_text else None
                    image_url = image_el.get("src") if image_el else None

                    product_url = None
                    if link_el:
                        href = link_el.get("href")
                        product_url = self.base_url + href if href and href.startswith("/") else href

                    if name and product_url and price is not None:
                        products_data.append({
                            "name": name,
                            "url": product_url,
                            "image_url": image_url,
                            "price": price,
                            "store": self.store_name
                        })

                except Exception as e:
                    logging.error(f"[{self.store_name}] Error procesando producto: {e}", exc_info=True)

        else:
            logging.error(f"No se pudo obtener la página de búsqueda para {query} en {self.store_name}.")

        logging.info(f"[{self.store_name}] Total productos encontrados: {len(products_data)}")
        return products_data

    def parse_product_page(self, product_url):
        logging.info(f"[{self.store_name}] Parseando página producto: {product_url}")

        soup = self._fetch_page(
            product_url,
            use_selenium=True,
            wait_for_selector=self.selectors["wait_for_product_name"]
        )

        product_details = {}

        if soup:
            name_el = soup.select_one(self.selectors["product_name"])
            product_details['name'] = name_el.get_text(strip=True) if name_el else "N/A"

            price = None
            if self.driver:
                try:
                    WebDriverWait(self.driver, 3).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, self.selectors["wait_for_product_price"]))
                    )
                    price_el = self.driver.find_element(By.CSS_SELECTOR, self.selectors["product_price"])
                    price_text = price_el.text.strip()
                    price = self._clean_price(price_text)
                    logging.info(f"[{self.store_name}] Precio encontrado: {price_text} -> {price}")
                except TimeoutException:
                    logging.warning(f"[{self.store_name}] Timeout esperando precio válido en {product_url}")
                except Exception as e:
                    logging.error(f"[{self.store_name}] Error obteniendo precio en {product_url}: {e}", exc_info=True)

            product_details['price'] = price

            img_el = soup.select_one(self.selectors["product_image"])
            product_details['image_url'] = img_el.get('src') if img_el else None

            desc_el = soup.select_one(self.selectors["product_description_container"])
            product_details['description'] = desc_el.get_text(strip=True) if desc_el else ""

            product_details['specifications'] = self._extract_specifications(soup)

            product_details['url'] = product_url
            product_details['store'] = self.store_name

        else:
            logging.error(f"No se pudo obtener la página de detalle para {product_url}")

        logging.debug(f"[{self.store_name}] Detalles producto: {product_details}")
        print(f"## DEBUG PRINT: _extract_specifications - Final specs: {product_details.get('specifications', {})}")
        return product_details

# Para que el RecommendationEngine pueda encontrar este scraper
if __name__ == '__main__':
    print("Este módulo contiene el scraper de Bestcell. No está diseñado para ejecutarse directamente.")
