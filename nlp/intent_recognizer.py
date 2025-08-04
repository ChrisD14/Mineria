# nlp/intent_recognizer.py
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def recognize_intent(user_prompt: str) -> str:
    """
    Reconoce la intención principal de la consulta del usuario.
    Prioriza intenciones más generales (como 'computadora') sobre componentes específicos si la consulta es sobre un sistema completo.
    Esta función ahora espera un prompt en INGLÉS.
    """
    prompt_lower = user_prompt.lower()
    
    logging.debug(f"Reconociendo intención para: '{prompt_lower}'")

    # *** CAMBIO CLAVE AQUÍ: Buscar palabras clave en inglés para "computadora" ***
    if "computer" in prompt_lower or "laptop" in prompt_lower or "pc" in prompt_lower or \
       "desktop" in prompt_lower or "workstation" in prompt_lower:
        logging.info("Intención detectada: computadora (prioridad alta)")
        return "computadora"
    
    # Si no es una computadora, entonces busca componentes específicos
    # 'ram' es común en ambos idiomas, 'memory' es el término en inglés.
    if "ram" in prompt_lower or "memory" in prompt_lower:
        logging.info("Intención detectada: memoria_ram")
        return "memoria_ram"
    
    # 'storage' y 'disk' son los términos en inglés.
    if "storage" in prompt_lower or "disk" in prompt_lower or \
       "ssd" in prompt_lower or "hdd" in prompt_lower or "nvme" in prompt_lower:
        logging.info("Intención detectada: almacenamiento")
        return "almacenamiento"
    
    # 'printer' es el término en inglés.
    if "printer" in prompt_lower:
        logging.info("Intención detectada: impresora")
        return "impresora"
    
    # Intención por defecto
    logging.info("Intención detectada: desconocido")
    return "desconocido"