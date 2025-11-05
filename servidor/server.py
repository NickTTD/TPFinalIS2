"""
server.py - Servidor principal
Integra todos los componentes
"""

import logging
import socket
import threading

from db import DynamoDBProxy
from managers import ObserverManager, SessionManager
from request_handler import RequestHandler
from client_connection import ClientConnection


class SingletonProxyObserverServer:
    """Servidor principal que integra todos los componentes"""
    
    def __init__(self, port: int = 8080, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.running = False
        
        # Componentes principales
        self.proxy = DynamoDBProxy()
        self.observer_manager = ObserverManager()
        self.session_manager = SessionManager()
        self.request_handler = RequestHandler(
            self.proxy, self.observer_manager, 
            self.session_manager, verbose
        )
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Maneja una conexión de cliente en un thread separado"""
        session = self.session_manager.generate_id()
        connection = ClientConnection(
            client_socket, address, 
            self.request_handler, session
        )
        connection.process()
    
    def start(self):
        """Inicia el servidor"""
        self.running = True
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            
            logging.info("="*70)
            logging.info("SingletonProxyObserverTPFI - Servidor iniciado (OOP)")
            logging.info("="*70)
            logging.info(f"Escuchando en puerto: {self.port}")
            logging.info(f"Modo verbose: {'Activado' if self.verbose else 'Desactivado'}")
            logging.info("Tablas DynamoDB: CorporateData, CorporateLog")
            logging.info("="*70)
            logging.info("Esperando conexiones...")
            
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    
                    # Crear thread para manejar el cliente
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                
                except KeyboardInterrupt:
                    logging.info("Deteniendo servidor...")
                    break
                except Exception as e:
                    if self.running:
                        logging.error(f"Error al aceptar conexión: {e}")
        
        finally:
            self.running = False
            server_socket.close()
            logging.info("Servidor detenido.")