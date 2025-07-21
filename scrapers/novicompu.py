# scrapers/novicompu.py
import logging
import urllib.parse
from scrapers.base_scrapers import BaseScraper # Asegúrate de que la importación sea correcta
from config import STORE_SELECTORS # Importa los selectores del archivo config.py

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NovicompuScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            base_url="https://www.novicompu.com",
            selectors=STORE_SELECTORS["novicompu"]
        )
        self.store_name = "Novicompu"

    def search_products(self, query):
        search_url = f"{self.base_url}/{urllib.parse.quote(query)}?_q={urllib.parse.quote_plus(query)}&map=ft"
        logging.info(f"--- Probando búsqueda de productos para: '{query}' en {self.store_name} ---")
        logging.info(f"[{self.store_name}] Buscando productos en: {search_url}")

        # *** CAMBIO CLAVE AQUÍ: Usar Selenium y esperar a que el primer producto cargue ***
        # El selector para esperar es el mismo que para la tarjeta de producto
        soup = self._fetch_page(search_url, use_selenium=True, wait_for_selector=self.selectors["listing_product_card"])

        products = []
        if soup:
            product_listings = soup.select(self.selectors["listing_product_card"])

            if not product_listings:
                logging.info(f"[{self.store_name}] No se encontraron listados de productos para la consulta: {query}")
                # Puedes guardar el HTML para depuración si no se encuentran productos
                # with open(f"novicompu_debug_no_products_{query}.html", "w", encoding="utf-8") as f:
                #     f.write(soup.prettify())
                # logging.info(f"HTML guardado en novicompu_debug_no_products_{query}.html para depuración.")
                return []

            logging.info(f"[{self.store_name}] Encontrados {len(product_listings)} productos.")

            for product_soup in product_listings:
                # Asegúrate de que product_soup es el elemento <a> que contiene la URL y el <article>
                name_element = product_soup.select_one(self.selectors["listing_product_name"])
                image_element = product_soup.select_one(self.selectors["listing_product_image"])
                price_element = product_soup.select_one(self.selectors["listing_product_price"])

                name = name_element.get_text(strip=True) if name_element else "N/A"
                relative_url = product_soup.get('href') # Obtener href directamente del <a>
                product_url = urllib.parse.urljoin(self.base_url, relative_url) if relative_url else "#"

                image_url = image_element.get('src') if image_element else "#"
                price = self._clean_price(price_element.get_text(strip=True)) if price_element else None

                if name != "N/A" and product_url != "#" and price is not None:
                    products.append({
                        'name': name,
                        'url': product_url,
                        'image_url': image_url,
                        'price': price,
                        'store': self.store_name
                    })
                else:
                    logging.debug(f"[{self.store_name}] Producto incompleto detectado y omitido: Nombre='{name}', URL='{product_url}', Precio='{price}'")
        else:
            logging.error(f"[{self.store_name}] No se pudo obtener el contenido de la página de búsqueda.")

        logging.info(f"No se encontraron productos para la búsqueda." if not products else f"Búsqueda finalizada. Total de productos encontrados: {len(products)}")
        return products

    def parse_product_page(self, product_url):
        # logging.info(f"[{self.store_name}] Obteniendo detalles para: {product_url}") # Esta línea ya estaba
        
        # Este es el cuerpo del método que tenías para get_product_details
        # No necesitas cambiar nada DENTRO de este método, solo su nombre.
        logging.info(f"[{self.store_name}] Obteniendo detalles para: {product_url}")
        soup = self._fetch_page(product_url, use_selenium=True, wait_for_selector=self.selectors["product_name"]) 
        
        
        details = {}
        if soup:
            name_element = soup.select_one(self.selectors["product_name"])
            price_element = soup.select_one(self.selectors["product_price"])
            image_element = soup.select_one(self.selectors["product_image"])
            
            details['name'] = name_element.get_text(strip=True) if name_element else "N/A"
            details['price'] = self._clean_price(price_element.get_text(strip=True)) if price_element else None
            details['image_url'] = image_element.get('src') if image_element else "#"
            details['url'] = product_url 

            description_container = soup.select_one(self.selectors["product_overview_container"])
            description_text = ""
            if description_container:
                paragraphs = description_container.select(self.selectors["product_description_text"])
                description_text = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if not description_text:
                    description_text = description_container.get_text(strip=True)
            details['description'] = description_text if description_text else "No disponible."

            specs_table = soup.select_one(self.selectors["product_specifications_table"])
            details['specifications'] = self._extract_specs(specs_table) if specs_table else {}
            
            if not details['specifications'] and description_text:
                details['specifications'] = self._extract_specs_from_text(details['description'])

        return details