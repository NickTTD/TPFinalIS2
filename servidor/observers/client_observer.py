#!/usr/bin/env python3
"""
observers/client_observer.py - Observer para clientes
Implementación concreta del patrón Observer
"""

import json
import logging
import socket
from typing import Any, Dict

from .observer import Observer


class ClientObserver(Observer):
    """Observer para clientes suscritos"""
    
    def __init__(self, client_socket: socket.socket, uuid: str):
        self.client_socket = client_socket
        self.uuid = uuid
        self._active = True
    
    def update(self, data: Dict[str, Any]):
        """Envía actualizaciones al cliente suscrito"""
        if not self._active:
            return
        
        try:
            message = json.dumps(data, default=str)
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error al notificar cliente {self.uuid}: {e}")
            self._active = False
    
    def is_active(self) -> bool:
        """Verifica si el observer está activo"""
        return self._active
    
    def close(self):
        """Cierra la conexión del observer"""
        self._active = False
        try:
            self.client_socket.close()
        except:
            pass