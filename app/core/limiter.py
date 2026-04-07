from slowapi import Limiter
from slowapi.util import get_remote_address

# Única instancia global del rate limiter para toda la aplicación
limiter = Limiter(key_func=get_remote_address)
