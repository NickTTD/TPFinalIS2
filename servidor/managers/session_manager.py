#!/usr/bin/env python3
"""
managers/session_manager.py - Gestor de sesiones
Patrón Singleton
"""

import threading
import uuid as uuid_lib
import platform


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
        # Inicializar datos de CPU
        self._cpu_data = self._get_cpu_data()
    
    def generate_id(self) -> str:
        """Genera un ID de sesión único con uuid4(random)"""
        return str(uuid_lib.uuid4())
    
    def _get_cpu_data(self) -> dict:
        """Obtiene información de la CPU del sistema"""
        return {
            'processor': platform.processor(),
            'machine': platform.machine(),
            'architecture': platform.architecture(),
            'system': platform.system(),
            'platform': platform.platform(),
            'cpu_uuid': hex(uuid_lib.getnode())  # UUID único de la CPU (dirección MAC)
        }
    
    def get_cpu_info(self) -> dict:
        """Retorna la información de CPU almacenada"""
        return self._cpu_data.copy()
    
    def get_cpu_uuid(self) -> str:
        """Retorna el UUID único de la CPU"""
        return self._cpu_data['cpu_uuid']