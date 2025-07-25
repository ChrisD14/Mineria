# config.py

# URLs de las tiendas a scrapear
# Asegúrate de usar las URLs base correctas
STORE_URLS = {
    "la_ganga": "https://laganga.com",
    "computron": "https://www.computron.com.ec",
    "novicompu": "https://www.novicompu.com",
    "bestcell": "https://www.bestcell.com.ec",
    "mobilestore": "https://mobilestore.ec",
}

# Selectores CSS/XPath para cada tienda (esto es solo un EJEMPLO, debes inspeccionarlos)
# Esto ayudará a centralizar la configuración de los selectores, facilitando el mantenimiento.
STORE_SELECTORS = {
    "la_ganga": {
        "product_name": "div.product-title-wrap h1.page-title",
        "product_price": "div.product-rate-price span.price",
        "product_image": "div.product_item_images a.product-image-photo img.product-image-photo",
        "product_overview_container": "div.product.attribute.overview",
        "product_description_text": "div.product.attribute.overview div.value p",
        "product_specs_list": "div.product.attribute.overview div.value ul",
        "search_item_container": "li.item.product.product-item",
        "search_item_name": "strong.product.name.product-item-name", 
        "search_item_link": "strong.product.name.product-item-name a.product-item-link", 
        "search_item_price": "div.price-box.price-final_price span.price-container span.price",
        "search_item_image": "div.product_item_images img",
    },
    "computron": {
        "search_item_container": "article.blog-post-loop", 
        "search_item_name": "h2.entry-title a",
        "search_item_link": "h2.entry-title a",
        "search_item_image": "div.entry-thumbnail-wrapper.psot-thumbnail",
        "product_name": "h1.product_title.entry-title",
        "product_price": "p.price span.woocommerce-Price-amount bdi",
        "product_image": "img.attachment-woocommerce_single.size-woocommerce_single.wp-post-image",
        "product_overview_container": "div.woocommerce-tabs-panel",
        "product_description_text": "div.woocommerce-Tabs-panel--description.panel.entry-content.wc-tab p",
                                    
    },
     "novicompu": {
        "base_url": "https://www.novicompu.com",
        "search_url_format": "https://www.novicompu.com/{}?_q={}&map=ft",
        "listing_product_link_card": "a.vtex-product-summary-2-x-clearLink", # Este es el elemento principal iterable (el enlace <a>)
        "listing_product_article_inside_link": "article.vtex-product-summary-2-x-element", # El <article> DENTRO del enlace <a>
        "listing_product_name": "div.vtex-product-summary-2-x-nameContainer", # Relativo al <article>
        "listing_product_image": "img.vtex-product-summary-2-x-image", # Relativo al <article>
        "listing_product_price": "span.vtex-product-price-1-x-sellingPrice", # Relativo al <article>
        "wait_for_listing_product_card": "a.vtex-product-summary-2-x-clearLink", # Esperar a que aparezca el enlace principal del producto

        # Selectores para PÁGINA DE DETALLE DE PRODUCTO
        "product_name": "h1.vtex-store-components-3-x-productNameContainer",
        "wait_for_product_name": "h1.vtex-store-components-3-x-productNameContainer",  # Mejor que span.brand
        "product_price": "span.vtex-product-price-1-x-sellingPrice",
        "wait_for_product_price": "span.vtex-product-price-1-x-sellingPrice",
        "product_image": "img.vtex-store-components-3-x-productImageTag",
        "product_description_container": "div.vtex-store-components-3-x-description",
        "product_description_text": "div.vtex-store-components-3-x-productDescriptionContainer",
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
        "listing_product_price": None, 

        # Selectores para la página de detalle del producto
        "product_name": "h1.product_title.entry-title",
        # Selector de precio más específico para la página de detalle, basado en image_b7821f.png
        "product_price": "p.price span.woocommerce-Price-amount bdi",
        "product_image": "div.woocommerce-product-gallery__image img, .wp-post-image",
        "product_description_container": "div.woocommerce-product-details__short-description, div.woocommerce-tabs #tab-description",
        "product_description_text": "p",
        "product_specifications_table": "table.woocommerce-product-attributes", # No se ve en las últimas imágenes, pero lo mantenemos por si acaso.
    },
    "bestcell": {
        "base_url": "https://www.bestcell.com.ec",
        "search_url_format": "https://www.bestcell.com.ec/buscar/{}",  # Para query url encoded

        # Listado búsqueda (ya dado antes)
        "wait_for_listing_product_card": "div.col-xl-4.col-lg-4.col-sm-6.mb-3",
        "product_container": "div.col-xl-4.col-lg-4.col-sm-6.mb-3",
        "name": "h2.h6 a.reset-anchor",
        "price": "p > b > span[style*='font-size:1.2rem']",
        "image": "img.img-fluid",

        # Página detalle producto:
        "wait_for_product_name": "div.col-lg-6 h1.h4",   # Esperar que el nombre esté visible
        "product_name": "div.col-lg-6 h1.h4",           # Selector nombre producto
        "wait_for_product_price": "div.col-lg-6 p.lead span.p-2.h4 b",  # Espera precio promo efectivo visible
        "product_price": "div.col-lg-6 p.lead span.p-2.h4 b",           # Precio promo efectivo
        "product_image": "a.d-block > img#IDIMGPrincipal",               # Imagen principal producto

        "product_description_container": "div.col-lg-6 p.text-small.mb-4",  # Descripción corta (p)
        'product_description': 'div.p-4.p-lg-5.bg-white'
        # Puedes agregar más selectores si quieres extraer stock, marca, categoría, etc.
    }
}

# Umbrales para recomendaciones de computadoras
RECOMMENDATION_THRESHOLDS = {
    # Precios máximos para diferentes presupuestos (ej. en USD)
    "low_budget_max_price": 100.00,
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