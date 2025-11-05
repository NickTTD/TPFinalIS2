"""
managers/session_manager.py - Gestor de sesiones
Patrón Singleton
"""

import threading
import uuid as uuid_lib


class SessionManager:
    """Gestor de sesiones único (Singleton)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SessionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    def generate_id(self) -> str:
        """Genera un ID de sesión único con uuid4(random)"""
        return str(uuid_lib.uuid4())