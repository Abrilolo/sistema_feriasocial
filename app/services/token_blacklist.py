# app/services/token_blacklist.py
"""
Servicio de blacklist de tokens JWT para cierres de sesión efectivos.
En producción, esto debería usar Redis o una base de datos.
"""
from datetime import datetime, timedelta
import threading
from typing import Set

# En memoria - para producción usar Redis
_blacklisted_tokens: Set[str] = set()
_cleanup_lock = threading.Lock()


def blacklist_token(token: str) -> None:
    """Añade un token a la blacklist"""
    with _cleanup_lock:
        _blacklisted_tokens.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Verifica si un token está en la blacklist"""
    return token in _blacklisted_tokens


def cleanup_blacklist():
    """Limpieza periódica de tokens expirados (placeholder)"""
    # En implementación real, esto usaría TTL de Redis
    pass
