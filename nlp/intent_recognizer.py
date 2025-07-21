# nlp/intent_recognizer.py

def recognize_intent(user_prompt: str) -> str:
    """
    Reconoce la intención principal de la consulta del usuario.
    En una implementación real, esto podría ser un modelo de clasificación de texto.
    """
    prompt_lower = user_prompt.lower()

    if "computadora" in prompt_lower or "laptop" in prompt_lower or "pc" in prompt_lower or \
       "ordenador" in prompt_lower:
        return "computadora"
    elif "ram" in prompt_lower or "memoria" in prompt_lower:
        return "memoria_ram"
    elif "disco" in prompt_lower or "almacenamiento" in prompt_lower or \
         "ssd" in prompt_lower or "hdd" in prompt_lower or "nvme" in prompt_lower:
        return "almacenamiento"
    elif "impresora" in prompt_lower: # Ejemplo de otra categoría
        return "impresora"
    # Puedes añadir más intenciones aquí
    
    return "desconocido"