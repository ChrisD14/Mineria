# scrapers/mobilestore.py
from scrapers.base_scrapers import BaseScraper
from bs4 import BeautifulSoup
import re
import logging
from config import STORE_SELECTORS
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException # Importar TimeoutException

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MobilestoreScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url=STORE_SELECTORS["mobilestore"]["base_url"],
                         selectors=STORE_SELECTORS["mobilestore"])
        self.currency_pattern = re.compile(r'[^\\d.,]+')

    def _clean_price(self, price_text):
        if not price_text:
            return None
        cleaned = (
            str(price_text)
            .replace('$', '')
            .replace('USD', '')
            .replace(',', '')
            .replace('\xa0', '')
            .strip()
        )
        try:
            return float(cleaned)
        except ValueError:
            logging.error(f"No se pudo convertir el precio a float: '{price_text}' -> '{cleaned}'", exc_info=True)
            return None

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

        full_text = soup.get_text() # Obtener todo el texto visible de la página

        # Extraer RAM
        ram_match = re.search(r'(?:Memoria\s*RAM|RAM):\s*(\d+)\s*GB(?:\s*DDR\d+)?|\b(\d+)\s*GB(?:\s*DDR\d+)?\s*RAM\b', full_text, re.IGNORECASE)
        if ram_match:
            ram_gb = int(ram_match.group(1) or ram_match.group(2))
            specs['ram_gb'] = ram_gb
            logging.debug(f"RAM extraída: {ram_gb}GB de '{ram_match.group(0)}'")
        else:
            logging.debug("No se pudo extraer la RAM del texto completo.")

        # Extraer Almacenamiento
        storage_match = re.search(r'(?:Almacenamiento:\s*)?(\d+)\s*(TB|GB)\s*(SSD|HDD)', full_text, re.IGNORECASE)
        if storage_match:
            storage_value = int(storage_match.group(1))
            storage_unit = storage_match.group(2).upper()
            storage_type = storage_match.group(3).upper()

            if storage_unit == 'TB':
                specs['storage_gb'] = storage_value * 1024
            else:
                specs['storage_gb'] = storage_value
            specs['storage_type'] = storage_type
            logging.debug(f"Almacenamiento extraído: {specs['storage_gb']}GB ({specs['storage_type']}) de '{storage_match.group(0)}'")
            
        else:
            logging.debug("No se pudo extraer el almacenamiento del texto completo.")

        # Extraer CPU
        cpu_match = re.search(r'(Intel|AMD)\s+(Core|Ryzen)\s*([i|r]\d+)-?[\w\d]*\s*(\w*\d*)?', full_text, re.IGNORECASE)
        if cpu_match:
            specs['cpu_brand'] = cpu_match.group(1)
            specs['cpu_model'] = f"{cpu_match.group(1)} {cpu_match.group(2)} {cpu_match.group(3)}{cpu_match.group(4) or ''}".strip()
            logging.debug(f"CPU extraída: {specs['cpu_brand']} {specs['cpu_model']} de '{cpu_match.group(0)}'")
        else:
            logging.debug("No se pudo extraer el CPU del texto completo.")

        # Extraer GPU
        dedicated_gpu_match = re.search(r'(NVIDIA\s*GeForce\s*(?:RTX|GTX|MX)\s*\d{3,4}(?:[A-Z]X)?|AMD\s*Radeon\s*RX\s*\d{3,4}(?:[A-Z]X)?)\s*(?:\d+\s*GB)?', full_text, re.IGNORECASE)
        if dedicated_gpu_match:
            specs['gpu_model'] = dedicated_gpu_match.group(1).strip()
            specs['gpu_required'] = True
            logging.debug(f"GPU dedicada extraída: {specs['gpu_model']} de '{dedicated_gpu_match.group(0)}'")
        else:
            integrated_gpu_match = re.search(r'(intel\s+iris\s+xe(?:\s+graphics)?|intel\s+uhd\s+graphics|amd\s+radeon\s+graphics)', full_text, re.IGNORECASE)
            if integrated_gpu_match:
                specs['gpu_model'] = integrated_gpu_match.group(0).replace('intel', 'Intel').replace('amd', 'AMD').title()
                specs['gpu_required'] = False
                logging.debug(f"GPU integrada extraída: {specs['gpu_model']} de '{integrated_gpu_match.group(0)}'")
            else:
                logging.debug("No se pudo extraer ninguna GPU.")

        logging.debug(f"Especificaciones finales extraídas: {specs}")
        print(f"## DEBUG PRINT: _extract_specifications - Final specs: {specs}")
        return specs

    def search_products(self, query):
        search_url = self.base_url + '?s=' + query.replace(' ', '+')
        logging.info(f"[MobilestoreScraper] Buscando productos en: {search_url}")

        soup = self._fetch_page_with_selenium(search_url, self.selectors["listing_product_card"])
        if not soup:
            logging.error(f"No se pudo obtener la página de búsqueda para: {query}")
            return []

        products_data = []
        product_cards = soup.select(self.selectors["listing_product_card"])
        logging.info(f"[MobilestoreScraper] Encontrados {len(product_cards)} productos básicos.")

        for card in product_cards:
            name_element = card.select_one(self.selectors["listing_product_name"])
            link_element = card.select_one(self.selectors["listing_product_link"])

            name = name_element.get_text(strip=True) if name_element else "N/A"
            product_url = link_element['href'] if link_element else None

            if product_url: 
                products_data.append({
                    'name': name,
                    'url': product_url
                })
        return products_data

    def parse_product_page(self, product_url):
        logging.info(f"[MobilestoreScraper] Parseando página de producto: {product_url}")

        soup = self._fetch_page_with_selenium(product_url, self.selectors["product_name"])
        if not soup:
            logging.error(f"No se pudo obtener la página del producto para: {product_url}")
            return None

        price_text = "$0.00"

        if self.driver:
            try:
                price_locator = (By.CSS_SELECTOR, self.selectors["product_price"])

                # Espera a que el <bdi> exista y contenga algún número
                WebDriverWait(self.driver, 5).until(
                    lambda d: re.search(r'\d', d.find_element(*price_locator).get_attribute("textContent") or "")
                )

                price_el = self.driver.find_element(*price_locator)
                # textContent suele ser más fiable que .text con WooCommerce + JS
                raw_text = price_el.get_attribute("textContent").strip()

                # DEBUG opcional
                logging.debug(f"[MobilestoreScraper] raw price text: '{raw_text}'")

                price_text = self._extract_numeric_from_price(raw_text)

            except TimeoutException as e:
                logging.warning(f"Timeout esperando el precio en {product_url}: {e}")
                logging.error(f"Error al extraer el precio para {product_url}: {e}", exc_info=True)

        # Nombre
        name_element = soup.select_one(self.selectors["product_name"])
        name = name_element.get_text(strip=True) if name_element else "N/A"

        price = self._clean_price(price_text)

        specs = self._extract_specifications(soup)

        product_details = {
            'name': name,
            'price': price,
            'url': product_url,
            'store': 'mobilestore',
            'specifications': specs
        }
        logging.debug(f"Detalles del producto parseados: {product_details}")
        return product_details

    def _extract_numeric_from_price(self, text):
        """
        Devuelve la parte numérica del precio encontrada en el texto.
        Ej: '$ 1,149.00 Incluye IVA' -> '1,149.00'
        """
        if not text:
            return None
        text = text.replace('\xa0', ' ')
        m = re.search(r'(\d[\d\.,]*)', text)
        return m.group(1) if m else None

# Para que el RecommendationEngine pueda encontrar este scraper
if __name__ == '__main__':
    print("Este módulo contiene el scraper de Mobilestore. No está diseñado para ejecutarse directamente.")