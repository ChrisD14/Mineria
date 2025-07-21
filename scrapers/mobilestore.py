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
        """Limpia el texto del precio y lo convierte a flotante."""
        if not price_text:
            logging.debug("Precio no encontrado o es nulo.")
            print(f"## DEBUG PRINT: _clean_price - Input: '{price_text}', Cleaned: None (not found or null)")
            return None
        
        # Elimina símbolos de dólar y comas, luego convierte a flotante
        cleaned_price = price_text.replace('$', '').replace(',', '')
        try:
            price = float(cleaned_price)
            logging.debug(f"Precio limpiado: '{price_text}' -> {price}")
            print(f"## DEBUG PRINT: _clean_price - Input: '{price_text}', Cleaned: {price}")
            return price
        except ValueError:
            logging.error(f"No se pudo convertir el precio a flotante: '{price_text}' -> '{cleaned_price}'", exc_info=True)
            print(f"## DEBUG PRINT: _clean_price - Error converting price: '{price_text}' -> '{cleaned_price}'")
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
            print(f"## DEBUG PRINT: _extract_specifications - RAM match: {ram_match.group(0) if ram_match else 'None'}, Extracted RAM: {specs['ram_gb']}")
        else:
            logging.debug("No se pudo extraer la RAM del texto completo.")
            print(f"## DEBUG PRINT: _extract_specifications - No RAM match found.")

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
            print(f"## DEBUG PRINT: _extract_specifications - Storage match: {storage_match.group(0) if storage_match else 'None'}, Extracted Storage: {specs['storage_gb']}GB {specs['storage_type']}")
        else:
            logging.debug("No se pudo extraer el almacenamiento del texto completo.")
            print(f"## DEBUG PRINT: _extract_specifications - No Storage match found.")

        # Extraer CPU
        cpu_match = re.search(r'(Intel|AMD)\s+(Core|Ryzen)\s*([i|r]\d+)-?[\w\d]*\s*(\w*\d*)?', full_text, re.IGNORECASE)
        if cpu_match:
            specs['cpu_brand'] = cpu_match.group(1)
            specs['cpu_model'] = f"{cpu_match.group(1)} {cpu_match.group(2)} {cpu_match.group(3)}{cpu_match.group(4) or ''}".strip()
            logging.debug(f"CPU extraída: {specs['cpu_brand']} {specs['cpu_model']} de '{cpu_match.group(0)}'")
            print(f"## DEBUG PRINT: _extract_specifications - CPU match: {cpu_match.group(0) if cpu_match else 'None'}, Extracted CPU: {specs['cpu_brand']} {specs['cpu_model']}")
        else:
            logging.debug("No se pudo extraer el CPU del texto completo.")
            print(f"## DEBUG PRINT: _extract_specifications - No CPU match found.")

        # Extraer GPU
        dedicated_gpu_match = re.search(r'(NVIDIA\s*GeForce\s*(?:RTX|GTX|MX)\s*\d{3,4}(?:[A-Z]X)?|AMD\s*Radeon\s*RX\s*\d{3,4}(?:[A-Z]X)?)\s*(?:\d+\s*GB)?', full_text, re.IGNORECASE)
        if dedicated_gpu_match:
            specs['gpu_model'] = dedicated_gpu_match.group(1).strip()
            specs['gpu_required'] = True
            logging.debug(f"GPU dedicada extraída: {specs['gpu_model']} de '{dedicated_gpu_match.group(0)}'")
            print(f"## DEBUG PRINT: _extract_specifications - Dedicated GPU match: {dedicated_gpu_match.group(0) if dedicated_gpu_match else 'None'}, Extracted GPU: {specs['gpu_model']}, GPU Required: {specs['gpu_required']}")
        else:
            integrated_gpu_match = re.search(r'(intel\s+iris\s+xe(?:\s+graphics)?|intel\s+uhd\s+graphics|amd\s+radeon\s+graphics)', full_text, re.IGNORECASE)
            if integrated_gpu_match:
                specs['gpu_model'] = integrated_gpu_match.group(0).replace('intel', 'Intel').replace('amd', 'AMD').title()
                specs['gpu_required'] = False
                logging.debug(f"GPU integrada extraída: {specs['gpu_model']} de '{integrated_gpu_match.group(0)}'")
                print(f"## DEBUG PRINT: _extract_specifications - Integrated GPU match: {integrated_gpu_match.group(0) if integrated_gpu_match else 'None'}, Extracted GPU: {specs['gpu_model']}, GPU Required: {specs['gpu_required']}")
            else:
                logging.debug("No se pudo extraer ninguna GPU.")
                print(f"## DEBUG PRINT: _extract_specifications - No GPU match found.")

        logging.debug(f"Especificaciones finales extraídas: {specs}")
        print(f"## DEBUG PRINT: _extract_specifications - Final specs: {specs}")
        return specs

    def search_products(self, query):
        """
        Busca productos en Mobilestore.ec usando Selenium.
        """
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
        """
        Parsea la página de detalle de un producto individual en Mobilestore.ec usando Selenium.
        """
        logging.info(f"[MobilestoreScraper] Parseando página de producto: {product_url}")
        
        # Obtenemos la página primero, esperando que el nombre del producto (h1) esté presente
        soup = self._fetch_page_with_selenium(product_url, self.selectors["product_name"])
        if not soup:
            logging.error(f"No se pudo obtener la página del producto para: {product_url}")
            return None

        price_text = "$0.00" # Valor por defecto

        if self.driver: # Asegurarse de que el driver de Selenium esté disponible
            try:
                # El selector de precio ahora apunta a la etiqueta <ins> que contiene el precio actual
                price_selector = self.selectors["product_price"] 
                
                # Primero, esperamos que el contenedor general del precio (<p.price>) sea visible
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "p.price"))
                )

                # Ahora, esperamos que el elemento <ins> dentro de <p.price> tenga un texto válido y un valor > 0
                def price_has_valid_text(driver):
                    try:
                        # Encontrar el elemento <ins> que contiene el precio actual
                        ins_price_element = driver.find_element(By.CSS_SELECTOR, price_selector)
                        
                        # Obtener su outerHTML para parsearlo con BeautifulSoup
                        outer_html_ins = ins_price_element.get_attribute('outerHTML')
                        soup_ins = BeautifulSoup(outer_html_ins, 'html.parser')
                        
                        # Extraer todo el texto de la etiqueta <ins>
                        text = soup_ins.get_text(strip=True)
                        
                        # Mensajes de depuración detallados
                        print(f"## DEBUG PRICE CHECK (Mobilestore) - Selector usado para <ins>: '{price_selector}'")
                        print(f"## DEBUG PRICE CHECK (Mobilestore) - outerHTML de <ins>: {outer_html_ins}")
                        print(f"## DEBUG PRICE CHECK (Mobilestore) - Texto extraído de BeautifulSoup (<ins>): '{text}'")
                        
                        cleaned_price_value = self._clean_price(text)
                        
                        print(f"## DEBUG PRICE CHECK (Mobilestore) - Valor de precio limpio: {cleaned_price_value}")
                        
                        return cleaned_price_value is not None and cleaned_price_value > 0.0
                    except Exception as e:
                        logging.debug(f"Excepción durante la verificación de price_has_valid_text (reintento con <ins>): {e}")
                        return False

                # Tiempo de espera principal para que el precio se cargue y sea válido
                WebDriverWait(self.driver, 30).until(price_has_valid_text) 
                
                # Una vez que la condición se cumple, obtenemos el texto final del precio
                price_element = self.driver.find_element(By.CSS_SELECTOR, price_selector) 
                price_text = price_element.text.strip() # Usamos .text.strip() aquí, ya que ya sabemos que el elemento tiene texto válido
                logging.info(f"Precio encontrado y texto válido. Texto crudo del precio: '{price_text}'")

            except TimeoutException as e:
                logging.warning(f"Timeout waiting for price element or valid price for {product_url}: {e}")
                print(f"## DEBUG PRINT: parse_product_page - Elemento de precio no encontrado o no se actualizó de $0.00 (Timeout). Error: {e}")
                price_text = "$0.00" # Mantener el valor por defecto si hay timeout
            except Exception as e:
                logging.error(f"Error al extraer el precio para {product_url}: {e}", exc_info=True)
                print(f"## DEBUG PRINT: parse_product_page - Error general al extraer el precio. Error: {e}")
                price_text = "$0.00" # Mantener el valor por defecto en caso de error

        name_element = soup.select_one(self.selectors["product_name"])
        name = name_element.get_text(strip=True) if name_element else "N/A"

        # Pasa el price_text extraído a _clean_price
        price = self._clean_price(price_text)

        specs = self._extract_specifications(soup)
        
        product_details = {
            'name': name,
            'price': price, 
            'url': product_url,
            **specs
        }
        logging.debug(f"Detalles del producto parseados: {product_details}")
        return product_details

# Para que el RecommendationEngine pueda encontrar este scraper
if __name__ == '__main__':
    print("Este módulo contiene el scraper de Mobilestore. No está diseñado para ejecutarse directamente.")