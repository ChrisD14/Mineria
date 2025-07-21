# config.py

# URLs de las tiendas a scrapear
# Asegúrate de usar las URLs base correctas
STORE_URLS = {
    "la_ganga": "https://laganga.com",
    "computron": "https://www.computron.com.ec",
    "marcimex": "https://www.marcimex.com",
    "tecnomegastore": "https://www.tecnomegastore.ec",
    "maxitec": "https://www.maxitec.com.ec",
    "bestpc": "https://bestpc.ec",
    "novicompu": "https://www.novicompu.com",
    "bestcell": "https://www.bestcell.com.ec",
    "mobilestore": "https://mobilestore.ec",
    "nomadaware": "https://nomadaware.com.ec",
}

# Selectores CSS/XPath para cada tienda (esto es solo un EJEMPLO, debes inspeccionarlos)
# Esto ayudará a centralizar la configuración de los selectores, facilitando el mantenimiento.
STORE_SELECTORS = {
    "la_ganga": {
        # Selectores para la PÁGINA DE DETALLE DE PRODUCTO (basado en tu última imagen)
        "product_name": "div.product-title-wrap h1.page-title", # Ajusta el h1.product-name si es diferente
        "product_price": "div.product-rate-price span.price", # Revisa la estructura dentro de product-rate-price
        # Selector para la IMAGEN PRINCIPAL (basado en tu última imagen)
        "product_image": "div.product_item_images a.product-image-photo img.product-image-photo", # Asumo una clase común 'main-product-image' para el <img>
                                                                       
        
        # Selector del contenedor principal de la descripción y las especificaciones
        "product_overview_container": "div.product.attribute.overview",
        # Selector para la descripción detallada (el párrafo)
        "product_description_text": "div.product.attribute.overview div.value p",
        # Selector para el contenedor de la lista de especificaciones (la <ul>)
        "product_specs_list": "div.product.attribute.overview div.value ul", # Dentro del div.value, busca el ul

        # Selectores para la PÁGINA DE RESULTADOS DE BÚSQUEDA (¡AHORA PRECISOS GRACIAS A TUS IMÁGENES!)
        "search_item_container": "li.item.product.product-item", # Este es el <li> individual

        # Selectores DENTRO del "search_item_container" (el <li>)
        "search_item_name": "strong.product.name.product-item-name", # El <strong> que contiene el nombre
        "search_item_link": "strong.product.name.product-item-name a.product-item-link", # El <a> dentro del <strong>
        "search_item_price": "div.price-box.price-final_price span.price-container span.price", # La ruta completa al span del precio

        # Selector para la imagen (este no lo vimos en la última imagen, pero es común)
        # Revisa dentro de cada <li> un <img> o un <div> que lo contenga.
        "search_item_image": "div.product_item_images img", # Ejemplo, VERIFICA ESTE EN EL HTML.
    },
    "computron": {
        # **Selectores para PÁGINA DE RESULTADOS DE BÚSQUEDA (Adaptado a la estructura de 'articles-list')**
        # El contenedor de cada "producto" individual es un <article> con la clase 'blog-post-loop'.
        "search_item_container": "article.blog-post-loop", # Cada <article> es un ítem de búsqueda

        # Ahora, los siguientes selectores DEBEN ser encontrados DENTRO de CADA "article.blog-post-loop"
        # ¡Necesitarás INSPECCIONAR DENTRO de un <article> para obtener los siguientes:!
        # Basado en la captura, parece que hay un h2 o similar para el nombre y un <a> para el link.
        "search_item_name": "h2.entry-title a", # EJEMPLO: Esto es común en temas de WordPress tipo blog/portafolio
        #"search_item_price": "span.price", # EJEMPLO: Habrá que buscar dónde está el precio
        "search_item_link": "h2.entry-title a", # EJEMPLO: A menudo el mismo link del nombre
        "search_item_image": "div.entry-thumbnail-wrapper.psot-thumbnail", # EJEMPLO: O img.attachment-post-thumbnail

         # Selectores para PÁGINA DE DETALLE DE PRODUCTO (¡AHORA PRECISOS GRACIAS A TUS IMÁGENES!)
        "product_name": "h1.product_title.entry-title",
        "product_price": "p.price span.woocommerce-Price-amount bdi",
        "product_image": "img.attachment-woocommerce_single.size-woocommerce_single.wp-post-image",

        "product_overview_container": "div.woocommerce-tabs-panel",
        "product_description_text": "div.woocommerce-Tabs-panel--description.panel.entry-content.wc-tab p", # El <p> dentro del div de descripción
                                    
    },
     "novicompu": {
        "base_url": "https://www.novicompu.com",
        "search_url_format": "https://www.novicompu.com/{}?_q={}&map=ft",

        # Selectores para PÁGINA DE LISTADO (resultados de búsqueda)
        "listing_product_link_card": "a.vtex-product-summary-2-x-clearLink", # Este es el elemento principal iterable (el enlace <a>)
        "listing_product_article_inside_link": "article.vtex-product-summary-2-x-element", # El <article> DENTRO del enlace <a>
        "listing_product_name": "div.vtex-product-summary-2-x-nameContainer", # Relativo al <article>
        "listing_product_image": "img.vtex-product-summary-2-x-image", # Relativo al <article>
        "listing_product_price": "span.vtex-product-price-1-x-sellingPrice", # Relativo al <article>
        "wait_for_listing_product_card": "a.vtex-product-summary-2-x-clearLink", # Esperar a que aparezca el enlace principal del producto

        # Selectores para PÁGINA DE DETALLE DE PRODUCTO
        "product_name": "h1.vtex-store-components-3-x-productBrand", # Basado en tu log y estructura VTEX común
        "product_price": "div.vtex-store-components-3-x-sellingPrice", # El DIV padre que contiene el precio
        "product_image": "img.vtex-store-components-3-x-productImageTag", # Selector de imagen común en páginas de detalle VTEX
        "product_description_container": "div.vtex-store-components-3-x-description", # Contenedor de descripción VTEX común
        "product_description_text": "div.vtex-store-components-3-x-description p", # Párrafos dentro de la descripción
        "product_specifications_table": "table.vtex-store-components-3-x-specificationsTable", # Si existe una tabla de especificaciones
        "wait_for_product_name": "span.vtex-store-components-13-x-productBrand", # Esperar por el nombre del producto
        "wait_for_product_price": "span.vtex-product-price-11-x-sellingPrice" # Esperar por la visibilidad del contenedor del precio
    },
    "mobilestore": {
        "base_url": "https://mobilestore.ec",
        "wait_for_listing_product_card": "article.product",
        "wait_for_product_name": "h1.product_title.entry-title",

        # Selectores para la página de búsqueda (listado de productos)
        "listing_product_card": "article.product",
        "listing_product_link": "a.woocommerce-LoopProduct-link, a.image-result",
        "listing_product_name": "h2.entry-title, h2.woocommerce-loop-product__title",
        "listing_product_image": "a.image-result img, img.wp-post-image, article.product img",
        "listing_product_price": None, # <<--- CRUCIAL: No se espera el precio en la lista

        # Selectores para la página de detalle del producto
        "product_name": "h1.product_title.entry-title",
        # Selector de precio más específico para la página de detalle, basado en image_b7821f.png
        "product_price": "p.price ins",
        "product_image": "div.woocommerce-product-gallery__image img, .wp-post-image",
        "product_description_container": "div.woocommerce-product-details__short-description, div.woocommerce-tabs #tab-description",
        "product_description_text": "p",
        "product_specifications_table": "table.woocommerce-product-attributes", # No se ve en las últimas imágenes, pero lo mantenemos por si acaso.
    }
}

# Umbrales para recomendaciones de computadoras
RECOMMENDATION_THRESHOLDS = {
    # Precios máximos para diferentes presupuestos (ej. en USD)
    "low_budget_max_price": 600.00,
    "medium_budget_max_price": 1200.00,
    "high_budget_max_price": 2500.00, # Puedes ajustar según el mercado de Ecuador

    # RAM mínima sugerida para diferentes propósitos
    "office_ram_min_gb": 8,
    "gaming_ram_min_gb": 16,
    "design_ram_min_gb": 16, # Ajusta a 32 si el diseño es muy pesado

    # Almacenamiento mínimo sugerido para diferentes propósitos
    "office_storage_min_gb": 256, # SSD
    "gaming_storage_min_gb": 512, # SSD
    "design_storage_min_gb": 512, # SSD o 1TB HDD + SSD

    # GPU mínima sugerida para gaming de alto presupuesto (ej. keyword para búsqueda o match)
    "gaming_gpu_min": "RTX 3050", # O ajusta a RTX 4060, RX 7600, etc.
    # Porcentaje de similitud mínimo para una recomendación (0.0 a 1.0)
    "min_score": 0.5,
    "max_results_to_return":5,
}