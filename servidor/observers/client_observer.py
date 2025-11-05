"""
observers/client_observer.py - Observer para clientes
Implementación concreta del patrón Observer para notificaciones via sockets.
"""

import json
import logging
import socket
from typing import Any, Dict

from .observer import Observer


class ClientObserver(Observer):
    """
    Observer para notificar a clientes suscritos via sockets TCP.
    
    Maneja la comunicación en tiempo real con clientes que reciben
    notificaciones de cambios en el sistema.
    """
    
    def __init__(self, client_socket: socket.socket, uuid: str):
        """
        Inicializa el observer con socket y UUID del cliente.
        
        Args:
            client_socket: Socket conectado al cliente
            uuid: Identificador único del cliente para tracking
        """
        self.client_socket = client_socket
        self.uuid = uuid
        self._active = True
    
    def update(self, data: Dict[str, Any]):
        """
        Envía actualizaciones al cliente suscrito.
        
        Serializa los datos a JSON y los envía a través del socket.
        Si falla, marca el observer como inactivo.
        """
        if not self._active:
            return
        
        try:
            message = json.dumps(data, default=str)
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error al notificar cliente {self.uuid}: {e}")
            self._active = False
    
    def is_active(self) -> bool:
        """Verifica si el observer está activo y puede recibir notificaciones."""
        return self._active
    
    def close(self):
        """Cierra la conexión del observer y libera recursos."""
        self._active = False
        try:
            self.client_socket.close()
        except OSError as e:
            logging.debug(f"Error al cerrar socket del observer {self.uuid}: {e}")