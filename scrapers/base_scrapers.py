# scrapers/base_scrapers.py
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import time # Para añadir pausas entre solicitudes
import random # Para pausas aleatorias
import re # Para expresiones regulares y limpieza de texto
import logging # Importa logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException # Importa NoSuchElementException

# Configura el logger para que puedas ver los mensajes de depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BaseScraper(ABC):
    def __init__(self, base_url, selectors):
        self.base_url = base_url
        self.selectors = selectors # Diccionario con selectores CSS para nombres, precios, etc.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        } # Es crucial para evitar bloqueos
        self.session = requests.Session() # Usar una sesión para mantener cookies, etc.
        self.driver = None

    def _initialize_selenium_driver(self):
        """Inicializa el driver de Selenium si aún no está inicializado."""
        if self.driver is None:
            logging.info("Inicializando WebDriver de Chrome...")
            chrome_options = Options()
            chrome_options.add_argument("--headless") # Ejecutar en modo sin cabeza (sin ventana de navegador)
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={self.headers['User-Agent']}") # Usar el mismo User-Agent

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("WebDriver de Chrome inicializado.")

    def _fetch_page(self, url, use_selenium=False, wait_for_selector=None, selenium_timeout=4):
        if not use_selenium:
            logging.info(f"Página {url} fetched con requests.")
            try:
                response = self.session.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                logging.info(f"Página {url} fetched y parseada exitosamente con requests.")
                return soup
            except requests.exceptions.RequestException as e:
                logging.error(f"Error al obtener la página con requests: {e}", exc_info=True)
                return None
        else:
            if not self.driver:
                self._initialize_selenium_driver()
            if self.driver is None:
                logging.error(f"No se pudo inicializar el driver de Selenium. No se puede obtener la página: {url}")
                return None
            try:
                logging.info(f"[{self.__class__.__name__}] Usando Selenium para obtener: {url}")
                self.driver.get(url)
                if wait_for_selector:
                    logging.info(f"[{self.__class__.__name__}] Esperando selector: '{wait_for_selector}' con timeout de {selenium_timeout} segundos.")
                    WebDriverWait(self.driver, selenium_timeout).until( # <<-- ¡VERIFICA ESTA LÍNEA!
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                logging.info(f"Página {url} fetched con Selenium y parseada exitosamente.")
                return soup
            except TimeoutException as e:
                logging.error(f"Error al obtener la página con Selenium (Timeout después de {selenium_timeout}s): {e}", exc_info=True)
                return None
            except Exception as e:
                logging.error(f"Error al obtener la página con Selenium: {e}", exc_info=True)
                return None
            
    def _clean_price(self, price_text):
        """Limpia la cadena de texto del precio y la convierte a float."""
        if price_text:
            # Asegurarse de que price_text es una cadena
            price_str = str(price_text)
            
            # Eliminar símbolos de moneda, espacios no deseados y comas (que pueden ser separadores de miles)
            cleaned_text = price_str.replace('$', '').replace('USD', '').replace('€', '').replace(' ', '').strip()
            
            # Si el formato decimal es con coma (ej. "1.234,56"), reemplazar coma por punto
            # Esto asume que si hay un punto, es separador de miles, y si hay una coma, es separador decimal
            if ',' in cleaned_text and '.' in cleaned_text: # Si ambos están, probablemente la coma es decimal
                parts = cleaned_text.split(',')
                # Si la parte decimal tiene 2 dígitos (ej. 1,23), entonces la coma es decimal
                if len(parts[-1]) == 2: 
                    cleaned_text = cleaned_text.replace('.', '').replace(',', '.')
                else: # Si no, la coma es de miles, y el punto es decimal
                    cleaned_text = cleaned_text.replace(',', '') # Eliminar solo las comas de miles
            elif ',' in cleaned_text: # Solo comas, asumir que es decimal
                cleaned_text = cleaned_text.replace(',', '.')

            try:
                # Intentar convertir a float
                return float(cleaned_text)
            except ValueError:
                logging.warning(f"No se pudo convertir el precio '{price_text}' (limpio: '{cleaned_text}') a float.")
                return None
        return None

    def _extract_specs(self, specs_table):
        """Extrae especificaciones de una tabla HTML."""
        specs = {}
        if specs_table:
            rows = specs_table.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    if key and value:
                        specs[key] = value
        return specs

    def _extract_specs_from_text(self, text):
        specs = {}
        full_text = text.lower() # Trabajar con minúsculas para la búsqueda

        # --- Extracción de RAM ---
        # Patrón mejorado para capturar "XGB RAM" o "X GB RAM"
        ram_match = re.search(r'(\d+)\s*(gb|tb)\s*ram', full_text, re.IGNORECASE)
        if ram_match:
            amount = int(ram_match.group(1))
            unit = ram_match.group(2).upper()
            if unit == 'TB':
                amount *= 1024 # Convertir TB a GB
            specs['RAM_GB'] = amount
        else: # Intento alternativo para RAM sin la palabra "RAM" explícita
            # Busca números seguidos de GB/TB que no estén cerca de "almacenamiento", "disco", "ssd", "hdd"
            # Esta es una heurística y puede tener falsos positivos/negativos
            ram_alt_match = re.search(r'(\d+)\s*(gb)(?![a-z]* (?:almacenamiento|disco|ssd|hdd))', full_text, re.IGNORECASE)
            if ram_alt_match and 'ram' not in full_text[ram_alt_match.start():ram_alt_match.end()+10]: # Pequeño lookahead
                 specs['RAM_GB'] = int(ram_alt_match.group(1))


        # --- Extracción de Almacenamiento ---
        storage_match = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|m\.2)?', full_text, re.IGNORECASE)
        if storage_match:
            amount = int(storage_match.group(1))
            unit = storage_match.group(2).upper()
            storage_type = storage_match.group(3)
            if unit == 'TB':
                amount *= 1024 # Convertir TB a GB
            specs['Almacenamiento_GB'] = amount
            if storage_type:
                specs['Tipo_Almacenamiento'] = storage_type.upper()
        else: # Intento ambiguo, si no se especifica el tipo (ej. "512GB")
            storage_match_ambiguous = re.search(r'(\d+)\s*(gb|tb)(?!\\s*ram)', full_text, re.IGNORECASE)
            if storage_match_ambiguous and 'ram' not in full_text[storage_match_ambiguous.end()-50:storage_match_ambiguous.end()+50]: # Doble chequeo
                amount = storage_match_ambiguous.group(1)
                unit = storage_match_ambiguous.group(2).upper()
                specs['Almacenamiento'] = f"{amount}{unit}"
        
        # --- Extracción de Procesador (CPU) ---
        # Patrones más específicos para capturar la serie completa
        cpu_match = re.search(r'(intel\\s+core\\s+i\\d+|amd\\s+ryzen\\s*\\d+|intel\\s+core\\s+ultra\\s*\\d+|amd\\s+ryzen\\s+threadripper|apple\\s+(?:m\\d|m\\d\\s+pro|m\\d\\s+max|m\\d\\s+ultra))', full_text, re.IGNORECASE)
        if cpu_match:
            specs['Procesador'] = cpu_match.group(0).replace('intel core', 'Intel Core').replace('amd ryzen', 'AMD Ryzen').replace('intel core ultra', 'Intel Core Ultra').title()

        # --- Extracción de Tarjeta Gráfica (GPU) ---
        # Patrones para tarjetas dedicadas
        gpu_match = re.search(r'(rtx\\s*\\d{3,4}|gtx\\s*\\d{3,4}|radeon\\s*rx\\s*\\d{3,4}|nvidia\\s+geforce|amd\\s+radeon)', full_text, re.IGNORECASE)
        if gpu_match:
            specs['Tarjeta_Grafica'] = gpu_match.group(0).replace('nvidia geforce', 'NVIDIA GeForce').replace('amd radeon', 'AMD Radeon').upper()
        else: # Podría ser un chip integrado si no se encuentra nada dedicado
            integrated_gpu_match = re.search(r'(intel\\s+iris\\s+xe|intel\\s+uhd\\s+graphics|amd\\s+radeon\\s+graphics)', full_text, re.IGNORECASE)
            if integrated_gpu_match:
                specs['Tarjeta_Grafica'] = integrated_gpu_match.group(0).replace('intel', 'Intel').replace('amd', 'AMD').title()

        return specs

    def __del__(self):
        """Cierra el driver de Selenium cuando el objeto scraper es destruido."""
        if self.driver:
            logging.info(f"Cerrando WebDriver de {self.__class__.__name__}.")
            self.driver.quit()

    @abstractmethod
    def search_products(self, query):
        """
        Método abstracto para buscar productos en la tienda.
        Debe ser implementado por cada scraper específico de tienda.
        """
        pass

    @abstractmethod
    def parse_product_page(self, product_url):
        """
        Método abstracto para parsear la página de detalle de un producto individual.
        Debe ser implementado por cada scraper específico de tienda.
        """
        pass

    def _fetch_page_with_selenium(self, url, wait_for_selector=None):
        """
        Obtiene el contenido de una página web usando Selenium.
        Útil para sitios que cargan contenido dinámicamente con JavaScript.
        """
        logging.info(f"[BaseScraper] Usando Selenium para obtener: {url}")
        if not self.driver:
            logging.info("Inicializando WebDriver de Chrome...")
            try:
                # Opciones de Chrome para headless mode y evitar problemas
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # Ejecutar en segundo plano sin UI
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info("WebDriver de Chrome inicializado.")
            except Exception as e:
                logging.error(f"Error al inicializar WebDriver de Chrome: {e}", exc_info=True)
                return None
        
        try:
            self.driver.get(url)
            if wait_for_selector:
                logging.info(f"[BaseScraper] Esperando selector: {wait_for_selector}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                )
            
            # Obtener el HTML después de que la página se haya cargado completamente
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            logging.info(f"Página {url} fetched con Selenium y parseada exitosamente.")
            return soup
        except Exception as e:
            logging.error(f"Error al obtener o parsear la página con Selenium: {url} - {e}", exc_info=True)
            return None

# --- Bloque de prueba (solo para ejecución directa de este archivo, no se ejecuta normalmente) ---
if __name__ == '__main__':
    print("Este es un módulo base. No está diseñado para ejecutarse directamente.")
    print("Para probar scrapers, ejecuta los módulos específicos de tienda (ej. computron.py).")